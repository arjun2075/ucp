# COMPATIBILITY — validation evidence for the price-on-request prototype

**Method:** real validators against pinned trees — `jsonschema` 4.10.3 (draft
2020-12) for schema legs, `pydantic` 2.13.5 for the Python SDK leg, and the
published `@ucp-js/sdk@0.5.1` tarball (zod-generated schemas) for the JS SDK leg.
Harness: `harness/run.py` (README has the commands); pass-2 logs in `logs/`.
All audits are self-review, never independent validation.

## 1. Full matrix: old/new payloads × baseline/proposed schemas

Legs A–D, 20 fixture vectors (`harness/vectors.json` + `harness/fixtures/`):

| Fixture | Baseline (released) | Proposed | Reading |
|---|---|---|---|
| `priced_variant_basic.json` | valid | valid | no regression |
| `priced_variant_full.json` | valid | valid | no regression |
| `priced_variant_free.json` (`amount: 0`) | valid | valid | zero-means-free preserved |
| `priced_product.json` | valid | valid | no regression |
| `onrequest_variant_quote_required.json` | **invalid** (`'price' is a required property`) | valid | the gap is real; the prototype closes it |
| `onrequest_variant_contract_only.json` | invalid | valid | same |
| `onrequest_variant_buyer_specific_noprice.json` | invalid | valid | same |
| `onrequest_variant_buyer_specific_priced.json` | valid | valid | linked-buyer shape already worked; marker reinterpreted, not new |
| `onrequest_product_mixed_norange.json` | invalid | valid | mixed product w/o range |
| `onrequest_product_all_norange.json` | invalid | valid | all-on-request product w/o range |
| `conflict_variant_price_and_quote_required.json` | valid (marker ignored) | **invalid** | conflicting signals rejected under proposed |
| `accidental_priceless_variant.json` | invalid | invalid | accidental omission stays an error under both |
| `bogus_mode_variant.json` | valid (marker ignored) | **invalid** | unknown modes fail closed |
| `onrequest_product_all_with_range.json` | invalid | invalid | all-on-request product MUST NOT carry a range |
| `onrequest_variant_quote_required_with_list_price.json` | invalid | valid | `list_price` is a legitimate reference on an unpriced variant |
| `onrequest_variant_quote_required_with_unit_price.json` | invalid | invalid | `unit_price` is a per-unit selling price: banned with no-price modes |
| `onrequest_variant_buyer_specific_noprice_with_unit_price.json` | invalid | invalid | `unit_price` requires `price` to be present |
| `onrequest_variant_buyer_specific_priced_with_unit_price.json` | valid | valid | priced `buyer_specific` variant may carry `unit_price` |
| `onrequest_product_mixed_list_price_range.json` | invalid | valid | mixed product may carry `list_price_range` (over priced variants) |
| `onrequest_product_all_norange_with_list_price_range.json` | invalid | invalid | `list_price_range` MUST be omitted when no variant is priced |

**Validity changes, baseline → proposed (qualified compatibility analysis):**

| Payload class | Baseline | Proposed | Reading |
|---|---|---|---|
| Priced, no `pricing` field | valid | valid | no change (fuzz covers generated subset only) |
| Priceless, no marker | invalid | invalid | no change — accidental omission stays an error |
| Priceless + valid marker | invalid | valid | the intended gap closure |
| `price` + `pricing.mode: quote_required`/`contract_only` | valid (marker ignored via `additionalProperties`) | **invalid** | **narrows** — conflict rejection |
| `pricing.mode` = unknown value | valid (`additionalProperties`) | **invalid** | **narrows** — closed enum |
| Priced + `pricing` marker (`public`/`buyer_specific`) | valid | valid | no change — but the field is *reinterpreted*, not new |

The last three rows defeat two false claims previously present in this
handoff: (1) "any payload containing `pricing` is new by definition" is
**false** — the baseline schema permits additional properties, so a
`pricing` field could already exist in the wild (e.g. a vendor extension)
and would be reinterpreted; (2) "no previously-valid payload becomes
invalid" is **false** — the conflict and unknown-mode classes narrow.

**Legs A–D: 20 passed, 0 failed** (`logs/harness_run1.log`, re-run
`logs/pass2_harness_run.log`, exit 0). Six vectors added 2026-10-02 for
numeric-price consistency (`list_price` reference legitimacy, `unit_price`
conflict rules, `list_price_range` omission rule).

