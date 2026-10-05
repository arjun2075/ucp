# [Proposal]: Price-on-request catalog pricing state (UCP #877)

> **UNSENT DRAFT — do not file without the user's explicit word on this exact text.**
> This draft was prepared by a single research pass (**self-review**); it has not
> been independently reviewed and claims no maintainer, TC, or community
> consensus. The three questions asked on the thread below remain unanswered as
> of 2026-10-02 ~08:00 PDT.
>
> **UPDATED 2026-10-05** to incorporate feedback attributed to evoleinik and
> juanferrub: `mode` is now an open vocabulary (D1 below is revised, not
> reversed from its original closed-enum recommendation — the recommendation
> changes to open vocabulary with explicit safe-fallback handling); priced
> `buyer_specific` responses (D2-ii) are now stated as the proposed normative
> behavior rather than a recommendation among two live options; buyer-specific
> cache isolation (D5) is elevated from a recommendation to explicit normative
> MUST language, including derived `price_range`; `contract_only`'s
> entitled-caller path (D3) was deliberately left open in this first pass — the
> schema was relaxed to permit (not require) `price` alongside `contract_only`.
>
> **SECOND UPDATE, same date — `contract_only` (D3) is now RESOLVED, reversing
> the first pass's relaxation.** New maintainer guidance selects the per-caller
> transition: a stranger with a gated price sees `contract_only` (no price); an
> entitled/recognized customer sees `buyer_specific` + price. `contract_only` is
> restored to a genuinely unpriced state — `price` MUST NOT be present with it,
> exactly as with `quote_required`. This is the EP's adopted working design, not
> a resolution the maintainers merely leaned toward; "buyer_specific semantics
> unconfirmed" and "contract_only has no entitled-price path" are removed from
> the risk/open-question framing below. `next_step`'s orthogonality to a
> resolved numeric price is also clarified (it never implies price must be
> absent, and never participates in price requiredness), and a new risk/
> composition note is added for the concurrent draft issue #901 (Purchase
> Options) — this EP does not resolve #901, but the pricing-state model should
> be reusable at finer-grained price-bearing nodes if #901 allows them to be
> unpriced. This update does not claim any new maintainer consensus beyond the
> feedback it responds to.

- **Linked issue:** Universal-Commerce-Protocol/ucp#877 ("Catalog items with no
  public price")
- **Prior thread:** the researcher's coordination comment —
  https://github.com/Universal-Commerce-Protocol/ucp/issues/877#issuecomment-5954902121 —
  points at the prototype and asks the thread three questions: (1)
  `buyer_specific` priced-for-recognized-caller vs mode transition; (2)
  `contract_only` entitled-caller price delivery; (3) closed enum vs open
  vocabulary for `mode`. Per a recheck on 2026-10-02 ([FEEDBACK_RECHECK.md](FEEDBACK_RECHECK.md) in this follow-through bundle), there have been **no substantive replies** from evoleinik,
  juanferrub, or maintainers, and zero reactions. All open decisions below are
  genuinely open — this proposal recommends a direction for each; it does not
  claim the thread has settled them.
- **Pinned prototype** (validation harness + schema diff, not a PR):
  https://github.com/arjun2075/ucp/tree/6fee3503125dfd3b17908bdf9c69ec69fc4e716b/research/price-on-request
- **Evidence provenance:** the original prototype is pinned above at `6fee350`.
  This branch's follow-through evidence is published alongside this draft:
  [verification results](VERIFICATION_RESULTS.md), [expanded compatibility
  matrix](COMPATIBILITY.md), and [raw logs](logs/). The 28-vector expansion,
  live JS SDK rerun, schema lint and docs build occurred after the original
  publication. The new results were agent-run and self-reviewed; their
  publication does not imply independent review or TC agreement.
- **Credits:** @evoleinik (issue author; caller-dependent-mode and
  filter-exclusion lessons from two live sellers); @juanferrub (the four-mode
  pricing-state object sketch: `public | buyer_specific | quote_required |
  contract_only` with `reason`/`next_step`).

---

## Summary

Add an optional `pricing` pricing-state object to catalog Variants so a Business
can explicitly declare "no public price for this item" in the core schema,
instead of misusing `amount: 0`, shipping schema-invalid payloads, or dropping
items from the catalog entirely. `variant.price` and `product.price_range`
become conditionally required via `if`/`then` gating rather than
unconditionally required:

- `pricing` absent or `mode: public` → `price` REQUIRED (status quo, fail-closed)
- `mode: quote_required` → `price` MUST NOT be present
- `mode: buyer_specific` → `price` optional; the mode describes **this response**
  (anonymous caller vs recognized buyer), per the caller-dependence lesson from
  the issue thread. When present, `mode` MUST remain `buyer_specific` — this is
  now the proposed normative behavior (UPDATED 2026-10-05; see D2).
- `mode: contract_only` → `price` MUST NOT be present (RESOLVED 2026-10-05;
  see D3 — reverses the first pass's relaxation: `contract_only` is a
  genuinely unpriced state describing the unresolved response to a caller who
  has not established entitlement; the resolved/entitled response transitions
  to `buyer_specific` + `price` instead)
- `mode` is an open vocabulary (no closed enum; UPDATED 2026-10-05, see D1):
  an unrecognized value MUST NOT be rejected merely for being unrecognized,
  and `price` MAY be absent or present alongside it, subject to the
  conservative safe-fallback behavioral contract below
- `product.price_range`: required when every variant is priced; omittable over
  mixed products (computed over priced variants only, plus a disclosure
  warning); omitted when none is priced
