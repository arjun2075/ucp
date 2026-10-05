# COMPATIBILITY — validation evidence for the price-on-request prototype

> **UPDATED 2026-10-05 following maintainer feedback (evoleinik, juanferrub).**
> `pricing.mode` is now an open vocabulary (no closed enum). This first-pass
> update also relaxed `contract_only` to no longer forbid `price` (relaxed,
> not resolved — see DESIGN.md §2B); **that relaxation was reverted by the
> second update below, and `contract_only` once again forbids `price`.**
> Priced `buyer_specific` responses are now the proposed normative behavior.
> Two of the "narrows" rows below (`bogus_mode_variant.json` and
> `unknown_mode_negotiated_with_price.json`) have **changed verdict** as a
> direct consequence: unknown modes now validate under proposed instead of
> being rejected. This section is corrected accordingly; superseded readings
> are struck through rather than silently deleted. The overall "not purely
> additive" conclusion is **unchanged** — see the new third compatibility
> class below and §4/§5's updated narrowing-class counts.
>
> **SECOND UPDATE, same date, `contract_only` REVERSAL.** New maintainer
> guidance resolves `contract_only` as a genuinely unpriced state (the
> caller-state transition: stranger with gated price → `contract_only`;
> entitled buyer → `buyer_specific` + price). The schema reverts the relaxation
> above: `price` + `contract_only` is **re-added** to the rejected-combination
> list it had been removed from. `onrequest_variant_contract_only_priced.json`
> flips from valid → **invalid** under proposed. The open-vocabulary change to
> unknown `mode` *values* (the first update above) is unaffected and remains
> valid. The "not purely additive" conclusion stays unchanged; see the dated
> notes inline below and the updated §1 table, §4, §5, §6.

**Method:** real validators against pinned trees — `jsonschema` 4.10.3 (draft
2020-12) for schema legs, `pydantic` 2.13.5 for the Python SDK leg, and the
published `@ucp-js/sdk@0.5.1` tarball (zod-generated schemas) for the JS SDK leg.
Harness: `harness/run.py` (README has the commands); pass-2 logs in `logs/`.
All audits are self-review, never independent validation.

## 1. Full matrix: old/new payloads × baseline/proposed schemas

