"""Synthetic automatic-policy tests; no model calls or real GT."""
import copy
import json
from pathlib import Path
import tempfile
import io
import unittest
from unittest.mock import patch
try:
    import numpy as np
except ImportError:
    np = None

from test_correction_features import fixture
from llmgnn_sara.sara3 import weighted_arbitration_v2 as v2


class WeightedTests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads(v2.CONFIG_PATH.read_text(encoding="utf-8"))
        self.row = fixture()["rows"][0]
        self.row.update(b1_class=1, shared_support=1, topic_consistent=True)
        for p in (self.row["blind"], self.row["compare"]):
            p.update(counter_count=0, auxiliary_warning=False, uncertainty=False)

    def test_candidate_switch_and_real_third_class_switch(self):
        a = v2.decide(self.row, {"P": 0, "N": 1}, self.cfg)
        self.assertEqual((a["decision"], a["score"], a["label"]), ("SWITCH_TO_AGENT", 3, 1))
        self.row["b1_class"] = 0
        b = v2.decide(self.row, {"P": 1, "N": None}, self.cfg)
        self.assertEqual((b["decision"], b["score"], b["third_class"]), ("SWITCH_TO_AGENT", 4, True))
        self.assertFalse(b["training_eligible"])
        self.row["topic_consistent"] = False
        self.assertEqual(v2.decide(self.row, {"P": 1, "N": None}, self.cfg)["decision"], "KEEP_NARRATIVE")

    def test_missing_neutral_but_not_positive_and_penalty_weights(self):
        a = v2.decide(self.row, {"P": None, "N": None}, self.cfg)
        self.assertEqual(a["score"], 2)
        self.assertEqual(a["reason"], "NO_POSITIVE_PROTOTYPE_OR_NEIGHBOR_SUPPORT")
        self.assertIsNone(a["components"]["P"])
        self.row["blind"].update(counter_count=1, auxiliary_warning=True, uncertainty=True)
        b = v2.decide(self.row, {"P": 1, "N": 0}, self.cfg)
        self.assertEqual(b["score"], 0)
        self.assertEqual(b["decision"], "KEEP_NARRATIVE")

    def test_l1_abstention_missing_invalid_class_and_disagreement(self):
        for key, value in (("l1", "FAIL"), ("abstain", True), ("state", "REJECTED"), ("class_index", 7)):
            row = copy.deepcopy(self.row); row["compare"][key] = value
            self.assertEqual(v2.decide(row, {"P": 1, "N": 1}, self.cfg)["decision"], "NO_VALID_AGENT_RESPONSE")
        self.row["compare"]["class_index"] = 2
        self.assertEqual(v2.decide(self.row, {"P": 1, "N": 1}, self.cfg)["reason"], "PHASE_CLASS_DISAGREEMENT")

    def test_same_label_not_correction_gt_fields_and_config_changes_rejected(self):
        self.row["narrative_class"] = 1
        self.assertEqual(v2.decide(self.row, {"P": 1, "N": 1}, self.cfg)["decision"], "KEEP_NARRATIVE")
        self.row["blind"]["gt"] = 1
        with self.assertRaises(ValueError): v2.decide(self.row, {"P": 1, "N": 1}, self.cfg)
        del self.row["blind"]["gt"]
        self.cfg["third_class_threshold"] = 3
        with self.assertRaises(ValueError): v2.decide(self.row, {"P": 1, "N": 1}, self.cfg)

    @unittest.skipIf(np is None, "Optional NumPy not installed; graph math not verified")
    def test_prototypes_density_seed_scarcity_and_target_exclusion(self):
        x = np.asarray([[1., 0.]] * 6 + [[0., 1.]] * 5)
        adj = [set(range(11)) - {i} for i in range(11)]
        seeds = {i: 1 if i < 6 else 0 for i in range(1, 11)}
        result = v2.support(0, 1, 0, x, adj, seeds, self.cfg)
        self.assertEqual(result["P"], 1)
        self.assertEqual(result["prototype_counts"], {"0": 5, "1": 5})
        self.assertEqual(result["N"], 0)  # Observed tie, not missing support.
        unknown = v2.support(0, 1, 0, x, [set() for _ in x], {1: 1}, self.cfg)
        self.assertIsNone(unknown["P"]); self.assertIsNone(unknown["N"])
        only_agent_neighbors = [set() for _ in x]
        for i in range(4):
            only_agent_neighbors[i] = set(range(4)) - {i}
        positive = v2.support(0, 1, 0, x, only_agent_neighbors, seeds, self.cfg)
        self.assertEqual(positive["N"], 1)
        # Target's own pseudo-label cannot satisfy the five-sample minimum.
        small = v2.support(0, 1, 0, x, adj, {0: 1, 1: 1, 2: 1, 3: 1, 4: 1}, self.cfg)
        self.assertIsNone(small["P"])

    @unittest.skipIf(np is None, "Optional NumPy not installed; graph math not verified")
    def test_corrupt_graph_and_source_hash_fail_closed(self):
        x = np.ones((3, 2)); adj = [{1}, set(), set()]
        with self.assertRaises(ValueError): v2.support(0, 1, 0, x, adj, {}, self.cfg)
        x[0, 0] = np.nan
        with self.assertRaises(ValueError): v2.support(0, 1, 0, x, [set() for _ in x], {}, self.cfg)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "graph.pt"; path.write_bytes(b"untrusted")
            with patch.object(v2.zipfile, "ZipFile", side_effect=AssertionError("Must hash before inspection")):
                with self.assertRaises(ValueError): v2.load_graph(path)

    def test_determinism_and_no_input_mutation(self):
        before = copy.deepcopy(self.row)
        a = v2.decide(self.row, {"P": 1, "N": 0}, self.cfg)
        self.assertEqual(a, v2.decide(self.row, {"P": 1, "N": 0}, self.cfg))
        self.assertEqual(self.row, before)

    def test_evaluator_rejects_forged_score_and_training_promotion(self):
        from llmgnn_sara.evaluation.weighted_arbitration_v2 import validate_report, evaluate
        table = fixture()
        rows = []
        for row in table["rows"]:
            rows.append({"router": row["router"], "node_id": row["node_id"],
                         "narrative_class": row["narrative_class"], "support": {"P": 1, "N": 0},
                         **v2.decide(row, {"P": 1, "N": 0}, self.cfg)})
        report = {"schema": v2.VERSION, "config": self.cfg, "source_feature_sha256": v2.FEATURE_SHA,
                  "training_admissions": 0, "graph_provenance": {"graph_sha256": v2.GRAPH_SHA256,
                     "label_storage_read": False}, "rows": rows,
                  "rule_sha256": v2.digest({"version": v2.VERSION, "config": self.cfg})}
        self.assertEqual(evaluate(report, table, [0] * 2708)["routers"]["r0"]["net_change"], 0)
        for change in ("score", "training_eligible", "label"):
            bad = copy.deepcopy(report); bad["rows"][0][change] = 100
            with self.subTest(change=change), self.assertRaises(ValueError): validate_report(bad, table)

    def test_evaluator_hash_failure_never_opens_gt(self):
        from llmgnn_sara.evaluation import weighted_arbitration_v2 as module
        with patch.object(module, "read_pinned_json", side_effect=ValueError("Bad SHA")), \
             patch.object(module, "_labels_from_original_graph") as gt, patch("sys.stderr", io.StringIO()):
            code = module.main(["--report", "missing", "--report-sha256", "0" * 64,
                                "--features", "missing", "--graph", "forbidden", "--frozen-root", "missing",
                                "--output", "missing"])
        self.assertEqual(code, 1); gt.assert_not_called()


if __name__ == "__main__": unittest.main()