- Related-price rules: `list_price` (pre-discount reference) MAY accompany an
  unpriced variant; `unit_price` (a per-unit *selling* price) MUST NOT appear
  without `price`; price filters exclude priceless variants and MUST NOT treat a
  missing price as zero

Checkout is untouched (`item.price` stays required), `amount: 0` keeps meaning
free, and no quote, RFQ, entitlement, or payment workflow is defined —
on-request is catalog representation only. The prototype backing this proposal
validates 42 fixture vectors at 42/42 (28 from the original publication, 14 added across the two 2026-10-05 maintainer-feedback passes) and runs 300+300 differential fuzz cases
with 0 verdict mismatches against the pinned schemas (evidence in the prototype
tree; scope limits stated in the Test Plan).

## Motivation

Issue #877 makes the gap concrete with one figure: a reporter with **318
products and no public price** has three broken options today — display a
misleading `$0.00`, ship a schema-invalid omission, or drop the items from the
catalog (losing them to `ask`-based discovery). Two live sellers are already
working around this outside the schema. The released schema cannot represent
the situation: `variant.price` is unconditionally required, `amount: 0` means
free, and a vendor extension cannot relax `required` — verified by execution
(`allOf` composition cannot retract the base's required list, so the priceless
payload fails identically with or without an extension marker; see the
prototype harness). Per CONTRIBUTING.md's guidance to attempt the extensions
framework first, that route was attempted and is mechanically insufficient —
hence a core-schema Enhancement Proposal.

The beneficiaries are the Platforms and Businesses #877's sellers represent:
B2B contract pricing, NDA-gated software vendors, and lessors need a
schema-native way to say "a price exists, but it is not public for this
caller," and consumers need a validation-distinguishable representation so they
never again read a missing price as $0.00.

## Goals

- Catalog variants can explicitly declare no-public-price in the core schema;
  priceless-with-marker validates, priceless-without-marker fails validation
  (accidental omission stays an error).
- `amount: 0` retains its released "free" meaning; numeric-price invariants are
  preserved for priced variants (42/42 fixture vectors; 0 fuzz mismatches on
  the generated priced subset).
- Conflicting signals are rejected by validation: price alongside a no-price
  mode (`quote_required`/`contract_only`), and `unit_price` without `price`.
- Per-caller pricing disclosure is encoded without inventing identity,
  entitlement, quote, or payment machinery: the schema states the mode; the
  catalog→commercial transition points are named, not built.
- The proposal reaches a TC decision: either advancement to Provisional with
  the open decisions (D1–D6 below) resolved or explicitly deferred with
  recorded rationale, or a documented rejection.

## Non-Goals

- Quote/RFQ creation, quote locking or expiry, invoice, or payment workflows.
- Account-identity, buyer-entitlement, or access-control machinery (the schema
  carries no access-control semantics; which buyers see which price is Business
  policy).
- Cache transport mechanisms (e.g. new headers): the EP states a
  no-cross-context-caching **requirement**; the mechanism is a follow-on.