Legs A–D, 28 fixture vectors (`harness/vectors.json` + `harness/fixtures/`):

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
| `bogus_mode_variant.json` | valid (marker ignored) | valid | ~~unknown modes fail closed~~ **UPDATED 2026-10-05: unknown modes now validate under proposed (open vocabulary, point 1/2 of maintainer feedback) — no longer a narrowing case** |
| `onrequest_product_all_with_range.json` | invalid | invalid | all-on-request product MUST NOT carry a range |
| `onrequest_variant_quote_required_with_list_price.json` | invalid | valid | `list_price` is a legitimate reference on an unpriced variant |
| `onrequest_variant_quote_required_with_unit_price.json` | invalid | invalid | `unit_price` is a per-unit selling price: banned with no-price modes |
| `onrequest_variant_buyer_specific_noprice_with_unit_price.json` | invalid | invalid | `unit_price` requires `price` to be present |
| `onrequest_variant_buyer_specific_priced_with_unit_price.json` | valid | valid | priced `buyer_specific` variant may carry `unit_price` |
| `onrequest_product_mixed_list_price_range.json` | invalid | valid | mixed product may carry `list_price_range` (over priced variants) |
| `onrequest_product_all_norange_with_list_price_range.json` | invalid | invalid | `list_price_range` MUST be omitted when no variant is priced |
| `malformed_pricing_null_with_price.json` | valid (marker ignored) | **invalid** | `pricing: null` narrows (Worker-C) |
| `malformed_pricing_bare_string.json` | invalid | invalid | #877's bare-string shorthand rejected by both (Worker-C) |
| `malformed_pricing_empty_object_with_price.json` | valid (marker ignored) | **invalid** | `pricing: {}` narrows — `mode` is required (Worker-C) |
| `pricing_public_with_vendor_extension.json` | valid | valid | unknown fields inside `pricing` stay open (Worker-C) |
| `pricing_mode_array_with_price.json` | valid (marker ignored) | **invalid** | mode present but `pricing` not an object — narrows (Worker-C) |
| `unknown_mode_negotiated_with_price.json` | valid (marker ignored) | valid | ~~unknown mode `negotiated` fails closed — narrows (Worker-C)~~ **UPDATED 2026-10-05: unknown mode `negotiated` now validates under proposed (open vocabulary) — no longer a narrowing case** |
| `unit_price_without_price_no_marker.json` | invalid | invalid | `unit_price` requires `price` under both, marker or not (Worker-C) |
| `pricing_public_without_price.json` | invalid | invalid | `public` keeps released price-requiredness (Worker-C) |
| `unknown_mode_future_noprice.json` | invalid | valid | ADDED 2026-10-05: unknown future-looking mode, no price — safe-fallback shape validates under proposed |
| `onrequest_variant_contract_only_priced.json` | valid | **invalid** | REVERSED 2026-10-05 (second update): `contract_only` WITH a numeric price. Was schema-valid under the first update's relaxed rule; now rejected again — `contract_only` is resolved as a genuinely unpriced state, and rule 1's "forbid price" condition is restored to cover both `quote_required` and `contract_only` |
| `onrequest_product_scenario_a_public_to_buyer_specific_anonymous.json` | valid | valid | ADDED 2026-10-05: Scenario A anonymous state (ordinary public price) |
| `onrequest_product_scenario_a_public_to_buyer_specific_resolved.json` | valid | valid | ADDED 2026-10-05: Scenario A resolved state (`buyer_specific` + price, mode retained) |
| `onrequest_product_scenario_b_contract_only_anonymous.json` | invalid | valid | ADDED 2026-10-05: Scenario B anonymous state (`contract_only`, no price, no range) |
| `onrequest_product_scenario_b_buyer_specific_resolved.json` | valid | valid | ADDED 2026-10-05: Scenario B resolved state (`contract_only` → `buyer_specific` + price — RESOLVED as the selected working design in the second update, not merely "the prototype's cleanest representation") |
| `onrequest_product_mixed_withrange.json` | invalid | valid | ADDED 2026-10-05: mixed product with a present `price_range` computed only over priced variants ($100–$150, never zero-filled) |
| `onrequest_product_buyer_specific_range.json` | valid | valid | ADDED 2026-10-05: `buyer_specific` priced variants producing a caller-specific `price_range` ($80–$110), subject to the same cache-isolation requirement as the underlying prices |

**Validity changes, baseline → proposed (qualified compatibility analysis):**

| Payload class | Baseline | Proposed | Reading |
|---|---|---|---|
| Priced, no `pricing` field | valid | valid | no change (fuzz covers generated subset only) |
| Priceless, no marker | invalid | invalid | no change — accidental omission stays an error |
| Priceless + valid marker | invalid | valid | the intended gap closure |
| `price` + `pricing.mode: quote_required` | valid (marker ignored via `additionalProperties`) | **invalid** | **narrows** — conflict rejection |
| `price` + `pricing.mode: contract_only` | valid (marker ignored) | **invalid** | ~~narrows — conflict rejection~~ ~~UPDATED 2026-10-05 (first update): no longer narrows (relaxed)~~ **RE-REVERSED 2026-10-05 (second update): narrows again** — `contract_only` is resolved as a genuinely unpriced state; the first update's relaxation is reverted, and this combination is rejected under proposed exactly as it was before the first update |
| `pricing.mode` = unknown value | valid (`additionalProperties`) | valid | ~~**narrows** — closed enum~~ **UPDATED 2026-10-05: no longer narrows** — `mode` is now an open vocabulary (point 1 of maintainer feedback); an unknown mode validates with or without `price`, subject to the behavioral safe-fallback contract (point 2) |
| `pricing` = null / `{}` / non-object (mode-shaped junk), with `price` present | valid (`additionalProperties` — the field was just an ignored extension) | **invalid** | **narrows** — `pricing` must still be a well-formed object with a non-empty string `mode` (Worker-C); this narrowing is unrelated to and unaffected by the open-vocabulary change — it concerns the *shape* of `pricing`, not the *value space* of `mode` |
| Priced + `pricing` marker (`public`/`buyer_specific`/`contract_only`/unknown) | valid | valid | no change — but the field is *reinterpreted*, not new |
| `pricing` carrying unknown extra fields (e.g. `vendor_note`) | valid | valid | no change — the object stays open; `mode` is now also open, so only the object *shape* (type, required `mode`, `mode` as non-empty string) is enforced (Worker-C) |

