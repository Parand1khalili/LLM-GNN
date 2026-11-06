"""Synthetic, offline tests of R0 discovery and private node journey."""
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from llmgnn_sara.evaluation import cora_node_journey as journey
from llmgnn_sara.sara2.policy import Annotation, Pair, route_r0
from llmgnn_sara.sara3.audit import PrivateAudit


def fixture():
    pairs = {}
    for n in range(140):
        confidence = 10 if n < 37 else 90
        pairs[n] = Pair(
            Annotation(n, 0, confidence),
            Annotation(n, 0, confidence),
            "Synthetic paper about mathematical learning")
    selected = list(route_r0(tuple(pairs.values()), 37))
    assert selected == list(range(37))
    reasons = (["COUNTER_EVIDENCE_UNRESOLVED"] * 11 +
               ["THIRD_CLASS_DIAGNOSTIC_ONLY"] * 9 +
               ["BLIND_ABSTENTION"] * 7 +
               ["AUXILIARY_METHOD_WARNING"] * 6 +
               ["VERIFIER_ABSTAINED"] * 2 +
               ["PRIMARY_TOPIC_DRIFT"] +
               ["L1_DUPLICATE_EVIDENCE"])
    labels = [n % 7 for n in range(2708)]
    for n in range(11, 20):
        labels[n] = 1 if n < 15 else 0
    decisions = []
    for n in range(140):
        reason = reasons[n] if n < 37 else "FROZEN_BASELINE"
        blind = 1 if 11 <= n < 20 else 0
        comparison = blind
        if 18 <= n < 20:
            comparison = 0
        if 20 <= n < 27:
            blind = comparison = None
        if n in (33, 34, 36):
            comparison = None
        decisions.append({
            "node_id": n,
            "routed_for_review": n < 37,
            "b1_class_index": 0, "narrative_v0_class_index": 0,
            "blind_class_index": blind if n < 37 else None,
            "comparison_class_index": comparison if n < 37 else None,
            "reason": reason,
            "accepted": n >= 37,
            "training_class_index": 0 if n >= 37 else None,
            "l2_status": "NOT_ASSESSED" if n < 37 else "NOT_APPLICABLE_BASELINE_POLICY",
            "semantic_validation": "NOT_PERFORMED",
        })
    return selected, decisions, pairs, labels


class NodeJourneyTests(unittest.TestCase):
    def setUp(self):
        self.selected, self.decisions, self.pairs, self.labels = fixture()

    def report(self):
        return journey.build_journey(
            self.selected, self.decisions, self.pairs, self.labels)

    def test_all_140_and_37_selection_quality_without_conflating_agent(self):
        result = self.report()
        summary, rows = result["summary"], result["node_rows_owner_private"]
        self.assertEqual(len(rows), 140)
        self.assertEqual(len({row["node_id"] for row in rows}), 140)
        self.assertEqual(sum(row["r0_selected_for_review"] for row in rows), 37)
        self.assertEqual(sum(row["r0_selected_for_review"] is False for row in rows), 103)
        self.assertEqual(summary["who_flagged_for_review"], "R0_NOT_SARA3")
        oracle = summary["r0_oracle_routing"]["either_wrong"]
        self.assertEqual(oracle["all_140"], 116)
        self.assertEqual(oracle["selected_true_positive"], 27)
        self.assertEqual(oracle["selected_false_positive"], 10)
        self.assertEqual(oracle["missed_false_negative"], 89)
        self.assertEqual(oracle["not_selected_true_negative"], 14)
        for name in journey.CRITERIA:
            counts = summary["r0_oracle_routing"][name]
            self.assertEqual(counts["selected_true_positive"] + counts["selected_false_positive"], 37)
            self.assertEqual(counts["missed_false_negative"] + counts["not_selected_true_negative"], 103)
        self.assertNotIn("node_id", json.dumps(summary))
        self.assertFalse(summary["narrative_fallback_descriptive_only"]["blind"].get("is_policy", False))

    def test_per_node_review_answers_and_counterfactual_fallback_are_exact(self):
        result = self.report()
        row = next(x for x in result["node_rows_owner_private"] if x["node_id"] == 11)
        self.assertEqual(row["b1_class_index"], 0)
        self.assertEqual(row["narrative_v0_class_index"], 0)
        self.assertEqual(row["blind_class_index"], 1)
        self.assertEqual(row["ground_truth_class_index"], 1)
        self.assertEqual(row["narrative_to_blind"], "CORRECTED_BASELINE_ERROR")
        damaged = next(x for x in result["node_rows_owner_private"] if x["node_id"] == 15)
        self.assertEqual(damaged["narrative_to_blind"], "DAMAGED_CORRECT_BASELINE")
        self.assertEqual(damaged["narrative_to_comparison"], "DAMAGED_CORRECT_BASELINE")
        blank = next(x for x in result["node_rows_owner_private"] if x["node_id"] == 23)
        self.assertEqual(blank["narrative_to_blind"], "NO_CLASS_PREDICTION")
        unrouted = next(x for x in result["node_rows_owner_private"] if x["node_id"] == 137)
        self.assertEqual(unrouted["narrative_to_blind"], "NOT_REVIEWED")
        self.assertIsNone(unrouted["frozen_arbitration_reason"])
        self.assertEqual(sum(x["frozen_training_admitted"] is True
                             for x in result["node_rows_owner_private"]), 0)
        self.assertEqual(result["summary"]["reviewed_phase_changes"]["b1_to_blind"]["denominator"], 37)
        self.assertEqual(result["summary"]["reviewed_phase_changes"]["narrative_v0_to_comparison"]["NO_CLASS_PREDICTION"], 10)
        for phase in journey.PHASES:
            fallback = result["summary"]["narrative_fallback_descriptive_only"][phase]
            ref = result["summary"]["reviewed_phase_changes"][f"narrative_v0_to_{phase}"]
            self.assertEqual(fallback["net_delta_correct"], ref["net_corrections_on_covered"])

    def test_selection_tampering_and_frozen_decisions_fail_closed(self):
        bad = list(self.selected)
        bad[0], bad[-1] = bad[-1], bad[0]
        with self.assertRaises(ValueError):
            journey.build_journey(bad, self.decisions, self.pairs, self.labels)
        for field, value in [("routed_for_review", False),
                             ("training_class_index", 3),
                             ("blind_class_index", 7)]:
            decisions = deepcopy(self.decisions)
            decisions[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                journey.build_journey(self.selected, decisions, self.pairs, self.labels)

    def test_private_content_addressed_write_and_sanitized_cli(self):
        report = self.report()
        with tempfile.TemporaryDirectory() as root:
            audit = PrivateAudit(Path(root) / ".local_artifacts" / "gt_journey")
            digest = audit.write(report)
            self.assertEqual(audit.read(digest), report)
            self.assertEqual(audit.write(report), digest)
        args = [item for field in ("frozen-root", "authentic-root", "run-root",
                                  "gateway-config", "graph-file", "audit-root")
                for item in ("--" + field, "unused")]
        with patch.object(journey, "run", side_effect=journey.EvaluationStageError(
                "NODE_JOURNEY_RECONCILIATION")), \
             patch("sys.stdout", new_callable=io.StringIO) as stdout, \
             patch("sys.stderr", new_callable=io.StringIO) as stderr:
            self.assertEqual(journey.main(args), 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(json.loads(stderr.getvalue()),
                         {"status": "FAIL_CLOSED", "stage": "NODE_JOURNEY_RECONCILIATION"})


if __name__ == "__main__":
    unittest.main()
