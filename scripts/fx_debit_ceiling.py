#!/usr/bin/env python3
"""Reference evaluator for a provider-backed buyer debit ceiling.

This module demonstrates the integration decision described in
docs/specification/payment/cross-currency-debit-ceilings.md. It is intentionally
provider-neutral and does not define a UCP schema or perform payment execution.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any


PROCEED = "proceed"
STOP_AND_REAUTHORIZE = "stop_and_reauthorize"


def _parse_instant(value: Any) -> datetime | None:
  if not isinstance(value, str):
    return None
  try:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
  except ValueError:
    return None
  if parsed.tzinfo is None:
    return None
  return parsed.astimezone(timezone.utc)


def _valid_money(value: Any) -> bool:
  return (
    isinstance(value, dict)
    and isinstance(value.get("amount"), int)
    and not isinstance(value.get("amount"), bool)
    and value["amount"] >= 0
    and isinstance(value.get("currency"), str)
    and re.fullmatch(r"[A-Z]{3}", value["currency"]) is not None
  )


def _stop(reason: str) -> dict[str, str]:
  return {"decision": STOP_AND_REAUTHORIZE, "reason": reason}


def evaluate(
  buyer_policy: dict[str, Any],
  checkout: dict[str, Any],
  instrument: dict[str, Any],
  guarantee: dict[str, Any] | None,
  decision_time: str,
) -> dict[str, str]:
  """Return proceed only for a complete, current, exactly bound guarantee."""
  ceiling = buyer_policy.get("maximum_debit")
  required_fees = buyer_policy.get("required_fee_categories")
  if not _valid_money(ceiling):
    return _stop("invalid_buyer_ceiling")
  if not isinstance(required_fees, list) or not all(
    isinstance(fee, str) and fee for fee in required_fees
  ):
    return _stop("invalid_buyer_fee_policy")

  if guarantee is None:
    return _stop("missing_firm_guarantee")
  if guarantee.get("status") != "firm" or guarantee.get("invalidated") is True:
    return _stop("guarantee_not_firm")
  if not all(
    isinstance(guarantee.get(field), str) and guarantee[field]
    for field in ("id", "provider", "enforced_by")
  ):
    return _stop("missing_guarantee_identity_or_enforcer")

  now = _parse_instant(decision_time)
  issued_at = _parse_instant(guarantee.get("issued_at"))
  expires_at = _parse_instant(guarantee.get("expires_at"))
  if now is None or issued_at is None or expires_at is None:
    return _stop("invalid_guarantee_validity")
  if issued_at > now or expires_at <= now or issued_at >= expires_at:
    return _stop("guarantee_outside_validity_window")

  maximum_debit = guarantee.get("maximum_debit")
  if not _valid_money(maximum_debit):
    return _stop("invalid_guaranteed_amount")
  if maximum_debit["currency"] != ceiling["currency"]:
    return _stop("guarantee_currency_mismatch")
  if maximum_debit["amount"] > ceiling["amount"]:
    return _stop("guarantee_exceeds_buyer_ceiling")

  checkout_total = checkout.get("total")
  if not _valid_money(checkout_total):
    return _stop("invalid_checkout_total")
  binding = guarantee.get("binding")
  if not isinstance(binding, dict):
    return _stop("missing_guarantee_binding")
  expected_binding = {
    "checkout_id": checkout.get("id"),
    "checkout_revision": checkout.get("revision"),
    "checkout_total": checkout_total,
    "instrument_id": instrument.get("id"),
    "handler_id": instrument.get("handler_id"),
    "route_id": instrument.get("route_id"),
  }
  if any(value in (None, "") for value in expected_binding.values()):
    return _stop("incomplete_payment_path_binding")
  if any(binding.get(key) != value for key, value in expected_binding.items()):
    return _stop("guarantee_binding_mismatch")

  fee_scope = guarantee.get("fee_scope")
  if not isinstance(fee_scope, dict):
    return _stop("missing_fee_scope")
  included = fee_scope.get("included")
  excluded = fee_scope.get("excluded")
  if not isinstance(included, list) or not isinstance(excluded, list):
    return _stop("invalid_fee_scope")
  if not all(isinstance(fee, str) and fee for fee in included + excluded):
    return _stop("invalid_fee_scope")
  included_set = set(included)
  excluded_set = set(excluded)
  required_set = set(required_fees)
  if included_set & excluded_set:
    return _stop("contradictory_fee_scope")
  if not required_set.issubset(included_set) or required_set & excluded_set:
    return _stop("required_fees_not_covered")

  return {"decision": PROCEED, "reason": "valid_bound_guarantee"}
