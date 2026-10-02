# Verification results — price-on-request prototype (Worker B, self-review)

Date: 2026-10-02. Environment: clean /tmp working copies; read-only clones under
`~/workspace/ucp-phase1-repos/` never modified; no commits; no external writes.
Patch: `patch/price-on-request-prototype.diff` applied to
Universal-Commerce-Protocol/ucp@b0e81ad in `/tmp/por-verify`
(`git apply --check` clean; 6 files changed).
Baseline control tree (unpatched b0e81ad): `/tmp/por-baseline`.

**Self-review label:** every check below was executed by the authoring agent's
own worker; none of this is independent validation.

## Summary table

| # | Check | Command | Version | Exit | Log file | Outcome / blocker |
|---|-------|---------|---------|------|----------|-------------------|
| 1 | `ucp-schema lint` on patched schemas | `ucp-schema lint source/` (in `/tmp/por-verify`) | ucp-schema **1.4.1** (cargo **1.99.0**, rustc **1.99.0** from `~/.rustup`, not on PATH) | **0** | `logs/02-ucp-schema-lint.log` | **PASS** — 144 files checked, all passed. Only pre-existing `W002` warnings (missing `$id`) on `handlers/tokenization/openapi.json` and `services/*` files the patch does not touch. Previously blocked on Rust toolchain — **gap closed** (toolchain exists at `~/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin`, just not on PATH; `cargo install ucp-schema` log: `logs/01-ucp-schema-install.log`, exit 0). |
| 2a | Repo example validation (CI: docs.yml) | `python scripts/validate_examples.py --schema-base source/schemas/` (docs venv; `ucp-schema` on PATH) | validate_examples.py @ b0e81ad; ucp-schema 1.4.1 | **1** | `logs/02b-validate-examples.log` | **374 passed, 3 failed, 0 errors, 53 skipped.** Baseline control (`logs/02b-validate-examples-BASELINE.log`): **376 passed, 0 failed** — all 3 failures are patch-caused (see Findings F1). |
| 2b | Validator unit tests (CI: docs.yml) | `python scripts/test_validate_examples.py` | same | **0** | `logs/02d-validator-unit-tests.log` | **59 passed, 0 failed.** (First attempt showed 2 "failures" that were skips: `ucp-schema` not on PATH in that shell; rerun with PATH fixed → 59/59.) |
| 2c | Edge-case probe (supplementary) | `edge_probe.py` (jsonschema 4.10.3, harness `$id`-store pattern) | jsonschema 4.10.3, pydantic 2.13.5, referencing (pip) | 0 | `logs/02c-edge-probe.log` | Confirms F1 mechanics; also refutes an empty-variants contradiction hypothesis (`variants` has `minItems: 1` in both trees). |
| 3 | SDK generation + enforcement demo | `bash generate_models_local.sh` (= `generate_models.sh` with **only** the `git clone` step replaced by `cp -a /tmp/por-verify ucp`; every generation step verbatim) | uv **0.12.22** (`~/.local/bin/uv`, pre-existing, not on PATH); datamodel-code-generator **0.71.0** | **1** | `logs/03-sdk-generation-rerun2.log` | **BLOCKED — concrete, patch-independent blocker** (see Findings F2). No models emitted, so the (a)/(b)/(c) enforcement assertions could not run through the prescribed pipeline. Check left incomplete per instructions (no substituted test). |
| 4a | Strict docs build (per task) | `mkdocs build --strict` (docs venv = `uv sync` output; venv relocated to `/home/hatch/por-docs-venv` via `UV_PROJECT_ENVIRONMENT` — /tmp is a 512 MB tmpfs) | mkdocs **1.6.1**, Python 3.12.3 | **0** | `logs/04-mkdocs-build-strict.log` | **PASS** — built in 65.82 s, 0 warnings. Caveat: on main-branch state this renders only the root site (47 files: homepage, redirects, non-versioned docs); versioned spec pages are deployed via mike, so the new section is not in this output. |
| 4b | Full local build (supplementary, CI-prescribed for main) | `bash scripts/build_local.sh --draft-only` (`CI=true`, git identity set locally in the /tmp copy) | mike (docs venv), ucp-schema 1.4.1 (version check vs crates.io passed) | **0** | `logs/04b-build-local-draft-only.log` | **PASS** — new "Pricing state" section renders in `local_preview/latest/specification/shopping/catalog/index.html` ("Pricing state" ×5, `quote_required` ×4, `buyer_specific` ×4, `price_on_request` ×3). |
| 5 | Live JS SDK validation (npm retry) | `npm ping` → PONG 825 ms; `npm install @ucp-js/sdk@0.5.1` → exit 0; `node live_check.mjs` (zod `VariantElementSchema.safeParse` on 3 harness fixtures) | node **v24.20.0**, npm **10.9.4**, @ucp-js/sdk **0.5.1**, zod **3.25.76** | **0** | `logs/05-js-sdk-npm-install.log`, `logs/05-js-sdk-live-check.log` | **3/3 PASS** — priced ACCEPTED; on-request (no price) REJECTED `[{"path":["price"],"message":"Required"}]`; buyer_specific+price ACCEPTED. Previously blocked on npm-via-proxy — **gap closed** (registry reachable today). Note: this validates the *old* SDK's fail-closed baseline behavior, not the new conditional rules. |
| 6 | Harness verbatim | `python harness/run.py --proposed /tmp/por-verify` (venv: jsonschema==4.10.3, pydantic 2.13.5) | harness @ phase5 | **0** | `logs/06-harness-verbatim.log` | **ALL LEGS PASS** — A–D 20/20 fixture vectors, E 300/300 differential fuzz, F 3/3 old-SDK leg. |

