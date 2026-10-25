"""Same-state reissuance: semantic equality does NOT subsume AP2's
latest-artifact (hash) check.

Setup: the merchant signs the SAME checkout content twice, independently.
ES256 (ECDSA) signatures are probabilistic, so the two detached JWS
values differ, both verify, and — once converted to a Checkout JWT via
the RFC 7515 App. F reinsertion (issue #905's proposal) — the two
checkout_jwt strings differ and hash differently.

Delivery interpretation (stated, not assumed): the second signed checkout
is delivered to the platform as a Checkout response artifact (e.g. the
response to a Get Checkout, which businesses sign like every checkout
response under AP2 negotiation, ap2-mandates.md L112-113). On the
"latest = most recent issued signed artifact" reading, the second
artifact is now the latest checkout_jwt for the session.

Results:
- UCP semantic comparators (A and B): the mandate's embedded checkout and
  the current/latest state are semantically EQUAL -> state check passes.
- AP2 latest-JWT hash rule: the mandate's checkout_hash (over the first
  artifact) != hash of the latest checkout_jwt (second artifact) -> the
  AP2 rule REJECTS a semantically identical, fully valid authorization.

Conclusion: the two checks answer different questions (state equivalence
vs artifact freshness/identity). Neither subsumes the other:
- semantic equality does not subsume the latest-artifact check (here);
- the latest-artifact check does not subsume semantic equality
  (test_latest_jwt.py case (i): it is vacuous when state drifts without
  reissuance).
A complete verifier needs both, and UCP currently specifies neither
precisely. A verifier enforcing ONLY the latest-hash rule would also
produce false rejections after harmless re-signing (e.g. a Get that
re-signs identical state) — which is why "latest" needs a definition
tied to state, not merely to issuance order.
"""

from __future__ import annotations

import copy
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ap2_audit import (  # noqa: E402
    checkout_hash,
    checkout_jwt,
    compare_a,
    compare_b,
    complete_checkout_v2,
    create_checkout_mandate,
    sign_checkout,
    verify_merchant_authorization,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def load_checkout() -> dict:
    return json.loads((FIXTURES / "checkout_a.json").read_text())


def test_same_state_two_signatures_differ():
    content = load_checkout()
    signed_1 = sign_checkout(content)
    signed_2 = sign_checkout(content)

    # Byte-identical signed content (everything except the signature).
    body_1 = {k: v for k, v in signed_1.items() if k != "ap2"}
    body_2 = {k: v for k, v in signed_2.items() if k != "ap2"}
    assert body_1 == body_2

    # Both merchant signatures are genuine and verify.
    assert verify_merchant_authorization(signed_1) is True
    assert verify_merchant_authorization(signed_2) is True

    # The detached JWS values differ (probabilistic ECDSA)...
    jws_1 = signed_1["ap2"]["merchant_authorization"]
    jws_2 = signed_2["ap2"]["merchant_authorization"]
    assert jws_1 != jws_2

    # ...so the reconstructed Checkout JWTs differ, and so do their hashes.
    assert checkout_jwt(signed_1) != checkout_jwt(signed_2)
    assert checkout_hash(signed_1) != checkout_hash(signed_2)


def test_semantic_equality_does_not_subsume_latest_check():
    content = load_checkout()
    signed_1 = sign_checkout(content)          # artifact the buyer authorized
    mandate = create_checkout_mandate(signed_1)
    signed_2 = sign_checkout(content)          # reissued, identical content,
                                               # delivered as a later response

    current_state = copy.deepcopy(content)     # live state == authorized state

    # Semantic comparators: EQUAL under both readings of AP2M L443-445.
    assert compare_a(signed_1, current_state) is True
    assert compare_b(signed_1, current_state) is True

    # Full completion with the reissued artifact as "latest":
    r = complete_checkout_v2(
        current_state, mandate, comparator="B", latest_signed_checkout=signed_2
    )
    assert r.signature_valid is True and r.mandate_valid is True
    assert r.state_equivalent is True
    assert r.decision_ucp_only == "accept"
    # AP2 latest-JWT rule, applied mechanically, rejects: hash(latest)
    # is the second signature's hash, not the mandate's checkout_hash.
    assert r.latest_jwt_match is False
    assert r.decision_with_latest == "reject"
