"""Synthetic-only test of real R1 verifier scorer (never uses Cora GT or HTTP)."""
from copy import deepcopy
import io
import json
from pathlib import Path
from types import SimpleNamespace
import socket
import tempfile
import unittest
from unittest.mock import patch

from llmgnn_sara.evaluation import cora_r1_real_gt as target
from llmgnn_sara.sara2.policy import Annotation, Pair
from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.selection import select_router
from llmgnn_sara.sara3.gateway_run import gateway_run, approval_template


def fixture():
    pairs = {}
    for n in range(140):
        text = ("rule_learning and theoretical methods" if n % 3 == 0 else
                "neural networks with learning algorithms" if n % 3 == 1
                else "an arbitrary scholarly topic with no atlas matches")
        pairs[n] = Pair(Annotation(n, 0, 10 if n < 37 else 90),
                        Annotation(n, 0, 10 if n < 37 else 90), text)
    selected = list(select_router(tuple(pairs.values()), 37, "r1_v1"))
    labels = [n % 7 for n in range(2708)]
    for n in selected[:8]:
        labels[n] = 1
    decisions = []
    for n in range(140):
        review = n in selected
        blind = None if n in selected[:4] else 1 if n in selected[4:12] else 0
        comparison = None if n in selected[:6] else blind
        decisions.append({
            "node_id": n, "routed_for_review": review,
            "b1_class_index": 0, "narrative_v0_class_index": 0,
            "blind_class_index": blind if review else None,
            "comparison_class_index": comparison if review else None,
            "accepted": not review,
            "training_class_index": None if review else 0,
            "l2_status": "NOT_ASSESSED" if review else "NOT_APPLICABLE_BASELINE_POLICY",
            "semantic_validation": "NOT_PERFORMED",
            "reason": "NOT_ATTEMPTED_AFTER_HALT" if review and blind is None
            else "COUNTER_EVIDENCE_UNRESOLVED" if review else "FROZEN_BASELINE",
        })
    return selected, decisions, pairs, labels