## Findings

### F1 — Repo example validation FAILS on the patched tree (patch-caused; baseline 376/0 → patched 374/3)

All three failures are the patch's new product rule
(`source/schemas/shopping/types/product.json`, rule 2:
"`price_range` MUST be omitted when no variant carries a numeric price",
`then: {not: {required: ["price_range"]}}`):

1. **`docs/specification/shopping/catalog/index.md:287` — the patch's own new doc example.**
   The example declares a `quote_required` variant with no price; the
   `catalog_lookup` `get_product` scaffold merges in a `price_range`
   (`min`=`max`=1000 USD), and the merged payload violates the patch's own
   rule. This confirms the "mode-aware scaffold update" open question flagged
   in `harness/README.md` is a real incompatibility, not just tooling polish:
   the current scaffolds encode the old invariant (price_range always present).
2. **`docs/specification/shopping/catalog/mcp.md:408`** (pre-existing "Blue Runner Pro" example).
3. **`docs/specification/shopping/catalog/rest.md:309`** (pre-existing "Blue Runner Pro"/"Trail Blazer X" examples).

Mechanism for 2–3: the examples write `"variants": [ ... ]` (elision). The
validator lowers this to a `["..."]` sentinel, strips it to `[]`, and
*suppresses validation errors at the elided path* (so `minItems: 1` on
`variants` does not fire) — but the new `price_range` rule errors at the
*product* path (`/products/0`), which is not suppressed. On baseline these
examples pass because baseline *requires* `price_range` unconditionally.

Edge probe (`logs/02c-edge-probe.log`) additionally shows the intended shapes
still validate (all-unpriced variants without `price_range` → VALID;
all-priced + range → VALID), and that an empty-`variants` rule contradiction
does not exist (`minItems: 1` rejects `[]` first, in both trees).

### F2 — SDK generation blocked by a pre-existing python-sdk/ucp drift (NOT the patch)

`generate_models_local.sh` (verbatim generation steps; only the GitHub `git
clone` replaced with a local copy of the patched tree, since the script has no
local-source option) fails at the `datamodel_code_generator` step:

```
Error at schema path 'common/types/constraint_expression.json#': ValidationError:
  2 validation errors for JsonSchemaObject
  properties.anyOf.JsonSchemaObject
    Input should be a valid dictionary or instance of JsonSchemaObject
    [type=model_type, input_value=['type', 'description', 'minItems', 'items']]
```

Root cause: python-sdk's `preprocess_schemas.py` treats any key named `anyOf`
as a polymorphic combinator — but `constraint_expression.json` (newer than the
schema release the SDK was generated from) has a legitimate *property named*
`anyOf` ("Alternative Object Constraints"). The preprocessor pops it and
extends a branch list with the dict's keys, mangling the property schema into
`['type', 'description', 'minItems', 'items']`, which datamodel-code-generator
0.71.0 rejects. The file is **byte-identical in the unpatched baseline**
(verified with `diff`), so this failure is patch-independent upstream drift.
(`uv.lock` in the python-sdk working tree is not tracked in git at 51bf73c;
0.71.0 was resolved from it.)

Because no models are emitted, the required (a)/(b)/(c) enforcement
demonstration could not run through the prescribed pipeline and is left
incomplete — no substitute test was run in its place. Supporting analysis
(not the check): the pipeline never translated `if`/`then` conditionals into
generated-model validators even when it succeeds — the run's own
`postprocess_models.py` logs `unsupported conditional required rule; skipped`
for pre-existing conditional rules (e.g. `location.json`), so generated-model
enforcement of the new conditional price rules would need hand-written
validators regardless.

