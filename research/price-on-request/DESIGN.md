# DESIGN — representation comparison, prototype, and design decisions

Condensed from `work/w2-representation.md` (+ `work/exp-por/`) and
`work/w3-prototype.md`. All schema behavior below is **PROPOSED**; released text is
labeled as such.

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
(`{"pricing": {"mode", "reason"?, "next_step"?}}`, closed enum) — see §2 for why.
The validated mechanism (conditional requiredness) transfers unchanged; only the
marker's shape changed. (b) remains the runner-up; (c) is refuted.

## 2. Chosen prototype

`pricing` — optional **object** on catalog Variant:

- `mode` (required, closed enum): `public` | `buyer_specific` | `quote_required` | `contract_only`
- `reason` (optional string): Business-defined, informational (e.g.
  `contract_or_volume_dependent`); consumers MUST NOT infer semantics beyond `mode`
- `next_step` (optional string): well-known value `request_quote`; informational only —
  defines no quote/RFQ/identity-linking workflow

Conditional requiredness (`allOf`, draft 2020-12):
- `pricing` absent or `mode: public` → `price` REQUIRED (status quo, fail-closed default)
- `mode: quote_required | contract_only` → `price` MUST NOT be present (conflicting
  price + no-price assertion is rejected)
- `mode: buyer_specific` → `price` optional: present for a recognized buyer, absent
  for an anonymous caller — **mode describes *this response*, not a fixed variant
  property** (evoleinik's caller-dependence lesson, encoded)
- Unknown modes, empty `pricing: {}`, `pricing: null`, and the string form
  `"pricing": "on_request"` are all rejected (verified in `logs/pass2_edge_cases.log`)

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
- Closed enum (fail-closed on unknown modes) vs UCP's open-vocabulary convention
  ("well-known values" + MAY-extend). An open vocabulary needs explicit unknown-mode handling without inventing
  public-price or quote semantics; the EP must decide explicitly.
- `quote_required` + indicative "from $X" price is banned (conflict rejection).
  Defensible against ambiguous display, but narrows real B2B practice — EP scope.
- Mixed-product `price_range` over priced variants only can mislead (e.g. $10–$20
  range beside enterprise on-request variants); mitigation is SHOULD-disclosure,
  not MUST. EP may strengthen.

## 2A. `buyer_specific`: two interpretations (OPEN — EP must decide)

The prototype implements interpretation **(ii)**: `buyer_specific` MAY carry a
numeric price when the response is addressed to a recognized buyer; the mode then
documents disclosure context ("this price is specific to you, the caller").

Interpretation **(i)** — Juan's original direction ("omit price for non-public
modes"): non-public modes never carry a price. Under (i), `buyer_specific` means
"a price exists but is not in this response"; the buyer obtains it through a
separate step (identity linking → re-request, or a quote hand-off).

| Consequence | (i) always omit | (ii) priced for recognized caller (prototype) |
|---|---|---|
| Filtering | Priceless variants dropped from price filters, uniformly | A priced `buyer_specific` variant participates in filters for that caller |
| Caching | Cached response carries no price — leak impossible from the payload | Cached priced response served to a different buyer **is a price leak**; needs the cache-isolation rule urgently |
| Disclosure boundary | Mode has one meaning ("no price here") | Mode does double duty ("no public price" + "here is your price"); consumers must read `mode` to distinguish from `public` |
| Evoleinik's data | Anonymous → `buyer_specific`, linked → priced | Same observable behavior — his report is compatible with both and does **not** establish agreement to (ii) |

The prototype keeps (ii) as the working assumption because the mode preserves
information across the transition (the caller can see the price was
buyer-specific, not public). This is explicitly **unconfirmed** — the EP and
the #877 comment ask for an explicit decision. If the thread chooses (i), the
schema change is small (extend the conflict ban: `price` MUST NOT be present
with `buyer_specific` either); the fixtures and prose would follow.

## 2B. `contract_only` has no entitled-price path (OPEN — EP must decide)

`contract_only` bans `price` outright — but an authenticated contract customer
must receive their price somehow, and the prototype names no transition. This
gap is real and is not papered over. Options:

- (a) **Mode transitions per caller:** an entitled contract customer receives
  `buyer_specific` + price (the same transition `buyer_specific` already has).
  Then `contract_only` vs `buyer_specific` differ only in the anonymous posture —
  the EP should decide whether two modes are worth that distinction.
- (b) **Commercial-term hand-off:** the price arrives via the accepted-term
  hand-off (#845) at checkout time. But contract pricing may need *catalog*
  display ("your contract price: $X" on the product page), which (b) cannot serve.
- (c) **`contract_only` permits price for entitled callers** (mode describes the
  anonymous posture only). This collapses toward (a) with different labeling.

Catalog representation stays separate from checkout pricing policy either way:
the catalog states the mode; the hand-off point (identity linking → re-request,
or the #845 term hand-off) is named, not invented. No quote/RFQ workflow is
defined here.

## 3. Design questions — resolved

1. **Zero-means-free preserved.** `price.amount: 0` keeps its released meaning; the
   `pricing` axis is orthogonal (fixture `priced_variant_free.json` passes both schemas).
2. **Explicit vs accidental omission distinguishable.** Priceless + marker → valid;
   priceless without marker → `'price' is a required property` (both schemas).
3. **Conflicting price + no-price mode:** rejected for `quote_required`/`contract_only`;
   allowed for `buyer_specific` (mode documents disclosure context for *this
   response*; a linked buyer's numeric price does not contradict it).
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
     Schema-enforced: MUST NOT be present with `quote_required`/`contract_only`
     (conflict branch extended), and `unit_price` requires `price` to be
     present (new `allOf` branch) — so a priceless `buyer_specific` variant
     cannot carry one either. Fixtures: `..._with_unit_price.json` (invalid),
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

## 4. Design questions — explicitly open (for the EP / TC / thread)

- **Closed enum vs open vocabulary** for `mode` (see tradeoffs).
- **`buyer_specific` interpretation** — (i) always omit price vs (ii) priced for
  recognized callers (see §2A). The prototype implements (ii); confirmation needed.
- **`contract_only` entitled-price path** — how an authenticated contract customer
  receives a price when the mode bans it (see §2B: per-caller mode transition,
  commercial-term hand-off, or entitled-price permission).
- **`reason` / `next_step` standardization** — currently Business-defined,
  informational. Note: `next_step: request_quote` points at a workflow the spec
  does not define; EP should define the target or drop the key.
- **Indicative pricing** alongside `quote_required` ("from $X") — currently banned.
- **Cache coherence for per-response modes:** a cached anonymous `buyer_specific`
  response served to a linked buyer (or vice versa — price leak) breaks the mode's
  semantics. The prototype defines no cache/`Vary`-like rule (found in pass 1).
- **`pricing` field-name collision:** Variant has no `additionalProperties: false`;
  existing vendor extensions may already use a `pricing` key. EP should survey
  `com.shopware.quote` / `com.ucpready.procurement` (found in pass 1).
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
