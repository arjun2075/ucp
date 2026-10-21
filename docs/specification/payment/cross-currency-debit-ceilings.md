<!--
   Copyright 2026 UCP Authors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
-->

# Cross-Currency Buyer Debit Ceilings

This integration note shows how a Platform can enforce a buyer policy such as
"debit no more than USD 500" when the Checkout total is denominated in another
currency. It applies to payment handlers whose provider can return a firm,
fee-scoped debit guarantee.

This is reference guidance, not a new UCP capability or Core field. The
guarantee contract is provider- and handler-specific. A handler can define its
shape in the handler's own schema and carry or reference the guarantee through
its existing configuration or credential flow. The examples below use the
illustrative namespace `com.example.fx_debit_guarantee`; implementations must
use a namespace they control.

## The decision boundary

Three amounts must remain distinct:

| Amount | Authority | Meaning |
| :----- | :-------- | :------ |
| Checkout total | Business | What the Business charges in the Checkout currency |
| Buyer debit ceiling | Buyer or Platform policy | Maximum permitted final debit in the buyer's account currency |
| Provider guarantee | Payment provider | Maximum debit the provider commits to enforce for one bound payment path |

An indicative exchange-rate estimate is useful for display, but it is not an
enforceable upper bound. A Platform must not convert the buyer's ceiling into a
different currency, add an arbitrary safety margin, or treat an estimate as a
guarantee. If it cannot prove that the selected payment path enforces the
ceiling, it must stop or obtain new buyer authorization.

The decision has three outcomes:

| Provider evidence | Platform decision |
| :---------------- | :---------------- |
| Indicative estimate only | Stop or reauthorize; do not claim the ceiling is enforced |
| Valid, bound, fee-complete guarantee at or below the ceiling | Proceed using exactly the bound Checkout, instrument, and route |
| Missing, expired, invalidated, mismatched, fee-incomplete, or over-limit guarantee | Stop or reauthorize |

## Guarantee contract

A provider-backed guarantee needs enough information to answer all of the
following questions without relying on mutable local state:

1. **What is guaranteed?** A maximum debit amount, currency, and minor-unit
   representation.
2. **What is it bound to?** Checkout identity and revision, authoritative total,
   selected instrument, handler, and payment route.
3. **Which fees are covered?** Provider conversion and processing fees, plus
   issuer fees when the buyer policy requires them. Exclusions must be explicit.
4. **When is it valid?** Guarantee identifier, provider identity, issue time,
   expiry, status, and invalidation state.
5. **Who enforces it?** The provider or other party that applies the ceiling on
   the selected payment path.

The following response is illustrative. It is not a registered UCP schema.

<!-- ucp:example skip reason="Illustrative provider guarantee contract; not a UCP schema" -->
```json
{
  "type": "com.example.fx_debit_guarantee",
  "id": "fxg_01K7A6Q4C9",
  "provider": "Example Payments",
  "status": "firm",
  "issued_at": "2026-10-20T23:55:00Z",
  "expires_at": "2026-10-21T00:05:00Z",
  "invalidated": false,
  "maximum_debit": {
    "amount": 50000,
    "currency": "USD"
  },
  "fee_scope": {
    "included": ["provider", "issuer"],
    "excluded": []
  },
  "binding": {
    "checkout_id": "chk_123",
    "checkout_revision": "7",
    "checkout_total": {
      "amount": 45000,
      "currency": "EUR"
    },
    "instrument_id": "pi_card_1",
    "handler_id": "handler_fx_1",
    "route_id": "route_usd_presentment_1"
  },
  "enforced_by": "Example Payments"
}
```

Amounts are integer minor units. The provider contract must define the currency
exponent it applies; implementations must not compare floating-point converted
values. The guarantee amount and the buyer ceiling must use the same currency.

If issuer fees are outside the guarantee, the Platform cannot describe it as a
complete account-debit ceiling when the buyer policy includes issuer fees. It
may proceed only after the buyer changes that policy or separately authorizes a
defined uncovered amount.

## Integration flow

1. Obtain the authoritative Checkout response and record its identity,
   revision, total amount, and currency.
2. Select the payment handler, instrument, and route that will be submitted.
3. Request a firm guarantee from the provider using the handler-specific
   protocol. A displayed estimate is not a substitute.
4. Validate the guarantee immediately before Checkout completion:
   * status is firm and the guarantee is not invalidated;
   * issue time is not in the future and expiry is strictly after the decision
     time;
   * maximum debit uses the buyer-ceiling currency and does not exceed it;
   * all Checkout, instrument, handler, and route bindings match exactly; and
   * every fee category required by buyer policy is included and not excluded.
5. Submit exactly the bound instrument and route. Any Checkout mutation or
   instrument/route change invalidates the decision and requires a new
   guarantee.
6. If completion fails or returns an unknown outcome, resolve the existing
   attempt idempotently. Do not request a new guarantee and retry blindly: the
   first attempt may already have consumed or applied the guarantee.

The reference evaluator in
[`scripts/fx_debit_ceiling.py`](https://github.com/Universal-Commerce-Protocol/ucp/blob/main/scripts/fx_debit_ceiling.py)
implements the local validation decision. It deliberately does not request a
rate, execute a payment, or assert legal compliance.

## Failure and reauthorization cases

| Condition | Required handling |
| :-------- | :---------------- |
| Checkout total or revision changes | Obtain a new guarantee for the new Checkout state |
| Instrument, handler, or route changes | Obtain a new guarantee for the selected payment path |
| Guarantee expires before submission | Stop and obtain a fresh guarantee |
| Guarantee amount exceeds the buyer ceiling | Obtain buyer authorization for a higher ceiling or select another route |
| Required fee is excluded or not listed | Stop; do not represent coverage as complete |
| Provider rejects or invalidates the guarantee | Stop and surface a recoverable payment choice or authorization flow |
| Payment response is lost | Reconcile idempotently using the existing payment attempt and guarantee identifiers |

Business-side Checkout limits such as the approved payment maximum remain
separate. They constrain what the Business may charge under the Checkout; they
do not prove what the buyer's account will finally be debited after currency
conversion and fees.

## Security considerations

Treat the guarantee as authorization-adjacent payment data. Verify provider
authentication and integrity using the payment handler's trust model, bind the
guarantee to immutable identifiers rather than display strings, and redact
provider references from logs when they could enable replay. A local evaluator
cannot establish that a provider will honor a promise; production integrations
must rely on an authenticated provider contract and enforce the provider's
single-use, replay, and idempotency rules.

## Related work

* [Discussion #925: Guarantee a buyer-currency maximum debit](https://github.com/Universal-Commerce-Protocol/ucp/discussions/925)
* [Proposal #815: Record the Checkout payment maximum and Order payment summaries](https://github.com/Universal-Commerce-Protocol/ucp/issues/815)
* [Proposal #820: Add payment processing policy and reporting](https://github.com/Universal-Commerce-Protocol/ucp/issues/820)
