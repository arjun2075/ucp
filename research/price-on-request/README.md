# Experimental price-on-request catalog prototype

This branch is a research prototype for [UCP #877](https://github.com/Universal-Commerce-Protocol/ucp/issues/877).
It is **not approved UCP behavior** and is not an upstream implementation PR.

Credits: evoleinik supplied the use case and implementation observations;
juanferrub proposed the pricing-mode object. Arjun Garg prepared this prototype.
Buyer-specific and contract-only semantics, enum extensibility, release
classification and cache isolation remain design decisions for the EP process.

Base: `b0e81adecf816a1771b736464f17586d76950f7f`.
The six schema/spec modifications are in their normal repository paths.
[Design](DESIGN.md), [compatibility](COMPATIBILITY.md), [source map](SOURCE_MAP.md)
and [unsent submission-ready EP draft](EP_SUBMISSION_DRAFT.md) describe the candidate.

## Run the schema checks

From the root of a clone of this branch:

```bash
python3 -m venv /tmp/ucp-por-venv
/tmp/ucp-por-venv/bin/pip install jsonschema==4.10.3
git worktree add --detach /tmp/ucp-por-baseline b0e81adecf816a1771b736464f17586d76950f7f
/tmp/ucp-por-venv/bin/python research/price-on-request/harness/run.py \
  --baseline /tmp/ucp-por-baseline --proposed "$PWD" --skip-sdk --fuzz 300
```

The schema harness contains 28 fixture vectors plus 300 generated priced variants
and 300 generated priced products. Generated cases cover that subset only;
they do not prove universal compatibility. The candidate rejects some payloads
accepted by the baseline, including conflicting or unknown `pricing` values.

The SDK leg is explicitly skipped above. To run it, install Pydantic and pass
`--sdk` pointing to the pinned Python SDK clone; see [harness documentation](harness/README.md).
JS SDK evidence is static corroboration only. Repository schema lint, example
validation, SDK generation and strict docs checks remain incomplete; this
publication does not claim these checks passed. Historical results were
self-reviewed; no maintainer or TC endorsement is claimed.

## Publication verification

On 2026-10-02 the schema-only harness was rerun against pinned upstream schema
files and the applied patch: 28/28 fixtures passed, and 300 generated variants
plus 300 generated products had zero mismatches (exit 0). SDK checks were skipped.
See [raw output](logs/publication-schema-check.log). This was another agent check,
not independent human validation.

## Follow-through evidence (2026-10-02)

The schema/spec candidate is unchanged from `6fee350`. This follow-up publishes
8 additional fixtures, the expanded compatibility matrix, formal EP filing draft,
and [verification results](VERIFICATION_RESULTS.md) with the canonical raw logs.
Schema lint and strict docs build passed in the research agent's environment;
live JS SDK validation passed 3/3. Example validation ran but failed: baseline
376 passed/0 failed; patched 374 passed/3 failed. All three failures are caused
by the candidate/scaffold interaction. SDK generation remains blocked, and logs
also show conditional rules being skipped. No new generated-model enforcement
is claimed. The EP is **unfiled** and no upstream implementation PR is open.

The published log subset contains the successful checks and canonical failures.
Superseded environment failures and installation logs remain in the Drive
handoff. Paths in historical logs identify the research agent's workspace.
Those historical runs were not independently rerun by the publishing agent;
only the expanded schema harness was rerun for this publication.

Expanded publication rerun: 28/28 fixtures, 300 variants + 300 products with zero
mismatches, exit 0; SDK skipped. See [raw output](logs/publication-followthrough-schema-check.log).
