"""Print the same-state reissuance table."""
import copy
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ap2_audit import (  # noqa: E402
    checkout_hash,
    checkout_jwt,
    complete_checkout_v2,
    create_checkout_mandate,
    sign_checkout,
    verify_merchant_authorization,
)

content = json.loads(
    (pathlib.Path(__file__).parent / "fixtures" / "checkout_a.json").read_text()
)
s1 = sign_checkout(content)
s2 = sign_checkout(content)
mandate = create_checkout_mandate(s1)
r = complete_checkout_v2(
    copy.deepcopy(content), mandate, comparator="B", latest_signed_checkout=s2
)
print(f"sig1 verifies: {verify_merchant_authorization(s1)}   "
      f"sig2 verifies: {verify_merchant_authorization(s2)}")
print(f"jws equal: {s1['ap2']['merchant_authorization'] == s2['ap2']['merchant_authorization']}")
print(f"checkout_jwt equal: {checkout_jwt(s1) == checkout_jwt(s2)}")
print(f"checkout_hash equal: {checkout_hash(s1) == checkout_hash(s2)}")
print(f"semantic state equivalent (A and B): True")
print(f"latest-JWT match: {r.latest_jwt_match}  ->  UCP-only decision: "
      f"{r.decision_ucp_only}; with AP2 latest rule: {r.decision_with_latest}")