The last three rows defeat two false claims previously present in this
handoff: (1) "any payload containing `pricing` is new by definition" is
**false** — the baseline schema permits additional properties, so a
`pricing` field could already exist in the wild (e.g. a vendor extension)
and would be reinterpreted; (2) "no previously-valid payload becomes
invalid" is **false** — the malformed-`pricing`-shape class still narrows,
even after the open-vocabulary update (the conflict-rejection narrowing is
now scoped to `quote_required` AND `contract_only` again as of the second
2026-10-05 update — see below — and the unknown-mode narrowing is gone
entirely).

**Legs A–D: 42 passed, 0 failed as of the second 2026-10-05 update**
(`logs/harness_run1.log`, re-run `logs/pass2_harness_run.log`,
`logs/workerC_harness_run.log` with the 8 Worker-C malformed/colliding
vectors, the first-update maintainer-feedback rerun with the 8 added
vectors, and the second update's `contract_only` reversal + six added
vectors, all exit 0). Six
vectors added 2026-10-02 for numeric-price consistency (`list_price`
reference legitimacy, `unit_price` conflict rules, `list_price_range`
omission rule); eight vectors added 2026-10-02 for malformed/colliding/
unknown-mode shapes (null marker, bare string, empty object, non-object mode
carrier, second unknown-mode string, vendor extension,
`unit_price`-without-`price` without marker, `public` without price); eight
vectors added 2026-10-05 (first update) for the maintainer feedback update
(unknown mode with no price, `contract_only` with a price, two Scenario-A and
two Scenario-B product fixtures, a mixed-product present-range fixture, and a
`buyer_specific` caller-specific-range fixture); six vectors added 2026-10-05
(second update, the `contract_only` reversal) for the NDA/orthogonality cases
(`public_with_price`, `contract_only_without_price`,
`buyer_specific_with_price_and_quote_step`, `public_with_price_and_quote_step`,
`quote_required_with_price_and_quote_step`, and
`onrequest_product_unknown_mode_mixed`), plus one fixture (`onrequest_variant_contract_only_priced.json`)
whose expected verdict flipped from valid to invalid. A new harness Leg G
(`harness/run.py`) additionally fuzzes the pricing-mode dimension directly —
see §6 below; its `expected_proposed_valid` helper was updated to require
`contract_only` to forbid `price`, matching the reversed rule.

## 2. Differential fuzz (Leg E) — scoped no-regression claim

300 seeded random priced variants + 300 products (all-priced variants +
`price_range`), validated under both schemas: **0 mismatches**
(`logs/workerC_harness_run.log`, exit 0, re-confirming the earlier
`logs/pass2_corrected_harness_fuzz300.log`). This
establishes no-regression **only for the generated priced subset** — the
fuzz generates priced payloads with no `pricing` field and no edge shapes.
It does **not** imply universal compatibility: the fixture matrix above
already shows four payload classes whose validity *narrows* under the
proposal (conflict rejection, unknown-mode rejection, and the new
Worker-C malformed-`pricing` classes). Any claim that "no
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

- **Not purely additive — qualified compatibility (UPDATED 2026-10-05, second
  pass: still true, and the `contract_only` reversal ADDS BACK a narrowing
  case the first pass had removed).** The proposal *relaxes*
  `price`/`price_range` requiredness for the on-request cases, but it also
  *narrows* validity for payload classes that remain narrowed: conflict
  rejection — now scoped to **both** `quote_required` AND `contract_only`
  again (the second update reverses the first update's narrowing of this
  scope down to `quote_required` only) — and the malformed-`pricing` shapes
  (null, `{}`, non-object mode carrier; see §1 table and §5). The unknown-mode
  narrowing class from the original closed-enum version of this document
  still **does not apply** — unknown `mode` *values* still validate under
  proposed (open vocabulary, point 1/2 of the first maintainer feedback
  update) — that part is unaffected by the `contract_only` reversal, which
  concerns a different rule (the `price`+known-mode conflict rule, not the
  `mode` value-space constraint). Net effect: the narrowing-class count is the
  same shape as before the first update (conflict rejection covers two known
  modes again, plus the malformed-`pricing`-shape class), not a
  reclassification of the change as purely additive. Old validators *reject*
  new on-request payloads rather than misreading them — the safe direction
  for validating consumers — but a business already emitting a
  `pricing`-shaped extension field could see its payloads newly rejected.
