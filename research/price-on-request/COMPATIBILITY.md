# COMPATIBILITY — validation evidence for the price-on-request prototype

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
| `bogus_mode_variant.json` | valid (marker ignored) | **invalid** | unknown modes fail closed |
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
| `unknown_mode_negotiated_with_price.json` | valid (marker ignored) | **invalid** | unknown mode `negotiated` fails closed — narrows (Worker-C) |
| `unit_price_without_price_no_marker.json` | invalid | invalid | `unit_price` requires `price` under both, marker or not (Worker-C) |
| `pricing_public_without_price.json` | invalid | invalid | `public` keeps released price-requiredness (Worker-C) |

**Validity changes, baseline → proposed (qualified compatibility analysis):**

| Payload class | Baseline | Proposed | Reading |
|---|---|---|---|
| Priced, no `pricing` field | valid | valid | no change (fuzz covers generated subset only) |
| Priceless, no marker | invalid | invalid | no change — accidental omission stays an error |
| Priceless + valid marker | invalid | valid | the intended gap closure |
| `price` + `pricing.mode: quote_required`/`contract_only` | valid (marker ignored via `additionalProperties`) | **invalid** | **narrows** — conflict rejection |
| `pricing.mode` = unknown value | valid (`additionalProperties`) | **invalid** | **narrows** — closed enum |
| `pricing` = null / `{}` / non-object (mode-shaped junk), with `price` present | valid (`additionalProperties` — the field was just an ignored extension) | **invalid** | **narrows** — `pricing` must now be a well-formed object (Worker-C) |
| Priced + `pricing` marker (`public`/`buyer_specific`) | valid | valid | no change — but the field is *reinterpreted*, not new |
| `pricing` carrying unknown extra fields (e.g. `vendor_note`) | valid | valid | no change — the object stays open; only `mode` is a closed enum (Worker-C) |

The last three rows defeat two false claims previously present in this
handoff: (1) "any payload containing `pricing` is new by definition" is
**false** — the baseline schema permits additional properties, so a
`pricing` field could already exist in the wild (e.g. a vendor extension)
and would be reinterpreted; (2) "no previously-valid payload becomes
invalid" is **false** — the conflict and unknown-mode classes narrow.

**Legs A–D: 28 passed, 0 failed** (`logs/harness_run1.log`, re-run
`logs/pass2_harness_run.log`, and `logs/workerC_harness_run.log` with the 8
Worker-C malformed/colliding vectors, exit 0). Six vectors added 2026-10-02 for
numeric-price consistency (`list_price` reference legitimacy, `unit_price`
conflict rules, `list_price_range` omission rule); eight vectors added
2026-10-02 for malformed/colliding/unknown-mode shapes (null marker, bare
string, empty object, non-object mode carrier, second unknown-mode string,
vendor extension, `unit_price`-without-`price` without marker, `public`
without price).

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

- **Not purely additive — qualified compatibility:** the proposal *relaxes*
  `price`/`price_range` requiredness for the on-request cases, but it also
  *narrows* validity for four payload classes (conflict rejection,
  unknown-mode rejection, and the malformed-`pricing` shapes — null, `{}`,
  non-object mode carrier; see §1 table and §5). Old validators *reject* new
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
   through. The narrowing classes are exactly: conflict, unknown `mode`
   values, and malformed (`null`/`{}`/non-object) `pricing` — a vendor
   extension that merely *adds* fields to a well-formed marker is not
   affected.

### Release classification: still UNRESOLVED

Nothing in §5 changes §4's versioning position: the change *relaxes*
requiredness for the on-request classes but *narrows* validity for four
payload classes (conflict, unknown mode, malformed `pricing`; §1 table).
Whether that ships as minor or major is pending the project's versioning
decision (date-based versioning; breaking changes require Governing
Council majority per CONTRIBUTING.md). The `feat:` prefix in the patch
header and PR_DRAFT remains **provisional**, not a final classification.
