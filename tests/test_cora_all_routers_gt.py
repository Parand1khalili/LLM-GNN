"""All-router GT oracle tests use synthetic labels and synthetic frozen decisions."""
from copy import deepcopy
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from llmgnn_sara.evaluation import cora_all_routers_gt as target
from llmgnn_sara.sara2.policy import Annotation, Pair, route_r0
from llmgnn_sara.sara3.audit import PrivateAudit


def fixture():
    pairs = {}
    for node in range(140):
        confidence = 10 if node < 37 else 90
        sample = ("rule induction theorem" if node % 3 == 0 else
                  "neural network reward probabilistic" if node % 3 == 1 else
                  "ordinary unrelated article words")
        pairs[node] = Pair(
            Annotation(node, 0, confidence),
            Annotation(node, 0, confidence), sample)
    selected = list(route_r0(tuple(pairs.values()), 37))
    assert selected == list(range(37))
    reasons = (["COUNTER_EVIDENCE_UNRESOLVED"] * 11 +
               ["THIRD_CLASS_DIAGNOSTIC_ONLY"] * 9 +
               ["BLIND_ABSTENTION"] * 7 +
               ["AUXILIARY_METHOD_WARNING"] * 6 +
               ["VERIFIER_ABSTAINED"] * 2 +
               ["PRIMARY_TOPIC_DRIFT", "L1_DUPLICATE_EVIDENCE"])
    assert len(reasons) == 37
    labels = [node % 7 for node in range(2708)]
    for node in range(11, 20):
        labels[node] = 1 if node < 15 else 0
    decisions = []
    for node in range(140):
        reason = reasons[node] if node < 37 else "FROZEN_BASELINE"
        blind = 1 if 11 <= node < 20 else 0
        comparison = 0 if 18 <= node < 20 else blind
        if 20 <= node < 27:
            blind = comparison = None
        if node in (33, 34, 36):
            comparison = None
        decisions.append({
            "node_id": node, "routed_for_review": node < 37,
            "b1_class_index": 0, "narrative_v0_class_index": 0,
            "blind_class_index": blind if node < 37 else None,
            "comparison_class_index": comparison if node < 37 else None,
            "accepted": node >= 37,
            "training_class_index": 0 if node >= 37 else None,
            "l2_status": "NOT_ASSESSED" if node < 37 else "NOT_APPLICABLE_BASELINE_POLICY",
            "semantic_validation": "NOT_PERFORMED", "reason": reason})
    return selected, decisions, pairs, labels


