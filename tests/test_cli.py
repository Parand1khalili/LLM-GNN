"""Offline integration and enforcement at CLI / pseudo-training boundaries."""
import ast
import contextlib
import io
import json
from pathlib import Path
import socket
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from llmgnn_sara import cli


class CliTests(unittest.TestCase):
    def test_doctor_and_mock_demo_without_network(self):
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network attempted")):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli.main(["doctor"]), 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report["training_execution"], "DISABLED")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli.main(["sara3-offline", "--demo"]), 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report["provider_calls"], 0)
            self.assertEqual(report["input_provenance"], "SYNTHETIC_DEMONSTRATION_NOT_HISTORICAL_ARTIFACT")

    def test_baseline_mismatch_stops_before_extension(self):
        with patch("llmgnn_sara.annotation.replay.replay_frozen", return_value={"status": "FAIL"}), \
                patch("llmgnn_sara.sara3.run_offline", side_effect=AssertionError("Extension attempted")), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            code = cli.main(["pipeline", "--b1", "unused", "--narrative", "unused", "--selection", "unused"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())["extensions"], "NOT_RUN_BASELINE_MISMATCH")

    def test_unknown_hash_fails_without_echoing_contents(self):
        with patch("llmgnn_sara.annotation.replay.replay_frozen", side_effect=ValueError("PRIVATE_SENTINEL")), \
                contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(cli.main(["replay-frozen", "--b1", "x", "--narrative", "x", "--selection", "x"]), 1)
        self.assertNotIn("PRIVATE_SENTINEL", error.getvalue())

    def test_arbitration_to_training_rejects_third_class(self):
        row = SimpleNamespace(target_id=0, class_index=0,
                              samples=(SimpleNamespace(source_kind="original_fresh"),))
        dataset = SimpleNamespace(predictions=(row,), by_arm=lambda _: (row,), target_ids=(0,))
        for label, proposal, allowed in ((1, None, False), (0, 1, False), (0, None, True)):
            with self.subTest(label=label, proposal=proposal), self.assertRaises(ValueError):
                cli._plan(dataset, "sensitivity", "ce", accepted=[{
                    "node_id": 0, "training_class_index": label, "label_confidence_percent": 90,
                    "accepted": True, "third_class_proposal": proposal,
                    "third_class_training_allowed": allowed}])
        result = cli._plan(dataset, "sensitivity", "ce", accepted=[{
            "accepted": False, "training_class_index": None}])
        self.assertEqual(result["status"], "BLOCKED_NO_ACCEPTED_LABELS")

    def test_no_runtime_diagnostic_imports_gt_attributes_or_dynamic_execution(self):
        root = Path(cli.__file__).parent
        for file in root.rglob("*.py"):
            if "evaluation" in file.relative_to(root).parts:
                continue
            tree = ast.parse(file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn("evaluation", (node.module or "").split("."), str(file))
                if isinstance(node, ast.Attribute):
                    self.assertNotIn(node.attr, {"y", "fixed_y", "raw_y"}, str(file))
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"eval", "exec", "__import__"}, str(file))

    def test_real_frozen_pipeline_preserves_matched_masks(self):
        root = Path(__file__).resolve().parents[1] / ".local_artifacts" / "frozen"
        paths = (root / "b1_final_predictions.json", root / "narrative_v0_final_predictions.json",
                 root / "selection_manifest.json")
        if not all(p.is_file() for p in paths):
            self.skipTest("External pinned frozen inputs are not installed")
        argv = ["pipeline", "--b1", str(paths[0]), "--narrative", str(paths[1]),
                "--selection", str(paths[2]), "--cohort", "primary", "--loss", "wce"]
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network attempted")), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(argv), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["replay"]["predictions_matched"], 280)
        a, b = report["baseline_gcn_plans"]["b1"], report["baseline_gcn_plans"]["narrative_v0"]
        self.assertEqual(a["test_ids"], b["test_ids"])
        self.assertEqual(a["config"]["seeds"], b["config"]["seeds"])
        self.assertEqual((a["train_count"], a["common_test_count"]), (135, 2568))
        sara = report["sara_gcn_plan"]
        self.assertEqual(sara["test_ids"], a["test_ids"])
        self.assertTrue(all(sara["pseudo_y"][i] == -1 for i in sara["test_ids"] + sara["excluded_ids"]))
        self.assertEqual(report["sara3"]["completed_review_count"], 0)
        self.assertEqual(report["sara3"]["target_count"], 135)
        self.assertTrue(set(report["sara3"]["selected_node_ids"]).isdisjoint(a["excluded_ids"]))
        self.assertEqual(report["provider_calls"], 0)


if __name__ == "__main__":
    unittest.main()