class R1RealGTTests(unittest.TestCase):
    def setUp(self):
        self.selected, self.decisions, self.pairs, self.labels = fixture()
        net = patch.object(socket.socket, "connect", side_effect=AssertionError("No network"))
        net.start()
        self.addCleanup(net.stop)

    def report(self, status="COMPLETE_LIVE_UNASSESSED"):
        return target.analyze(self.selected, self.decisions, self.pairs,
                              self.labels, status=status)

    def test_one_frozen_r1_selection_full_node_journey_and_abstentions(self):
        old = deepcopy((self.selected, self.decisions, self.labels))
        report = self.report()
        self.assertEqual(old, (self.selected, self.decisions, self.labels))
        rows, summary = report["owner_private_node_rows"], report["aggregate"]
        self.assertEqual(len(rows), 140)
        self.assertEqual(sum(x["r1_selected"] for x in rows), 37)
        self.assertEqual(sum(x["r1_selected"] is False for x in rows), 103)
        for k in target.CRITERIA:
            d = summary["oracle_router_detection"][k]
            self.assertEqual(d["true_positive"] + d["false_positive"], 37)
            self.assertEqual(d["false_negative"] + d["true_negative"], 103)
            self.assertEqual(d["true_positive"] + d["false_negative"], d["all_140"])
        self.assertEqual(summary["r1_review_coverage_and_accuracy"]["blind"]["covered"], 33)
        self.assertEqual(summary["r1_review_coverage_and_accuracy"]["comparison"]["covered"], 31)
        self.assertEqual(summary["reviewed_training_admissions"], 0)
        for prefix in ("b1", "narrative"):
            for phase in ("blind", "comparison"):
                d = summary["paired_correction_vs_baselines"][f"{prefix}_vs_{phase}"]
                self.assertEqual(sum(d[x] for x in target.PAIRED), 37)
        for phase in ("blind", "comparison"):
            d = summary["hypothetical_narrative_fallback"][phase]
            paired = summary["paired_correction_vs_baselines"][f"narrative_vs_{phase}"]
            self.assertEqual(d["net_difference_140"], paired["net_correct_change_on_covered"])
        self.assertNotIn('"node_id"', json.dumps(summary))
        self.assertNotIn('"gt_class_index"', json.dumps(summary))

    def test_missing_l1_and_real_partial_run_are_explicit(self):
        report = self.report("BLOCKED_NO_AUTOMATIC_RETRY")
        self.assertEqual(report["aggregate"]["status_of_real_run"], "BLOCKED_NO_AUTOMATIC_RETRY")
        self.assertGreater(report["aggregate"]["decision_reason_counts"]
                           ["NOT_ATTEMPTED_AFTER_HALT"], 0)
        row = next(x for x in report["owner_private_node_rows"]
                   if x["node_id"] == self.selected[0])
        self.assertEqual(row["narrative_vs_blind"], "NO_CLASS_PREDICTION")
        self.assertIsNone(row["blind_correct"])

    def test_r1_selection_disagreements_and_admission_tampering_fail_closed(self):
        wrong = list(self.selected)
        wrong.reverse()
        with self.assertRaises(ValueError):
            target.analyze(wrong, self.decisions, self.pairs, self.labels,
                           status="COMPLETE_LIVE_UNASSESSED")
        for field, value in (("accepted", True),
                             ("training_class_index", 1),
                             ("l2_status", "APPROVED"),
                             ("blind_class_index", 7),
                             ("routed_for_review", False)):
            d = deepcopy(self.decisions)
            d[self.selected[0]][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                target.analyze(self.selected, d, self.pairs, self.labels,
                               status="COMPLETE_LIVE_UNASSESSED")
        labels = self.labels[:]
        labels[0] = 99
        with self.assertRaises(ValueError):
            target.analyze(self.selected, self.decisions, self.pairs, labels,
                           status="COMPLETE_LIVE_UNASSESSED")
        with self.assertRaises(ValueError):
            self.report("FAKE_RUN_CANNOT_SCORE_REAL")

    def test_existing_gateway_r1_v1_full_fake_pipeline_and_no_unapproved_live(self):
        """Positive end-to-end local fake, negative live consent before journal."""
        cfg = json.loads((Path(__file__).resolve().parents[1] /
                          "configs/gapgpt_rich_v2_output4096_proposed.json").read_text())
        frozen = SimpleNamespace(by_arm=lambda name: ())
        inputs = SimpleNamespace(pairs=tuple(self.pairs.values()),
                                 provenance=(), frozen=frozen)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / ".local_artifacts" / "r1_fake"
            result = gateway_run(inputs, root, router="r1_v1",
                                 budget=37, cohort="sensitivity",
                                 config=cfg, fake=True)
            self.assertEqual(result["status"], "COMPLETE_FAKE_HTTP")
            self.assertEqual(result["router"], "r1_v1")
            self.assertEqual(result["selected_node_ids"], self.selected)
            self.assertEqual(result["selected_count"], 37)
            self.assertTrue(result["no_training_label_for_routed_proposals"])
            self.assertFalse(result["GT_accessed"])
            self.assertEqual(result["training_runs"], 0)
            self.assertGreater(result["new_dispatches"], 0)
            second = gateway_run(inputs, root, router="r1_v1",
                                 budget=37, cohort="sensitivity",
                                 config=cfg, fake=True)
            self.assertEqual(second["new_dispatches"], 0)
            self.assertEqual(second["private_report_sha256"],
                             result["private_report_sha256"])
            live_root = Path(temp) / ".local_artifacts" / "r1_unapproved"
            with self.assertRaises(ValueError):
                gateway_run(inputs, live_root, router="r1_v1",
                            budget=37, cohort="sensitivity",
                            config=cfg, fake=False, approval=None)
            self.assertFalse(live_root.exists())
            owner = approval_template(inputs, "r1_v1", 37, "sensitivity", cfg)
            self.assertFalse(owner["data_sharing_approved"])
            self.assertFalse(owner["spend_approved"])
            self.assertFalse(owner["explicit_batch_dispatch_approved"])

    def test_fake_gateway_report_is_rejected_before_any_GT_graph_access(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / ".local_artifacts"
            run_root = root / "r1_fake_source"
            journal = PrivateAudit(run_root / "journal")
            # Valid content address but a fake source: it can never be
            # scored as if it came from a real paid R1 run.
            sha = journal.write({
                "schema": target.CONTRACT,
                "mode": "FAKE_HTTP", "router": "r1_v1",
                "status": "COMPLETE_FAKE_HTTP"})
            with patch.object(target, "_labels_from_original_graph",
                              side_effect=AssertionError("No GT access before live trust")):
                with self.assertRaises(target.EvaluationStageError) as raised:
                    target.run(root / "frozen", root / "authentic",
                               run_root, root / "cfg.json", sha,
                               root / "original.pt", root / "gt_private")
            self.assertEqual(raised.exception.stage,
                             "R1_LIVE_REPORT_AND_PROVENANCE")

    def test_private_audit_readback_and_sanitized_cli_no_GT_stdout(self):
        report = self.report()
        with tempfile.TemporaryDirectory() as tmp:
            audit = PrivateAudit(Path(tmp) / ".local_artifacts" / "r1_real_gt")
            digest = audit.write(report)
            self.assertEqual(audit.read(digest), report)
            self.assertEqual(audit.write(report), digest)
        args = [item for name in (
            "frozen-root", "authentic-root", "r1-root", "gateway-config",
            "graph-file", "audit-root")
            for item in ("--" + name, "none")] + ["--summary-sha256", "a" * 64]
        with patch.object(target, "run",
                          side_effect=target.EvaluationStageError("R1_LIVE_REPORT_AND_PROVENANCE")), \
             patch("sys.stdout", new_callable=io.StringIO) as stdout, \
             patch("sys.stderr", new_callable=io.StringIO) as stderr:
            self.assertEqual(target.main(args), 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(json.loads(stderr.getvalue()), {
            "status": "FAIL_CLOSED", "stage": "R1_LIVE_REPORT_AND_PROVENANCE"})


if __name__ == "__main__":
    unittest.main()
