"""UCP AP2 extension-aware authorization verification — test harness.

Implements, faithfully and only, what the pinned specifications describe:

* Merchant authorization: detached JWS (ES256) over
  JCS(RFC 8785)-canonicalized checkout-minus-`ap2`, exactly per the
  pseudocode in UCP `docs/specification/payment/extensions/ap2-mandates.md`
  (commit ba9795a6a1c55dc98ec50032cc124a77fba16750, lines 195-220).
* Checkout mandate: a real SD-JWT+KB (ES256) issued with the `sd-jwt`
  reference implementation (sd-jwt==0.10.4 — the same library the AP2 SDK at
  AP2 commit e1ea56db72a6385bce3e5c1112b3a56ce60acb43 depends on), whose
  disclosed claims are {"vct": "mandate.checkout.1", "checkout": <full
  checkout response including ap2.merchant_authorization>}, as UCP requires:
  "The checkout mandate MUST contain the full checkout response including
  the ap2.merchant_authorization field" (ap2-mandates.md lines 230-232).
  All claims are disclosed (no redaction); signature and key-binding
  verification are fully real. The payment mandate is represented by its
  binding-relevant claims (amount, currency, payee, checkout_hash) signed
  in the same SD-JWT flow — see TEST_MATRIX.md limitations.
* Business verification at complete_checkout, per ap2-mandates.md
  "Business Verification" (lines 411-445), with the final step —
  "Verify Terms Match: Confirm the embedded checkout terms match the
  current session state (id, totals, line items)" — implemented in two
  competing ways (Approach A and Approach B) so their outcomes can be
  compared against the same signed artifacts.

Nothing in this module contacts a network or an upstream repository.
Test keys are fixed, test-only EC P-256 keys in fixtures/keys.json.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import time
from dataclasses import dataclass, field

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)
from jwcrypto.jwk import JWK
from sd_jwt.holder import SDJWTHolder
from sd_jwt.issuer import SDJWTIssuer
from sd_jwt.verifier import SDJWTVerifier

FIXTURE_DIR = __file__.rsplit("/", 1)[0] + "/fixtures"

# ---------------------------------------------------------------- keys


def _load_keys() -> dict[str, JWK]:
    with open(f"{FIXTURE_DIR}/keys.json") as f:
        raw = json.load(f)
    return {name: JWK.from_json(json.dumps(jwk)) for name, jwk in raw.items()}


KEYS = _load_keys()
MERCHANT_KID = "merchant_2026"
PLATFORM_KID = "platform_2026"


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64u_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _ec_priv(jwk: JWK) -> ec.EllipticCurvePrivateKey:
    return jwk.get_op_key("sign")


def _ec_pub(jwk: JWK) -> ec.EllipticCurvePublicKey:
    return jwk.get_op_key("verify")


# ------------------------------------------------- merchant authorization
# Spec pseudocode: ap2-mandates.md lines 197-220 (sign) and 314-337 (verify).


def sign_checkout(checkout: dict, kid: str = MERCHANT_KID) -> dict:
    """Return a copy of `checkout` with ap2.merchant_authorization embedded."""
    out = copy.deepcopy(checkout)
    payload = {k: v for k, v in out.items() if k != "ap2"}
    canonical = rfc8785.dumps(payload)
    header = {"alg": "ES256", "kid": kid}
    encoded_header = _b64u(json.dumps(header, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{_b64u(canonical)}".encode("ascii")
    priv = _ec_priv(KEYS["merchant"])
    der = priv.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    raw = r.to_bytes(32, "big") + s.to_bytes(32, "big")  # JWS ES256 raw r||s
    out["ap2"] = {"merchant_authorization": f"{encoded_header}..{_b64u(raw)}"}
    return out


def verify_merchant_authorization(checkout_with_ap2: dict) -> bool:
    """Verify the detached JWS exactly as the spec pseudocode prescribes."""
    jws = checkout_with_ap2.get("ap2", {}).get("merchant_authorization")
    if not jws:
        return False
    parts = jws.split(".")
    if len(parts) != 3 or parts[1] != "":
        return False
    encoded_header, _, encoded_sig = parts
    try:
        header = json.loads(_b64u_decode(encoded_header))
    except Exception:
        return False
    if header.get("alg") not in ("ES256", "ES384", "ES512"):
        return False
    if header.get("kid") != MERCHANT_KID:
        return False
    payload = {k: v for k, v in checkout_with_ap2.items() if k != "ap2"}
    canonical = rfc8785.dumps(payload)
    signing_input = f"{encoded_header}.{_b64u(canonical)}".encode("ascii")
    raw = _b64u_decode(encoded_sig)
    if len(raw) != 64:
        return False
    r, s = int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")
    der = encode_dss_signature(r, s)
    try:
        _ec_pub(KEYS["merchant"]).verify(der, signing_input, ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False


def checkout_jwt(checkout_with_ap2: dict) -> str:
    """Reinsert the detached payload (RFC 7515 App. F) — the conversion
    proposed by UCP issue #905. Used only to compute checkout_hash."""
    jws = checkout_with_ap2["ap2"]["merchant_authorization"]
    encoded_header, _, encoded_sig = jws.split(".")
    payload = {k: v for k, v in checkout_with_ap2.items() if k != "ap2"}
    return f"{encoded_header}.{_b64u(rfc8785.dumps(payload))}.{encoded_sig}"