## 2. Differential fuzz (Leg E) — scoped no-regression claim

300 seeded random priced variants + 300 products (all-priced variants +
`price_range`), validated under both schemas: **0 mismatches**. This
establishes no-regression **only for the generated priced subset** — the
fuzz generates priced payloads with no `pricing` field and no edge shapes.
It does **not** imply universal compatibility: the fixture matrix above
already shows two payload classes whose validity *narrows* under the
proposal (conflict rejection, unknown-mode rejection). Any claim that "no
previously-valid payload becomes invalid" is **false** and is struck
everywhere in this handoff.

## 3. Old-client behavior (the "fail-closed" claim, qualified)

**Python SDK** (`ucp-sdk` 0.4.6 @ `51bf73c`, pydantic, Leg F):
- priced payload → accepted; on-request payload (no price) → **rejected**
  (`price: Field required`, `logs/sdk_rejection_detail.log`); priced payload +
  `pricing` marker → accepted (`extra="allow"`).

**JS SDK** (`@ucp-js/sdk` 0.5.1, `logs/js_sdk_check.log`):
- priced → ACCEPTED; on-request (no price) → **REJECTED**
  (`[{"path":["price"],"message":"Required"}]`); `buyer_specific` + price → ACCEPTED.
- Corroborated Oct 2 from the published 0.5.1 tarball's generated source:
  `VariantElementSchema` declares `price` required (not `.optional()`), and with no
  `.strict()`/`.passthrough()` on the variant schema, zod's default strip silently
  drops the unknown `pricing` marker. Live re-execution wasn't possible (npm
  registry unreachable for the `zod` dependency); the log stands as recorded with
  this static corroboration.

**Qualified claim:** fail-closed holds for **schema-validating** consumers (the
three above). It does **not** universally hold:
- *Lenient non-validating* consumers (e.g. `variant.get("price", {}).get("amount", 0)`)
  silently read $0.00/"free" — the exact harm #877 reports. The proposed
  MUST-NOT-treat-missing-as-zero norm binds future implementations, not deployed code.
- *Strict hand-rolled* consumers (`variant["price"]["amount"]`) crash loudly
  (KeyError) — fail-loud, not silent.
- A *new* business emitting price+`quote_required` without validating would have old
  consumers display the price (the combination is schema-invalid, but only
  validation enforces it).

## 4. Version / capability implications (stated honestly)

- **Not purely additive — qualified compatibility:** the proposal *relaxes*
  `price`/`price_range` requiredness for the on-request cases, but it also
  *narrows* validity for two payload classes (conflict rejection,
  unknown-mode rejection — see §1 table). Old validators *reject* new
  on-request payloads rather than misreading them — the safe direction for
  validating consumers — but a business already emitting a `pricing`-shaped
  extension field could see its payloads newly rejected.
- **Release classification UNRESOLVED:** whether this ships as a minor or
  major change is pending the project's versioning decision (date-based
  versioning; breaking changes require Governing Council majority per
  CONTRIBUTING.md). The `feat:` commit prefix in the patch header and
  PR_DRAFT is **provisional**, not a final classification.
- **Capability negotiation:** the prototype does not define a capability flag for
  pricing-state support. A platform cannot currently discover whether a Business
  emits on-request variants except by receiving one. Whether the EP should add
  capability surface is open.
- **Capability negotiation:** the prototype does not define a capability flag for
  pricing-state support. A platform cannot currently discover whether a Business
  emits on-request variants except by receiving one. Whether the EP should add
  capability surface is open.
- **Conformance:** current REST conformance requires valid `Price` objects on
  catalog responses; a business serving on-request listings would fail today's
  conformance suite. The feature needs conformance updates alongside the EP —
  noted, not implemented.
- **`ucp-schema lint` / `validate_examples.py`:** could not run here (no Rust
  toolchain build; `logs/ucp_schema_build_fail.log`). The doc example added to
  `catalog/index.md` is not executed by the harness; a mode-aware scaffold update
  for the example validator is an open tooling question.
- **Feed (#866):** feed records are catalog Products, so the schema rule covers
  feeds with no separate schema change; the feed capability doc still needs the
  aggregation sentence when #866 merges.
