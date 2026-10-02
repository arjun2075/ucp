# [Proposal]: Price-on-request catalog pricing state (UCP #877)

> **UNSENT DRAFT — do not file without the user's explicit word on this exact text.**
> This draft was prepared by a single research pass (**self-review**); it has not
> been independently reviewed and claims no maintainer, TC, or community
> consensus. The three questions asked on the thread below remain unanswered as
> of 2026-10-02 ~08:00 PDT.

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
- `mode: quote_required | contract_only` → `price` MUST NOT be present
- `mode: buyer_specific` → `price` optional; the mode describes **this response**
  (anonymous caller vs recognized buyer), per the caller-dependence lesson from
  the issue thread
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
validates 28 fixture vectors at 28/28 and runs 300+300 differential fuzz cases
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
  preserved for priced variants (28/28 fixture vectors; 0 fuzz mismatches on
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
  - `mode` (required when `pricing` is present): string, closed enum —
    `public` | `buyer_specific` | `quote_required` | `contract_only`
    (recommendation, see D1)
  - `reason` (optional string): Business-defined, informational (e.g.
    `contract_or_volume_dependent`). Consumers MUST NOT infer semantics beyond
    `mode`.
  - `next_step` (optional string): well-known value `request_quote`,
    informational only — names no quote/RFQ workflow.
- `required` drops `"price"` (R: `["id","title","description","price"]`).
- New `allOf` branches (draft 2020-12):
  1. `pricing.mode ∈ {quote_required, contract_only}` → `price` and
     `unit_price` MUST NOT be present (conflicting price + no-price assertion
     rejected).
  2. `pricing` absent or `mode: public` → `price` REQUIRED (status quo).
  3. `unit_price` present → `price` REQUIRED (unit price is derived from the
     selling price).
  4. `pricing.mode = buyer_specific` → `price` MAY be present (priced for a
     recognized caller) or absent (anonymous caller); the mode documents the
     disclosure context of *this response*.
- Unknown `pricing.mode` values, empty `pricing: {}`, `pricing: null`, and the
  string form `"pricing": "on_request"` are all rejected (proposed decision,
  see D1).
- `list_price`: unchanged (optional). Prose states it is a legitimate
  pre-discount **reference** price that MAY accompany an unpriced variant (e.g.
  strikethrough "List $100" beside a "request quote" disclosure) and MUST NOT
  be treated as the selling price. It never conflicts with a no-price mode
  because it is explicitly not the transaction price.

**`shopping/types/product.json`**:

- `required` drops `"price_range"` (R: `["id","title","description",
  "price_range","variants"]`).
- New `allOf` rule: `price_range` is REQUIRED when every variant **carries a
  numeric price**; MAY be omitted when ≥1 variant is priceless; MUST be omitted
  when no variant carries a numeric price. "Carries a numeric price" =
  the `price` property is present in this response (`amount: 0` counts — free
  is priced; a priced `buyer_specific` variant counts; a priceless one does
  not).
- When present over a mixed product, `price_range` MUST be computed over
  priced variants only, and the product SHOULD carry a `price_on_request`
  disclosure warning.
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
2. **Cache isolation (proposed requirement, see D5):** a consumer MUST NOT
   serve or reuse a cached catalog response to a caller in a different buyer
   or entitlement context than the response was addressed to. Mode equality
   does **not** establish shareability: two `buyer_specific` responses with
   different prices are addressed to different buyers, and serving one buyer's
   priced response to another buyer is a price leak. The requirement is stated
   at the schema-norm level; no transport mechanism is prescribed here.
3. **Catalog→commercial transitions (named, not built):**
   - `buyer_specific` → identity linking → re-request (recognized caller
     receives `buyer_specific` + price).
   - `contract_only` (entitled caller) → per-caller mode transition: the
     entitled contract customer receives `buyer_specific` + price (see D3).
   - `quote_required` → the accepted-commercial-term hand-off (#845) at
     checkout time.
4. **Checkout untouched:** `item.json` still requires `price`; on-request is
   catalog-representation only.

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
| D1 | `mode` vocabulary: closed vs open | **Closed enum; unknown modes rejected by validation.** An open vocabulary must handle unknown modes explicitly — and it must do so *without* inventing semantics. "Treat unknown as `public`" would demand a price where none may exist; "treat unknown as `quote_required`" would hide a real price. Rejection is the only fail-closed unknown-mode handling, so the candidate is a closed enum now. | (a) Open vocabulary ("well-known values" + MAY-extend) with reject-unknown handling — functionally identical to closed today; TC may open deliberately later with versioned semantics. (b) Open with a "treat unknown as public" fallback — rejected: forces price-requiredness onto payloads whose price status is unknown. | The modes govern whether a price *must* be present; guessing at an unknown mode's meaning is exactly the class of harm #877 reports (misleading $0 display). Deviating from UCP's open-vocabulary convention is justified and is disclosed as such. |
| D2 | `buyer_specific` with vs without numeric price | **(ii) Priced for recognized callers:** `buyer_specific` MAY carry `price` when the response is addressed to a recognized buyer, and omits it for anonymous callers. The mode then documents the disclosure context of *this response* ("this price is specific to you, the caller"), preserving the caller-dependence lesson from evoleinik. | (i) Always omit price for non-public modes (juanferrub's original direction): `price` MUST NOT be present with `buyer_specific` either. Simpler validation and no same-mode cache-leak class — but the disclosure boundary is lost (a linked buyer seeing a price cannot tell public from personalized), and for sellers that already serve priced responses to linked buyers (e.g. the NDA vendor in #877) it discards price information the seller already discloses, requiring a separate priced-response path. | evoleinik's report fits both readings, so evidence does not settle it; the deciding factor is information preservation across the identity-linking transition, with the D5 cache-isolation requirement covering the leak risk (ii) introduces. |
| D3 | `contract_only` entitled-caller path | **(a) Per-caller mode transition:** an authenticated/entitled contract customer receives `buyer_specific` + price — the same transition `buyer_specific` already encodes. `contract_only` then means "never priced in the anonymous posture," keeping the mode's anonymous meaning absolute. | (b) Commercial-term hand-off (#845) delivers the price at checkout: cannot serve catalog display ("your contract price: $X" on the product page). (c) `contract_only` permits price for entitled callers: collapses toward (a) with different labeling, muddying the mode's meaning. | (a) needs no new mode, gives consumers uniform logic ("`buyer_specific` + price = your price"), and keeps the catalog display use case. No quote workflow is invented: the hand-off point (identity linking → re-request) is named, not built. |
| D4 | Reference prices & range aggregation | **(a) `list_price` legitimate reference:** MAY accompany an unpriced variant (strikethrough "List $100" beside the disclosure), with a MUST-NOT-treat-as-selling-price norm — no schema change (already optional). **(b) `unit_price` conflict:** MUST NOT be present without `price` (schema-enforced); it is a per-unit *selling* price and conflicts with a no-price mode. **(c) Range aggregation:** `price_range` required iff every variant carries a numeric price; mixed products MAY omit or compute over priced variants only (+ SHOULD warn); omitted when none is priced; `list_price_range` MUST be omitted when none is priced. "Carries a numeric price" = `price` present, `amount: 0` counts. | Indicative "from $X" alongside `quote_required` (banned in the prototype): defensible against ambiguous display, but narrows real B2B practice — left as an EP open question for TC. Alternative range rule "omit whenever any variant is priceless": simpler, but hides priceable items from price summaries. | Reference-vs-selling-price is the semantic line already in the released schema (`list_price` is pre-discount display data); extending it to unpriced variants is additive. The aggregation rule preserves the released invariant for all-priced products exactly while keeping mixed listings honest. |
| D5 | Buyer/entitlement cache isolation | **Normative no-reuse requirement:** a consumer MUST NOT serve a cached catalog response to a caller in a different buyer or entitlement context than the one the response was addressed to — **including two responses with the same `buyer_specific` mode but different prices** (mode equality does not establish shareability; the isolation key must include the identity/entitlement context, not just the mode). Mechanism (headers, cache keys) is out of scope; the requirement is stated, not the transport. | (a) No stated rule: leaves price leaks to implementation luck — rejected; the leak class is real and introduced by per-response modes. (b) Prescribe a specific transport mechanism: premature for a schema EP; vendors differ. | Per-response modes make a cached anonymous `buyer_specific` response served to a linked buyer wrong, and a priced one served cross-buyer a leak. The requirement is the minimum normative content; mechanism can follow in a conformance or guidance note. |
| D6 | Feed representation (#866) & compatibility/versioning | **Feed:** no separate schema change — feed records are catalog Products, so the rule covers feeds; the feed capability doc (#866, draft) takes the aggregation sentence as a documented dependency when it merges. **Compatibility (qualified, not additive):** relaxing `required` opens the intended cases, but several previously-valid payload classes *narrow* — `price` + `quote_required`/`contract_only` (conflict rejection), unknown `pricing.mode` values (closed enum), and malformed `pricing` shapes (`pricing: null`, `pricing: {}`, non-object `pricing`) that the baseline ignored via `additionalProperties` but the proposal rejects as ill-formed. Old schema-validating consumers reject new on-request payloads (safe direction; executed for the Python SDK, statically corroborated for JS); lenient non-validating consumers may still misread missing price as $0.00 — the proposed MUST-NOT norm binds future implementations, not deployed code. **Release classification: unresolved** — minor vs major is a TC/versioning decision (date-based versioning; breaking changes need Governing Council majority per CONTRIBUTING.md). The staged `feat:` prefix is provisional. | Claiming pure additivity: false and struck — see the validity-change table in the prototype COMPATIBILITY.md. Pre-classifying the release: out of the EP author's hands; left to TC. | Honest compatibility is load-bearing for this EP: these narrowing classes defeat the easy "nothing breaks" story, and the feed dependency must be recorded so #866's doc lands with the aggregation rule rather than rediscovering it. |

**Coherent candidate design (the proposal in one paragraph):** object-form
`pricing` with closed-enum `mode` plus informational `reason`/`next_step`;
caller-dependent per-response modes; `if`/`then` conditional requiredness with
conflict bans for `quote_required`/`contract_only`; `buyer_specific` priced for
recognized callers (D2-ii) and used as the entitled-caller transition for
`contract_only` (D3-a); `list_price` as legitimate reference, `unit_price`
conflict-banned, ranges aggregated over priced variants (D4); a normative
cache-isolation requirement including same-mode different-price responses (D5);
feed covered by the schema rule with a doc dependency on #866; qualified
compatibility with release classification left to TC (D6). Checkout is
untouched and no quote workflow is defined.

## Risks and Mitigations

- **Security — cross-buyer price disclosure via caching.** Per-response modes
  create a new leak class: a cached priced `buyer_specific` response served to
  a different buyer discloses a negotiated price. *Mitigation:* the D5
  normative no-cross-context-caching requirement (mode equality ≠
  shareability); conformance guidance to follow before Candidate stage.
- **Security — lenient consumers misread priceless as $0.00.** The exact harm
  #877 reports; validation cannot reach deployed non-validating code.
  *Mitigation:* the MUST-NOT-display/infer/compute-as-zero norm; fail-closed
  direction for validating consumers (executed); disclosure-warning code for
  in-proximity rendering.
- **Performance.** The `allOf` branches add a constant number of cheap
  conditional checks per variant; no new endpoints, no extra round trips, no
  server-side computation beyond range aggregation over priced variants
  (linear in variant count). No performance benchmark was run; validation
  cost is unmeasured at this stage.
- **Backward Compatibility.** Qualified, not purely additive (see D6): several
  previously-valid payload classes narrow (conflict rejection, unknown-mode
  rejection, and malformed-`pricing` shapes), and a business already emitting a `pricing`-shaped extension
  field (the baseline schema permits additional properties) could see payloads
  newly rejected. *Mitigation:* fail-closed direction for validating old
  consumers (they reject rather than misread); the field-name collision survey
  (`com.shopware.quote`, `com.ucpready.procurement` candidates found —
  incomplete) must complete before Provisional; release classification is an
  explicit TC decision.
- **Complexity.** One new optional object + four conditional branches; the
  per-response (caller-dependent) semantics ask consumers to treat identical
  variant IDs as different responses — a genuine conceptual cost.
  *Mitigation:* keep `reason`/`next_step` informational (no workflows to
  maintain); name transitions instead of building them; conformance suite
  updates are staged as implementation work, not EP content.

## Test Plan

**Unit Tests** (schema/logic level):
- Per-mode fixture vectors against baseline and proposed schemas
  (jsonschema 4.10.3, draft 2020-12): priced baselines (no regression),
  per-mode on-request payloads, accidental omission (must stay invalid),
  conflict (`price` + `quote_required`/`contract_only` — must reject),
  `unit_price` without `price` (must reject), bogus mode (must reject),
  `list_price` reference on unpriced variants (must accept),
  `list_price_range` on all-priceless products (must reject). Current state:
  28/28 passing (prototype harness `research/price-on-request/harness/`;
  the 8 malformed/colliding vectors expanding the original 20 are
  follow-through additions — local until published, see Evidence
  provenance above).
- "Carries a numeric price" edge cases: `amount: 0` counts (free is priced);
  priced `buyer_specific` counts; priceless does not.
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
- Prototype harness: **28/28 vectors, 300+300 fuzz with 0 mismatches**,
  SDK leg 3/3, exit 0.
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