class AllRoutersGTTests(unittest.TestCase):
    def setUp(self):
        self.selected, self.decisions, self.pairs, self.labels = fixture()
        no_network = patch.object(socket.socket, "connect",
                                  side_effect=AssertionError("No HTTP allowed"))
        no_network.start()
        self.addCleanup(no_network.stop)

    def report(self):
        return target.compare_routers(
            self.selected, self.decisions, self.pairs, self.labels)

    def test_all_six_router_selections_budget_overlap_and_r0_preserved(self):
        before = deepcopy((self.selected, self.decisions, self.labels))
        report = self.report()
        self.assertEqual(before, (self.selected, self.decisions, self.labels))
        aggregate = report["aggregate"]
        self.assertEqual(set(aggregate["router_names"]), {
            "r0", "semantic", "r1_v1", "r1_neutral_v1", "r1_v2", "r2_v1"})
        self.assertEqual(len(report["node_rows_owner_private"]), 140)
        self.assertEqual(len(aggregate["pairwise_selection_and_error_capture"]), 15)
        for name, stats in aggregate["GT_only_routing_accuracy"].items():
            self.assertEqual(stats["selected_count"], 37, name)
            detect = stats["oracle_error_discovery_posthoc"]
            for criterion in target.ERROR_CRITERIA:
                row = detect[criterion]
                self.assertEqual(row["selected_error"] + row["selected_no_error"], 37)
                self.assertEqual(row["missed_error"] + row["not_selected_no_error"], 103)
                self.assertEqual(row["selected_error"] + row["missed_error"], row["all_140"])
            self.assertEqual(sum(x["selected_truth_support"]
                                 for x in stats["per_true_class_oracle_selected"]), 37)
        self.assertEqual(
            aggregate["GT_only_routing_accuracy"]["r0"]
            ["oracle_error_discovery_posthoc"]["either_wrong"]["selected_error"], 27)
        self.assertEqual(aggregate["GT_only_routing_accuracy"]["r0"]
                         ["oracle_error_discovery_posthoc"]["either_wrong"]["all_140"], 116)
        self.assertEqual(aggregate["GT_only_routing_accuracy"]["r0"]
                         ["overlap_with_real_R0_review"], 37)
        self.assertEqual(aggregate["real_R0_verifier_only"]
                         ["reviewed_phase_changes"]["narrative_v0_to_blind"]
                         ["NO_CLASS_PREDICTION"], 7)
        for name in aggregate["router_names"]:
            self.assertIn(name, aggregate["GT_only_routing_accuracy"])
            if name != "r0":
                self.assertEqual(aggregate["GT_only_routing_accuracy"][name]
                                 ["real_agent_verifier_for_this_router"],
                                 "NOT_RUN_FOR_THIS_ROUTER")

    def test_each_router_per_node_is_oracle_only_and_actual_verifier_r0_only(self):
        report = self.report()
        rows = report["node_rows_owner_private"]
        row0 = rows[0]
        self.assertEqual(row0["ground_truth_class_index"], self.labels[0])
        self.assertEqual(row0["r0_selected_for_review"], True)
        self.assertEqual(row0["router_membership"]["r0"]["actual_verifier_execution"],
                         "R0_FROZEN")
        self.assertEqual(row0["router_membership"]["r0"]["rank_if_selected"], 1)
        for row in rows:
            for name in target.ROUTER_NAMES:
                selection = row["router_membership"][name]
                if name != "r0":
                    self.assertEqual(selection["actual_verifier_execution"], "NOT_EXECUTED")
                self.assertEqual(selection["selected"], selection["rank_if_selected"] is not None)
            if not row["r0_selected_for_review"]:
                self.assertIsNone(row["blind_class_index"])
                self.assertIsNone(row["comparison_class_index"])
        self.assertEqual(report["aggregate"]["other_router_verifier_results"],
                         "NO_REAL_LLM_RUN_NO_LABEL_CORRECTION_RESULTS")
        self.assertNotIn("node_id", json.dumps(report["aggregate"]))
        self.assertNotIn("ground_truth_class_index", json.dumps(report["aggregate"]))

    def test_pairwise_true_error_accounting_and_neutral_is_distinct(self):
        report = self.report()
        stats = report["aggregate"]["GT_only_routing_accuracy"]
        expected = {}
        for name in target.ROUTER_NAMES:
            expected[name] = {r["node_id"] for r in report["node_rows_owner_private"]
                              if r["router_membership"][name]["selected"]}
        self.assertEqual(expected["r0"], set(self.selected))
        pairs = report["aggregate"]["pairwise_selection_and_error_capture"]
        for i, a in enumerate(target.ROUTER_NAMES):
            for b in target.ROUTER_NAMES[i+1:]:
                item = pairs[f"{a}__{b}"]
                self.assertEqual(item["common_nodes"], len(expected[a] & expected[b]))
                self.assertEqual(item["a_only"], 37 - item["common_nodes"])
                self.assertEqual(item["b_only"], 37 - item["common_nodes"])
                self.assertEqual(
                    item["common_with_baseline_error"] + item["a_only_with_baseline_error"],
                    stats[a]["oracle_error_discovery_posthoc"]["either_wrong"]["selected_error"])
                self.assertEqual(
                    item["common_with_baseline_error"] + item["b_only_with_baseline_error"],
                    stats[b]["oracle_error_discovery_posthoc"]["either_wrong"]["selected_error"])

    def test_invalid_r0_decision_or_registry_fail_closed(self):
        with patch.object(target, "ROUTERS", ("r0", "semantic", "r1_v1", "r1_v2", "r2_v1", "new")):
            with self.assertRaises(ValueError):
                self.report()
        changed = deepcopy(self.decisions)
        changed[0]["accepted"] = True
        with self.assertRaises(ValueError):
            target.compare_routers(self.selected, changed, self.pairs, self.labels)
        wrong = self.labels[:]
        wrong[0] = 99
        with self.assertRaises(ValueError):
            target.compare_routers(self.selected, self.decisions, self.pairs, wrong)
        selected = list(self.selected)
        selected.reverse()
        with self.assertRaises(ValueError):
            target.compare_routers(selected, self.decisions, self.pairs, self.labels)

    def test_owner_only_content_addressed_result_and_safe_cli(self):
        report = self.report()
        with tempfile.TemporaryDirectory() as root:
            audit = PrivateAudit(Path(root) / ".local_artifacts" / "all_routers")
            digest = audit.write(report)
            self.assertEqual(audit.read(digest), report)
            self.assertEqual(audit.write(report), digest)
        args = [item for name in ("frozen-root", "authentic-root", "run-root",
                                  "gateway-config", "graph-file", "audit-root")
                for item in ("--"+name, "unused")]
        with patch.object(target, "run", side_effect=target.EvaluationStageError(
                "ALL_ROUTERS_GT_SCORING")), \
             patch("sys.stderr", new_callable=io.StringIO) as stderr, \
             patch("sys.stdout", new_callable=io.StringIO) as stdout:
            self.assertEqual(target.main(args), 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(json.loads(stderr.getvalue()),
                         {"status": "FAIL_CLOSED", "stage": "ALL_ROUTERS_GT_SCORING"})


if __name__ == "__main__":
    unittest.main()
