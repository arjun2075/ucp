# Enhancement Proposal DRAFT — Price-on-request catalog pricing state (UNSENT)

**Status: UNSENT DRAFT. Do not file without the user's explicit word on this
exact text.** Per org CONTRIBUTING.md, this follows the required EP template
(Summary, Motivation, Detailed Design, Risks, Test Plan, Graduation Criteria)
and would enter the lifecycle at **Proposal** (anyone can submit) → Provisional
(TC majority vote) → Implemented (TC majority vote, code complete and merged).

- **Linked issue:** Universal-Commerce-Protocol/ucp#877 ("Catalog items with no
  public price")
- **Credits:** @evoleinik (issue author; live-implementation lessons from two
  sellers); @juanferrub (pricing-state object sketch: four modes +
  `reason`/`next_step`); prototype + validation harness prepared in research
  (see `patch/price-on-request-prototype.diff`, `harness/`).
- **Prototype base:** `Universal-Commerce-Protocol/ucp @ b0e81ad`
- **Self-review:** this draft was prepared by a single research pass; it has
  not been independently reviewed and implies no maintainer or TC agreement.

---

## Summary

Add an optional `pricing` pricing-state object to catalog Variants so a Business
can explicitly declare "no public price for this item" in the schema, instead of
misusing `amount: 0` or shipping schema-invalid payloads. `variant.price` and
`product.price_range` become conditionally (not unconditionally) required via
`if`/`then` gating:

- `pricing` absent or `mode: public` → `price` REQUIRED (status quo)
- `mode: quote_required | contract_only` → `price` MUST NOT be present, nor
  `unit_price` (a per-unit selling price)
- `mode: buyer_specific` → `price` optional; mode describes *this response*
  (anonymous caller vs recognized buyer)
- `product.price_range`: required when every variant is priced; omittable over
  mixed products (computed over priced variants only); omitted when none is priced.
  `list_price_range` remains optional and MUST be omitted when none is priced.
- `list_price` (pre-discount reference) MAY accompany an unpriced variant;
  `unit_price` requires `price`
- Price filters exclude priceless variants and MUST NOT treat missing price as
  zero; `price_on_request` warning code added for disclosure rendering

Checkout is untouched (`item.price` still required). No quote, RFQ, expiry,
invoice, or payment workflow is defined — on-request is catalog representation
only. A local prototype with 20 executable fixture vectors and differential
fuzz evidence is staged alongside this draft.

## Motivation

UCP issue #877 documents the gap with a concrete figure: one reporter has 318
products with no public price and three broken options today — misleading
`$0.00` display, schema-invalid omission, or dropping the items from the
catalog (losing them to `ask`-based discovery). Two live sellers (per
@evoleinik) already work around this outside the schema. The released schema
cannot represent the situation: `variant.price` is unconditionally required,
`amount: 0` means free, and a vendor extension cannot relax `required`
(verified by execution: `allOf` composition cannot retract the base's required
list — the priceless payload fails identically with or without an extension
marker). Per CONTRIBUTING.md's versioning guidance ("new features should
typically be attempted through the extensions framework first"), the extension
route was attempted and is mechanically insufficient — hence a core-schema
proposal.

## Detailed Design

### Schema changes (`source/schemas/`)

**`shopping/types/variant.json`**
- `required` drops `"price"` (now conditional).
- New optional `pricing` object: `mode` (required string, closed enum —
  see open decision D1), `reason` (optional, Business-defined informational),
  `next_step` (optional; well-known value `request_quote`; informational only,
  defines no workflow).
- `allOf` branch 1: `pricing.mode ∈ {quote_required, contract_only}` →
  `price` and `unit_price` MUST NOT be present (conflicting price signals
  rejected).
- `allOf` branch 2: `pricing` absent or `mode: public` → `price` REQUIRED.
- `allOf` branch 3: `unit_price` present → `price` REQUIRED (unit price is
  derived from the selling price).
- `list_price`: unchanged (optional); prose clarifies it is a legitimate
  reference price on unpriced variants and MUST NOT be treated as the selling
  price.

**`shopping/types/product.json`**
- `required` drops `"price_range"` (now conditional).
- `allOf`: `price_range` REQUIRED iff every variant carries a numeric price
  (`price` present; `amount: 0` counts); MAY be omitted when ≥1 variant is
  priceless; MUST be omitted when none is priced. When present over a mixed
  product, MUST be computed over priced variants only; product SHOULD carry a
  `price_on_request` disclosure warning.
- `list_price_range` (already optional): MUST be omitted when no variant is
  priced (new `allOf` branch); otherwise follows the same rule.

**`common/types/price_filter.json`** (description only): priceless variants are
excluded from min/max matching; a filter MUST NOT treat a missing price as
zero.

**`common/types/warning_code.json`**: add `price_on_request` to the examples.

### Spec prose (`docs/specification/shopping/catalog/`)

New "Pricing state" section in `index.md`: the mode table, the Platform
MUST-NOT-display/infer/compute-or-treat-as-zero norm, the accidental-omission
distinguishability rule, the `list_price`/`unit_price` reference-vs-conflict
rules, the catalog→commercial transition pointers (identity linking for
`buyer_specific`; the accepted-commercial-term hand-off for quotes — named, not
invented), and a worked `quote_required` example. `search.md`: filter-exclusion
prose.