Two earlier generation attempts failed for environmental reasons, recorded in
`logs/03-sdk-generation.log` (ENOSPC: schema files copied as 0-byte while /tmp
was full) and the first half of `logs/03-sdk-generation-rerun.log`
(`EOFError: marshal data too short` from a venv corrupted by the same ENOSPC
event); both were discarded and rerun cleanly.

## Gaps closed vs still blocked

**Closed since the last pass:**
- `ucp-schema lint` — Rust toolchain exists (`~/.rustup`, cargo 1.99.0); installed ucp-schema 1.4.1; lint passes on patched schemas.
- Live JS SDK check — npm registry reachable; `@ucp-js/sdk@0.5.1` installs and the live 3-case validation passes.
- Strict docs build — `mkdocs build --strict` exits 0; full `build_local.sh --draft-only` exits 0 with the new section rendering.
- Harness — 20/20 vectors (+300 fuzz, +3 SDK leg) pass in the clean env.

**Still blocked / failing:**
- **F2**: SDK model generation + generated-model enforcement demo — blocked by the
  `constraint_expression.json` `anyOf`-property preprocessing bug (concrete
  blocker above; patch-independent).
- **F1**: `scripts/validate_examples.py` fails 3/430 on the patched tree — the
  patch's product-level `price_range` rules conflict with the patch's own new
  doc example (via scaffold merge) and two pre-existing doc examples. This is
  a genuine patch-vs-repo-contract finding for the parent to disposition.

## Environment notes (for reproducibility)

- `/tmp` is a 512 MB tmpfs shared with sibling workers; two ENOSPC incidents
  during this run. Mitigations used: `CARGO_TARGET_DIR=/home/hatch/cargo-target-por`
  (overlay fs) for the ucp-schema build; `UV_PROJECT_ENVIRONMENT=/home/hatch/por-docs-venv`
  for the docs venv. (One `uv sync` inside `build_local.sh` still replaced a
  `.venv` symlink with a real 173 MB venv on /tmp and hit ENOSPC once; reran
  with the env var exported — clean.)
- `uv` (0.12.22) and `cargo`/`rustc` (1.99.0) were present on the machine but
  not on PATH (`~/.local/bin/uv`, `~/.rustup/toolchains/...`).
- crates.io: `cargo` client works (index updated, install succeeded); bare
  `curl -sSI https://crates.io` returns 403 (user-agent filtering) — not a blocker.
- pypi.org, github.com, registry.npmjs.org all reachable through the proxy
  today (npm PONG 825 ms).
- Read-only clones untouched: all work happened in `/tmp/por-verify` (patched),
  `/tmp/por-baseline` (control), `/tmp/por-sdk` (SDK work copy), `/tmp/por-js`
  (JS check). No commits made anywhere. A local git identity (`por-verify`)
  was configured inside the `/tmp/por-verify` copy only, for `mike deploy`.

## Raw logs

All under `~/workspace/ucp-price-on-request-contribution-phase5/logs/`:

- `01-ucp-schema-install.log` — `cargo install ucp-schema` (exit 0; 1.4.1)
- `02-ucp-schema-lint.log` — `ucp-schema lint source/` (exit 0; 144 files)
- `02b-validate-examples.log` — patched tree (374 pass / 3 fail / 53 skip; exit 1)
- `02b-validate-examples-BASELINE.log` — baseline control (376 pass / 0 fail; exit 0)
- `02c-edge-probe.log` — product-schema edge cases (E1–E5)
- `02d-validator-unit-tests.log` — `test_validate_examples.py` (59 pass; exit 0)
- `03-sdk-generation.log` — attempt 1 (ENOSPC-corrupted; superseded)
- `03-sdk-generation-rerun.log` — attempt 2 (corrupt venv; superseded)
- `03-sdk-generation-rerun2.log` — attempt 3, clean env (**exit 1**; the F2 blocker)
- `04-mkdocs-uv-sync.log` — `uv sync` for docs env (exit 0)
- `04-mkdocs-build-strict.log` — `mkdocs build --strict` (exit 0)
- `04b-build-local-draft-only.log` — `build_local.sh --draft-only` (exit 0)
- `05-js-sdk-npm-install.log` — `npm install @ucp-js/sdk@0.5.1` (exit 0)
- `05-js-sdk-live-check.log` — live zod validation (3/3; exit 0)
- `06-harness-verbatim.log` — `harness/run.py --proposed /tmp/por-verify` (exit 0; all legs pass)
