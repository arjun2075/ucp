# Harness instructions

For the portable publication command, see [the prototype README](../README.md).
Pass --baseline and --proposed explicitly. Defaults below describe the original
research workspace; they are not prerequisites for a new checkout.

# Price-on-request prototype harness

Validates the candidate patch (see `../patch/price-on-request-prototype.diff`)
with real, pinned validators. **Read-only**: it never writes to either schema
tree; the SDK leg only imports the SDK, it does not modify it.

## Requirements

- Python 3.10+
- `jsonschema==4.10.3` (pinned; the version used by the Worker-2 experiments)
- `pydantic>=2` (only for the SDK leg)

```bash
pip install -r requirements.txt
```

## Run

From anywhere:

```bash
python3 /path/to/harness/run.py [--baseline PATH] [--proposed PATH] [--sdk PATH]
                                [--fuzz N] [--skip-sdk]
```

Defaults:

| flag         | default                                                        |
|--------------|----------------------------------------------------------------|
| `--baseline` | `~/workspace/ucp-phase1-repos/ucp` (read-only clone @ b0e81ad) |
| `--proposed` | **must be supplied** — e.g. a tree built per the top-level README step 0 (the old `scratch-ucp` default was removed) |
| `--sdk`      | `~/workspace/ucp-phase1-repos/python-sdk` (@ 51bf73c)          |
| `--fuzz`     | 300                                                            |

Exit code `0` iff every non-skipped leg passes.

## Legs

- **A–D — fixture matrix** (`vectors.json` + `fixtures/`): each fixture has a
  declared expected outcome against the baseline and the proposed schema.
  - A: existing priced payloads vs baseline → valid
  - B: existing priced payloads vs proposed → valid (no regression)
  - C: new on-request payloads vs baseline → invalid (proves the gap)
  - D: new on-request payloads vs proposed → valid
  - plus negative vectors both schemas must reject (accidental omission,
    conflicting price+mode, bogus mode, fabricated range).
- **E — differential fuzz**: N seeded random priced variants and N products
  (all-priced variants + `price_range`); every instance must validate
  identically (valid) under both schemas. Any mismatch is a regression.
- **F — old python SDK** (`ucp-sdk` 0.4.6 @ 51bf73c, pydantic models):
  priced payload → accepted; new on-request payload → rejected with
  `price: Field required` (fail-closed); priced payload carrying the new
  `pricing` marker → accepted (`extra="allow"`).

## Notes / limitations

- `ucp-schema lint` / `scripts/validate_examples.py` from the ucp repo could
  not run here (no Rust toolchain binary prebuilt; `ucp-schema` is installed
  from source — see `../work/w3-prototype.md` for the outcome).
- The doc example added to `catalog/index.md` is *not* executed by this
  harness; `validate_examples.py` deep-merges examples into scaffolds, and a
  mode-aware scaffold update is an open tooling question (see work doc).
- The JS SDK (`@ucp-js/sdk` 0.5.1) check is recorded in
  `../logs/js_sdk_check.log`: priced variant → ACCEPTED; on-request variant
  (no price) → REJECTED with `[{"path":["price"],"message":"Required"}]`;
  `buyer_specific` variant with price → ACCEPTED. Oct 2 corroboration
  (static, from the published 0.5.1 tarball): the generated
  `VariantElementSchema` declares `price` required (not `.optional()`) and
  uses zod's default strip behavior (no `.strict()`/`.passthrough()` on the
  variant schema), so a missing price fails with "Required" while the
  unknown `pricing` marker is silently stripped — exactly the logged
  outcomes. Live re-execution was not possible Oct 2 (npm registry
  unreachable for the `zod` dependency), so the log stands as recorded
  with this static corroboration.
