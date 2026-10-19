from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("reference", ROOT / "reference.py")
assert SPEC and SPEC.loader
reference = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reference)


class ReferenceTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.traces = json.loads(
            (ROOT / "fixtures" / "reference_traces.json").read_text()
        )["traces"]

    def test_four_reference_traces_verify(self):
        self.assertEqual(4, len(self.traces))
        for trace in self.traces:
            reference.verify_trace(trace)

    def test_reference_traces_cover_expected_scenarios(self):
        self.assertEqual(
            {
                "paid-placement-ordering",
                "marketplace-cross-sell",
                "seller-upsell",
                "affiliated-substitution",
            },
            {trace["trace_id"] for trace in self.traces},
        )

    def test_every_reference_trace_reaches_checkout(self):
        for trace in self.traces:
            self.assertEqual("checkout", trace["bindings"][-1]["stage"])

    def test_statement_mutation_is_detected(self):
        trace = copy.deepcopy(self.traces[0])
        trace["statement"]["basis"] = "platform_merchandising"
        with self.assertRaises(reference.IntegrityError):
            reference.verify_trace(trace)

    def test_subject_mutation_is_detected(self):
        trace = copy.deepcopy(self.traces[0])
        trace["bindings"][-1]["subject_ref"] = "line_item:other"
        with self.assertRaises(reference.IntegrityError):
            reference.verify_trace(trace)

    def test_missing_predecessor_is_detected(self):
        trace = copy.deepcopy(self.traces[0])
        trace["bindings"][2]["predecessor_binding_digest"] = None
        with self.assertRaises(reference.IntegrityError):
            reference.verify_trace(trace)

    def test_stale_predecessor_race_is_detected(self):
        trace = copy.deepcopy(self.traces[0])
        trace["bindings"][3]["predecessor_binding_digest"] = trace["bindings"][1]["binding_digest"]
        with self.assertRaises(reference.IntegrityError):
            reference.verify_trace(trace)

    def test_stage_reordering_is_detected(self):
        trace = copy.deepcopy(self.traces[0])
        trace["bindings"][1], trace["bindings"][2] = trace["bindings"][2], trace["bindings"][1]
        with self.assertRaises(reference.ProvenanceError):
            reference.verify_trace(trace)

    def test_unknown_statement_field_is_rejected(self):
        statement = copy.deepcopy(self.traces[0]["statement"])
        statement["trust_tier"] = "trusted"
        with self.assertRaises(reference.ProvenanceError):
            reference.statement_digest(statement)

    def test_actor_and_asserter_must_be_explicit(self):
        statement = copy.deepcopy(self.traces[0]["statement"])
        del statement["asserter"]
        with self.assertRaises(reference.ProvenanceError):
            reference.statement_digest(statement)

    def test_complete_empty_disclosure_means_none_asserted(self):
        self.assertEqual(
            "none_asserted",
            reference.classify_disclosure(
                {"negotiated": True, "complete": True, "interventions": []}
            ),
        )

    def test_not_negotiated_empty_disclosure_remains_unknown(self):
        self.assertEqual(
            "unknown",
            reference.classify_disclosure(
                {"negotiated": False, "complete": True, "interventions": []}
            ),
        )

    def test_incomplete_empty_disclosure_remains_unknown(self):
        self.assertEqual(
            "unknown",
            reference.classify_disclosure(
                {"negotiated": True, "complete": False, "interventions": []}
            ),
        )

    def test_complete_disclosure_requires_array(self):
        with self.assertRaises(reference.ProvenanceError):
            reference.classify_disclosure({"negotiated": True, "complete": True})

    def test_retry_returns_identical_result(self):
        store = reference.ProjectionStore()
        partial = copy.deepcopy(self.traces[0])
        partial["bindings"] = partial["bindings"][:3]
        first = store.project("transition-1", partial, "checkout", "checkout_line_item:hub")
        retry = store.project("transition-1", partial, "checkout", "checkout_line_item:hub")
        self.assertEqual(first, retry)

    def test_transition_id_reuse_with_changed_input_is_rejected(self):
        store = reference.ProjectionStore()
        partial = copy.deepcopy(self.traces[0])
        partial["bindings"] = partial["bindings"][:3]
        store.project("transition-1", partial, "checkout", "checkout_line_item:hub")
        with self.assertRaises(reference.ReplayConflict):
            store.project("transition-1", partial, "checkout", "checkout_line_item:other")

    def test_projection_cannot_repeat_stage(self):
        partial = copy.deepcopy(self.traces[0])
        partial["bindings"] = partial["bindings"][:3]
        with self.assertRaises(reference.ProjectionError):
            reference.append_projection(partial, "cart", "cart_line_item:hub")

    def test_projection_does_not_change_actor_or_asserter(self):
        partial = copy.deepcopy(self.traces[0])
        partial["bindings"] = partial["bindings"][:3]
        projected = reference.append_projection(partial, "checkout", "checkout_line_item:hub")
        self.assertEqual(partial["statement"]["actor"], projected["statement"]["actor"])
        self.assertEqual(partial["statement"]["asserter"], projected["statement"]["asserter"])

    def test_digest_is_deterministic_across_key_order(self):
        statement = self.traces[0]["statement"]
        reversed_statement = dict(reversed(list(statement.items())))
        self.assertEqual(
            reference.statement_digest(statement),
            reference.statement_digest(reversed_statement),
        )

    def test_same_statement_can_bind_different_subjects_without_changing_statement_digest(self):
        statement = self.traces[0]["statement"]
        one = reference.make_binding(statement, "catalog", "result:1", None)
        two = reference.make_binding(statement, "catalog", "result:2", None)
        self.assertEqual(one["statement_digest"], two["statement_digest"])
        self.assertNotEqual(one["binding_digest"], two["binding_digest"])


if __name__ == "__main__":
    unittest.main()
