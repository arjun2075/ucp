#!/usr/bin/env python3
"""Tests for the cross-currency buyer debit ceiling reference evaluator."""

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fx_debit_ceiling import PROCEED, STOP_AND_REAUTHORIZE, evaluate  # noqa: E402


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "fx_debit_ceiling.json"


class DebitCeilingEvaluatorTest(unittest.TestCase):
  """Exercise the evaluator's proceed and fail-closed decisions."""

  @classmethod
  def setUpClass(cls) -> None:
    """Load the canonical valid fixture once for all test cases."""
    cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

  def _evaluate(self, fixture: dict | None = None) -> dict[str, str]:
    case = fixture or self.fixture
    return evaluate(
      case["buyer_policy"],
      case["checkout"],
      case["instrument"],
      case.get("guarantee"),
      case["decision_time"],
    )

  def _mutated(self) -> dict:
    return copy.deepcopy(self.fixture)

  def test_valid_exact_boundary_proceeds(self) -> None:
    """Accept a fee-complete guarantee exactly at the buyer ceiling."""
    self.assertEqual(PROCEED, self._evaluate()["decision"])

  def test_indicative_estimate_never_substitutes_for_guarantee(self) -> None:
    """Reject an indicative estimate when the firm guarantee is absent."""
    case = self._mutated()
    case["estimate"] = {
      "amount": 49500,
      "currency": "USD",
      "kind": "indicative",
    }
    case["guarantee"] = None
    self.assertEqual(STOP_AND_REAUTHORIZE, self._evaluate(case)["decision"])

  def test_expired_guarantee_stops(self) -> None:
    """Treat the expiry instant itself as outside the validity window."""
    case = self._mutated()
    case["decision_time"] = case["guarantee"]["expires_at"]
    self.assertEqual(
      "guarantee_outside_validity_window", self._evaluate(case)["reason"]
    )

  def test_checkout_revision_tamper_stops(self) -> None:
    """Reject reuse after the bound Checkout revision changes."""
    case = self._mutated()
    case["checkout"]["revision"] = "8"
    self.assertEqual(
      "guarantee_binding_mismatch", self._evaluate(case)["reason"]
    )

  def test_checkout_total_tamper_stops(self) -> None:
    """Reject reuse after the authoritative Checkout total changes."""
    case = self._mutated()
    case["checkout"]["total"]["amount"] += 1
    self.assertEqual(
      "guarantee_binding_mismatch", self._evaluate(case)["reason"]
    )

  def test_instrument_change_stops(self) -> None:
    """Reject reuse with another payment instrument."""
    case = self._mutated()
    case["instrument"]["id"] = "pi_card_2"
    self.assertEqual(
      "guarantee_binding_mismatch", self._evaluate(case)["reason"]
    )

  def test_route_change_stops(self) -> None:
    """Reject reuse on a payment route the provider did not bind."""
    case = self._mutated()
    case["instrument"]["route_id"] = "route_usd_presentment_2"
    self.assertEqual(
      "guarantee_binding_mismatch", self._evaluate(case)["reason"]
    )

  def test_additional_provider_binding_metadata_is_allowed(self) -> None:
    """Allow provider extensions without weakening required bindings."""
    case = self._mutated()
    case["guarantee"]["binding"]["provider_attempt_id"] = "attempt_1"
    self.assertEqual(PROCEED, self._evaluate(case)["decision"])

  def test_over_limit_guarantee_stops(self) -> None:
    """Reject a firm maximum that exceeds the buyer's debit ceiling."""
    case = self._mutated()
    case["guarantee"]["maximum_debit"]["amount"] += 1
    self.assertEqual(
      "guarantee_exceeds_buyer_ceiling", self._evaluate(case)["reason"]
    )

  def test_currency_mismatch_stops_without_conversion(self) -> None:
    """Reject a guarantee denominated in another currency."""
    case = self._mutated()
    case["guarantee"]["maximum_debit"]["currency"] = "EUR"
    self.assertEqual(
      "guarantee_currency_mismatch", self._evaluate(case)["reason"]
    )

  def test_uncovered_issuer_fee_stops(self) -> None:
    """Reject a guarantee that excludes a fee required by buyer policy."""
    case = self._mutated()
    case["guarantee"]["fee_scope"] = {
      "included": ["provider"],
      "excluded": ["issuer"],
    }
    self.assertEqual(
      "required_fees_not_covered", self._evaluate(case)["reason"]
    )

  def test_invalidated_guarantee_stops(self) -> None:
    """Reject a provider-invalidated guarantee even before expiry."""
    case = self._mutated()
    case["guarantee"]["invalidated"] = True
    self.assertEqual("guarantee_not_firm", self._evaluate(case)["reason"])

  def test_boolean_amount_is_not_an_integer_amount(self) -> None:
    """Reject Python booleans even though bool subclasses int."""
    case = self._mutated()
    case["guarantee"]["maximum_debit"]["amount"] = True
    self.assertEqual(
      "invalid_guaranteed_amount", self._evaluate(case)["reason"]
    )

  def test_non_ascii_currency_code_stops(self) -> None:
    """Require an ASCII three-letter currency code."""
    case = self._mutated()
    case["guarantee"]["maximum_debit"]["currency"] = "ÜSD"
    self.assertEqual(
      "invalid_guaranteed_amount", self._evaluate(case)["reason"]
    )


if __name__ == "__main__":
  unittest.main()