def checkout_hash(checkout_with_ap2: dict) -> str:
    return _b64u(hashlib.sha256(checkout_jwt(checkout_with_ap2).encode("ascii")).digest())


# ------------------------------------------------------- checkout mandate
# SD-JWT+KB via the sd-jwt reference implementation (AP2 SDK dependency).

AUD = "merchant.example"
NONCE = "business-nonce-42"


def create_checkout_mandate(
    signed_checkout: dict, *, expires_in: int = 3600, now: int | None = None
) -> str:
    """Platform (issuer) signs; user holder key-binds (+kb) at presentation.

    Returns the SD-JWT+KB presentation string for ap2.checkout_mandate.
    """
    now = int(time.time()) if now is None else now
    claims = {
        "vct": "mandate.checkout.1",
        "checkout": signed_checkout,
        "checkout_hash": checkout_hash(signed_checkout),
        "iat": now,
        "exp": now + expires_in,
    }
    issuer = SDJWTIssuer(
        claims, KEYS["platform"], holder_key=KEYS["user"], sign_alg="ES256"
    )
    holder = SDJWTHolder(issuer.sd_jwt_issuance)
    holder.create_presentation({}, aud=AUD, nonce=NONCE, holder_key=KEYS["user"])
    return holder.sd_jwt_presentation


@dataclass
class MandateResult:
    valid: bool
    error: str | None = None
    embedded_checkout: dict | None = None
    verified_claims: dict | None = None


def verify_checkout_mandate(presentation: str) -> MandateResult:
    """Business-side mandate verification per ap2-mandates.md lines 415-421:
    SD-JWT signature, key binding, and expiration (via sd-jwt verifier)."""
    platform_pub = JWK.from_json(KEYS["platform"].export_public())

    def cb(_iss, _hdr):
        return platform_pub

    try:
        verifier = SDJWTVerifier(
            presentation, cb, expected_aud=AUD, expected_nonce=NONCE
        )
        payload = verifier.get_verified_payload()
    except Exception as e:  # sd-jwt raises several exception types
        return MandateResult(False, error=f"{type(e).__name__}: {e}")
    # Expiration is NOT enforced by sd-jwt's SDJWTVerifier.get_verified_payload
    # (it returns claims after signature/KB checks only). The AP2 SDK adds this
    # check itself (AP2 code/sdk/python/ap2/sdk/sdjwt/chain.py, _validate_times:
    # "Token {i} expired at {exp}"), and UCP requires the business to verify
    # expiration per the AP2 spec — so the harness does it explicitly here.
    exp = payload.get("exp")
    if exp is not None and int(time.time()) > int(exp):
        return MandateResult(False, error=f"mandate_expired: expired at {exp}")
    if payload.get("vct") != "mandate.checkout.1":
        return MandateResult(False, error="mandate_scope_mismatch: vct")
    embedded = payload.get("checkout")
    if not isinstance(embedded, dict) or "ap2" not in embedded:
        return MandateResult(False, error="mandate_scope_mismatch: no checkout")
    if payload.get("checkout_hash") != checkout_hash(embedded):
        return MandateResult(False, error="mandate_scope_mismatch: checkout_hash")
    return MandateResult(True, embedded_checkout=embedded, verified_claims=payload)


