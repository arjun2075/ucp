"""Print the latest-JWT reconciliation table: for T1/T2 x cases (i)/(ii)/(iii),
cryptographic validity is reported separately from AP2 latest-JWT compliance
and from the UCP comparator decision."""

from __future__ import annotations

import copy
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ap2_audit import complete_checkout_v2, create_checkout_mandate, sign_checkout

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def base():
    return json.loads((FIXTURES / "checkout_a.json").read_text())


def fmt(v):
    return {True: "yes", False: "NO", None: "n/a"}[v]


def run():
    print(f"{'scenario':28} {'case':22} {'sig':5} {'mandate':8} {'latest-JWT':11} {'A-eq':5} {'UCP-only':9} {'+AP2 rule':9}")
    print("-" * 104)
    for name, mutate in (
        ("T1 destination", lambda s: s["fulfillment"]["methods"][0].update(selected_destination_id="dest_2")),
        ("T2 option (same price)", lambda s: s["fulfillment"]["methods"][0]["groups"][0].update(selected_option_id="express")),
    ):
        signed_a = sign_checkout(base())
        mandate_a = create_checkout_mandate(signed_a)
        revised = base(); mutate(revised)
        signed_b = sign_checkout(revised)
        mandate_b = create_checkout_mandate(signed_b)
        cases = (
            ("(i) change, no new JWT", copy.deepcopy(revised), mandate_a, signed_a),
            ("(ii) new JWT, old mandate", copy.deepcopy(revised), mandate_a, signed_b),
            ("(iii) new JWT, new mandate", copy.deepcopy(revised), mandate_b, signed_b),
        )
        for case, current, mand, latest in cases:
            r = complete_checkout_v2(current, mand, comparator="A", latest_signed_checkout=latest)
            print(
                f"{name:28} {case:22} {fmt(r.signature_valid):5} {fmt(r.mandate_valid):8} "
                f"{fmt(r.latest_jwt_match):11} {fmt(r.state_equivalent):5} "
                f"{r.decision_ucp_only:9} {r.decision_with_latest:9}"
            )
    print()
    print("sig/mandate = cryptographic validity of the presented mandate and its embedded merchant signature.")
    print("latest-JWT   = mandate checkout_hash == hash(latest signed checkout)  [AP2 S&P L52-53].")
    print("A-eq         = UCP (id, totals, line_items) comparison vs live state  [AP2M L443-445].")
    print("Case (i): the latest-JWT rule is satisfied vacuously and prohibits nothing.")
    print("Case (ii): validity != compliance — A alone accepts, the AP2 rule rejects.")


if __name__ == "__main__":
    run()
