# DESIGN — representation comparison, prototype, and design decisions

Condensed from `work/w2-representation.md` (+ `work/exp-por/`) and
`work/w3-prototype.md`. All schema behavior below is **PROPOSED**; released text is
labeled as such.

> **UPDATED 2026-10-05 (second pass) — `contract_only` RESOLVED, reversing the
> prior round's schema relaxation.** Per new maintainer guidance, `contract_only`
> is now a genuinely unpriced state again: `price` MUST NOT be present with
> `contract_only` (the "forbid price" `allOf` rule in `variant.json` is restored
> to cover both `quote_required` and `contract_only`). The prior round's relaxation
> — which let `price` be present or absent with `contract_only` as an "open design
> question" — is reverted. See §2B (replaced), §2C (new, `next_step` orthogonality),
> and §2D (new, composition with Purchase Options #901) below. This remains
> prototype behavior pending EP/TC adoption; it is no longer testing three
> competing alternatives for `contract_only`.

## 1. Representation comparison

Three approaches were evaluated (Worker 2; extension-refutation executed with
`jsonschema` 4.10.3, draft 2020-12, on verbatim schema copies):

| Dimension | (a) pricing-status field | (b) discriminated union on `price` | (c) vendor-extension assertion |
|---|---|---|---|
| Mechanics | Clean: `if`/`then`/`else` + status field (executed) | Clean: `oneOf` (executed) | **Refuted by execution**: `allOf` is conjunction; an extension's `required: []` cannot retract the base's `required: ["price"]`; explicit-on-request and accidental-omission fail identically |
| Old validating consumers | New priceless payloads stay invalid — safe direction | Old validators see `{"on_request": true}` and report confusing union errors; hand-rolled `price.amount` readers crash | Both fail-closed but indistinguishable from data corruption |
| `amount: 0` = free | Preserved (orthogonal axis) | Preserved | N/A |
| Accidental-missing vs explicit-on-request | Distinguishable by validation | Distinguishable | **Not distinguishable** (executed) |
| Consumer ergonomics | `price: Price` untouched | Changes the shape of the most-consumed field; every consumer branches | — |

**Worker 2 recommended (a) as a string field** (`pricing: "on_request"`, open
vocabulary). **The prototype supersedes this with juanferrub's object form**
(`{"pricing": {"mode", "reason"?, "next_step"?}}`, originally a closed enum,
**now (2026-10-05) an open vocabulary on `mode` itself — see §2**) — see §2 for
why the object form was chosen over the string. The validated mechanism
(conditional requiredness) transfers unchanged; only the marker's shape
changed. (b) remains the runner-up; (c) is refuted.

## 2. Chosen prototype

**UPDATED 2026-10-05 following maintainer feedback (evoleinik, juanferrub) — see
§2A/§2B and the dated note at the end of this section.** `pricing` — optional
**object** on catalog Variant:

- `mode` (required): string, **open vocabulary** (no longer a closed enum —
  see the dated note). Well-known values, documented as `examples` in the
  schema: `public` | `buyer_specific` | `quote_required` | `contract_only`. A
  Business MAY introduce new values; a Platform MUST tolerate values it does
  not recognize.
- `reason` (optional string): Business-defined, informational (e.g.
  `contract_or_volume_dependent`); consumers MUST NOT infer semantics beyond `mode`
- `next_step` (optional string): well-known value `request_quote`; informational only —
  defines no quote/RFQ/identity-linking workflow

Conditional requiredness (`allOf`, draft 2020-12):
- `pricing` absent or `mode: public` → `price` REQUIRED (status quo, fail-closed default)
- `mode: quote_required` → `price` MUST NOT be present (conflicting price +
  no-price assertion is rejected). This is a KNOWN-mode rule, scoped
  specifically to `quote_required`.
- `mode: contract_only` → `price` MUST NOT be present (**RESOLVED
  2026-10-05, reversing the prior round's relaxation**; see §2B —
  `contract_only` is a genuinely unpriced state describing the unresolved
  response to a caller who has not established the necessary entitlement;
  the resolved/entitled response transitions to `buyer_specific` + `price`
  instead)
- `mode: buyer_specific` → `price` optional: present for a recognized buyer, absent
  for an anonymous caller — **mode describes *this response*, not a fixed variant
  property** (evoleinik's caller-dependence lesson, encoded). When a price is
  present, `mode` MUST remain `buyer_specific` (see §2A — this is now the
  proposed normative behavior, not an open question).
- An unrecognized/unknown `mode` → `price` MAY be absent or present; no rule
  constrains it (see the dated note below and §4's resolved former-open-item).
  Empty `pricing: {}`, `pricing: null`, and the string form
  `"pricing": "on_request"` remain rejected — these are malformed-shape
  rejections (`pricing` must be a well-formed object with a non-empty string
  `mode`), unrelated to the open-vocabulary change to `mode`'s value space.

### Dated note (2026-10-05): `mode` is now an open vocabulary

Following feedback from evoleinik and juanferrub, `mode`'s closed `enum` was
removed. `mode` is now an ordinary non-empty string (`minLength: 1`) with the
four well-known values moved into the schema's `examples` and documented as
an open vocabulary in the `description`. This is **not** a disguised closed
enum: there is no regex restricting values to the known set. Rationale: a
future producer must be able to introduce a new pricing mode (for example
`negotiated_tier` or `auction_pending`) without an older schema-validating
consumer rejecting the whole payload. This also means a generated SDK's
binding for `mode` must preserve unknown string values rather than failing
deserialization on an unrecognized enum member — codegen tooling that binds
`mode` to a closed language enum needs to represent it as an open/extensible
string type instead (see COMPATIBILITY.md's new third compatibility class).

**Safe behavior for unknown modes (behavioral, not schema-enforced):** an
unrecognized `mode` value MUST NOT make the payload schema-invalid merely for
being unrecognized — `{"pricing": {"mode": "future_negotiated_mode"}, "price":
{"amount": 12500, "currency": "USD"}}` is schema-valid, with or without
`price`. JSON Schema can only constrain the data *shape*; it cannot enforce
consumer display/filter behavior. The normative behavioral contract (stated
here and in the EP draft) is: a Platform that does not recognize `mode` MUST
treat the item conservatively as having **no usable display price** — it MUST
NOT interpret a missing price as zero, MUST NOT display an accompanying
numeric price as authoritative, MUST NOT assume the item is free, and MUST
exclude the item from numeric price filtering, sorting, or ranking unless it
understands that mode.

**No per-determinant modes.** `buyer_specific` stays broad enough to cover any
numeric price resolved specifically for the current buyer, regardless of the
merchant-side pricing algorithm. This update deliberately does **not**
introduce modes like `region_specific`, `customer_type`, `agreement_specific`,
or `volume_specific` — these are business-side pricing inputs, not
interoperability states, and fragmenting `mode` by pricing determinant would
reopen the same closed-enum-in-disguise problem this update just resolved.

`product.price_range`: `required` drops to conditional — REQUIRED when every variant
carries a numeric price (status quo preserved exactly); MAY be omitted when ≥1
variant is priceless; MUST be omitted when no variant carries a numeric price.
"Carries a numeric price" means the variant has the `price` property present in
this response (`amount: 0` counts — free is priced; a priced `buyer_specific`
variant counts). When present over a mixed product it MUST be computed over
priced variants only and the product SHOULD carry a `price_on_request`
disclosure warning. `list_price_range` follows the same rule (prose; already optional).

`price_filter`: prose-only change — on-request variants are excluded from min/max
matching; a filter MUST NOT treat a missing price as zero; mixed results apply the
filter to priced variants and drop the rest (evoleinik's observed implementation
made normative); Business MAY surface dropped items via a message.

`warning_code.json`: `price_on_request` added to the freeform examples — the
in-proximity rendering vehicle with `presentation: "disclosure"`.

Checkout untouched: `item.json` still requires `price`. On-request is
catalog-representation only; how a variant becomes purchasable (identity linking →
`buyer_specific`; accepted quote → #845 handoff) is pointed to, not invented.

**Why the object form over Worker 2's string:** the thread adopted the object form after
Worker 2's analysis — juanferrub's Sep 29 sketch is the object with four modes and
`reason`/`next_step` keys; evoleinik's Oct 1 reply adopts the four modes for his two
live sellers. The string form cannot carry them. **Divergence to disclose:** #877's
*body* sketches the string form `"pricing": "on_request"`; the prototype rejects
that literal syntax. The unsent comment asks the thread to confirm the object form.

**Tradeoffs accepted in the prototype:**
- ~~Closed enum (fail-closed on unknown modes) vs UCP's open-vocabulary convention~~
  **RESOLVED 2026-10-05:** following maintainer feedback, `mode` adopted UCP's
  open-vocabulary convention ("well-known values" + MAY-extend) with explicit
  unknown-mode safe-fallback handling (conservative treat-as-unpriced-for-display
  behavior; see the dated note in §2) rather than inventing public-price or
  quote semantics for unrecognized modes.
- `quote_required` + indicative "from $X" price is banned (conflict rejection).
  Defensible against ambiguous display, but narrows real B2B practice — EP scope.
- Mixed-product `price_range` over priced variants only can mislead (e.g. $10–$20
  range beside enterprise on-request variants); mitigation is SHOULD-disclosure,
  not MUST. EP may strengthen.

## 2A. `buyer_specific`: priced-for-recognized-caller is the PROPOSED normative behavior (RESOLVED 2026-10-05)

**Updated following evoleinik's reported live-implementation behavior:**
retaining `buyer_specific` on a priced response — interpretation **(ii)**
below — is now stated as the proposed normative behavior, not merely one of
two open interpretations. The schema continues to allow BOTH:

- `{"pricing": {"mode": "buyer_specific"}}` (anonymous/unresolved caller — no price)
- `{"pricing": {"mode": "buyer_specific"}, "price": {...}}` (resolved for a
  recognized buyer — price present, **mode retained**, not switched to `public`)

The historical record of the two interpretations is preserved below for
context, but the open question it used to pose is now resolved in favor of (ii):

The prototype implements interpretation **(ii)**: `buyer_specific` MAY carry a
numeric price when the response is addressed to a recognized buyer; the mode then
documents disclosure context ("this price is specific to you, the caller").
When such a price is present, `mode` **MUST remain** `buyer_specific` (not
revert to `public`) so a Platform can tell the value is caller-specific.

Interpretation **(i)** — Juan's original direction ("omit price for non-public
modes"): non-public modes never carry a price. Under (i), `buyer_specific` means
"a price exists but is not in this response"; the buyer obtains it through a
separate step (identity linking → re-request, or a quote hand-off). This
interpretation is **not** adopted.

| Consequence | (i) always omit | (ii) priced for recognized caller (now proposed normative) |
|---|---|---|
| Filtering | Priceless variants dropped from price filters, uniformly | A priced `buyer_specific` variant participates in filters for that caller |
| Caching | Cached response carries no price — leak impossible from the payload | Cached priced response served to a different buyer **is a price leak**; addressed below by the now-explicit cache-isolation requirement (point 4) |
| Disclosure boundary | Mode has one meaning ("no price here") | Mode does double duty ("no public price" + "here is your price"); consumers must read `mode` to distinguish from `public` |
| Evoleinik's data | Anonymous → `buyer_specific`, linked → priced | Same observable behavior, and evoleinik's reported live-implementation behavior is the direct support for adopting (ii) as the proposed resolution |

The mode preserves information across the identity-linking transition (the
caller can see the price was buyer-specific, not public). The cache-isolation
risk (ii) introduces is addressed normatively below, not by abandoning (ii).

### Cache isolation for buyer-specific prices (NEW, normative — point 4)

**A Platform MUST NOT reuse or serve a priced `buyer_specific` representation,
or any value derived from it, for a different caller.** This is a protocol/
behavioral requirement — JSON Schema cannot express or enforce it; it is
stated here, in the EP draft, and in COMPATIBILITY.md as prose. It covers:

(a) `variant.price` itself when `pricing.mode` is `buyer_specific`: a response
generated for one buyer's resolved price MUST NOT be served to a different
buyer or to an anonymous caller.

(b) Anything **derived** from a buyer-specific price — explicitly including
`product.price_range` computed from buyer-specific variant prices. A
product-level `price_range` aggregated over buyer-specific variant prices is
itself caller-specific and carries the same leak risk: caching a
sanitized/leak-free variant price while still caching a buyer-specific
product-level `price_range` would leak pricing information through the
range alone.

**Concrete example:** Buyer A resolves to $875, Buyer B resolves to $740,
and an anonymous caller sees no price. A response generated for Buyer A MUST
NOT be served to Buyer B or to the anonymous caller — mode equality
(`buyer_specific` on both) does not establish that two responses are
interchangeable; the isolation key must include the identity/entitlement
context, not just the mode. **Caches containing caller-dependent catalog
pricing need an identity-aware cache key, or must avoid shared caching
entirely** for buyer-specific responses and any `price_range` derived from them.

**Clarifying nuance (added 2026-10-05, with the NDA example):** `buyer_specific`
does not necessarily mean the amount is mathematically unique to that one
person. A priced `{"pricing": {"mode": "buyer_specific", "next_step":
"request_quote"}, "price": {...}}` response (fixture
`buyer_specific_with_price_and_quote_step.json`) is still caller-specific —
the existence of the quote path does not weaken the cache rule, and a
Platform MUST NOT reuse that representation, its price, or a range derived
from it for another caller. The NDA deployment demonstrates the same list
price may be visible to multiple entitled buyers while remaining non-public.
The mode primarily communicates disclosure/pricing context, not "this number
was individually calculated for exactly one human."

## 2B. `contract_only` RESOLVED via the per-caller transition (2026-10-05, reversing the prior relaxation)

**This section replaces the prior round's "three alternatives, open question"
framing.** Per new maintainer guidance, `contract_only` is resolved in favor of
the per-caller state transition, and the schema is reverted to keep
`contract_only` a genuinely unpriced state (the "forbid price" `allOf` rule
once again covers both `quote_required` and `contract_only`, undoing the prior
round's relaxation):

```
Anonymous, public price available
    -> mode: public + price

Anonymous, price restricted to entitled customers
    -> mode: contract_only, no price

Entitled/recognized customer
    -> mode: buyer_specific + price
```

`contract_only` + a numeric `price` is therefore **rejected again**:

```json
{
  "pricing": { "mode": "contract_only" },
  "price": { "amount": 45000, "currency": "USD" }
}
```

`contract_only` and `buyer_specific` now have a coherent, distinct meaning:

- `contract_only` describes the **unresolved** response to a caller who has
  not established the necessary entitlement — a genuinely unpriced state,
  identical in strictness to `quote_required`.
- `buyer_specific` describes the response **after** the Business has resolved
  pricing in the current buyer context — it may carry `price`.

The actual pricing algorithm behind that resolution — a contract, an NDA,
customer type, region, volume agreement, a negotiated discount, or something
else — does not require separate Catalog modes. `reason` remains the
informational, Business-defined escape hatch for that detail.

Both anonymous postures from the issue thread are preserved as fixtures:

- **Public/general-price stranger** (fixture `public_with_price.json`):
  `{"id": "var_sec_suite", "price": {"amount": 49900, "currency": "USD"},
  "pricing": {"mode": "public"}}` — valid.
- **Contract-gated stranger** (fixture `contract_only_without_price.json`):
  `{"id": "var_sec_suite", "pricing": {"mode": "contract_only"}}` — valid, no
  price.
- **Entitled buyer in either case** (fixture
  `onrequest_variant_buyer_specific_priced.json` /
  `onrequest_product_scenario_b_buyer_specific_resolved.json`):
  `{"id": "var_sec_suite", "price": {"amount": 45000, "currency": "USD"},
  "pricing": {"mode": "buyer_specific"}}` — valid.

This establishes explicitly: `pricing.mode` describes **the pricing state of
this representation for this caller**, not an immutable classification of the
SKU — the same variant transitions `public`/`contract_only` → `buyer_specific`
as the calling context changes, per §2A's caller-dependence lesson.

Scenario A/B framing from the prior round is retained as illustration, not as
open alternatives:

- **Scenario A (public catalog price exists):** anonymous sees the ordinary
  public price (`pricing` absent or `mode: public`); once identified, the
  buyer's negotiated price is `buyer_specific` + price (fixtures
  `onrequest_product_scenario_a_public_to_buyer_specific_anonymous.json` and
  `..._resolved.json`).
- **Scenario B (no anonymous price exists):** anonymous sees `contract_only`
  with no price; once resolved, the representation transitions to
  `buyer_specific` + price — this is now the **selected working design**, not
  one of two open alternatives (fixtures
  `onrequest_product_scenario_b_contract_only_anonymous.json` and
  `..._buyer_specific_resolved.json`). The previously-open alternative —
  retaining `contract_only` with a price on resolution — is rejected (fixture
  `onrequest_variant_contract_only_priced.json`, now INVALID; flipped from the
  prior round, which had made it schema-valid as an open-question data shape).

Catalog representation stays separate from checkout pricing policy: the
catalog states the mode; the hand-off point (identity linking → re-request, or
the #845 term hand-off) is named, not invented. No quote/RFQ workflow is
defined here. This remains **prototype behavior until the EP/TC formally
adopts it** — the schema and fixtures implement one selected working design,
not three competing alternatives to be tested side by side.

## 2C. `next_step` orthogonality (new, 2026-10-05)

`next_step` (well-known value `request_quote`) identifies a well-known
pricing-related interaction the Business wishes to expose in connection with
the variant. Its presence does **not** imply that the interaction is
mandatory, and does **not** determine whether a usable price is present:
`request_quote` means a quote path is available; `pricing.mode` determines
whether obtaining a quote is necessary to obtain a usable price. `next_step`
MUST NOT participate in, and is not referenced by, the conditional `price`
rules — price requiredness depends solely on `mode`.

```
quote_required + request_quote
    -> no usable price; quote is required to resolve pricing

buyer_specific + price + request_quote
    -> caller has a usable price; quote path is additionally available

public + price + request_quote
    -> public price exists; Business also accepts quote requests
```

The NDA deployment case (fixture `buyer_specific_with_price_and_quote_step.json`)
demonstrates two independent facts: `price` = what the buyer can currently
see/use; `next_step` = another commercial interaction that may be available. A
buyer may have a real catalog price and still be able to request a negotiated
quote. The third, orthogonal case — `public` + `price` + `request_quote`
(fixture `public_with_price_and_quote_step.json`) — is added even though not
explicitly reported on the issue thread, specifically to test that the model
is actually orthogonal rather than accidentally special-casing NDA pricing.

Conversely, `quote_required` + `price` + `request_quote` (fixture
`quote_required_with_price_and_quote_step.json`) stays **invalid**: `price` is
UCP's ordinary selling/current-purchase price; `quote_required` says no such
usable price has been resolved. Allowing both would force Platforms to guess
whether the numeric price is indicative/starting-at/list/stale/estimated/
actually-purchasable — exactly the ambiguity the structured pricing state is
meant to eliminate. If a Business wants a reference value while a quote is
required, it should use `list_price` (already exists) or a future
explicitly-defined indicative-price construct — `price` must not be
overloaded for this.

**Non-normative EP design note (Open Questions/Alternatives):** the name
`next_step` may overstate ordering/requirement semantics when the interaction
is optional. Before standardization, consider whether this should eventually
be named `available_action` / `available_actions`, or bound to a capability
that defines the interaction. The field is **not** renamed in this prototype —
that would introduce unnecessary churn for a research prototype.

## 2D. Composition with Purchase Options (#901)

This is a forward-looking composition analysis for **proposed Purchase
Options work in concurrent PR #901**. That schema does not exist in this
codebase (`grep -r purchase_option` and `grep -r 901` over `source/` return
nothing) because #901 is a separate, concurrent proposal — not because the
work itself is speculative. This section is pure design-sketch documentation
— **no new schema file is added for `purchase_options`, and no existing
schema is modified to add a `purchase_options` property.**

#901 as proposed defines approximately:

```json
{
  "id": "po_lease",
  "title": "Lease, 60 months",
  "price": { "amount": 12345, "currency": "USD" }
}
```

and requires `price` on every purchase option. Therefore it currently cannot
represent:

```json
{
  "id": "po_lease",
  "title": "Lease, 60 months",
  "pricing": { "mode": "quote_required", "next_step": "request_quote" }
}
```

That is a genuine composition gap. **This is not fixed in the core Variant
prototype** by allowing a fake/default `price` on a purchase option — a
pricing state belongs at the same granularity as the price it qualifies. Once
`purchase_options[]` owns independent prices, Variant-level `pricing` alone
cannot model every combination, for example:

```
One-time purchase     $10,000 public
60-month lease        quote required
36-month lease        $300/month buyer-specific
```

A single Variant-level `pricing.mode` cannot describe all three simultaneously.
A stronger example makes the gap unambiguous — the Variant itself has a
perfectly valid public buying option, so simply inheriting a Variant-level
`quote_required` cannot solve it either:

```json
{
  "id": "var_machine",
  "price": { "amount": 1000000, "currency": "USD" },
  "pricing": { "mode": "public" },
  "purchase_options": [
    { "id": "po_buy", "title": "Buy outright", "price": { "amount": 1000000, "currency": "USD" } },
    { "id": "po_lease", "title": "Lease, 60 months" }
  ]
}
```

Under #901 as proposed, this is invalid because the lease option
lacks `price`. This is stronger evidence than the lease-only case: the
Variant's own public price cannot stand in for (or excuse) the lease option's
missing price, so any complete composition solution needs **option-level**
pricing-state semantics or an equally granular mechanism — not a Variant-level
fallback.

If #901 is intended to support quoted purchase options, the eventual
composition should probably let each purchase option carry the same
pricing-state concept. This is a **non-normative strawman sketch**, clearly
not implemented in schema, and not part of the current #877 prototype:

```json
{
  "purchase_options": [
    {
      "id": "po_once",
      "title": "Buy outright",
      "price": { "amount": 1000000, "currency": "USD" },
      "pricing": { "mode": "public" }
    },
    {
      "id": "po_lease",
      "title": "Lease, 60 months",
      "pricing": { "mode": "quote_required", "next_step": "request_quote" }
    }
  ]
}
```

This must be raised with the #901 author/maintainers before incorporating
into the EP — #877 does not depend on a draft extension, but the two proposals
should eventually compose. See `harness/README.md`'s composition note (or the
harness itself) for why this is deliberately kept **out of the counted
pass/fail harness legs**: there is no real `purchase_option.json` schema in
this repo to validate against, so these examples are prose/illustration only,
never wired into `run.py`'s Legs A–G.

## 3. Design questions — resolved

1. **Zero-means-free preserved.** `price.amount: 0` keeps its released meaning; the
   `pricing` axis is orthogonal (fixture `priced_variant_free.json` passes both schemas).
2. **Explicit vs accidental omission distinguishable.** Priceless + marker → valid;
   priceless without marker → `'price' is a required property` (both schemas).
3. **Conflicting price + no-price mode:** rejected for both `quote_required`
   AND `contract_only` (REVERSED 2026-10-05 — `contract_only` is restored to
   this rule, undoing the prior round's relaxation; see §2B — this is now
   RESOLVED, not open); allowed only for `buyer_specific` (mode documents
   disclosure context for *this response*; a linked buyer's numeric price does
   not contradict it — and per §2A's cache-isolation nuance, `buyer_specific`
   does not imply the amount was individually computed for exactly one
   person).
4. **Identity-dependent prices encoded** (§2, caller-dependence).
5. **Cross-buyer disclosure boundaries out of scope, stated:** "Which buyers see
   which price is Business policy — the schema carries no access-control semantics."
6. **Catalog→commercial transition points, doesn't invent:** identity linking for
   `buyer_specific`; accepted-commercial-term handoff (#845) for quotes. No RFQ,
   quote-locking, expiry, invoice, or payment constructs added.
7. **`list_price` / `unit_price` / `list_price_range` on unpriced variants —
   decided and aligned across schema, prose, and fixtures (corrected
   2026-10-02):**
   - `list_price` is a **legitimate reference price**: it MAY accompany an
     unpriced variant (e.g. strikethrough "List $100" beside a "request quote"
     disclosure). It is explicitly "before discounts" display data, never the
     transaction price, so it does not conflict with a no-price mode. No schema
     change (already optional); prose states the permission + the MUST-NOT-treat
     -as-selling-price rule; fixture
     `onrequest_variant_quote_required_with_list_price.json` (valid).
   - `unit_price` is a **conflicting signal**: it is a per-unit *selling* price.
     Schema-enforced: MUST NOT be present with `quote_required` or
     `contract_only` (REVERSED 2026-10-05: `contract_only` is back in the
     "forbid price" rule, so it is doubly excluded from carrying `unit_price`
     — both directly, and via `unit_price`'s separate, unconditional
     requirement that `price` be present). A priceless `buyer_specific`
     variant likewise cannot carry a `unit_price`. Fixtures:
     `..._with_unit_price.json` (invalid),
     `..._buyer_specific_noprice_with_unit_price.json` (invalid),
     `..._buyer_specific_priced_with_unit_price.json` (valid).
   - `list_price_range` follows the `price_range` rule: MUST be omitted when no
     variant carries a numeric price (new schema branch); MAY be omitted or
     computed over priced variants only when mixed (already optional, prose
     rule). Fixtures: `onrequest_product_mixed_list_price_range.json` (valid),
     `onrequest_product_all_norange_with_list_price_range.json` (invalid).
   - **"Carries a numeric price"** (used by all range rules): the variant has
     the `price` property present — `amount: 0` counts (free is priced); a
     priced `buyer_specific` variant counts; a priceless `buyer_specific`
     variant does not.
8. **Warning-code registration done minimally** (`price_on_request` in examples +
   `presentation: "disclosure"` prose).
9. **`product.price_range` computation over mixed priced/unpriced variants —
   clarified 2026-10-05 (no schema change; prose clarification only), and
   RE-CLARIFIED in this round because open vocabulary creates a new
   aggregation problem:** "carries a numeric price" (the prior round's test)
   is **not sufficient** once an unknown mode may legally coexist with a
   numeric price — e.g. `{"pricing": {"mode": "future_special_mode"},
   "price": {"amount": 10000, "currency": "USD"}}` is schema-valid for
   forward compatibility, but an older Platform that doesn't recognize
   `future_special_mode` must treat it conservatively and not display its
   price, so it would be unsafe to blindly fold into `product.price_range`.
   The precise behavioral definition is now **range-eligible price = a
   numeric price whose pricing semantics the Platform understands as usable
   for this caller**:
   - `pricing` absent + `price` → eligible
   - `public` + `price` → eligible
   - `buyer_specific` + `price` → eligible for this caller
   - `quote_required` → not eligible (no price exists anyway)
   - `contract_only` → not eligible (no price exists anyway, per §2B's
     reversal — REVERSED from the prior round, which counted a priced
     `contract_only` variant as "carrying a numeric price")
   - unknown mode → not eligible to an unaware Platform
   Producer-side: the core well-known range calculation includes
   ordinary/public prices and resolved `buyer_specific` prices only.
   Consumer-side fallback (behavioral, not schema-enforced): if a product
   contains a pricing mode the Platform does not understand, the Platform
   MUST NOT assume `product.price_range` includes only prices that are safe
   for it to display — the safest old-consumer behavior is to
   suppress/recompute the range from understood variants. The same
   principle applies to price filtering.
   When present over a mixed product, `price_range` MUST be computed only
   over range-eligible variants — never zero-filled or synthesized for
   ineligible ones. Example: Variant A=$100 (public), B=`quote_required` (no
   price), C=$150 (public) → the range MUST be $100–$150, never $0–$150
   (fixture `onrequest_product_mixed_withrange.json`, contrasted with
   `onrequest_product_mixed_norange.json`, which tests the omit-range case).
   An identified-buyer scenario with `buyer_specific` priced variants (e.g.
   A=$80, B=$110) CAN produce a caller-specific `price_range` of $80–$110
   (fixture `onrequest_product_buyer_specific_range.json`), but that range is
   subject to the SAME cache-isolation requirement as the underlying
   buyer-specific prices (§2A) — stated here as prose since JSON Schema
   cannot verify a range was mathematically derived from the correct
   subset/caller. A mixed product carrying one range-eligible and one
   unknown-mode-with-price variant is demonstrated by fixture
   `onrequest_product_unknown_mode_mixed.json` — the shape validates (schema
   can only check data shape), but the *consumer's* decision of which
   variants are range-eligible is the behavioral rule stated here and in
   `product.json`'s `price_range` description. `next_step`'s presence (e.g.
   `request_quote`) has **no bearing** on range/filter eligibility — eligibility
   is determined solely from price usability/mode semantics (§2C). All variants
   unpriced/ineligible → `price_range` absent (already correctly enforced by
   the existing schema rule, unchanged).

## 5. Design questions — explicitly open (for the EP / TC / thread)

- ~~**Closed enum vs open vocabulary** for `mode`~~ **RESOLVED 2026-10-05:**
  `mode` is now an open vocabulary (no enum); see the dated note in §2.
- ~~**`buyer_specific` interpretation**~~ **RESOLVED 2026-10-05:** (ii) priced
  for recognized callers is now the proposed normative behavior; see §2A.
- ~~**`contract_only` entitled-price path**~~ **RESOLVED 2026-10-05 (this
  round, reversing the prior round's relaxation) — see §2B.** The per-caller
  state transition is the selected working design: `contract_only` stays a
  genuinely unpriced state; an entitled/recognized customer's resolved price
  transitions to `buyer_specific` + `price`. This is prototype behavior
  pending formal EP/TC adoption, but the prototype no longer tests three
  competing alternatives for this decision.
- **`reason` / `next_step` standardization** — currently Business-defined,
  informational; `next_step`'s orthogonality to `price` is now documented in
  §2C. Naming concern noted non-normatively in §2C/EP draft (possible future
  `available_action(s)` rename) — not renamed in this prototype.
- **Indicative pricing** alongside `quote_required` ("from $X") — currently
  banned; see §2C's rationale for why `price` must not be overloaded for this
  (use `list_price` or a future indicative-price construct instead).
- **Purchase Options (#901) composition** — new in this round, see §2D: a
  concurrent draft issue's apparent price-required-on-every-option assumption
  does not compose with an unpriced `quote_required`/`contract_only` option.
  Documented as a composition requirement and a non-normative strawman sketch
  only; raised with the #901 author/maintainers before incorporation, not
  implemented as schema in this prototype.
- ~~**Cache coherence for per-response modes**~~ **RESOLVED (as a normative
  requirement, not a mechanism) 2026-10-05:** a Platform MUST NOT reuse a
  buyer-specific price, or a `price_range` derived from it, across callers;
  see §2A's "Cache isolation" subsection. The transport mechanism (cache keys,
  `Vary`-like headers) remains unspecified and is a follow-on, not resolved here.
- **`pricing` field-name collision:** Variant has no `additionalProperties: false`;
  existing vendor extensions may already use a `pricing` key. EP should survey
  `com.shopware.quote` / `com.ucpready.procurement` (found in pass 1).
- **Possible future split of `pricing` into separate visibility/access-policy
  vs. price-provenance dimensions** — noted as a one-paragraph alternative in
  the EP draft's Open Questions section; explicitly NOT implemented as a
  schema field in this update (out of scope — see point 16 of the maintainer
  feedback). The existing `reason` and `next_step` fields are left as-is.
- **Sort semantics** for on-request items (no sort construct in `price_filter` today).
- **Feed (#866) spec text:** schema rule covers feed records (they are Products),
  but the feed capability doc (draft PR, not at this pin) needs the aggregation sentence.
- **Tooling:** `ucp-schema lint` / `validate_examples.py` could not run here
  (`logs/ucp_schema_build_fail.log`); a mode-aware scaffold update for doc examples
  is an open tooling question (Worker 3's writeup of this point is truncated —
  see README.md).

## Publication review clarification

Cache isolation must account for buyer and entitlement context, including two
responses with the same `buyer_specific` mode but different prices. Mode equality
alone does not establish that responses can be shared. `list_price_range` stays
optional; only `price_range` is required for all-priced products.

## Maintainer feedback incorporated (2026-10-05, first pass)

Following review from evoleinik and juanferrub, this update: (1) opened
`mode`'s vocabulary (removed the closed enum; §2); (2) documented explicit
safe-fallback behavior for unrecognized modes (§2, dated note); (3) confirmed
priced `buyer_specific` responses as the proposed normative behavior, not an
open interpretation (§2A); (4) made buyer-specific cache isolation — including
derived `price_range` — an explicit normative requirement (§2A); (5)
deliberately left `contract_only` + price an open design question by relaxing,
not resolving, the schema (§2B, **superseded by the second pass below**); (6)
confirmed the decision not to add per-determinant modes (§2, dated note); (7)
kept `quote_required`'s strict no-price semantics unchanged (§3.3); (8)
verified the full `allOf` rule set traces correctly for every case including
unknown modes (§2, §3.3); (9) added clarifying prose for `price_range`
computation over mixed/buyer-specific variants (§3.9); (10)-(11) expanded the
fixture matrix to 36 vectors and added a pricing-mode fuzz leg (Leg G) to the
harness (rerun result: exit 0, 36/36 fixtures, 300+300 Leg E, 300+300 Leg G);
(12)-(14) updated COMPATIBILITY.md,
the EP draft, and README.md accordingly. Checkout remained untouched
throughout (point 15); no `pricing.visibility`/`pricing.provenance`
restructuring was introduced (point 16) beyond a one-paragraph Alternatives
note in the EP draft.

## Maintainer feedback incorporated (2026-10-05, second pass — `contract_only` reversal)

Following new maintainer guidance, this second pass on the same date: (1)
**resolves** `contract_only` via the per-caller transition
(`public`/`contract_only` for anonymous callers → `buyer_specific` + price for
entitled callers), **reverting** the first pass's schema relaxation —
`contract_only` once again forbids `price` (§2B, replacing the "three
alternatives, open question" framing); (2) preserves both anonymous postures
from the issue thread as fixtures (`public_with_price.json`,
`contract_only_without_price.json`); (3) keeps `buyer_specific` + `price` +
`next_step` as a first-class NDA deployment fixture
(`buyer_specific_with_price_and_quote_step.json`), confirming `next_step`
never participates in the conditional `price` rules; (4) documents
`next_step`'s orthogonality precisely (§2C), adding the `public` + `price` +
`request_quote` case (`public_with_price_and_quote_step.json`) and a
non-normative EP naming note, without renaming the field; (5) keeps
`quote_required` + `price` invalid even with `next_step` present
(`quote_required_with_price_and_quote_step.json`), with the semantic
rationale (price ambiguity) stated in §2C; (6)-(7) treats the proposed
#901 Purchase Options interaction as a documentation-only composition problem
in new §2D — no schema file or property added; (8) reverts rule 1's `allOf`
condition in `variant.json` to `enum: ["quote_required", "contract_only"]`
(not a closed enum on `mode` itself — only this rule's two known literals),
verified by tracing that an unknown mode matches neither the forbid-price nor
the require-price rule; (9) replaces "carries a numeric price" with
"range-eligible price" for `price_range`/`price_filter` purposes, since an
unknown mode may legally coexist with a numeric price (§3.9, product.json);
(10) confirms `next_step` has no bearing on range/filter eligibility; (11)
adds the NDA cache-isolation nuance (§2A) — `buyer_specific` does not imply
per-person computed uniqueness. The harness was rerun after these changes:
42/42 fixtures, 300+300 Leg E, 300+300 Leg G, exit 0 — see
`../logs/` for the dated rerun log. The #901 composition illustrations were
kept entirely in DESIGN.md prose and are NOT counted in the harness's
pass/fail legs, per the explicit instruction to keep #877 independent of a
draft extension that does not exist in this codebase.