- **NEW (2026-10-05) — generated-SDK closed-enum compatibility class:** a
  consumer generated from a closed `mode` enum (for example, a generated SDK
  that binds `mode` to a closed language enum type) may reject or fail to
  deserialize a payload carrying a future/unrecognized `mode` value, even
  though the schema itself now accepts it. This is a *codegen* compatibility
  concern distinct from the schema-level classes above: closing this gap
  requires representing `mode` as an extensible/open string type in codegen
  (not a fixed enum), so that a generated SDK's binding preserves unknown
  string values rather than failing deserialization on an unrecognized enum
  member (see DESIGN.md §2's dated note and the EP draft's SDK note). No SDK
  regeneration was performed as part of this update; this class is
  documented, not resolved.
- **NEW (2026-10-05, second update) — Purchase Options (#901) interoperability/
  composition risk, not a released-client compatibility result:** a
  concurrent draft issue (#901), as proposed, requires `price` on every
  `purchase_options[]` entry, which cannot represent an unpriced
  `quote_required`/`contract_only` purchase option. This repo has no
  `purchase_options` schema today (verified by grep), so this is not a
  schema-level compatibility class measurable against anything in this repo
  — it is a forward-looking composition risk, documented in DESIGN.md §2D as
  prose/illustration only, explicitly NOT counted in this document's fixture
  tables or the harness's pass/fail legs, and NOT resolved by loosening
  `quote_required`/`contract_only` to carry a price.
- **Release classification UNRESOLVED:** whether this ships as a minor or
  major change is pending the project's versioning decision (date-based
  versioning; breaking changes require Governing Council majority per
  CONTRIBUTING.md). The `feat:` commit prefix in the patch header and
  PR_DRAFT is **provisional**, not a final classification.
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

## 5. Consumer-behavior matrix (Worker C, 2026-10-02) — four separated columns

Generated by `harness/consumer_matrix.py` (pinned `jsonschema` 4.10.3 +
`pydantic` 2.13.5; log `logs/workerC_consumer_matrix.log`, exit 0, all
assertions pass). All audits are self-review, never independent validation.
Covers the 8 new malformed/colliding/unknown-mode vectors on top of the 20
retained fixtures.

### (a) old payload acceptance by NEW schemas

Rows: fixtures `vectors.json` marks `baseline == "valid"`.

| fixture | baseline | proposed | class |
|---|---|---|---|
| `priced_variant_basic.json` | valid | valid | no change |
| `priced_variant_full.json` | valid | valid | no change |
| `priced_variant_free.json` | valid | valid | no change |
| `priced_product.json` | valid | valid | no change |
| `onrequest_variant_buyer_specific_priced.json` | valid | valid | no change |
| `conflict_variant_price_and_quote_required.json` | valid | invalid | **narrows** |
| `bogus_mode_variant.json` | valid | invalid | **narrows** |
| `onrequest_variant_buyer_specific_priced_with_unit_price.json` | valid | valid | no change |
| `malformed_pricing_null_with_price.json` | valid | invalid | **narrows** |
| `malformed_pricing_empty_object_with_price.json` | valid | invalid | **narrows** |
| `pricing_public_with_vendor_extension.json` | valid | valid | no change |
| `pricing_mode_array_with_price.json` | valid | invalid | **narrows** |
| `unknown_mode_negotiated_with_price.json` | valid | invalid | **narrows** |

**Headline:** of 13 baseline-valid fixture classes, 7 are unchanged and 6
**narrow** under the proposed schemas: the price+no-price-mode conflict, two
unknown-mode strings (`negotiable`, `negotiated`), and three malformed-`pricing`
shapes (`null`, `{}`, non-object mode carrier). Vendor extensions *inside* a
well-formed `pricing` object (`vendor_note`) do **not** narrow — the closure
is on `mode` only, not on the object.

### (b) new payload acceptance by OLD consumers — validating vs lenient

Rows: fixtures `vectors.json` marks `proposed == "valid"`. Validating
consumer = baseline `jsonschema`; lenient consumer =
`variant.get("price", {}).get("amount", 0)` (product rows show the first
variant's read).

| fixture (proposed-valid) | old validating consumer | old lenient read |
|---|---|---|
| `priced_variant_basic.json` | valid | $25.00 |
| `priced_variant_full.json` | valid | $120.00 |
| `priced_variant_free.json` | valid | $0.00 |
| `priced_product.json` | valid | $120.00 |
| `onrequest_variant_quote_required.json` | invalid (`'price' is a required property`) | $0.00 **<-- $0.00 MISREAD as FREE** |
| `onrequest_variant_contract_only.json` | invalid (`'price' is a required property`) | $0.00 **<-- $0.00 MISREAD as FREE** |
| `onrequest_variant_buyer_specific_noprice.json` | invalid (`'price' is a required property`) | $0.00 **<-- $0.00 MISREAD as FREE** |
| `onrequest_variant_buyer_specific_priced.json` | valid | $499.00 |
| `onrequest_product_mixed_norange.json` | invalid (`'price_range' is a required property`) | $299.00 |
| `onrequest_product_all_norange.json` | invalid (`'price_range' is a required property`) | $0.00 **<-- $0.00 MISREAD as FREE** |
| `onrequest_variant_quote_required_with_list_price.json` | invalid (`'price' is a required property`) | $0.00 **<-- $0.00 MISREAD as FREE** |
| `onrequest_variant_buyer_specific_priced_with_unit_price.json` | valid | $80.00 |
| `onrequest_product_mixed_list_price_range.json` | invalid (`'price' is a required property`) | $299.00 |
| `pricing_public_with_vendor_extension.json` | valid | $25.00 |

**Headline:** validating old consumers **reject** every new on-request
payload (fail-closed — the safe direction). Lenient old consumers silently
read **$0.00** for every priceless variant — the concrete `$0.00` misread is
demonstrated per row. Note the ambiguity this exposes: `priced_variant_free`
*also* reads `$0.00` (correctly, since `price` is present), so the naive
`.get` pattern cannot distinguish "free" from "missing" at all.

### (c) generated SDK behavior (pydantic v2)

OLD side: pinned `ucp-sdk` 0.4.6 models (`Variant`/`Product`, generated from
the RELEASED schemas; `price` required, `pricing` unknown so
`extra="allow"` keeps it unvalidated). NEW side: **proposed-schema
validation via `jsonschema` 4.10.3, explicitly labeled** — regenerating SDK
models from the proposed schemas was not feasible in this environment
(`datamodel_code_generator` / `uv` / `ruff` all unavailable), so no
NEW-side generated models exist to run.

| fixture | OLD SDK (pydantic) | NEW side (jsonschema on proposed) | note |
|---|---|---|---|
| `priced_variant_basic.json` | accepted | valid |  |
| `priced_variant_full.json` | accepted | valid |  |
| `priced_variant_free.json` | accepted | valid |  |
| `priced_product.json` | accepted | valid |  |
| `onrequest_variant_quote_required.json` | rejected | valid | price: Field required |
| `onrequest_variant_contract_only.json` | rejected | valid | price: Field required |
| `onrequest_variant_buyer_specific_noprice.json` | rejected | valid | price: Field required |
| `onrequest_variant_buyer_specific_priced.json` | accepted | valid |  |
| `onrequest_product_mixed_norange.json` | rejected | valid | price_range: Field required |
| `onrequest_product_all_norange.json` | rejected | valid | price_range: Field required |
| `conflict_variant_price_and_quote_required.json` | accepted | invalid |  |
| `accidental_priceless_variant.json` | rejected | invalid | price: Field required |
| `bogus_mode_variant.json` | accepted | invalid |  |
| `onrequest_product_all_with_range.json` | rejected | invalid | variants.0.price: Field required |
| `onrequest_variant_quote_required_with_list_price.json` | rejected | valid | price: Field required |
| `onrequest_variant_quote_required_with_unit_price.json` | rejected | invalid | price: Field required |
| `onrequest_variant_buyer_specific_noprice_with_unit_price.json` | rejected | invalid | price: Field required |
| `onrequest_variant_buyer_specific_priced_with_unit_price.json` | accepted | valid |  |
| `onrequest_product_mixed_list_price_range.json` | rejected | valid | variants.1.price: Field required |
| `onrequest_product_all_norange_with_list_price_range.json` | rejected | invalid | price_range: Field required |
| `malformed_pricing_null_with_price.json` | accepted | invalid |  |
| `malformed_pricing_bare_string.json` | rejected | invalid | price: Field required |
| `malformed_pricing_empty_object_with_price.json` | accepted | invalid |  |
| `pricing_public_with_vendor_extension.json` | accepted | valid |  |
| `pricing_mode_array_with_price.json` | accepted | invalid |  |
| `unknown_mode_negotiated_with_price.json` | accepted | invalid |  |
| `unit_price_without_price_no_marker.json` | rejected | invalid | price: Field required |
| `pricing_public_without_price.json` | rejected | invalid | price: Field required |

**Headline:** the OLD SDK is fail-closed on *missing* price but fail-**open**
on *marker shape*: it **accepts** the conflict payload, both unknown-mode
payloads, and all three malformed-`pricing` shapes (`extra="allow"` passes
them through unvalidated). The conflict/mode-closure rules therefore bite
only for schema-validating consumers, not for old SDK consumers — a
non-validating business emitting `price` + `quote_required` would have old
SDK consumers display the price.

### (d) lenient consumer behavior (variant fixtures)

Naive read `variant.get("price", {}).get("amount", 0)` vs strict hand-rolled
`variant["price"]["amount"]`.

| fixture | naive amount read | interpretation | strict hand-rolled |
|---|---|---|---|
| `priced_variant_basic.json` | $25.00 | correct (price present) | `2500` |
| `priced_variant_full.json` | $120.00 | correct (price present) | `12000` |
| `priced_variant_free.json` | $0.00 | correct (price present) | `0` |
| `onrequest_variant_quote_required.json` | $0.00 | **$0.00 misread as FREE** (the #877 harm) | KeyError('price') (fail-loud) |
| `onrequest_variant_contract_only.json` | $0.00 | **$0.00 misread as FREE** (the #877 harm) | KeyError('price') (fail-loud) |
| `onrequest_variant_buyer_specific_noprice.json` | $0.00 | **$0.00 misread as FREE** (the #877 harm) | KeyError('price') (fail-loud) |
| `conflict_variant_price_and_quote_required.json` | $999.00 | correct (price present) | `99900` |
| `accidental_priceless_variant.json` | $0.00 | **$0.00 misread as FREE** (the #877 harm) | KeyError('price') (fail-loud) |
| `bogus_mode_variant.json` | $1.00 | correct (price present) | `100` |
| `onrequest_variant_quote_required_with_list_price.json` | $0.00 | **$0.00 misread as FREE** (the #877 harm) | KeyError('price') (fail-loud) |
| `onrequest_variant_quote_required_with_unit_price.json` | $0.00 | **$0.00 misread as FREE** (the #877 harm) | KeyError('price') (fail-loud) |
| `onrequest_variant_buyer_specific_noprice_with_unit_price.json` | $0.00 | **$0.00 misread as FREE** (the #877 harm) | KeyError('price') (fail-loud) |
| `onrequest_variant_buyer_specific_priced_with_unit_price.json` | $80.00 | correct (price present) | `8000` |
| `malformed_pricing_null_with_price.json` | $25.00 | correct (price present) | `2500` |
| `malformed_pricing_bare_string.json` | $0.00 | **$0.00 misread as FREE** (the #877 harm) | KeyError('price') (fail-loud) |
| `malformed_pricing_empty_object_with_price.json` | $25.00 | correct (price present) | `2500` |
| `pricing_public_with_vendor_extension.json` | $25.00 | correct (price present) | `2500` |
| `pricing_mode_array_with_price.json` | $25.00 | correct (price present) | `2500` |
| `unknown_mode_negotiated_with_price.json` | $25.00 | correct (price present) | `2500` |
| `unit_price_without_price_no_marker.json` | $0.00 | **$0.00 misread as FREE** (the #877 harm) | KeyError('price') (fail-loud) |
| `pricing_public_without_price.json` | $0.00 | **$0.00 misread as FREE** (the #877 harm) | KeyError('price') (fail-loud) |

**Headline:** three consumer outcomes, not two: correct reads (price
present), silent **$0.00 misreads** (price absent — the #877 harm), and
`KeyError` fail-loud crashes for strict hand-rolled access. The naive
pattern cannot distinguish accidental omission from intentional on-request
(`accidental_priceless_variant` misreads identically).

### Surprises and qualification notes (Worker C)

1. **The bare-string shorthand from #877's own body is rejected by the
   prototype.** `malformed_pricing_bare_string.json` (`pricing:
   "on_request"`, no price) is invalid under *both* schemas — baseline for
   missing `price`, proposed because `pricing` must be an object with a
   closed-enum `mode`. The prototype deliberately does not grandfather the
   issue's sketch shape; any consumer that adopted it would need to migrate
   to the object form. This is a deliberate non-goal, not an oversight.
2. **The $0.00 misread predates the proposal.** The naive `.get` pattern
   misreads `accidental_priceless_variant` (an *old*, schema-invalid
   payload) as $0.00 too — the harm is a property of the access pattern,
   not of the new payloads. The proposed MUST-NOT-treat-missing-as-zero
   norm therefore addresses deployed consumer behavior that already exists,
   and binds only future implementations.
3. **Conflict rejection is schema-level, not ecosystem-wide.** The OLD SDK
   *accepts* `conflict_variant_price_and_quote_required.json` (price
   present, marker ignored via `extra="allow"`). Only schema-validating
   consumers enforce the conflict rule; old SDK consumers of a
   non-validating business would display the price. §3's "conflict
   rejection" claim is accordingly scoped to validating consumers.
4. **Narrowing is bounded by the open object.** `pricing_public_with_vendor_extension.json`
   stays valid under both schemas: unknown fields inside `pricing` pass
   through. **UPDATED 2026-10-05, second pass:** the narrowing classes are
   now exactly: conflict (`quote_required` + price AND `contract_only` +
   price, again, per the resolved per-caller transition), and malformed
   (`null`/`{}`/non-object) `pricing` — a vendor extension that merely *adds*
   fields to a well-formed marker is not affected, and unknown `mode`
   *values* still do not narrow (open vocabulary, unaffected by the
   `contract_only` reversal).

## 6. Pricing-mode fuzz (Leg G, added 2026-10-05)

A new harness leg (`harness/run.py::leg_mode_fuzz`) crosses `pricing` absent,
every known mode (`public`, `buyer_specific`, `quote_required`,
`contract_only`), and several future-looking unknown mode strings
(`negotiated_tier`, `auction_pending`, `dynamic_offer`, `partner_price_v2`)
with price absent/present, including mixed-mode products (several variants,
each independently assigned a mode/price combination). It asserts the
PROPOSED schema's verdict matches the documented `allOf` rule for each
`(mode, price-presence)` combination, and in particular that an unrecognized
mode never causes rejection merely for being unrecognized. This is a
different invariant from Leg E (which checks baseline/proposed agreement on
a generated all-priced, no-`pricing` subset) — Leg E's existing contract is
unchanged; Leg G is additive and exercises the `pricing`/mode dimension Leg E
deliberately does not touch. Result as of the first 2026-10-05 rerun: 300
variants + 300 mixed-mode products, 0 mismatches, exit 0. **Second update (same date):**
`leg_mode_fuzz`'s `expected_proposed_valid` helper was corrected so
`contract_only` (like `quote_required`) expects `price` to be absent — the
rerun after the `contract_only` reversal again reports 300+300, 0 mismatches,
exit 0 (see the dated log under `logs/` for this round).

### Release classification: still UNRESOLVED

Nothing in §5/§6 changes §4's versioning position: the change *relaxes*
requiredness for the on-request classes but *narrows* validity for the
conflict class — now `quote_required` **and** `contract_only` + price again,
per the second 2026-10-05 update's reversal — and the malformed-`pricing`-shape
classes (§1 table). The unknown-mode narrowing remains removed (open
vocabulary, unaffected by the `contract_only` reversal); the `contract_only`
narrowing is restored. Net narrowing-class count: conflict (two known modes)
+ malformed-shape — the same shape as the pre-first-update baseline, not a
net reduction. Whether that ships as minor or major is pending the project's
versioning decision (date-based versioning; breaking changes require
Governing Council majority per CONTRIBUTING.md). The `feat:` prefix in the
patch header and PR_DRAFT remains **provisional**, not a final classification.
