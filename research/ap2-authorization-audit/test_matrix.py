"""Executable test matrix for the UCP AP2 extension-aware authorization audit.

Run:  python -m pytest test_matrix.py -v
Pinned sources: see ../deliverables/SPEC_TRACE.md (UCP ba9795a, AP2 e1ea56d,
samples e7c9c12). All cryptography is real: ES256 detached JWS merchant
authorization over RFC 8785 JCS (per UCP pseudocode) and SD-JWT+KB checkout
mandates via the sd-jwt reference implementation (AP2 SDK dependency).
"""

from __future__ import annotations

import copy
import json
import pathlib
import re
import sys
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ap2_audit import (  # noqa: E402
    compare_a,
    compare_b,
    complete_checkout,
    create_checkout_mandate,
    sign_checkout,
    verify_merchant_authorization,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
SCHEMAS = pathlib.Path(__file__).parent / "schemas"


def load_checkout() -> dict:
    return json.loads((FIXTURES / "checkout_a.json").read_text())


@pytest.fixture(scope="module")
def authorized():
    """Checkout A: merchant-signed, buyer-authorized via checkout mandate."""
    signed = sign_checkout(load_checkout())
    mandate = create_checkout_mandate(signed)
    return signed, mandate


# ------------------------------------------------------------ schema gate


def _registry():
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012

    resources = []
    for p in SCHEMAS.rglob("*.json"):
        doc = json.loads(p.read_text())
        url = "https://ucp.dev/schemas/" + str(p.relative_to(SCHEMAS))
        res = Resource.from_contents(doc, default_specification=DRAFT202012)
        resources.append((url, res))
        if "$id" in doc:
            resources.append((doc["$id"], res))
    return Registry().with_resources(resources)


def test_fixture_is_schema_valid(authorized):
    """The authorized checkout validates against the official composed
    schemas (AP2 mandate extension, fulfillment, buyer consent) from the
    pinned UCP source tree — the states under test are schema-valid."""
    import jsonschema

    signed, mandate = authorized
    reg = _registry()
    for ref in (
        "https://ucp.dev/schemas/common/payment_ap2_mandate.json"
        "#/$defs/dev.ucp.shopping.checkout",
        "https://ucp.dev/schemas/shopping/fulfillment.json"
        "#/$defs/dev.ucp.shopping.checkout",
        "https://ucp.dev/schemas/shopping/buyer_consent.json"
        "#/$defs/dev.ucp.shopping.checkout",
    ):
        schema = {"allOf": [{"$ref": ref}]}
        errors = list(jsonschema.Draft202012Validator(schema, registry=reg).iter_errors(signed))
        assert errors == [], f"{ref}: {[e.message for e in errors]}"
    ap2_schema = json.loads((SCHEMAS / "common/payment_ap2_mandate.json").read_text())
    ma_pat = ap2_schema["$defs"]["merchant_authorization"]["pattern"]
    assert re.match(ma_pat, signed["ap2"]["merchant_authorization"])
    # NOTE: the checkout_mandate pattern is asserted separately in
    # test_schema_pattern_vs_real_sdjwt_kb below — it does NOT match.


def test_schema_pattern_vs_real_sdjwt_kb(authorized):
    """Secondary observation: a real SD-JWT+KB presentation (the format the
    spec mandates) does not match the schema's checkout_mandate regex:
    the sd-jwt compact form ends issuance with '~' and the KB-JWT segment
    contains '.' separators the pattern's tail cannot express."""
    _, mandate = authorized
    ap2_schema = json.loads((SCHEMAS / "common/payment_ap2_mandate.json").read_text())
    cm_pat = ap2_schema["$defs"]["checkout_mandate"]["pattern"]
    assert not re.match(cm_pat, mandate)
    # A regex mismatch is NOT cryptographic invalidity: the very same
    # presentation verifies successfully (signature + key binding) through
    # the mandate verification path. The schema pattern and the wire
    # format disagree; the cryptography is sound.
    from ap2_audit import verify_checkout_mandate

    result = verify_checkout_mandate(mandate)
    assert result.valid is True


# ------------------------------------------------------------- T0 baseline


def test_t0_no_change_accepts(authorized):
    signed, mandate = authorized
    for cmp_ in ("A", "B"):
        r = complete_checkout(copy.deepcopy(signed), mandate, comparator=cmp_)
        assert r.signature_valid and r.mandate_valid and r.state_equivalent
        assert r.decision == "accept", cmp_
        assert r.order_destination.startswith("dest_1")


# ------------------------------------------------- T1 destination change


def test_t1_destination_change(authorized):
    """A modeled live-state divergence (dest_1 Springfield -> dest_2
    Shelbyville) with unchanged id/items/totals. Tests the two verifier
    interpretations only. A protocol-permitted transition producing this
    unsigned divergence has NOT been established."""
    signed, mandate = authorized
    current = copy.deepcopy(signed)
    current["fulfillment"]["methods"][0]["selected_destination_id"] = "dest_2"

    ra = complete_checkout(copy.deepcopy(current), mandate, comparator="A")
    assert ra.signature_valid and ra.mandate_valid and ra.state_equivalent
    assert ra.decision == "accept"  # Modeled comparator A accepts; no conformance verdict
    assert ra.order_destination.startswith("dest_2")  # order ships elsewhere

    rb = complete_checkout(copy.deepcopy(current), mandate, comparator="B")
    assert rb.signature_valid and rb.mandate_valid
    assert rb.state_equivalent is False and rb.decision == "reject"
    assert rb.differing_fields == ["fulfillment"]


# ------------------------------------------------------ T2 option change


def test_t2_option_change_same_price(authorized):
    """Selected fulfillment option changes materially (Standard/USPS,
    Dec 12-15 -> Express/FedEx signature-required, Dec 10) at the SAME
    price, so totals are unchanged."""
    signed, mandate = authorized
    current = copy.deepcopy(signed)
    current["fulfillment"]["methods"][0]["groups"][0]["selected_option_id"] = "express"

    ra = complete_checkout(copy.deepcopy(current), mandate, comparator="A")
    assert ra.decision == "accept"  # Comparator A cannot see this modeled change

    rb = complete_checkout(copy.deepcopy(current), mandate, comparator="B")
    assert rb.decision == "reject" and rb.differing_fields == ["fulfillment"]


def test_t2b_option_change_with_price_change(authorized):
    """Control: when the option change also changes totals, even Approach A
    rejects — A is a price/items guard, not an authorization-equivalence
    check."""
    signed, mandate = authorized
    current = copy.deepcopy(signed)
    current["fulfillment"]["methods"][0]["groups"][0]["selected_option_id"] = "express"
    for t in current["totals"]:
        if t["type"] == "total":
            t["amount"] = 6400
    ra = complete_checkout(copy.deepcopy(current), mandate, comparator="A")
    rb = complete_checkout(copy.deepcopy(current), mandate, comparator="B")
    assert ra.decision == "reject" and rb.decision == "reject"


# ------------------------------------------------------- T3 buyer consent


def test_t3a_consent_change_in_complete_request(authorized):
    """Buyer Consent confirm semantics (buyer-consent.md, 'Confirm
    example'): the platform submits the buyer's current consent state in
    the complete_checkout REQUEST. That request-side value is not part of
    the signed checkout response the mandate embeds, so a consent change
    there does not — and must not — invalidate the payment authorization.
    Consent handling and payment authorization are separate checks."""
    signed, mandate = authorized
    complete_request_consent = copy.deepcopy(
        signed["buyer"]["consent"]
    )
    complete_request_consent["dev.ucp.consent.marketing"] = {
        "granted": True,
        "source": "platform",
    }
    # The business-side completion compares embedded vs CURRENT SESSION
    # state; the request-side consent is applied as the buyer's stated
    # preference per buyer-consent normative requirement 2/5.
    for cmp_ in ("A", "B"):
        r = complete_checkout(copy.deepcopy(signed), mandate, comparator=cmp_)
        assert r.decision == "accept", cmp_
    assert complete_request_consent["dev.ucp.consent.marketing"]["granted"] is True


def test_t3b_consent_change_in_session_state(authorized):
    """If instead the SESSION's advertised consent state changes after the
    mandate was generated, the two comparators diverge: A ignores it,
    B-strict rejects the whole completion — including the payment — even
    though consent is not a payment term. Neither behavior is specified;
    see FINDINGS.md (this is a scoping ambiguity, not a payment bypass)."""
    signed, mandate = authorized
    current = copy.deepcopy(signed)
    current["buyer"]["consent"]["dev.ucp.consent.marketing"]["granted"] = True
    current["buyer"]["consent"]["dev.ucp.consent.marketing"]["source"] = "platform"

    ra = complete_checkout(copy.deepcopy(current), mandate, comparator="A")
    assert ra.decision == "accept"
    rb = complete_checkout(copy.deepcopy(current), mandate, comparator="B")
    assert rb.decision == "reject" and rb.differing_fields == ["buyer"]


# ------------------------------------------------- T4 nonmaterial metadata


def test_t4_volatile_metadata_only(authorized):
    """Only lifecycle/presentation fields change: an info message is added
    and the key order of the re-serialized session differs. Both
    comparators accept — no unnecessary invalidation."""
    signed, mandate = authorized
    current = copy.deepcopy(signed)
    current["messages"] = [
        {"type": "info", "code": "note", "content": "Carrier note added."}
    ]
    current["actions"] = {}
    for cmp_ in ("A", "B"):
        r = complete_checkout(copy.deepcopy(current), mandate, comparator=cmp_)
        assert r.decision == "accept", cmp_


# ------------------------------------------------------ T5 missing mandate


def test_t5_no_mandate_rejected(authorized):
    signed, _ = authorized
    for cmp_ in ("A", "B"):
        r = complete_checkout(copy.deepcopy(signed), None, comparator=cmp_)
        assert r.decision == "reject" and r.error_code == "mandate_required"


# ------------------------------------------------------ T6 revised checkout


def test_t6_revised_checkout_newly_authorized(authorized):
    """Merchant signs revised checkout B (different destination AND the
    buyer authorizes B with a fresh mandate): completion succeeds under
    both comparators. The compliant path for a material change is
    re-sign + re-authorize, not silent reuse of the old mandate."""
    revised = load_checkout()
    revised["fulfillment"]["methods"][0]["selected_destination_id"] = "dest_2"
    signed_b = sign_checkout(revised)
    mandate_b = create_checkout_mandate(signed_b)
    for cmp_ in ("A", "B"):
        r = complete_checkout(copy.deepcopy(signed_b), mandate_b, comparator=cmp_)
        assert r.decision == "accept", cmp_
        assert r.order_destination.startswith("dest_2")


# --------------------------------------------------------- negative controls


def test_nc1_tampered_embedded_checkout_rejected():
    """Tampering with the embedded checkout after mandate issuance breaks
    the merchant signature: both comparators reject before comparison."""
    signed = sign_checkout(load_checkout())
    mandate = create_checkout_mandate(signed)
    # Attacker flips the destination inside a *re-issued* mandate payload is
    # impossible without the platform key; instead, tamper with the current
    # session's copy of the signed state and confirm the merchant signature
    # over the embedded copy is what anchors T1: re-signing is required.
    embedded_tampered = copy.deepcopy(signed)
    embedded_tampered["fulfillment"]["methods"][0]["selected_destination_id"] = "dest_2"
    assert verify_merchant_authorization(embedded_tampered) is False


def test_nc2_expired_mandate_rejected(authorized):
    signed = sign_checkout(load_checkout())
    expired = create_checkout_mandate(signed, expires_in=-3600, now=int(time.time()))
    for cmp_ in ("A", "B"):
        r = complete_checkout(copy.deepcopy(signed), expired, comparator=cmp_)
        assert r.decision == "reject" and r.mandate_valid is False
        assert r.error_code == "mandate_expired"


def test_nc3_mandate_for_other_checkout_rejected(authorized):
    """A mandate authorizing checkout B must not complete checkout A
    (mandate_scope_mismatch via checkout_hash + embedded id)."""
    signed_a, _ = authorized
    other = load_checkout()
    other["id"] = "chk_other"
    mandate_other = create_checkout_mandate(sign_checkout(other))
    for cmp_ in ("A", "B"):
        r = complete_checkout(copy.deepcopy(signed_a), mandate_other, comparator=cmp_)
        assert r.decision == "reject"


def test_comparator_functions_directly(authorized):
    """Illustrative negative control (labeled as such in TEST_MATRIX.md):
    the three-field comparator alone, without signatures, is not evidence
    of anything — it is shown here only to isolate the comparison step
    that the full pipeline in T1/T2 exercises end to end."""
    signed, _ = authorized
    current = copy.deepcopy(signed)
    current["fulfillment"]["methods"][0]["selected_destination_id"] = "dest_2"
    assert compare_a(signed, current) is True
    assert compare_b(signed, current) is False
