"""F-1 reconciliation: AP2's latest-checkout-JWT requirement.

AP2 security_and_privacy_considerations.md L52-53 (e1ea56d):
"Merchant MUST verify that `checkout_hash` matches the hash of the
latest `checkout_jwt`."

For both T1 (destination change) and T2 (fulfillment-option change),
three cases:

  (i)   A modeled live state change with NO replacement signed artifact.
        The latest checkout_jwt remains the authorized one, so the
        latest-JWT check passes vacuously. This is a verifier-robustness
        control ONLY: no protocol-permitted UCP transition producing
        that unsigned state divergence has been demonstrated.
  (ii)  Live state changes; the merchant issues a replacement signed
        artifact (in UCP, every checkout response is signed —
        ap2-mandates.md L112-113); the buyer presents the OLD mandate.
        All cryptographic checks on the old mandate still verify, but
        the latest-JWT check FAILS: validity != compliance. Approach A
        alone still accepts — an Approach-A-only merchant violates
        AP2 L52-53 in this branch.
  (iii) Replacement artifact + appropriately authorized replacement
        mandate: every check passes; completion accepts.
"""

from __future__ import annotations

import copy
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ap2_audit import (  # noqa: E402
    complete_checkout_v2,
    create_checkout_mandate,
    sign_checkout,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def load_checkout() -> dict:
    return json.loads((FIXTURES / "checkout_a.json").read_text())


def mutate_destination(state: dict) -> dict:
    state["fulfillment"]["methods"][0]["selected_destination_id"] = "dest_2"
    return state


def mutate_option(state: dict) -> dict:
    state["fulfillment"]["methods"][0]["groups"][0]["selected_option_id"] = "express"
    return state


MUTATIONS = {
    "T1_destination": mutate_destination,
    "T2_option": mutate_option,
}


@pytest.mark.parametrize("mutation_name", list(MUTATIONS))
def test_case_i_change_without_replacement_jwt(mutation_name):
    mutate = MUTATIONS[mutation_name]
    signed_a = sign_checkout(load_checkout())
    mandate_a = create_checkout_mandate(signed_a)
    # Live session record drifts; the merchant issues no new signed
    # artifact, so the latest signed artifact remains signed_a.
    current = mutate(copy.deepcopy(load_checkout()))

    for cmp_ in ("A", "B"):
        r = complete_checkout_v2(
            current, mandate_a, comparator=cmp_, latest_signed_checkout=signed_a
        )
        assert r.signature_valid and r.mandate_valid
        # The latest-JWT requirement is SATISFIED — vacuously: latest ==
        # authorized artifact. It does not compare live state at all.
        assert r.latest_jwt_match is True
        if cmp_ == "A":
            # UCP's narrow comparator accepts this modeled state.
            # The transition producing it is NOT established as
            # protocol-permitted, so this is not a conformance verdict.
            assert r.state_equivalent is True
            assert r.decision_ucp_only == "accept"
            assert r.decision_with_latest == "accept"
            assert r.order_destination.startswith("dest_2" if mutation_name == "T1_destination" else "dest_1")
        else:
            assert r.decision_ucp_only == "reject"


@pytest.mark.parametrize("mutation_name", list(MUTATIONS))
def test_case_ii_new_jwt_old_mandate(mutation_name):
    mutate = MUTATIONS[mutation_name]
    signed_a = sign_checkout(load_checkout())
    mandate_a = create_checkout_mandate(signed_a)
    # State changes AND the merchant issues a replacement signed artifact
    # (e.g. the signed Update response UCP requires for every response).
    revised = mutate(load_checkout())
    signed_b = sign_checkout(revised)
    current = copy.deepcopy(revised)

    r = complete_checkout_v2(
        current, mandate_a, comparator="A", latest_signed_checkout=signed_b
    )
    # Cryptographic validity of the presented mandate is undiminished...
    assert r.signature_valid is True and r.mandate_valid is True
    # ...but compliance with AP2 L52-53 fails: the mandate's checkout_hash
    # is not the hash of the latest checkout_jwt.
    assert r.latest_jwt_match is False
    # Approach A alone still accepts (id/totals/line_items unchanged by
    # both mutations): an A-only merchant is NOT conformant with AP2 here.
    assert r.state_equivalent is True and r.decision_ucp_only == "accept"
    # Enforcing the latest-JWT check rejects.
    assert r.decision_with_latest == "reject"


@pytest.mark.parametrize("mutation_name", list(MUTATIONS))
def test_case_iii_new_jwt_new_mandate(mutation_name):
    mutate = MUTATIONS[mutation_name]
    revised = mutate(load_checkout())
    signed_b = sign_checkout(revised)
    mandate_b = create_checkout_mandate(signed_b)
    current = copy.deepcopy(revised)

    for cmp_ in ("A", "B"):
        r = complete_checkout_v2(
            current, mandate_b, comparator=cmp_, latest_signed_checkout=signed_b
        )
        assert r.signature_valid and r.mandate_valid
        assert r.latest_jwt_match is True
        assert r.state_equivalent is True
        assert r.decision_ucp_only == "accept"
        assert r.decision_with_latest == "accept"


def test_latest_check_unavailable_without_retained_artifact():
    """If the merchant retains no latest signed artifact, the AP2 check
    cannot be performed at all (reported as None, not a pass). Neither
    AP2 nor UCP requires retaining one — the check's input is as
    unguaranteed as its UCP serialization (issue #905)."""
    signed_a = sign_checkout(load_checkout())
    mandate_a = create_checkout_mandate(signed_a)
    current = mutate_destination(copy.deepcopy(load_checkout()))
    r = complete_checkout_v2(
        current, mandate_a, comparator="A", latest_signed_checkout=None
    )
    assert r.latest_jwt_match is None
    assert r.decision_ucp_only == "accept"
