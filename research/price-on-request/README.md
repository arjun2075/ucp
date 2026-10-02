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
and [unsent EP draft](ENHANCEMENT_PROPOSAL_DRAFT.md) describe the candidate.

## Run the schema checks

From the root of a clone of this branch:

```bash
python3 -m venv /tmp/ucp-por-venv
/tmp/ucp-por-venv/bin/pip install jsonschema==4.10.3
git worktree add --detach /tmp/ucp-por-baseline b0e81adecf816a1771b736464f17586d76950f7f
/tmp/ucp-por-venv/bin/python research/price-on-request/harness/run.py \
  --baseline /tmp/ucp-por-baseline --proposed "$PWD" --skip-sdk --fuzz 300
```

The schema harness contains 20 fixture vectors plus 300 generated priced variants
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
files and the applied patch: 20/20 fixtures passed, and 300 generated variants
plus 300 generated products had zero mismatches (exit 0). SDK checks were skipped.
See [raw output](logs/publication-schema-check.log). This was another agent check,
not independent human validation.