### What is explicitly NOT in scope

Quote/RFQ creation, quote locking or expiry, invoice or payment workflows,
account-identity or entitlement machinery, cache transport mechanisms, feed
(#866) capability-doc text (schema rule covers feed records since they are
Products, but the feed doc needs the aggregation sentence when #866 merges).

## Risks

- **Compatibility is qualified, not purely additive.** The baseline schema
  permits additional properties, so a `pricing` field could already exist in
  the wild; under this proposal two previously-valid payload classes narrow:
  `price` + `quote_required`/`contract_only` (conflict rejection) and unknown
  `pricing.mode` values (closed enum). **Release classification (minor vs
  major) is an open decision** (date-based versioning; breaking changes need
  Governing Council majority). The staged `feat:` prefix is provisional.
- **Fail-closed is consumer-dependent.** Schema-validating consumers reject new
  on-request payloads (verified: Python SDK pydantic `Field required`,
  executed; JS SDK zod `Required`, static tarball corroboration). Lenient
  non-validating consumers may misread a missing price as $0.00 until they adopt
  the MUST-NOT norm — the exact harm #877 reports.
- **Per-response modes and caching.** A cached anonymous `buyer_specific`
  response served to a linked buyer (or vice versa) is wrong and can leak
  prices. Requirement: cache isolation must prevent reuse across incompatible buyer or entitlement
  contexts, including different prices under the same `buyer_specific` mode. No transport mechanism is prescribed here
  (open decision D3).
- **Field-name collision.** Variant has no `additionalProperties: false`;
  existing vendor extensions may already use a `pricing` key (candidates found:
  `com.shopware.quote`, `com.ucpready.procurement` — survey incomplete).
- **`buyer_specific` semantics unconfirmed** (open decision D2): the prototype
  lets recognized callers receive a price under `buyer_specific`; Juan's
  original direction omits price for all non-public modes.
- **`contract_only` has no entitled-price path** (open decision D4): the mode
  bans `price` outright with no named transition for authenticated contract
  customers.

## Test Plan

- **Schema validation:** 20 fixture vectors (priced baselines, per-mode
  on-request payloads, numeric-price consistency cases, negatives) against
  baseline and proposed schemas — 20/20 pass (jsonschema 4.10.3, draft
  2020-12). Vectors: `harness/vectors.json`, fixtures in `harness/fixtures/`.
- **Differential fuzz:** 300 priced variants + 300 priced products, 0 verdict
  mismatches (scoped: generated priced subset only).
- **SDK legs:** old Python SDK rejects on-request payloads (executed); old JS
  SDK declares `price` required (static corroboration).
- **Negative cases:** accidental omission, conflicting price+mode, bogus mode,
  fabricated range, `unit_price` without `price`, `list_price_range` on
  all-priceless products — all rejected as specified.
- **Before implementation PR:** `ucp-schema lint source/`,
  `scripts/validate_examples.py`, `bash sdk/python/generate_models.sh`,
  `pre-commit run --all-files`, `uv run mkdocs build --strict` — **all
  currently blocked/incomplete** (see below).

## Graduation Criteria

- **Proposal → Provisional:** TC majority vote; open decisions D1–D6 resolved
  or explicitly deferred with rationale recorded.
- **Provisional → Implemented:** implementation PR merged (post-EP), conformance
  suite updated for on-request listings, SDK models regenerated, doc examples
  validated, blocked checks green in CI.

## Open decisions (for the EP / TC / thread)

- **D1. Mode enum: closed vs open vocabulary.** Prototype: closed (unknown modes
  fail validation). UCP convention leans to well-known values + MAY-extend.
  An open vocabulary needs explicit handling of unknown modes without mapping
  them to `public` or `quote_required` and inventing semantics. Rejection is the
  closed-vocabulary option. No open-vocabulary handling is settled.
- **D2. `buyer_specific` interpretation.** (i) always omit price vs (ii) priced
  for recognized callers (prototype). Consequences differ for filtering,
  caching, and the disclosure boundary (see DESIGN.md §2A). Needs explicit
  confirmation; evoleinik's report fits both readings.
- **D3. Cache isolation.** Requirement stated (no reuse across incompatible buyer or entitlement
  contexts, including same-mode responses with different prices); mechanism not prescribed. Needs a concrete rule
  before Candidate stage.
- **D4. `contract_only` entitled-price path.** Per-caller mode transition,
  commercial-term hand-off, or entitled-price permission — see DESIGN.md §2B.
- **D5. Feed (#866) spec text.** Schema rule covers feed records; the feed
  capability doc needs the aggregation sentence when #866 merges.
- **D6. Compatibility / release classification.** Minor vs major, and whether
  the narrowing classes (conflict rejection, closed enum) are acceptable as
  minor under the project's date-based versioning.

## Blocked / incomplete checks (recorded honestly)

- `ucp-schema lint source/` and `scripts/validate_examples.py`: Rust toolchain
  build failure in this environment (`logs/ucp_schema_build_fail.log`).
- JS SDK live execution: npm registry unreachable; static tarball corroboration
  only (`logs/js_sdk_check.log`).
- `w3-prototype.md` worker writeup truncated mid-sentence (evidence survives in
  logs/harness; disclosed in README.md).
