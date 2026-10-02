# SOURCE_MAP — version-qualified sources for Phase 5

Condensed from `work/w1-upstream-state.md` (full retrieval detail there).
**Retrieval dates:** Oct 1–2, 2026 (PT). GitHub reads via `api.github.com`;
repo reads via the read-only clone at `~/workspace/ucp-phase1-repos/ucp`
(never modified). **No external writes were made at any point.**

## Pinned sources

| Source | Pin | Retrieved | Content type |
|---|---|---|---|
| ucp repo, main | `b0e81adecf816a1771b736464f17586d76950f7f` ("docs: update landing page domain carousel images (#874)") | Oct 1–2, 2026 (local clone) | released schemas + spec docs |
| `source/schemas/shopping/types/variant.json` L7–12 | same pin | Oct 1, 2026 | released: `"required": ["id","title","description","price"]` |
| `source/schemas/shopping/types/product.json` L7–13 | same pin | Oct 1, 2026 | released: `"required": ["id","title","description","price_range","variants"]` |
| `source/schemas/common/types/price.json` L14 | same pin | Oct 1, 2026 | released: `"Amount in ISO 4217 minor units. Use 0 for free items."` |
| Issue #877 (body + metadata) | open; created 2026-09-29; `updated_at` 2026-10-01T10:55:26Z; re-verified Oct 2 unchanged | Oct 1–2, 2026 (API) | feature request; 0 labels, no milestone, no linked PRs |
| #877 comment, juanferrub | id `5885765668`, 2026-09-29T07:33:43Z | Oct 1, 2026 (API) | practitioner design sketch (pricing-state object, 4 modes) |
| #877 comment, evoleinik | id `5929900236`, 2026-10-01T10:55:26Z | Oct 1, 2026 (API) | live-implementation lessons: caller-dependent mode; filter rule; feed scope |
| Issue #810 | open; updated 2026-09-25 | Oct 1, 2026 (API) | per-seller offers proposal; price required per offer — orthogonal |
| Issue #845 | open; updated 2026-09-29 | Oct 1, 2026 (API) | accepted-term handoff architecture — adjacent, downstream |
| Discussion #812 | open; 21 comments; updated 2026-09-18 | Oct 1, 2026 (API) | term-formation/execution boundary — adjacent, sibling |
| PR #538 (ask) | open; head `afc057c861488b300fc5a03b9b0d22838d936feb` | Oct 1, 2026 (API) | ask capability draft — minimal overlap |
| PR #866 (feed, draft) | open; updated 2026-09-30 | Oct 1, 2026 (API) | feed records are catalog Products — in-scope dependent |
| Org CONTRIBUTING.md | blob `802565ceb1c70f7d311310e66b488c6b77effd9a` | Oct 1, 2026 (API) | contribution process (see EP requirement below) |
| python-sdk (ucp-sdk 0.4.6) | `51bf73cec92cfe321a9282b8f49fc8f647068c2e` | Oct 1–2, 2026 (local clone) | old-SDK compatibility leg |
| @ucp-js/sdk 0.5.1 | published npm tarball (`npm pack`, Oct 2) | Oct 2, 2026 | JS SDK compatibility evidence (static) |

## The EP requirement (the gating fact for everything downstream)

Per org CONTRIBUTING.md (verified Oct 1, 2026): any change to core JSON schemas —
including adding/updating fields or field descriptions — is a **Significant Change**
and requires a formal **Enhancement Proposal** (template: Summary, Motivation,
Detailed Design, Risks, Test Plan, Graduation Criteria) **before implementation**.
EP lifecycle: Proposal → Provisional (TC majority vote) → Implemented (TC majority
vote, code complete and merged). Relaxing `variant.price` / `product.price_range`
from required is squarely a Core Schema Modification, so **no implementation PR may
be opened until the EP is TC-approved**. The vendor-namespace rule (try extensions
first) is addressed: Worker 2 demonstrated by execution that `allOf` composition
cannot relax `required`, so a vendor extension cannot solve #877 — the EP should
state this explicitly.

Other process notes from CONTRIBUTING.md: conventional-commit PR titles
(`feat: ...`; `!` for genuinely breaking changes — release classification for
this prototype is unresolved, so the staged `feat:` prefix is provisional);
2 maintainer approvals for routine changes; TC escalation
for cross-topic issues; schema changes need worked examples validated by
`scripts/validate_examples.py`; docs build `--strict` clean; Google CLA required.

## Absence evidence (no-duplication re-verification, Oct 2)

- #877 timeline: no `cross-referenced` events, no linked PRs (only
  mentioned/subscribed/commented).
- Issues search `price_on_request` in `repo:Universal-Commerce-Protocol/ucp`:
  `total_count: 1` (only #877).
- Local clone after `git fetch`: HEAD unchanged at `b0e81ad`; branch scan for
  `pric|quote|rfq|on.request|877` → no matches.
- **Result: no existing patch, prototype, PR, or fork addresses #877 within
  the org's repos** (searched Oct 2). This establishes no-duplication against
  org work only — it does not prove no external prototype exists, and no such
  claim is made.