- Feed capability-doc text (#866): feed records are catalog Products so the
  schema rule covers feeds; the feed doc's aggregation sentence is a documented
  dependency, not part of this EP.
- Conformance-suite updates and SDK model regeneration: required before
  Candidate stage, but implementation work, not EP content.
- Per-seller offer pricing (#810, orthogonal: price remains required per offer)
  and human-readable `display_value` (#650, orthogonal presentation string).

## Detailed Design

### API Changes

None. No new endpoints; no changes to existing request/response envelopes. The
change is confined to catalog data shapes (Variant/Product schemas) and the
prose norms governing them.

### Data Structures

**`shopping/types/variant.json`** (all proposed; released text marked R):

- New optional `pricing` object:
  - `mode` (required when `pricing` is present): string, **open vocabulary**
    (UPDATED 2026-10-05 — no longer a closed enum; see D1). Well-known
    values, listed as `examples`: `public` | `buyer_specific` |
    `quote_required` | `contract_only`. A Business MAY introduce new values; a
    Platform MUST tolerate values it does not recognize.
  - `reason` (optional string): Business-defined, informational (e.g.
    `contract_or_volume_dependent`). Consumers MUST NOT infer semantics beyond
    `mode`.
  - `next_step` (optional string): well-known value `request_quote`, meaning a
    quote-related interaction is available. Its presence does NOT imply the
    interaction is mandatory and does NOT determine whether a usable price is
    present — `next_step` MAY coexist with an already-resolved numeric
    `price` (e.g. `buyer_specific` + `price` + `request_quote`, or `public` +
    `price` + `request_quote`); it MUST NOT be read as defining a quote
    protocol, and it does not participate in the `price`-requiredness rules
    below (UPDATED 2026-10-05, second pass — see D3/next_step note).
- `required` drops `"price"` (R: `["id","title","description","price"]`).
- New `allOf` branches (draft 2020-12):
  1. `pricing.mode = quote_required` OR `pricing.mode = contract_only` →
     `price` and `unit_price` MUST NOT be present (conflicting price +
     no-price assertion rejected). **REVERSED 2026-10-05 (second pass):** the
     first pass had removed `contract_only` from this rule to study it as an
     open question; new maintainer guidance resolves `contract_only` as a
     genuinely unpriced state (see D3), so this rule is restored to cover
     both known modes, exactly as it read before the first pass's relaxation.
  2. `pricing` absent or `mode: public` → `price` REQUIRED (status quo).
  3. `unit_price` present → `price` REQUIRED (unit price is derived from the
     selling price).
  4. `pricing.mode = buyer_specific` → `price` MAY be present (priced for a
     recognized caller) or absent (anonymous caller); the mode documents the
     disclosure context of *this response*. When present, `mode` MUST remain
     `buyer_specific` (UPDATED 2026-10-05: now proposed normative behavior,
     see D2).
  5. An unrecognized/unknown `mode` → `price` MAY be absent or present; no
     rule constrains it (none of branches 1, 2, or 4 match an unrecognized
     mode, so it falls through unconstrained — this is the intended
     safe-fallback shape, verified by tracing the `allOf` rules).
- Empty `pricing: {}`, `pricing: null`, and the string form `"pricing":
  "on_request"` remain rejected — these are malformed-*shape* rejections
  (`pricing` must be a well-formed object with a non-empty string `mode`),
  unaffected by and unrelated to the open-vocabulary change to `mode`'s value
  space (UPDATED 2026-10-05; previously this bullet described unknown `mode`
  *values* as also rejected, which is no longer the case — see D1).
- `list_price`: unchanged (optional). Prose states it is a legitimate
  pre-discount **reference** price that MAY accompany an unpriced variant (e.g.
  strikethrough "List $100" beside a "request quote" disclosure) and MUST NOT
  be treated as the selling price. It never conflicts with a no-price mode
  because it is explicitly not the transaction price.

**`shopping/types/product.json`**:

- `required` drops `"price_range"` (R: `["id","title","description",
  "price_range","variants"]`).
- New `allOf` rule (schema-checkable shape only; see below for the behavioral
  refinement): `price_range` is REQUIRED when every variant carries the
  `price` property in this response; MAY be omitted when ≥1 variant lacks
  `price`; MUST be omitted when no variant carries `price`.
- **UPDATED 2026-10-05 (second pass) — "carries a numeric price" is refined to
  "range-eligible price"** because the open `mode` vocabulary creates a new
  aggregation problem: a numeric `price` may legally coexist with an unknown
  `pricing.mode` (forward compatibility), but an unaware Platform must not
  treat that price as safe to fold into a range. Range-eligible price = a
  numeric price whose pricing semantics the Platform understands as usable
  for this caller: `pricing` absent + `price` → eligible; `public` + `price`
  → eligible; `buyer_specific` + `price` → eligible for this caller;
  `quote_required` and `contract_only` → never eligible (no price exists on
  the variant in either case, per D3's resolution); unknown mode → not
  eligible to an unaware Platform. This is a behavioral producer/consumer
  rule, not a new schema constraint (JSON Schema cannot check which modes a
  given Platform understands).
- When present over a mixed product, `price_range` MUST be computed only
  over range-eligible variants — never zero-filled or synthesized for
  ineligible ones (e.g. variants priced $100 public, `quote_required` with no
  price, and $150 public yield a range of $100–$150, never $0–$150) — and the
  product SHOULD carry a `price_on_request` disclosure warning (clarified
  2026-10-05; no schema change, see D4/the product.json description).
  Consumer-side fallback: if a product contains a pricing mode the Platform
  does not understand, the Platform MUST NOT assume `product.price_range`
  includes only prices safe for it to display — the safest old-consumer
  behavior is to suppress/recompute the range from variants it understands.
  The same principle applies to price filtering. `next_step`'s presence has
  no bearing on range/filter eligibility — eligibility depends solely on
  `pricing.mode` and price usability.
- **NEW (2026-10-05):** when the priced variants underlying a `price_range`
  are `buyer_specific` and resolved for a recognized caller, the resulting
  `price_range` is itself caller-specific and subject to the SAME
  cache-isolation requirement as the underlying buyer-specific prices (D5) —
  a Platform MUST NOT expose or reuse that `price_range` for a different
  caller. JSON Schema cannot verify a range was mathematically derived from
  the correct subset/caller; this is stated as a behavioral/protocol
  requirement.
- **NEW (2026-10-05, refined second pass with "range-eligible" terminology):**
  for a variant carrying an unrecognized/unknown `pricing.mode` alongside a
  numeric `price`, that variant's price is not range-eligible to an unaware
  Platform, which MUST NOT treat it as safely comparable/usable for
  `price_range` computation or filtering (ties to the unknown-mode
  safe-fallback behavior below).
- `list_price_range` (R: already optional): MUST be omitted when no variant
  carries a numeric price; otherwise follows the same rule.

**`common/types/price_filter.json`** (description only): priceless variants are
excluded from min/max matching; a filter MUST NOT treat a missing price as
zero; mixed results apply the filter to priced variants and drop the rest
(the observed implementation reported on the thread, made normative); a
Business MAY surface dropped items via a message.

**`common/types/warning_code.json`**: add `price_on_request` to the freeform
examples — the in-proximity disclosure-rendering vehicle with
`presentation: "disclosure"`.

### Behavioral Changes

1. **Platform display/inference norms (proposed):** a Platform MUST NOT
   display, infer, or compute a selling price for a variant without a `price`
   in the response, and MUST NOT treat a missing price as zero. Explicit
   on-request is distinguishable from accidental omission by validation.
2. **Cache isolation (proposed requirement, see D5; UPDATED 2026-10-05 —
   elevated to explicit normative MUST language, including derived values):**
   a Platform MUST NOT expose or reuse a buyer-specific price, or a value
   derived from that price, for another caller. This explicitly covers (a)
   `variant.price` itself when `pricing.mode` is `buyer_specific`, and (b)
   anything derived from it — in particular `product.price_range` computed
   from buyer-specific variant prices, which is itself caller-specific and
   subject to the same isolation requirement (caching a sanitized/leak-free
   variant price while still caching a buyer-specific product-level
   `price_range` would leak pricing information). Concrete example: Buyer A
   resolves to $875, Buyer B resolves to $740, and an anonymous caller sees no
   price — a response generated for Buyer A MUST NOT be served to Buyer B or
   to the anonymous caller. Mode equality does **not** establish
   shareability: two `buyer_specific` responses with different prices are
   addressed to different buyers, and serving one buyer's priced response (or
   its derived `price_range`) to another buyer is a price leak. Caches
   containing caller-dependent catalog pricing need an identity-aware cache
   key, or must avoid shared caching entirely. The requirement is stated at
   the schema-norm/protocol level; no transport mechanism is prescribed here.
3. **Unknown pricing-mode safe-fallback norm (NEW 2026-10-05, see D1):**
   `pricing.mode` is an open vocabulary. A Platform MUST tolerate values it
   does not recognize. When a Platform does not recognize a pricing mode, it
   MUST treat the item conservatively as having no usable display price: it
   MUST NOT interpret a missing price as zero, MUST NOT display an
   accompanying numeric price as authoritative, and MUST exclude the item
   from numeric price filtering/comparison unless it understands that mode.
   JSON Schema enforces only the data shape (an unknown mode validates with
   or without `price`); this behavioral contract governs consumer display and
   filtering, and cannot itself be validated by the schema.
4. **Catalog→commercial transitions (named, not built):**
   - `buyer_specific` → identity linking → re-request (recognized caller
     receives `buyer_specific` + price, mode retained — see D2).
   - `contract_only` → **RESOLVED 2026-10-05, second pass (see D3), reversing
     the first pass's open framing:** an anonymous caller with a public price
     sees `public` + price; an anonymous caller whose price is gated sees
     `contract_only` with no price; once the caller is identified/entitled,
     the response transitions to `buyer_specific` + price. `contract_only`
     itself remains a genuinely unpriced state — `price` MUST NOT be present
     with it. The alternative of retaining `contract_only` with a price on
     resolution is explicitly rejected, not merely unadopted.
   - `quote_required` → the accepted-commercial-term hand-off (#845) at
     checkout time.
5. **Checkout untouched:** `item.json` still requires `price`; on-request is
   catalog-representation only.
6. **Purchase Options (#901) composition — risk noted, not resolved here (NEW
   2026-10-05, second pass):** this EP does NOT resolve Purchase Options
   (#901), a concurrent draft issue with no schema presence in this
   repository today. #901, as proposed, requires `price` on every purchase
   option, which cannot represent an unpriced `quote_required`/`contract_only`
   option — a genuine composition gap. This EP does not fix that gap by
   loosening `quote_required`/`contract_only` to permit a fake/default
   `price`; instead, the pricing-state model introduced here (`pricing.mode`
   + conditional `price`) should be reusable at finer-grained price-bearing
   nodes if #901 allows those nodes to be unpriced. This must be raised with
   the #901 author/maintainers before incorporation; see DESIGN.md §2D for
   the composition analysis and a non-normative strawman sketch (not
   implemented as schema in this EP).

### Spec prose

New "Pricing state" section in `docs/specification/shopping/catalog/index.md`:
the mode table, the MUST-NOT display/infer/compute-as-zero norm, the
accidental-omission distinguishability rule, the `list_price`/`unit_price`
reference-vs-conflict rules, the transition pointers, the cache-isolation
requirement, and a worked `quote_required` example. `search.md`: the
filter-exclusion prose.

### Decision table

Six decisions were identified during research. For each: the recommended
candidate, the considered alternative(s), and the rationale. All remain open
pending TC/thread confirmation — none is presented as settled.

| # | Decision | Recommendation | Alternative(s) | Rationale |
|---|---|---|---|---|
| D1 | `mode` vocabulary: closed vs open | **UPDATED 2026-10-05 (was: closed enum) — Open vocabulary with explicit safe-fallback handling.** `mode` is a non-empty string (no enum); well-known values are documented as `examples`. Unknown modes are NOT rejected and do NOT get guessed-at semantics: "treat unknown as `public`" would demand a price where none may exist; "treat unknown as `quote_required`" would hide a real price. Instead, the behavioral contract requires a Platform to treat an unrecognized mode conservatively — no usable display price, excluded from price filtering/sorting — without the schema itself asserting anything about `price`'s presence. | (a) Closed enum, unknown modes rejected by validation (the prototype's original recommendation) — simpler for validating consumers, but blocks a Business from introducing a new mode without breaking older validators; the original rationale for rejecting the open-vocabulary route (needing explicit unknown-mode handling) is resolved by the safe-fallback contract instead of being avoided. (b) Open with a "treat unknown as public" fallback — still rejected: forces price-requiredness onto payloads whose price status is unknown. | Forward compatibility requires a future producer to introduce a new pricing mode without an older schema-validating consumer rejecting the whole payload. The safe-fallback behavioral contract (conservative treat-as-unpriced) resolves the original concern (guessing at an unknown mode's meaning) without needing to close the vocabulary. A generated SDK's binding for `mode` must preserve unknown string values rather than failing deserialization on an unrecognized enum member. |
| D2 | `buyer_specific` with vs without numeric price | **UPDATED 2026-10-05 (was: recommendation among two live options) — (ii) Priced for recognized callers is now the PROPOSED NORMATIVE behavior, not merely a recommendation.** `buyer_specific` MAY carry `price` when the response is addressed to a recognized buyer, and omits it for anonymous callers; when present, `mode` MUST remain `buyer_specific`. The mode then documents the disclosure context of *this response* ("this price is specific to you, the caller"), directly supported by evoleinik's reported live-implementation behavior. | (i) Always omit price for non-public modes (juanferrub's original direction): `price` MUST NOT be present with `buyer_specific` either. Simpler validation and no same-mode cache-leak class — but the disclosure boundary is lost, and for sellers that already serve priced responses to linked buyers (e.g. the NDA vendor in #877) it discards price information the seller already discloses. **Not adopted.** | evoleinik's reported live-implementation behavior is the direct support for adopting (ii) as the proposed resolution; the D5 cache-isolation requirement (now normative MUST language, including derived `price_range`) covers the leak risk (ii) introduces. |
| D3 | `contract_only` entitled-caller path | **RESOLVED 2026-10-05, second pass — reverses the first pass's deliberate open relaxation.** New maintainer guidance selects the per-caller transition: `{"pricing": {"mode": "contract_only"}}` (no price) is the stranger-with-gated-price state; `{"pricing": {"mode": "buyer_specific"}, "price": {...}}` is the entitled/recognized-customer state. `contract_only` + a numeric `price` is REJECTED again — the schema's "forbid price" rule is restored to cover both `quote_required` and `contract_only`. `contract_only` and `buyer_specific` now have a coherent, distinct meaning: `contract_only` describes the unresolved response to a caller who has not established entitlement; `buyer_specific` describes the response after the Business has resolved pricing in the current buyer context. The underlying pricing algorithm (contract, NDA, customer type, region, volume agreement, negotiated discount, or otherwise) does not require separate Catalog modes. | (a) Per-caller mode transition — **ADOPTED.** (b) Commercial-term hand-off (#845) delivers the price at checkout only: cannot serve catalog display ("your contract price: $X" on the product page) — not adopted as the sole mechanism, but the catalog/commercial separation is retained. (c) `contract_only` permits price for entitled callers directly (mode describes the anonymous posture only) — **explicitly REJECTED** by this update; the first pass's relaxation that made this schema-valid is reverted. | This was the principal remaining open semantic decision; new maintainer guidance resolves it in favor of (a). Keeping two modes (`contract_only` vs `buyer_specific`) is justified because they now carry a coherent meaning (unresolved vs resolved), not merely "anonymous posture." |
| D4 | Reference prices & range aggregation | **(a) `list_price` legitimate reference:** MAY accompany an unpriced variant (strikethrough "List $100" beside the disclosure), with a MUST-NOT-treat-as-selling-price norm — no schema change (already optional). **(b) `unit_price` conflict:** MUST NOT be present without `price` (schema-enforced); it is a per-unit *selling* price and conflicts with a no-price mode (REVERSED 2026-10-05: `contract_only` is doubly excluded again — both by the restored "forbid price" rule and by `unit_price`'s separate requirement that `price` be present). **(c) Range aggregation:** `price_range` required iff every variant carries a range-eligible price; mixed products MAY omit or compute over range-eligible variants only (+ SHOULD warn) — REFINED 2026-10-05, second pass: "carries a numeric price" is replaced by **"range-eligible price"** (a numeric price whose pricing semantics the Platform understands as usable for this caller), because an unknown `mode` may legally coexist with a numeric `price` for forward compatibility, and an unaware Platform must not fold that price into a range. `quote_required` and `contract_only` are never range-eligible (no price exists on the variant either way). Computed ONLY over range-eligible variants, never zero-filled; omitted when none is eligible; `list_price_range` MUST be omitted when none is eligible. A caller-specific `price_range` from `buyer_specific` priced variants is subject to the same cache-isolation requirement as D5. `next_step`'s presence has no bearing on range/filter eligibility. | Indicative "from $X" alongside `quote_required` (banned in the prototype): defensible against ambiguous display, but narrows real B2B practice — left as an EP open question for TC; see D3's rationale for why `price` itself must not be overloaded for this (use `list_price` or a future indicative-price construct). Alternative range rule "omit whenever any variant is priceless": simpler, but hides priceable items from price summaries. | Reference-vs-selling-price is the semantic line already in the released schema (`list_price` is pre-discount display data); extending it to unpriced variants is additive. The aggregation rule preserves the released invariant for all-priced products exactly while keeping mixed listings honest, and the range-eligibility refinement keeps it honest even under an open `mode` vocabulary. |
| D5 | Buyer/entitlement cache isolation | **UPDATED 2026-10-05 — elevated to explicit normative MUST language, including derived values.** A Platform MUST NOT expose or reuse a buyer-specific price, or a value derived from that price (explicitly including a `product.price_range` computed from buyer-specific variant prices), for another caller — **including two responses with the same `buyer_specific` mode but different prices** (mode equality does not establish shareability; the isolation key must include the identity/entitlement context, not just the mode). Concrete example: Buyer A → $875, Buyer B → $740, Anonymous → no price; a response generated for Buyer A must not be served to Buyer B or anonymous. Caches containing caller-dependent catalog pricing need an identity-aware cache key, or must avoid shared caching entirely. Mechanism (headers, cache keys) is out of scope; the requirement is stated, not the transport. | (a) No stated rule: leaves price leaks to implementation luck — rejected; the leak class is real and introduced by per-response modes. (b) Prescribe a specific transport mechanism: premature for a schema EP; vendors differ. | Per-response modes make a cached anonymous `buyer_specific` response served to a linked buyer wrong, and a priced one served cross-buyer a leak — now extending explicitly to any derived `price_range`, since a sanitized variant price cached alongside a buyer-specific product-level range would still leak pricing information. The requirement is the minimum normative content; mechanism can follow in a conformance or guidance note. |
| D6 | Feed representation (#866) & compatibility/versioning | **Feed:** no separate schema change — feed records are catalog Products, so the rule covers feeds; the feed capability doc (#866, draft) takes the aggregation sentence as a documented dependency when it merges. **Compatibility (qualified, not additive; UPDATED 2026-10-05):** relaxing `required` opens the intended cases, but previously-valid payload classes still *narrow* — `price` + `quote_required` (conflict rejection, scoped to BOTH `quote_required` AND `contract_only` again as of D3's second-pass reversal — the first pass had scoped this to `quote_required` only) and malformed `pricing` shapes (`pricing: null`, `pricing: {}`, non-object `pricing`) that the baseline ignored via `additionalProperties` but the proposal rejects as ill-formed. Unknown `pricing.mode` *values* still do not narrow (D1's open vocabulary, unaffected by D3's reversal) — this reduces, but does not eliminate, the qualified-compatibility finding; the conflict-rejection narrowing is now the same shape as before D3's first-pass relaxation. A NEW compatibility class: a consumer generated from a closed `mode` enum (e.g. a generated SDK) may reject/fail-to-deserialize a future mode value unless `mode` is represented as an extensible/open string type in codegen. Old schema-validating consumers reject new on-request payloads (safe direction; executed for the Python SDK, statically corroborated for JS); lenient non-validating consumers may still misread missing price as $0.00 — the proposed MUST-NOT norm binds future implementations, not deployed code. **Release classification: unresolved** — minor vs major is a TC/versioning decision (date-based versioning; breaking changes need Governing Council majority per CONTRIBUTING.md). The staged `feat:` prefix is provisional. | Claiming pure additivity: false and struck — see the validity-change table in the prototype COMPATIBILITY.md. Pre-classifying the release: out of the EP author's hands; left to TC. | Honest compatibility is load-bearing for this EP: these narrowing classes defeat the easy "nothing breaks" story, and the feed dependency must be recorded so #866's doc lands with the aggregation rule rather than rediscovering it. |

**Coherent candidate design (the proposal in one paragraph; UPDATED 2026-10-05,
second pass):** object-form `pricing` with an **open-vocabulary** `mode` (D1)
plus informational `reason`/`next_step` (orthogonal to `price`, never part of
the conditional rules); caller-dependent per-response modes; `if`/`then`
conditional requiredness with a conflict ban covering BOTH `quote_required`
AND `contract_only` (D3, **RESOLVED** this pass, reversing the first pass's
relaxation); `buyer_specific` priced for recognized callers is the **proposed
normative** behavior (D2-ii), with `mode` required to remain `buyer_specific`
when a price is present; `contract_only`'s entitled-caller path is **RESOLVED**
via the per-caller transition — stranger-with-gated-price → `contract_only`
(no price); entitled/recognized customer → `buyer_specific` + price (D3);
`list_price` as legitimate reference, `unit_price` conflict-banned (doubly, for
`contract_only`), ranges aggregated over **range-eligible** variants only,
never zero-filled (D4, refined this pass); a normative cache-isolation
requirement including same-mode different-price responses AND any derived
`price_range`, now with the nuance that `buyer_specific` does not imply
per-person-computed uniqueness (D5); an explicit safe-fallback behavioral
contract for unrecognized `mode` values (no schema rejection, conservative
consumer treatment); a documented, non-normative composition risk for the
concurrent draft issue #901 (Purchase Options), explicitly not resolved here
and not implemented as schema; feed covered by the schema rule with a doc
dependency on #866; qualified compatibility — the conflict-rejection
narrowing is restored to its pre-first-pass shape (D1's unknown-mode
narrowing stays resolved, unaffected) — with release classification left to
TC (D6). Checkout is untouched and no quote workflow is defined. A possible
future split of `pricing` into separate visibility/access-policy and
price-provenance dimensions is noted as an alternative below but is
explicitly NOT implemented as a schema field.

## Alternatives and Open Questions

**`contract_only`'s entitled-caller path is now RESOLVED (see D3), reversing
the first pass's deliberately-open framing.** The selected working design:
the entitled caller receives `buyer_specific` + price; `contract_only` itself
remains a genuinely unpriced state. The alternative — retaining
`contract_only` + price on resolution — is explicitly rejected. This remains
prototype behavior pending formal EP/TC adoption.

**New alternative/risk surfaced this pass, explicitly NOT resolved here (see
D.6-bis below and DESIGN.md §2D):** Purchase Options (#901), a concurrent
draft issue (#901), as proposed, requires `price` on every purchase option and so
cannot represent an unpriced `quote_required`/`contract_only` purchase
option. This EP does not fix that gap by loosening `quote_required`/
`contract_only` to accept a fake/default `price` — the fix, if adopted,
belongs at the purchase-option granularity in #901's own schema, reusing this
EP's pricing-state model. Must be raised with the #901 author/maintainers
before incorporation.

**Alternative considered and explicitly rejected for this update (scope
discipline):** splitting `pricing` into two separate dimensions — a
visibility/access-policy axis (who may see a price) and a price-provenance
axis (how/why the price was determined) — rather than the single `mode`
field doing both jobs. This might eventually clarify cases where `mode`
currently conflates "is a price shown" with "why isn't one shown," but it is
a larger schema restructuring than this update's scope, and the existing
`reason`/`next_step` fields already provide an informational escape hatch for
provenance-like detail without a schema change. This update does not
implement that split as a schema field; it is noted here as a possible
future direction for the EP process to consider, not a recommendation to
pursue it now.

## Risks and Mitigations

- **Security — cross-buyer price disclosure via caching.** Per-response modes
  create a new leak class: a cached priced `buyer_specific` response served to
  a different buyer discloses a negotiated price — and (UPDATED 2026-10-05)
  the same risk extends to a `product.price_range` derived from
  buyer-specific variant prices, which is itself caller-specific. *Mitigation:*
  the D5 normative no-reuse requirement, now explicit that it covers both the
  price itself and values derived from it (mode equality ≠ shareability);
  conformance guidance to follow before Candidate stage.
- **Security — lenient consumers misread priceless as $0.00.** The exact harm
  #877 reports; validation cannot reach deployed non-validating code.
  *Mitigation:* the MUST-NOT-display/infer/compute-as-zero norm; fail-closed
  direction for validating consumers (executed); disclosure-warning code for
  in-proximity rendering.
- **Security — unrecognized pricing mode misread as priced/free/filterable.**
  (NEW 2026-10-05) Since `mode` is now open, a consumer could encounter a
  value it doesn't recognize. *Mitigation:* the explicit safe-fallback
  behavioral norm (treat as no usable display price; exclude from numeric
  filtering/sorting) — schema cannot enforce this, so it is stated
  normatively in the spec prose and EP draft.
- **Performance.** The `allOf` branches add a constant number of cheap
  conditional checks per variant; no new endpoints, no extra round trips, no
  server-side computation beyond range aggregation over priced variants
  (linear in variant count). No performance benchmark was run; validation
  cost is unmeasured at this stage.
- **Backward Compatibility.** Qualified, not purely additive (see D6): several
  previously-valid payload classes still narrow (conflict rejection — scoped
  to BOTH `quote_required` AND `contract_only` again, per D3's second-pass
  reversal — and malformed-`pricing` shapes), and a business already emitting
  a `pricing`-shaped extension field (the baseline schema permits additional
  properties) could see payloads newly rejected. **UPDATED 2026-10-05:** the
  unknown-mode narrowing class stays removed (D1's open vocabulary, unaffected
  by D3's reversal), and a NEW generated-SDK closed-enum compatibility class is
  added instead (a generated SDK binding `mode` to a closed enum may still
  reject an unrecognized value even though the schema itself now accepts it).
  *Mitigation:* fail-closed direction for validating old consumers (they
  reject rather than misread); the field-name collision survey
  (`com.shopware.quote`, `com.ucpready.procurement` candidates found —
  incomplete) must complete before Provisional; codegen guidance to represent
  `mode` as an open/extensible string type, not a closed enum; release
  classification is an explicit TC decision.
- **Composition — Purchase Options (#901) cannot represent unpriced options.**
  (NEW 2026-10-05, second pass.) A concurrent draft issue (#901), as proposed,
  requires `price` on every purchase option, so it cannot represent an
  unpriced `quote_required`/`contract_only` option today. *Mitigation:* this EP
  does not resolve #901 and does not fix the gap by loosening
  `quote_required`/`contract_only` to accept a fake/default `price` on the
  Variant; the composition requirement and a non-normative strawman sketch are
  documented (DESIGN.md §2D) for the #901 author/maintainers to consider —
  option-level pricing-state granularity is the likely eventual fix, kept out
  of this EP's scope.
- **Complexity.** One new optional object + four conditional branches; the
  per-response (caller-dependent) semantics ask consumers to treat identical
  variant IDs as different responses — a genuine conceptual cost.
  *Mitigation:* keep `reason`/`next_step` informational (no workflows to
  maintain; `next_step` is documented as orthogonal to `price` — see D3);
  name transitions instead of building them; conformance suite updates are
  staged as implementation work, not EP content.

## Test Plan

**Unit Tests** (schema/logic level):
- Per-mode fixture vectors against baseline and proposed schemas
  (jsonschema 4.10.3, draft 2020-12): priced baselines (no regression),
  per-mode on-request payloads, accidental omission (must stay invalid),
  conflict (`price` + `quote_required` — must reject; `price` +
  `contract_only` — REVERSED 2026-10-05, second pass: must reject again,
  reversing the first pass's relaxation, see D3), `price` + `quote_required`
  + `next_step` (must still reject — `next_step` does not change this),
  `unit_price` without `price` (must reject), unknown/bogus modes (must
  ACCEPT, with or without `price`, per D1's open vocabulary — unaffected by
  the `contract_only` reversal), `next_step` orthogonality (`buyer_specific`/
  `public` + `price` + `request_quote` must accept), `list_price` reference on
  unpriced variants (must accept), `list_price_range` on all-priceless
  products (must reject).
  Current state: **42/42 passing** (prototype harness
  `research/price-on-request/harness/`; 28 vectors from the original
  publication, 8 added 2026-10-05 (first pass) for the initial
  maintainer-feedback update, and 6 more added 2026-10-05 (second pass) for
  the `contract_only` reversal and `next_step` orthogonality cases — public
  with price, contract-gated stranger without price, the NDA
  `buyer_specific`+price+`request_quote` case, the `public`+price+
  `request_quote` orthogonality case, the `quote_required`+price+
  `request_quote` invalid case, and a mixed product with an unknown-mode
  priced variant — plus one fixture (`onrequest_variant_contract_only_priced.json`)
  whose expected verdict flipped from valid to invalid; see the dated log
  under `research/price-on-request/logs/`, exit 0). Harness leg G additionally
  fuzzes 300 variants and 300 mixed-mode products crossing every known/unknown
  mode with price absent/present, 0 mismatches, with its expected-verdict
  helper updated so `contract_only` forbids `price` again.
- "Range-eligible price" edge cases (REFINED 2026-10-05, second pass, from
  "carries a numeric price"): `amount: 0` counts (free is priced); priced
  `buyer_specific` counts for that caller; `contract_only`/`quote_required`
  never count (no price exists either way); priceless does not count; an
  unknown mode with a numeric price is schema-valid but not range-eligible to
  an unaware Platform (behavioral, not schema-checkable).
- Purchase Options (#901) composition illustrations (DESIGN.md §2D) are
  documented examples only — they are NOT wired into the counted harness
  pass/fail legs, since no `purchase_option.json` schema exists in this repo
  to validate against.
- Differential fuzz: 300 seeded priced variants + 300 products, 0 verdict
  mismatches — **scoped to the generated priced subset only**; it establishes
  no-regression for that subset, not universal compatibility (the validity
  table above shows the narrowing classes).

**Integration Tests:**
- Old SDK legs: the Python SDK (ucp-sdk 0.4.6, pydantic — executed) rejects
  new on-request payloads (`price: Field required`); the JS SDK 0.5.1
  (published tarball, zod-generated schemas — **live-validated 3/3 in the
  2026-10-02 re-run**: priced accepted, on-request rejected, priced
  `buyer_specific` accepted). Regenerated-SDK enforcement assertions are
  blocked (see below) and must run in CI before Provisional.
- New consumer behavior: price-filter exclusion of priceless variants; the
  MUST-NOT-treat-as-zero norm; cache-isolation behavior across buyer contexts.

**End-to-End Tests** (user scenarios to automate):
- B2B contract catalog: anonymous caller sees `contract_only`, no price;
  entitled caller sees `buyer_specific` + price after identity linking.
- NDA software vendor: anonymous → `buyer_specific` (no price); linked
  buyer → `buyer_specific` + price; cross-buyer cache reuse is refused.
- Lessor catalog: `quote_required` variants render with the disclosure
  warning; checkout still requires a price via the accepted-term hand-off.
- Search with a max-price filter drops on-request items from matching but the
  Business MAY surface them via a message.

**Verification state (2026-10-02, clean-environment re-runs; self-review):**
- `ucp-schema lint source/` (v1.4.1, installed via cargo): **passes** — 144
  files, exit 0 (only pre-existing W002 warnings on untouched files).
- `mkdocs build --strict`: **exit 0**, 0 warnings; the new "Pricing state"
  section renders (CI's `build_local.sh --draft-only` also exit 0).
- Live JS SDK (`@ucp-js/sdk@0.5.1`, zod 3.25.76, npm reachable in re-run):
  **3/3 pass** — priced payload accepted, on-request payload rejected
  (`price: Required`), `buyer_specific`+price accepted. This validates the
  old SDK's fail-closed baseline, not the new rules.
- Prototype harness: **42/42 vectors, 300+300 fuzz with 0 mismatches**,
  SDK leg 3/3, exit 0 (updated 2026-10-05, second pass, for the `contract_only`
  reversal; see the dated log under `research/price-on-request/logs/`).
- **`scripts/validate_examples.py`: RUNS but FAILS on the patched tree —
  374 passed, 3 failed vs 376/0 on the unpatched baseline (all 3
  patch-caused).** The patch's own new doc example (`catalog/index.md`,
  `get_product` scaffold) merges a `price_range` into a priceless product
  and is rejected by the new rule; two pre-existing doc examples
  (`catalog/mcp.md`, `catalog/rest.md`) elide `variants: [...]` and trip
  the same rule. The doc scaffold needs a mode-aware update before any
  implementation PR — recorded here as a genuine finding, not a blocker
  on the EP itself.
- **SDK generation (`sdk/python/generate_models.sh`): blocked by a
  patch-independent pre-existing bug** — python-sdk's
  `preprocess_schemas.py` mangles the property literally named `anyOf` in
  `constraint_expression.json`; the file is byte-identical in the
  unpatched baseline, so this is python-sdk-vs-ucp drift, not caused by
  this proposal. No models were emitted, so generated-model enforcement
  assertions could not run; left incomplete, no substitute test offered.
  Separately, the generation logs show the SDK generator **skipping
  unsupported conditional rules** (`if`/`then`) across existing schemas —
  so even with the preprocessing bug fixed, whether the generator would
  emit this proposal's new conditional requirements is unresolved and
  must be verified before Candidate stage. Both must be resolved
  (upstream or locally) before Candidate stage, since generated SDKs
  are the enforcement vehicle for validating consumers.

All validation evidence is self-review, not independent validation.

## Graduation Criteria

**Working Draft → Candidate:**

* [ ] Schema merged and documented (with Working Draft disclaimer).
* [ ] Unit and integration tests are passing.
* [ ] Initial documentation is written.
* [ ] TC majority vote to advance.

**Candidate → Stable:**

* [ ] Adoption feedback has been collected and addressed.
* [ ] Full documentation and migration guides are published.
* [ ] TC majority vote to advance.

## Implementation History

*This section will be updated by the maintainers as the proposal moves through
its lifecycle.*

* [YYYY-MM-DD]: Proposal submitted.
* [YYYY-MM-DD]: TC approved "Provisional"; capability enters "Working Draft".
* [YYYY-MM-DD]: TC approved advancement to "Candidate".
* [YYYY-MM-DD]: TC approved "Implemented"; capability enters "Stable".

(Note: this EP has **not yet been submitted** — the dates above are the
template's placeholders. No implementation PR may be opened until the EP is
TC-approved, per CONTRIBUTING.md.)

## Code of Conduct

- [ ] I agree to follow this project's Code of Conduct
