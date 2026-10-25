# UCP AP2 authorization-equivalence reproducer

**Independent specification-model reproducer. This is not a reported defect
in any production merchant implementation, and it does not demonstrate a
vulnerability in any deployed system.** No official UCP sample implementing
AP2 checkout completion was identified during the audit this reproducer
supports; the completion pipeline here is a faithful re-implementation of
the verification sequence written in the UCP AP2 Mandates specification,
built so that two readings of one normative sentence can be compared
executably.

## The question

UCP's AP2 Mandates extension, *Business Verification*, ends with:

> **Verify Terms Match:** Confirm the embedded checkout terms match the
> current session state (id, totals, line items).
> — `docs/specification/payment/extensions/ap2-mandates.md`, UCP commit
> `ba9795a6a1c55dc98ec50032cc124a77fba16750`

The merchant signature covers the *complete* checkout, including
extension-defined fields such as the Fulfillment extension's
`selected_destination_id` and `selected_option_id`. Does the parenthetical
`(id, totals, line items)` exhaust the completion-time comparison, or
illustrate it? This reproducer implements both readings:

- **Approach A** — compare only `id`, `totals`, `line_items`.
- **Approach B** — compare every field covered by `merchant_authorization`
  (the complete checkout except `ap2`), excluding only volatile lifecycle
  fields (`status`, `messages`, `actions`, `order`, `continue_url`).

## What is real and what is modeled

Real cryptography and real formats:

- Merchant authorization: ES256 detached JWS over the RFC 8785 (JCS)
  canonicalization of the checkout minus `ap2`, implemented line-for-line
  from the specification's pseudocode, using `cryptography`.
- Checkout mandate: a real SD-JWT+KB presentation produced and verified
  with the `sd-jwt` reference implementation (the same library the AP2 SDK
  depends on), with signature, key binding, audience, nonce, and explicit
  expiration checks.
- Fixtures validate with zero errors against the official UCP schemas
  (vendored under `schemas/`, unmodified, from the pinned commit below).

Modeled, and labeled as such:

- The business completion pipeline is a **specification model**, not an
  official or deployed server: no shipped implementation of this path was
  found to run.
- The payment mandate is represented by its binding-relevant claims, not
  as a second complete SD-JWT chain.
- UCP never defines the `checkout_jwt` string AP2 binds by hash; where a
  test needs one, it uses the RFC 7515 Appendix F reinsertion of UCP's
  detached JWS proposed in
  [UCP #905](https://github.com/Universal-Commerce-Protocol/ucp/issues/905).

## Findings the tests support

1. Under Approach A, a mandate remains acceptable after the selected
   fulfillment destination (or a same-price fulfillment option) changes;
   under Approach B it is rejected. The signed artifact is never tampered
   with — the difference is purely which fields the verifier compares.
2. The state-divergence cases are exercised in two branches. Where the
   change arrives via an Update Checkout, the business returns a new
   signed checkout response; AP2's "latest `checkout_jwt`" rule
   (AP2 `docs/ap2/security_and_privacy_considerations.md`, commit
   `e1ea56db72a6385bce3e5c1112b3a56ce60acb43`) then rejects the old
   mandate, while UCP's own verification sequence — which never mentions
   that check — accepts it under Approach A. A divergence with *no*
   replacement signed response is **not** established as a
   protocol-permitted transition (every protocol-visible UCP state change
   flows through a Checkout response); it is retained in the tests only as
   a verifier-robustness case and an open question, not as a conformance
   result.
3. Semantic state equality and AP2's latest-artifact hash check are
   independent: re-signing byte-identical checkout content produces a
   different Checkout JWT and hash (ES256 is probabilistic), so the
   latest-artifact check can reject a semantically identical, fully valid
   authorization, and it is vacuous when state drifts without reissuance.
   Neither check subsumes the other.
4. Separately, the official schema's `checkout_mandate` regex does not
   match a real SD-JWT+KB presentation — while that same presentation
   verifies cryptographically. A pattern mismatch is not cryptographic
   invalidity. This is tracked upstream as
   [UCP #599](https://github.com/Universal-Commerce-Protocol/ucp/issues/599);
   it is not claimed here as a new issue.

Related upstream context:
[#905](https://github.com/Universal-Commerce-Protocol/ucp/issues/905)
(Checkout JWT serialization — not duplicated here),
[#827](https://github.com/Universal-Commerce-Protocol/ucp/issues/827)
(cross-boundary projection contract),
[#599](https://github.com/Universal-Commerce-Protocol/ucp/issues/599)
(schema pattern).

## Run it

```sh
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
./venv/bin/python -m pytest -q        # expected: 24 passed, 0 skipped
./venv/bin/python run_matrix.py       # original T0-T6 / NC tables
./venv/bin/python run_latest_jwt.py   # latest-JWT branch table
./venv/bin/python run_reissuance.py   # same-state reissuance table
```

## Pinned sources

| Source | Commit |
|---|---|
| Universal-Commerce-Protocol/ucp | `ba9795a6a1c55dc98ec50032cc124a77fba16750` |
| Universal-Commerce-Protocol/samples | `e7c9c124864108cbb35e5102beeac9cbef80a154` |
| google-agentic-commerce/AP2 | `e1ea56db72a6385bce3e5c1112b3a56ce60acb43` |

Dependencies are pinned in `requirements.txt` (notably `sd-jwt==0.10.4`,
matching the AP2 SDK's own pin).

## Test keys

`fixtures/keys.json` contains fixed EC P-256 keys generated solely for
this reproducer so results are reproducible. They are **test-only**,
protect nothing, and are unrelated to any real account or service. Do not
reuse them for anything else.

## License and attribution

Code in this repository is released under the Apache License 2.0 (see
`LICENSE`). The JSON schemas under `schemas/` are unmodified copies from
the Universal Commerce Protocol repository at the pinned commit above,
© the UCP contributors, likewise Apache License 2.0. The harness design
follows the signing/verification pseudocode in UCP's AP2 Mandates
specification and uses the AP2 project's `sd-jwt` dependency; no other
upstream code is copied.