# ------------------------------------------------------------- comparison
# Approach A: the literal parenthetical in ap2-mandates.md line 444-445:
# "(id, totals, line items)" — nothing else.

APPROACH_A_FIELDS = ("id", "totals", "line_items")

# Approach B: deep equality (over JCS-canonicalized JSON) of the complete
# signed checkout state, excluding only lifecycle/presentation fields that
# the Checkout specification itself defines as changing across operations:
#   status    — Checkout status lifecycle (checkout/index.md lines 340-400)
#   messages  — per-operation outcome surface (Error Handling)
#   actions   — outstanding-work surface, appears/disappears per operation
#   order     — present only after completion
#   continue_url — handoff URL the spec ties to status
VOLATILE_FIELDS = {"status", "messages", "actions", "order", "continue_url"}


def compare_a(embedded: dict, current: dict) -> bool:
    return all(
        rfc8785.dumps(embedded.get(f)) == rfc8785.dumps(current.get(f))
        for f in APPROACH_A_FIELDS
    )


def compare_b(embedded: dict, current: dict) -> bool:
    e = {k: v for k, v in embedded.items() if k != "ap2" and k not in VOLATILE_FIELDS}
    c = {k: v for k, v in current.items() if k != "ap2" and k not in VOLATILE_FIELDS}
    return rfc8785.dumps(e) == rfc8785.dumps(c)


def diff_fields(embedded: dict, current: dict) -> list[str]:
    """Field-level differences (diagnostics; not a verification method)."""
    keys = set(embedded) | set(current)
    out = []
    for k in sorted(keys):
        if k == "ap2":
            continue
        if rfc8785.dumps(embedded.get(k)) != rfc8785.dumps(current.get(k)):
            out.append(k)
    return out


# --------------------------------------------------------- complete flow


@dataclass
class CompletionResult:
    signature_valid: bool | None  # merchant_authorization in embedded checkout
    mandate_valid: bool
    mandate_error: str | None
    state_equivalent: bool | None  # under the chosen comparator
    differing_fields: list[str] = field(default_factory=list)
    decision: str = "reject"  # "accept" | "reject"
    error_code: str | None = None
    order_destination: str | None = None  # what the order would ship to


def _order_destination(current: dict) -> str | None:
    """Mirror of the samples' order construction: the order's fulfillment
    expectation is built from the CURRENT session's selected destination
    (samples/rest/python/server/services/checkout_service.py,
    complete_checkout, expectation block)."""
    try:
        method = current["fulfillment"]["methods"][0]
        dest = next(
            d for d in method["destinations"] if d["id"] == method["selected_destination_id"]
        )
        return f'{dest["id"]}: {dest.get("street_address")}, {dest.get("address_locality")}'
    except Exception:
        return None


def complete_checkout(
    current_session: dict,
    checkout_mandate: str | None,
    *,
    comparator: str = "B",
) -> CompletionResult:
    """Business verification sequence from ap2-mandates.md lines 411-445.

    1. Enforce negotiation: missing mandate -> mandate_required (T5).
    2. Verify mandate (SD-JWT sig, KB, exp) and extract embedded checkout.
    3. Verify merchant_authorization inside the embedded checkout.
    4. Verify Terms Match against the current session (comparator A or B).
    """
    if checkout_mandate is None:
        return CompletionResult(
            None, False, "mandate_required", None, error_code="mandate_required"
        )
    m = verify_checkout_mandate(checkout_mandate)
    if not m.valid:
        err = (m.error or "").lower()
        if "mandate_expired" in err or "expired" in err:
            code = "mandate_expired"
        elif "mandate_scope_mismatch" in err:
            code = "mandate_scope_mismatch"
        else:
            code = "mandate_invalid_signature"
        return CompletionResult(None, False, m.error, None, error_code=code)
    embedded = m.embedded_checkout
    sig_ok = verify_merchant_authorization(embedded)
    if not sig_ok:
        return CompletionResult(
            False, True, None, None, error_code="merchant_authorization_invalid"
        )
    cmp_fn = compare_a if comparator == "A" else compare_b
    equiv = cmp_fn(embedded, current_session)
    diffs = diff_fields(embedded, current_session)
    if not equiv:
        return CompletionResult(
            True, True, None, False, diffs, error_code="mandate_scope_mismatch"
        )
    return CompletionResult(
        True,
        True,
        None,
        True,
        diffs,
        decision="accept",
        order_destination=_order_destination(current_session),
    )


