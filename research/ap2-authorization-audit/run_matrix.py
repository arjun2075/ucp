"""Print the T0-T6 / NC result table (four separate columns per spec:
signature validity, mandate validity, current-state equivalence, decision)
for both verification approaches, using the same pipeline as the tests."""

from __future__ import annotations

import copy
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ap2_audit import complete_checkout, create_checkout_mandate, sign_checkout

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def base():
    return json.loads((FIXTURES / "checkout_a.json").read_text())


def fmt(v):
    return {True: "valid", False: "INVALID", None: "n/a"}[v] if not isinstance(v, str) else v


def run():
    signed = sign_checkout(base())
    mandate = create_checkout_mandate(signed)

    scenarios = {}

    scenarios["T0 no change"] = (copy.deepcopy(signed), mandate)
    c = copy.deepcopy(signed)
    c["fulfillment"]["methods"][0]["selected_destination_id"] = "dest_2"
    scenarios["T1 destination change"] = (c, mandate)
    c = copy.deepcopy(signed)
    c["fulfillment"]["methods"][0]["groups"][0]["selected_option_id"] = "express"
    scenarios["T2 option change (same price)"] = (c, mandate)
    c = copy.deepcopy(signed)
    c["buyer"]["consent"]["dev.ucp.consent.marketing"]["granted"] = True
    c["buyer"]["consent"]["dev.ucp.consent.marketing"]["source"] = "platform"
    scenarios["T3b consent change (session)"] = (c, mandate)
    c = copy.deepcopy(signed)
    c["messages"] = [{"type": "info", "code": "note", "content": "Carrier note added."}]
    c["actions"] = {}
    scenarios["T4 volatile metadata only"] = (c, mandate)
    scenarios["T5 no mandate"] = (copy.deepcopy(signed), None)
    revised = base()
    revised["fulfillment"]["methods"][0]["selected_destination_id"] = "dest_2"
    signed_b = sign_checkout(revised)
    scenarios["T6 revised + re-authorized"] = (
        copy.deepcopy(signed_b),
        create_checkout_mandate(signed_b),
    )
    scenarios["NC2 expired mandate"] = (
        copy.deepcopy(signed),
        create_checkout_mandate(signed, expires_in=-3600, now=int(time.time())),
    )

    print(f"{'scenario':34} {'approach':8} {'sig':8} {'mandate':8} {'state-eq':8} {'decision':8} order-dest")
    print("-" * 118)
    for name, (current, mand) in scenarios.items():
        for cmp_ in ("A", "B"):
            r = complete_checkout(copy.deepcopy(current), mand, comparator=cmp_)
            print(
                f"{name:34} {cmp_:8} {fmt(r.signature_valid):8} {fmt(r.mandate_valid):8} "
                f"{fmt(r.state_equivalent):8} {r.decision:8} {r.order_destination or r.error_code or ''}"
            )
    print()
    print("Approach A = compare only (id, totals, line_items) — ap2-mandates.md L444-445 parenthetical.")
    print("Approach B = compare all signed state except volatile lifecycle fields (status/messages/actions/order/continue_url).")


if __name__ == "__main__":
    run()
