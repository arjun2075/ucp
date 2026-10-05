# Experimental price-on-request catalog prototype

This branch is a research prototype for [UCP #877](https://github.com/Universal-Commerce-Protocol/ucp/issues/877).
It is **not approved UCP behavior** and is not an upstream implementation PR.

Credits: evoleinik supplied the use case and implementation observations;
juanferrub proposed the pricing-mode object. Arjun Garg prepared this prototype.
Buyer-specific and contract-only semantics, enum extensibility, release
classification and cache isolation remain design decisions for the EP process.

**Current prototype position (2026-10-05, second pass):**
- `buyer_specific`: priced response retains `mode` (not reverted to `public`).
- `contract_only`: resolved — the unresolved stranger → entitled buyer
  transition uses `buyer_specific`; `price` is forbidden on `contract_only`
  itself (a genuinely unpriced state). This replaces the prior round's
  "`contract_only` stays an explicit open design question" framing.
- `mode` vocabulary: open, with a conservative unknown-mode fallback.
- `next_step`: retained and allowed beside a numeric `price`; workflow
  semantics intentionally not defined.
- Cache isolation: a normative behavioral requirement for `buyer_specific`
  pricing, including anything derived from it (e.g. `price_range`).
- Purchase Options (#901): a newly identified composition surface,
  documented in DESIGN.md §2D; not yet implemented, and not resolved by this
  prototype.

Base: `b0e81adecf816a1771b736464f17586d76950f7f`.
The six schema/spec modifications are in their normal repository paths.
[Design](DESIGN.md), [compatibility](COMPATIBILITY.md), [source map](SOURCE_MAP.md)
and [unsent submission-ready EP draft](EP_SUBMISSION_DRAFT.md) describe the candidate.

## Run the schema checks

From the root of a clone of this branch:

```bash
python3 -m venv /tmp/ucp-por-venv
/tmp/ucp-por-venv/bin/pip install jsonschema==4.10.3
git worktree add --detach /tmp/ucp-por-baseline b0e81adecf816a1771b736464f17586d76950f7f
/tmp/ucp-por-venv/bin/python research/price-on-request/harness/run.py \
  --baseline /tmp/ucp-por-baseline --proposed "$PWD" --skip-sdk --fuzz 300
```

The schema harness contains 42 fixture vectors (28 from the original
publication, plus 14 added across the two 2026-10-05 maintainer-feedback
passes) plus 300 generated priced variants and 300 generated priced products,
plus a pricing-mode fuzz leg (Leg G) of 300 variants and 300 mixed-mode
products. Generated cases cover that subset only; they do not prove universal
compatibility. The candidate rejects some payloads accepted by the baseline,
including conflicting or unknown `pricing` values — including, again as of
2026-10-05 (second pass), `contract_only` + a numeric `price`.

The SDK leg is explicitly skipped above. To run it, install Pydantic and pass
`--sdk` pointing to the pinned Python SDK clone; see [harness documentation](harness/README.md).
JS SDK evidence is static corroboration only. Repository schema lint, example
validation, SDK generation and strict docs checks remain incomplete; this
publication does not claim these checks passed. Historical results were
self-reviewed; no maintainer or TC endorsement is claimed.

## Publication verification

On 2026-10-02 the schema-only harness was rerun against pinned upstream schema
files and the applied patch: 28/28 fixtures passed, and 300 generated variants
plus 300 generated products had zero mismatches (exit 0). SDK checks were skipped.
See [raw output](logs/publication-schema-check.log). This was another agent check,
not independent human validation.

## Follow-through evidence (2026-10-02)

The schema/spec candidate is unchanged from `6fee350`. This follow-up publishes
8 additional fixtures, the expanded compatibility matrix, formal EP filing draft,
and [verification results](VERIFICATION_RESULTS.md) with the canonical raw logs.
Schema lint and strict docs build passed in the research agent's environment;
live JS SDK validation passed 3/3. Example validation ran but failed: baseline
376 passed/0 failed; patched 374 passed/3 failed. All three failures are caused
by the candidate/scaffold interaction. SDK generation remains blocked, and logs
also show conditional rules being skipped. No new generated-model enforcement
is claimed. The EP is **unfiled** and no upstream implementation PR is open.

The published log subset contains the successful checks and canonical failures.
Superseded environment failures and installation logs remain in the Drive
handoff. Paths in historical logs identify the research agent's workspace.
Those historical runs were not independently rerun by the publishing agent;
only the expanded schema harness was rerun for this publication.

Expanded publication rerun: 28/28 fixtures, 300 variants + 300 products with zero
mismatches, exit 0; SDK skipped. See [raw output](logs/publication-followthrough-schema-check.log).

## Maintainer feedback incorporated (2026-10-05)

Following feedback attributed to evoleinik and juanferrub, this update makes
these changes to the schema candidate and its prose (details in
[DESIGN.md](DESIGN.md), [COMPATIBILITY.md](COMPATIBILITY.md), and the
[EP draft](EP_SUBMISSION_DRAFT.md)):

- **`pricing.mode` is now an open vocabulary**, not a closed enum. The four
  well-known values (`public`, `buyer_specific`, `quote_required`,
  `contract_only`) are documented as `examples`; `mode` itself is a
  non-empty string with no enumerated restriction. A future Business can
  introduce a new mode without an older schema-validating consumer rejecting
  the whole payload.
- **Explicit safe unknown-mode fallback behavior is documented.** An
  unrecognized `mode` value does not make a payload invalid, but a Platform
  that doesn't recognize it MUST treat the item conservatively — no usable
  display price, excluded from numeric price filtering/sorting/ranking. This
  is a behavioral/protocol requirement that JSON Schema cannot itself
  enforce; it binds consumer display and filtering logic, not the wire shape.
- **Priced `buyer_specific` responses retain their mode as the proposed
  normative behavior**, not merely one of two previously-unresolved
  interpretations. `{"pricing": {"mode": "buyer_specific"}, "price": {...}}`
  is now stated as the resolved shape for a recognized caller, directly
  supported by evoleinik's reported live-implementation behavior.
- **Caller-isolation/cache requirements for buyer-specific prices — and
  values derived from them, explicitly including a product's `price_range`
  computed from buyer-specific variant prices — are now explicit normative
  MUST language**, not just a noted risk. Again, this is a protocol/behavioral
  requirement the prototype documents and demonstrates with fixtures; JSON
  Schema cannot verify that a cache actually isolates by caller.
- **Both the public-price and identify-first `contract_only` scenarios are
  documented** (Scenario A / Scenario B in DESIGN.md §2B), with fixtures for
  each state. At this point in the thread, `contract_only`'s entitled-caller
  representation was left an open design question — the schema was
  relaxed (permitting, not requiring, `price` alongside `contract_only`)
  specifically so both candidate representations stayed schema-valid while
  the maintainers decided. **This relaxation was superseded by later
  maintainer feedback — see "`contract_only` resolved" below.** `contract_only`
  represents an unresolved entitlement-gated response and does not carry
  `price`. Once pricing is resolved for an entitled caller, the response
  transitions to `buyer_specific` and may include the resolved price. Formal
  upstream adoption of this behavior still requires EP/TC review, but the
  prototype's current semantics are settled, not open.
- **Caller-specific product `price_range` handling is documented**: a mixed
  product's `price_range` must be computed only over priced variants (never
  zero-filled for an unpriced one), and a `price_range` derived from
  buyer-specific variant prices carries the same cache-isolation requirement
  as the underlying prices.

The fixture matrix grew from 28 to **36 vectors** (8 added for this update),
and a new harness leg (Leg G, `harness/run.py`) fuzzes 300 variants and 300
mixed-mode products crossing every known mode, `pricing` absent, and several
future-looking unknown modes (`negotiated_tier`, `auction_pending`,
`dynamic_offer`, `partner_price_v2`) with price absent/present. Rerun on
2026-10-05: 36/36 fixtures, 300+300 differential fuzz (Leg E) and 300+300
pricing-mode fuzz (Leg G), all 0 mismatches, exit 0.

As before: fixture and generative results demonstrate the tested sample only,
not universal compatibility, and schema/fixture validation is distinct from
the behavioral/protocol requirements (cache isolation, price-filter
treatment of unknown modes) described above — those bind consumer and
Platform behavior and cannot themselves be checked by `jsonschema`.

## `contract_only` resolved — second maintainer-feedback pass (2026-10-05)

New maintainer guidance **resolves** `contract_only` in favor of the
per-caller transition, **reversing** the relaxation described in the section
above:

```
Anonymous, public price available       -> mode: public + price
Anonymous, price restricted to callers  -> mode: contract_only, no price
Entitled/recognized customer            -> mode: buyer_specific + price
```

`contract_only` is once again a genuinely unpriced state — `price` MUST NOT
be present with it, exactly as with `quote_required`. The schema's rule 1
("forbid price") `if` condition is restored from `const: quote_required` back
to `enum: ["quote_required", "contract_only"]`, matching the original
pre-prototype structure (not a closed enum on `mode` itself — only this
rule's two known literal checks). `contract_only` and `buyer_specific` now
carry a coherent, distinct meaning: `contract_only` describes the unresolved
response to a caller who has not established entitlement; `buyer_specific`
describes the response after the Business has resolved pricing in the
current buyer context.

This update also:
- Adds fixtures for both anonymous postures (`public_with_price.json`,
  `contract_only_without_price.json`) and documents explicitly that
  `pricing.mode` describes the pricing state of this representation **for
  this caller**, not an immutable classification of the SKU.
- Keeps `buyer_specific` + `price` + `next_step: request_quote` as a
  first-class NDA deployment fixture
  (`buyer_specific_with_price_and_quote_step.json`), clarifying that
  `next_step` never participates in the conditional `price` rules.
  Documents `next_step`'s orthogonality precisely (DESIGN.md §2C), adding a
  `public` + `price` + `request_quote` fixture to test the model is
  genuinely orthogonal rather than accidentally NDA-specific, while keeping
  `quote_required` + `price` + `request_quote` invalid.
- Replaces "carries a numeric price" with **"range-eligible price"** for
  `price_range`/`price_filter` purposes, since an unknown `mode` may legally
  coexist with a numeric `price` — adds a mixed-product fixture
  (`onrequest_product_unknown_mode_mixed.json`) demonstrating the schema-valid
  shape, with the Platform-side eligibility judgment documented as prose.
- Adds a new DESIGN.md §2D treating the concurrent draft issue #901
  (Purchase Options) as a composition problem: documented in prose only (no
  schema file or property added for `purchase_options`), explicitly kept out
  of the harness's counted pass/fail legs, and flagged for the #901
  author/maintainers before incorporation.
- Flips `onrequest_variant_contract_only_priced.json`'s expected verdict from
  valid to **invalid**, and updates its note accordingly.

The fixture matrix grew from 36 to **42 vectors** (6 added, 1 flipped) for
this pass; harness leg G's expected-verdict helper was corrected so
`contract_only` forbids `price` again. Rerun: 42/42 fixtures, 300+300
differential fuzz (Leg E) and 300+300 pricing-mode fuzz (Leg G), all 0
mismatches, exit 0. See the dated log under [`logs/`](logs/) for this round's
raw output.

As always: this is prototype behavior pending formal EP/TC adoption, and the
fixture/fuzz evidence demonstrates the tested sample only, not universal
compatibility.
