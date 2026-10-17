# Experimental catalog pricing-state implementation

This is a research implementation supporting UCP issue #877. It is not
approved UCP behavior and must not be merged into upstream core before the
required TC decision. No standard capability identifier is allocated here.

evoleinik supplied the original use case and deployment observations;
juanferrub proposed the pricing-state object. Arjun Garg implemented the
schema prototype, compatibility analysis and tests. No coauthorship or
endorsement is implied.

## Baselines

- Current upstream base: `3ab41043b79373df33a6e2c377bc82a806175f78`.
- Historical prototype: `565e7c3046f25e588f1f26871dc3a88811145b3a`.
- This increment ports the eight schema/documentation changes to current main,
  repairs the harness's nested-reference resolution using an offline registry,
  adds unknown-mode range omission coverage, and supplies consumer helpers.

## Behavior

| Mode | Selling price |
| --- | --- |
| Absent or public | Required |
| buyer_specific | Optional; retained when resolved |
| quote_required or contract_only | Forbidden |
| Unknown string | Structurally optional; no usable price to an unaware client |

Missing price never means zero. Reference list prices are not selling prices.
Quote hints may coexist with a usable price. Price ranges and cache entries
retain the response's caller and authorization context.

The core schema cannot be relaxed by an ordinary allOf extension: its required
price constraint still applies. This explains the core EP request rather than
claiming vendor namespace support or ecosystem adoption that does not exist.

Purchase Options #901 was folded into the open #890 branch, not adopted on
main. This patch does not modify that branch's option schemas. The pricing
state must eventually qualify each price at its own granularity; mixed
public-buy/quote-only-lease options remain an explicit composition dependency.

## Reproduce

From the repository root, with a separate checkout of the upstream base:

```sh
python -m pip install -r research/price-on-request/harness/requirements.txt
python research/price-on-request/harness/run.py \
  --baseline ../ucp-pricing-baseline --proposed . --fuzz 300
python -m unittest discover -s research/price-on-request/harness -p 'test_*.py' -v
```

The suite exercises 44 baseline/proposed schema vectors, 600 generated priced
compatibility probes and 600 generated mode probes. These finite subsets do
not prove universal compatibility. Ten consumer tests cover the motivating
free-price error, unknown-mode fallback, reference prices, range recomputation,
quote hints and isolated response storage.

`consumer.py` accepts schema-validated inputs. Its cache is a reference map,
not buyer authentication or an HTTP cache: callers must derive the correct
opaque context and enforce expiry, entitlement revalidation and freshness.
It does not demonstrate production cache security. Currency conversion and
cross-unit comparison are unsupported. Schema validation is not generated-SDK
validation or end-to-end Cart/Checkout interoperability.

## Compatibility and publication

Old validating consumers reject unpriced payloads. An old lenient consumer
may incorrectly show a missing amount as zero. Reserving the previously-open
pricing property also invalidates some formerly accepted payloads: malformed
pricing objects and a selling price alongside a newly unpriced known mode.
Release/version negotiation and the field-name collision survey require TC
review. Do not describe this as purely additive or select a release version.

This increment is published as a draft PR in Arjun's fork for review. The
upstream schema decision, SDK generation, complete documentation-example
validation, independent interoperability and Purchase Options composition
remain gates before upstream implementation can be considered complete.