# ------------------------------------------- latest-checkout-JWT comparison
# Added for the F-1 reconciliation follow-up.
#
# AP2 security_and_privacy_considerations.md L52-53 (commit e1ea56d), under
# the threat "An attacker uses a closed Checkout Mandate with a different
# checkout session": "Merchant MUST verify that `checkout_hash` matches the
# hash of the latest `checkout_jwt`."
#
# AP2 never defines "latest checkout_jwt" elsewhere (the word occurs once
# in the corpus). The only object it can denote, in AP2's model where the
# merchant issues a merchant-signed JWT per checkout (AP2 specification.md
# L126-128) and merchant verification hashes "the Checkout JWT sent for
# approval" (L311-312), is the most recent merchant-signed checkout
# artifact issued for that checkout. In UCP serialization that artifact is
# the latest signed checkout response (businesses MUST include
# merchant_authorization in ALL checkout responses, ap2-mandates.md
# L112-113), converted to a checkout_jwt string via the RFC 7515 App. F
# reinsertion proposed by UCP issue #905 — the conversion this harness
# already uses for checkout_hash.


@dataclass
class CompletionResultV2:
    signature_valid: bool | None
    mandate_valid: bool
    mandate_error: str | None
    latest_jwt_match: bool | None  # AP2 L52-53 check, None if not applicable
    state_equivalent: bool | None  # under the chosen UCP comparator
    differing_fields: list[str] = field(default_factory=list)
    decision_ucp_only: str = "reject"  # comparator A/B + UCP sequence only
    decision_with_latest: str = "reject"  # additionally enforcing AP2 L52-53
    error_code: str | None = None
    order_destination: str | None = None


def complete_checkout_v2(
    current_session_state: dict,
    checkout_mandate: str | None,
    *,
    comparator: str = "A",
    latest_signed_checkout: dict | None = None,
) -> CompletionResultV2:
    """Business completion with the AP2 latest-JWT check tracked separately.

    `current_session_state` is the business's live session record (no `ap2`
    member needed; comparators ignore it). `latest_signed_checkout` is the
    most recent signed checkout artifact the merchant issued for this
    session, or None if the merchant retains none (in which case the AP2
    check cannot be performed and is reported as None, not as a pass).
    """
    if checkout_mandate is None:
        return CompletionResultV2(
            None, False, "mandate_required", None, None,
            error_code="mandate_required",
        )
    m = verify_checkout_mandate(checkout_mandate)
    if not m.valid:
        err = (m.error or "").lower()
        code = (
            "mandate_expired" if "expired" in err
            else "mandate_scope_mismatch" if "scope_mismatch" in err
            else "mandate_invalid_signature"
        )
        return CompletionResultV2(None, False, m.error, None, None, error_code=code)
    embedded = m.embedded_checkout
    sig_ok = verify_merchant_authorization(embedded)
    if not sig_ok:
        return CompletionResultV2(
            False, True, None, None, None,
            error_code="merchant_authorization_invalid",
        )
    # AP2 L52-53: mandate's checkout_hash vs hash of latest checkout_jwt.
    latest_match: bool | None = None
    if latest_signed_checkout is not None:
        latest_match = (
            m.verified_claims.get("checkout_hash")
            == checkout_hash(latest_signed_checkout)
        )
    cmp_fn = compare_a if comparator == "A" else compare_b
    equiv = cmp_fn(embedded, current_session_state)
    diffs = diff_fields(embedded, current_session_state)
    decision_ucp = "accept" if equiv else "reject"
    decision_full = (
        "accept" if (equiv and latest_match is not False) else "reject"
    )
    return CompletionResultV2(
        True,
        True,
        None,
        latest_match,
        equiv,
        diffs,
        decision_ucp_only=decision_ucp,
        decision_with_latest=decision_full,
        error_code=None if equiv else "mandate_scope_mismatch",
        order_destination=_order_destination(current_session_state)
        if decision_ucp == "accept"
        else None,
    )
