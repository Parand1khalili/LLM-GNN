"""Synthetic direct-seed coverage, immutable V2 and GT-boundary checks."""
import copy
import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
try:
    import numpy as np
except ImportError:
    np = None

from test_correction_features import fixture
from llmgnn_sara.sara3 import graph_support_coverage as audit
from llmgnn_sara.sara3 import weighted_arbitration_v2 as base
from llmgnn_sara.evaluation import graph_support_coverage as evaluation


class DirectSupportTests(unittest.TestCase):
    def test_minimum_supermajority_advantage_and_same_class(self):
        seeds = {1: 1, 2: 1, 3: 0}
        self.assertIsNone(audit.direct_support(1, 0, [1, 2], seeds))
        self.assertEqual(audit.direct_support(1, 0, [1, 2, 3], seeds), 1)
        self.assertEqual(audit.direct_support(0, 1, [1, 2, 3], seeds), 0)
        self.assertEqual(audit.direct_support(1, 1, [1, 2, 3], seeds), 0)
        self.assertIsNone(audit.direct_support(1, 0, [8, 9, 10], seeds))

    def test_bad_classes_duplicates_and_seed_order(self):
        for agent, ids, seeds in ((7, [1], {}), (1, [1, 1], {}), (1, [1], {1: True}),
                                  (1, [-1], {}), (True, [1], {})):
            with self.subTest(agent=agent, ids=ids), self.assertRaises(ValueError):
                audit.direct_support(agent, 0, ids, seeds)
        a, b = {1: 1, 2: 1, 3: 0}, {3: 0, 2: 1, 1: 1}
        self.assertEqual(audit.direct_support(1, 0, [1, 2, 3], a), audit.direct_support(1, 0, [3, 1, 2], b))

    def test_fail_closed_hash_before_gt(self):
        with patch.object(evaluation, "read_pinned_json", side_effect=ValueError()), \
             patch.object(evaluation.evaluator, "_labels_from_original_graph") as gt, patch("sys.stderr", io.StringIO()):
            self.assertEqual(evaluation.main(["--report", "absent", "--report-sha256", "0"*64,
                "--base-report", "absent", "--features", "absent", "--graph", "forbidden",
                "--frozen-root", "absent", "--output", "absent"]), 1)
        gt.assert_not_called()


@unittest.skipIf(np is None, "Optional NumPy unavailable; graph coverage not verified")
class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads(base.CONFIG_PATH.read_text(encoding="utf-8"))
        self.table = fixture()
        self.x = np.ones((60, 2))
        self.adj = [set() for _ in range(60)]
        self.adj[0] = {57, 58, 59}
        for i in (57, 58, 59): self.adj[i] = {0}
        self.inputs = SimpleNamespace(pairs=tuple(SimpleNamespace(node_id=i, agrees=True,
            b1=SimpleNamespace(class_index=int(i >= 57), confidence=90),
            narrative_v0=SimpleNamespace(class_index=int(i >= 57), confidence=90),
            neighborhood=SimpleNamespace(neighbor_ids=tuple(self.adj[i]), degree=len(self.adj[i]))) for i in range(60)))
        self.baseline = {"schema": base.VERSION, "config": self.cfg, "source_feature_sha256": base.FEATURE_SHA,
            "rule_sha256": base.digest({"version": base.VERSION, "config": self.cfg}),
            "graph_provenance": {"graph_sha256": base.GRAPH_SHA256, "label_storage_read": False},
            "training_admissions": 0, "rows": base.run(self.table, self.inputs, self.x, self.adj, self.cfg)}

    def report(self):
        coverage, rows = audit.audit_and_score(self.table, self.inputs, self.x, self.adj, self.cfg, self.baseline)
        return coverage, {**self.baseline, "schema": audit.VERSION, "contract": audit.CONTRACT,
                          "rule_sha256": base.digest(audit.CONTRACT), "base_report_sha256": audit.BASE_REPORT_SHA,
                          "rows": rows}

    def test_star_does_not_require_neighbor_neighbor_links_and_is_immutable(self):
        before = copy.deepcopy(self.baseline)
        coverage, report = self.report()
        self.assertIsNone(self.baseline["rows"][0]["support"]["N"])
        self.assertEqual(report["rows"][0]["support"]["N"], 1)
        self.assertEqual(coverage["routers"]["r0"]["seed_neighbor_histogram"], {"3": 1, "0": 36})
        self.assertEqual(coverage["canonical_frozen_neighborhood_alignment"], "PASS")
        self.assertEqual(self.baseline, before)
        self.assertEqual((coverage, report), self.report())
        evaluation.project(report, self.table, self.baseline)
        self.assertTrue(all(not r["training_eligible"] for r in report["rows"]))

    def test_missing_embeddings_and_scarce_samples_separated(self):
        self.x[57] = 0
        self.baseline["rows"] = base.run(self.table, self.inputs, self.x, self.adj, self.cfg)
        coverage, _ = self.report()
        proto = coverage["routers"]["r0"]["prototype_classes"][1]
        self.assertEqual((proto["seed_count"], proto["nonzero_embedding_seeds"], proto["zero_embedding_seeds"]), (3, 2, 1))
        self.assertFalse(proto["sample_minimum_pass"])
        self.assertEqual(coverage["zero_norm_embedding_rows"], 1)

    def test_bad_graph_gt_leakage_and_original_binding_fail_closed(self):
        bad = copy.deepcopy(self.table); bad["rows"][0]["gt"] = 0
        with self.assertRaises(ValueError): audit.audit_and_score(bad, self.inputs, self.x, self.adj, self.cfg, self.baseline)
        self.adj[57] = set()
        with self.assertRaises(ValueError): self.report()

    def test_forged_contract_prototype_score_or_training_rejected(self):
        _, report = self.report()
        for change in ("contract", "prototype", "score", "training"):
            bad = copy.deepcopy(report)
            if change == "contract": bad["contract"]["neighbor_min_samples"] = 1
            elif change == "prototype": bad["rows"][0]["support"]["P"] = 1
            elif change == "score": bad["rows"][0]["score"] = 100
            else: bad["rows"][0]["training_eligible"] = True
            with self.subTest(change=change), self.assertRaises(ValueError): evaluation.project(bad, self.table, self.baseline)


if __name__ == "__main__": unittest.main()
