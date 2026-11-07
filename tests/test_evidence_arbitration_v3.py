"""Synthetic V3 behavior, immutable controls, GT isolation and outcome accounting."""
import copy
import io
import json
import unittest
from unittest.mock import patch

from test_correction_features import fixture
from llmgnn_sara.sara3 import evidence_arbitration_v3 as policy
from llmgnn_sara.sara3 import weighted_arbitration_v2 as base
from llmgnn_sara.evaluation import evidence_arbitration_v3 as evaluation


class EvidenceV3Tests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads(base.CONFIG_PATH.read_text(encoding="utf-8"))
        self.row = fixture()["rows"][0]
        self.row.update(shared_support=1, topic_consistent=True)
        for p in (self.row["blind"], self.row["compare"]):
            p.update(support_count=1, quote_lengths=[40], counter_count=0,
                     auxiliary_warning=False, uncertainty=False)

    def test_third_class_and_candidate_switch_without_graph_or_prototype(self):
        third = policy.decide(self.row, {"P": None, "N": None}, self.cfg)
        self.assertEqual((third["decision"], third["score"], third["third_class"]), ("SWITCH_TO_AGENT", 4, True))
        self.assertFalse(third["training_eligible"])
        self.assertEqual(third["l2_status"], "NOT_ASSESSED")
        self.row["b1_class"] = 1
        self.row["blind"]["auxiliary_warning"] = True
        candidate = policy.decide(self.row, {"P": 0, "N": 0}, self.cfg)
        self.assertEqual((candidate["decision"], candidate["score"]), ("SWITCH_TO_AGENT", 3))
        self.row["b1_class"] = 0
        self.assertEqual(policy.decide(self.row, {"P": None, "N": None}, self.cfg)["decision"], "KEEP_NARRATIVE")

    def test_penalties_and_optional_signals_are_not_mandatory(self):
        for key, value, score in (("counter_count", 1, 2), ("auxiliary_warning", True, 3), ("uncertainty", True, 3)):
            row = copy.deepcopy(self.row); row["blind"][key] = value
            result = policy.decide(row, {"P": None, "N": None}, self.cfg)
            self.assertEqual(result["score"], score)
            self.assertEqual(result["decision"], "KEEP_NARRATIVE")
        self.row.update(shared_support=0, topic_consistent=False)
        self.assertEqual(policy.decide(self.row, {"P": 1, "N": 1}, self.cfg)["decision"], "KEEP_NARRATIVE")

    def test_invalid_phases_support_and_disagreement_fail_closed(self):
        for key, value in (("l1", "FAIL"), ("abstain", True), ("state", "REJECTED"), ("class_index", 7)):
            row = copy.deepcopy(self.row); row["compare"][key] = value
            self.assertEqual(policy.decide(row, {"P": None, "N": None}, self.cfg)["decision"], "NO_VALID_AGENT_RESPONSE")
        for count in (None, 0):
            row = copy.deepcopy(self.row); row["compare"]["support_count"] = count
            self.assertEqual(policy.decide(row, {"P": None, "N": None}, self.cfg)["reason"], "MISSING_L1_SUPPORT")
        self.row["compare"]["class_index"] = 2
        self.assertEqual(policy.decide(self.row, {"P": 1, "N": 1}, self.cfg)["reason"], "PHASE_CLASS_DISAGREEMENT")

    def test_malformed_support_and_gt_fields_rejected(self):
        for field, value in (("quote_lengths", []), ("quote_lengths", [False]), ("support_count", "1")):
            row = copy.deepcopy(self.row); row["blind"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): policy.decide(row, {"P": 0, "N": 0}, self.cfg)
        self.row["shared_support"] = 2
        with self.assertRaises(ValueError): policy.decide(self.row, {"P": 0, "N": 0}, self.cfg)
        self.row["shared_support"] = 1
        self.row["gt"] = 1
        with self.assertRaises(ValueError): policy.decide(self.row, {"P": 0, "N": 0}, self.cfg)

    def test_unchanged_class_and_controls_immutable(self):
        before = copy.deepcopy(self.row)
        original = base.decide(self.row, {"P": None, "N": None}, self.cfg)
        self.assertEqual(original["reason"], "NO_POSITIVE_PROTOTYPE_OR_NEIGHBOR_SUPPORT")
        result = policy.decide(self.row, {"P": None, "N": None}, self.cfg)
        self.assertEqual(result["decision"], "SWITCH_TO_AGENT")
        self.assertEqual(self.row, before)
        self.assertEqual(base.decide(self.row, {"P": None, "N": None}, self.cfg), original)
        self.assertEqual(result, policy.decide(self.row, {"P": None, "N": None}, self.cfg))
        self.row["narrative_class"] = 1
        self.assertEqual(policy.decide(self.row, {"P": None, "N": None}, self.cfg)["decision"], "KEEP_NARRATIVE")

    def report_fixture(self):
        table = fixture()
        for row in table["rows"]:
            row.update(shared_support=1, topic_consistent=True)
            for p in (row["blind"], row["compare"]):
                p.update(support_count=1, quote_lengths=[40], counter_count=0,
                         auxiliary_warning=False, uncertainty=False)
        rows = [{"router": r["router"], "node_id": r["node_id"], "narrative_class": r["narrative_class"],
                 "support": {"P": None, "N": None}, **base.decide(r, {"P": None, "N": None}, self.cfg)} for r in table["rows"]]
        baseline = {"schema": base.VERSION, "config": self.cfg, "source_feature_sha256": base.FEATURE_SHA, "rows": rows}
        report = {"schema": policy.VERSION, "contract": policy.CONTRACT, "rule_sha256": base.digest(policy.CONTRACT),
                  "base_report_sha256": policy.BASE_REPORT_SHA, "source_feature_sha256": base.FEATURE_SHA,
                  "training_admissions": 0, "rows": policy.score(table, baseline)}
        return table, baseline, report

    def test_report_tampering_and_training_promotion_rejected(self):
        table, baseline, report = self.report_fixture()
        policy.validate_report(report, table, baseline)
        for change in ("score", "optional_support", "training_eligible"):
            bad = copy.deepcopy(report)
            if change == "optional_support": bad["rows"][0][change]["P"] = 1
            else: bad["rows"][0][change] = 100
            with self.subTest(change=change), self.assertRaises(ValueError): policy.validate_report(bad, table, baseline)
        report = copy.deepcopy(report); report["contract"]["candidate_threshold"] = 1
        with self.assertRaises(ValueError): policy.validate_report(report, table, baseline)

    def test_independent_synthetic_fix_harm_and_dependencies(self):
        _, _, report = self.report_fixture()
        for truth, key in (([1]*2708, "fixes"), ([0]*2708, "harms"), ([2]*2708, "third_class_switches")):
            result = evaluation.summarize(report["rows"], truth)
            self.assertEqual(result["routers"]["r0"][key], 37)
        with self.assertRaises(ValueError): evaluation.summarize(report["rows"], [True]*2708)

    def test_bad_hash_never_reads_gt(self):
        with patch.object(evaluation, "read_pinned_json", side_effect=ValueError()), \
             patch.object(evaluation.base_evaluation, "_labels_from_original_graph") as gt, patch("sys.stderr", io.StringIO()):
            args = sum((["--"+name, "absent"] for name in ("report", "features", "base-report", "direct-report", "graph", "frozen-root", "output")), [])
            self.assertEqual(evaluation.main(args+["--report-sha256", "0"*64]), 1)
        gt.assert_not_called()


if __name__ == "__main__": unittest.main()
