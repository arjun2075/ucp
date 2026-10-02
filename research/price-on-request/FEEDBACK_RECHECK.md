# #877 Feedback Recheck — 2026-10-02 (Fri, ~07:52–08:00 PDT)

**Scope:** live state of https://github.com/Universal-Commerce-Protocol/ucp/issues/877
("Catalog items with no public price ('price on request')"),
rechecked after the user's coordination comment
(#issuecomment-5954902121, posted 2026-10-02T14:44:25Z = 07:44 PDT).

**Method:** unauthenticated public GitHub API fetches (the `custom.github`
credential is dead; no browser session used). Reads only; nothing posted.
Note: the `#issuecomment-5954902121` fragment URL returned upstream 500
earlier — the comment content was instead read through
`.../issues/877/comments?per_page=100`, which returned the full text.

## State summary

- **Issue state:** `open`, unlocked. Labels: none. Assignees: none. Milestone: none.
- **Comment count:** 3. `updated_at` = 2026-10-02T14:44:25Z — i.e., the most
  recent activity on the issue IS the user's own comment. **No replies after it.**
- **Reactions:** issue body has 1 reaction (🚀, total). All three comments have
  0 reactions, including the user's.
- **Timeline after the user's comment:** only notification events
  (`mentioned`/`subscribed` for juanferrub and evoleinik at 14:44:26–27Z). No
  new comments, no state changes, no labels added.
- **Linked work:** one `referenced` event at 2026-10-02T14:40:46Z pointing to
  commit `6fee3503125dfd3b17908bdf9c69ec69fc4e716b` on `arjun2075/ucp`
  (the prototype tree commit named in the user's comment). **No upstream PR,
  no linked branch, no cross-referenced implementation PR.**
- **Maintainer/TC engagement:** none. No comments, reviews, or labels from
  maintainers since the issue was filed (2026-09-29T02:28:35Z).

## Comment log (for reference)

1. **juanferrub** — 2026-09-29T07:33:43Z
   (https://github.com/Universal-Commerce-Protocol/ucp/issues/877#issuecomment-5885765668):
   proposed the four-mode `pricing` object (`public | buyer_specific |
   quote_required | contract_only` with `reason`/`next_step`), schema rules
   (price required for `public`, omitted for non-public, missing price ≠ zero,
   filters exclude), and the catalog→identity-linking→RFQ→term-handoff staging.
2. **evoleinik** — 2026-10-01T10:55:26Z
   (https://github.com/Universal-Commerce-Protocol/ucp/issues/877#issuecomment-5929900236):
   "Agree the state belongs in the schema. A message code can't tell a platform
   what it may do." Mapped two live sellers (lessor → `quote_required`;
   NDA software vendor → `buyer_specific`). Two learnings: (a) "The mode depends
   on the caller" — `pricing.mode` should describe *this response*, not be a
   fixed variant property; (b) filter rule for mixed results — they filter
   priced and drop the rest, asking if that's the intended default. Also flagged:
   "#866 feed records are catalog Products, so the same rule has to cover feeds."
3. **arjun2075 (user)** — 2026-10-02T14:44:25Z
   (https://github.com/Universal-Commerce-Protocol/ucp/issues/877#issuecomment-5954902121):
   prototype + compatibility analysis at
   https://github.com/arjun2075/ucp/tree/6fee3503125dfd3b17908bdf9c69ec69fc4e716b/research/price-on-request
   (20 fixture vectors + 300/300 generated differential runs; explicitly "not
   universal compatibility"; lint/example-validation/SDK-generation checks
   remain incomplete). Not claiming purely additive/backward compatible.
   Three questions asked: (1) `buyer_specific` priced-for-recognized-caller vs
   mode transition; (2) `contract_only` entitled-caller price delivery —
   caller-dependent mode transition vs allowing numeric price; (3) closed enum
   vs open vocabulary for `mode`. Noted draft EP records remaining filtering,
   reference-price, feed and cache-isolation decisions; "not been formally
   submitted, and no upstream implementation PR is open."

## Findings

### 1. No substantive responses since the user's comment
No new commenters, no maintainer/TC reply, no reactions on the comment.
The thread is quiet — **3 hours between the evoleinik comment (Oct 1 10:55 UTC)
and the user comment is unchanged; nothing new since 14:44 UTC.**

### 2. No overlapping EP work found
- Search `repo:Universal-Commerce-Protocol/ucp "price on request"` →
  5 hits, all false-positive or unrelated except #877 itself:
  - #877 (this issue)
  - #650 "[Proposal]: Add an optional human-readable `display_value` to money
    objects" (namansoood, opened 2026-07-29) — **orthogonal**: presentation-only
    string on money objects; does not address priceless variants or catalog
    pricing state. No overlap; not a duplicate risk.
  - #375 (store-based inventory RFC), #359 (docs validation PR), #250
    (eligibility claims PR) — incidental phrase matches, unrelated.
- Search `repo:... pricing mode catalog created:>=2026-10-01` → **0 hits**.
- Search `repo:... "Enhancement Proposal" created:>=2026-09-25` → 4 hits:
  #888 (contributing guide docs PR), #871 (cart_id bugfix PR), #868
  (idempotency-key PR) — all unrelated to catalog pricing.
- **Conclusion: no duplicate or competing price-on-request EP/issue/PR exists.
  No coordination vs duplicate decision is needed.** If the user files the EP,
  it will be the only such proposal.

### 3. EP open decisions — all still unanswered
The user's three questions (buyer_specific interpretation, contract_only
entitled pricing, open vs closed enum) and the draft EP's recorded open
decisions (filtering, indicative/reference pricing, feed coverage, cache
isolation) have **no thread answers yet**. The EP draft's open-decision list
stands as written; nothing in the live thread narrows it.

### 4. Note: posted comment ≠ corrected COMMENT_DRAFT
The live comment is shorter than the Oct-2 corrected draft in this work dir
(COMMENT_DRAFT.md): the posted version asks only buyer_specific, contract_only,
and extensibility; it omits the corrected draft's questions 4–6 (indicative
pricing under `quote_required`, cache coherence / no-cross-caller-caching
rule, filter follow-up with stronger response language). Those are recorded in
the unsent EP draft, so they are not lost — but if the user wants them visible
on the thread, that needs a follow-up comment with his explicit word.

## Verdict

- **Feedback state:** nothing new. No maintainer/TC response, no new
  commenters, no linked implementation, no overlapping proposals.
- **Nothing in the live thread requires EP changes** — the EP draft's open
  decisions remain open.
- **Nothing blocks or redirects the proposal.** The gating constraint is
  unchanged: per CONTRIBUTING.md the EP issue is the required next step, and
  per the user's standing rule no submission moves without his explicit word.
- **Recommended next step (for the user, not this worker):** wait for
  evoleinik/juanferrub replies to the three posted questions before or while
  formalizing the EP; optionally post a follow-up with questions 4–6 from the
  corrected draft if he wants them on the record.
