#!/usr/bin/env python3
"""Contract tests for caller-dependent catalog pricing states.

The cases exercise the compatibility default, each well-known mode, open-mode
forward compatibility, range eligibility, and conflicting selling-price
signals. Run with ``uv run python scripts/test_catalog_pricing_states.py``.
"""

import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_ROOT = REPO_ROOT / "source" / "schemas"


def _registry() -> Registry:
  """Build an offline registry for every source schema with a canonical ID."""
  registry = Registry()
  for path in SCHEMA_ROOT.rglob("*.json"):
    schema = json.loads(path.read_text(encoding="utf-8"))
    schema_id = schema.get("$id")
    if schema_id:
      registry = registry.with_resource(
        schema_id,
        Resource.from_contents(schema),
      )
  return registry


def _validator(path: str, registry: Registry) -> Draft202012Validator:
  """Return a Draft 2020-12 validator for a source schema."""
  schema = json.loads((SCHEMA_ROOT / path).read_text(encoding="utf-8"))
  return Draft202012Validator(
    schema,
    registry=registry,
    format_checker=FormatChecker(),
  )


def _price(amount: int = 10_000) -> dict:
  """Return a valid USD price."""
  return {"amount": amount, "currency": "USD"}


def _price_range(amount: int = 10_000) -> dict:
  """Return a valid single-value USD price range."""
  return {"min": _price(amount), "max": _price(amount)}


def _variant(
  variant_id: str,
  *,
  price: bool = False,
  mode: str | None = None,
  next_step: str | None = None,
) -> dict:
  """Build the minimal variant shape used by the cases."""
  value = {
    "id": variant_id,
    "title": variant_id,
    "description": {"plain": variant_id},
  }
  if price:
    value["price"] = _price()
  if mode is not None:
    value["pricing"] = {"mode": mode}
    if next_step is not None:
      value["pricing"]["next_step"] = next_step
  return value


def _product(variants: list[dict], *, price_range: bool = False) -> dict:
  """Build the minimal product shape used by the cases."""
  value = {
    "id": "prod_test",
    "title": "Test product",
    "description": {"plain": "Pricing-state contract fixture."},
    "variants": variants,
  }
  if price_range:
    value["price_range"] = _price_range()
  return value


def _unit_price() -> dict:
  """Return a valid unit-price comparator used for a conflict test."""
  return {
    "amount": 200,
    "currency": "USD",
    "measure": {"value": 40, "scale": 2, "unit": "LBR"},
    "reference": {"value": 1, "unit": "LBR"},
  }


def main() -> int:
  """Run positive and negative pricing-state contract cases."""
  registry = _registry()
  product_validator = _validator(
    "shopping/types/product.json",
    registry,
  )
  variant_validator = _validator(
    "shopping/types/variant.json",
    registry,
  )

  public = _variant("public", price=True)
  quote = _variant(
    "quote",
    mode="quote_required",
    next_step="request_quote",
  )
  buyer_unresolved = _variant("buyer-unresolved", mode="buyer_specific")
  buyer_resolved = _variant(
    "buyer-resolved",
    price=True,
    mode="buyer_specific",
  )
  unknown_unpriced = _variant("future-unpriced", mode="future_mode")
  unknown_priced = _variant(
    "future-priced",
    price=True,
    mode="future_mode",
  )

  cases = [
    (
      "legacy public price and range",
      _product([public], price_range=True),
      True,
    ),
    ("legacy public missing price", _product([_variant("bad")]), False),
    ("all public requires range", _product([public]), False),
    ("quote without price or range", _product([quote]), True),
    (
      "quote rejects a selling price",
      _product(
        [_variant("bad-quote", price=True, mode="quote_required")],
      ),
      False,
    ),
    ("all quote rejects range", _product([quote], price_range=True), False),
    ("buyer-specific unresolved", _product([buyer_unresolved]), True),
    (
      "buyer-specific resolved requires range",
      _product([buyer_resolved], price_range=True),
      True,
    ),
    ("unknown unpriced mode is tolerated", _product([unknown_unpriced]), True),
    ("unknown priced mode is tolerated", _product([unknown_priced]), True),
    (
      "unknown priced mode cannot create a range",
      _product([unknown_priced], price_range=True),
      False,
    ),
    ("mixed public and quote may omit range", _product([public, quote]), True),
    (
      "mixed public and quote may publish eligible range",
      _product([public, quote], price_range=True),
      True,
    ),
    (
      "mixed public and unknown may publish eligible range",
      _product([public, unknown_priced], price_range=True),
      True,
    ),
  ]

  failures = []
  for name, payload, expected in cases:
    errors = sorted(product_validator.iter_errors(payload), key=str)
    actual = not errors
    status = "PASS" if actual == expected else "FAIL"
    print(f"  {status}  {name}")
    if actual != expected:
      failures.append((name, errors))

  unit_conflict = _variant("unit-conflict", mode="contract_only")
  unit_conflict["unit_price"] = _unit_price()
  unit_errors = sorted(variant_validator.iter_errors(unit_conflict), key=str)
  unit_ok = bool(unit_errors)
  print(f"  {'PASS' if unit_ok else 'FAIL'}  unpriced mode rejects unit_price")
  if not unit_ok:
    failures.append(("unpriced mode rejects unit_price", unit_errors))

  if failures:
    for name, errors in failures:
      detail = "; ".join(error.message for error in errors[:3])
      print(f"FAIL: {name}: {detail}", file=sys.stderr)
    return 1

  print(f"\n{len(cases) + 1} passed, 0 failed")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
