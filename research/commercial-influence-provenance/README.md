# Commercial influence provenance reference harness

This directory is an experimental, vendor-namespaced reference package for
[Discussion #724](https://github.com/Universal-Commerce-Protocol/ucp/discussions/724).
It is not a UCP capability, does not allocate a `dev.ucp.*` identifier, and is
not a claim that UCP or any participant has adopted the model.

The package isolates the part of #724 that is not already owned by the generic
projection proposal in #827: a minimal `CommercialIntervention` assertion and
the rule that its attributable, content-bound provenance remains attached while
its represented effect survives from Catalog through Offer, Cart, and Checkout.

## Model

An immutable statement records:

* `actor`: the party that performed the commercial intervention;
* `asserter`: the party making the statement about that intervention;
* `kind`: the commercial operation that was applied;
* `effect`: the observable surface affected by that operation;
* `basis`: the asserted commercial context; and
* optional `sponsor` when a separate sponsor is relevant.

The statement digest deliberately does not include the stage-specific subject.
Each stage instead creates a binding digest over the immutable statement digest,
the stage, the current subject, and the predecessor binding digest. This makes
the derivation chain tamper-evident without pretending that a content hash proves
the truth of a self-reported commercial motive.

`actor` and `asserter` remain separate. Projecting a record into Business-owned
Checkout state does not make the Business the original actor or asserter. Any
new attestation or trust decision is outside this harness and must not be inferred
from successful projection.

## Four reference traces

`fixtures/reference_traces.json` contains:

1. paid placement affecting Catalog ordering;
2. marketplace cross-sell affecting a purchase proposal;
3. seller upsell affecting a purchase proposal; and
4. marketplace-affiliated substitution affecting commerce state.

Every trace covers Catalog → Offer → Cart → Checkout. `Offer` is an abstract
stage in this harness because Offer #738/#773 is not on the current UCP default
branch. The harness therefore does not claim conformance to an unmerged schema.

## Safety invariants

* A changed immutable statement invalidates every stage binding.
* A stale predecessor cannot win a concurrent projection race.
* The same transition identifier and same input replay deterministically.
* Reusing a transition identifier with different input is rejected.
* If the capability is negotiated and an effect still survives, missing
  provenance fails closed.
* An empty intervention list means “none asserted” only when complete disclosure
  is explicitly declared; absence or incomplete disclosure remains `unknown`.
* Projection never changes `actor` or `asserter` and never upgrades authority.

## Run

```bash
python3 -m unittest discover \
  -s research/commercial-influence-provenance/tests \
  -p 'test_*.py' -v

python3 research/commercial-influence-provenance/validate_fixtures.py
git diff --check
```

The validators use only the Python standard library. The JSON Schema is provided
for review and future `ucp-schema` integration; this experimental package is not
under `source/`, so the repository schema generator does not consume it.

## Scope boundaries

This package does not standardize ranking algorithms, recommendation weights,
auction bids, commission amounts, trust tiers, buyer-policy consequences,
cryptographic attestations, Offer, accepted-term handoff (#845), or mutation
admission/satisfaction evidence (#846). The generic projection lifecycle remains
in #827. Offer identity and state binding remain in #738.

