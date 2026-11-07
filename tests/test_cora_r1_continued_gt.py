"""R1 continued GT-only scorer must fail closed before reading GT on fake sources."""
import io
import json
from pathlib import Path
from types import SimpleNamespace
import socket
import tempfile
import unittest
from unittest.mock import patch

from llmgnn_sara.evaluation import cora_r1_continued_gt as scorer
from llmgnn_sara.evaluation.cora_r1_real_gt import analyze
from llmgnn_sara.sara2.policy import Annotation, Pair
from llmgnn_sara.sara3.selection import select_router
from llmgnn_sara.sara3.gateway_run import SyntheticGapGPTHttp, gateway_run

from test_gateway_r1_continuation import fixture, FailAt51
from test_cora_r1_real_gt import fixture as scoring_fixture


class ContinuedGTTests(unittest.TestCase):
    def test_fake_original_denied_before_any_truth_access(self):
        inputs, cfg, selected, first_nine = fixture()
        with tempfile.TemporaryDirectory() as base:
            root = Path(base) / ".local_artifacts"
            fake = root / "fake_r1"
            graph = root / "nonoriginal_graph.pt"
            graph.parent.mkdir(parents=True, exist_ok=True)
            graph.write_bytes(b"not a Cora graph")
            config = root / "gateway_config.json"
            config.write_text(json.dumps(cfg))
            network = patch.object(
                socket.socket, "connect",
                side_effect=AssertionError("No network allowed"))
            with network, patch.object(
                    scorer, "load_project_inputs", return_value=inputs), patch.object(
                    scorer, "_labels_from_original_graph",
                    side_effect=AssertionError("No GT for synthetic source")):
                output = gateway_run(
                    inputs, fake, router="r1_v1", budget=37,
                    cohort="sensitivity", config=cfg, fake=True,
                    transport=FailAt51(cfg["model"], first_nine))
                self.assertEqual(output["status"], "BLOCKED_NO_AUTOMATIC_RETRY")
                with self.assertRaises(scorer.EvaluationStageError) as got:
                    scorer.run(root / "frozen", root / "authentic", fake,
                               config, "a" * 64, graph,
                               root / "r1_gt_private")
                self.assertEqual(got.exception.stage,
                                 "R1_ORIGINAL_PRE_GT_RECONCILIATION")

    def test_pure_scoring_uses_real_continuation_status_as_explicit_new_arm(self):
        selected, decisions, pairs, labels = scoring_fixture()
        report = analyze(selected, decisions, pairs, labels,
                         status="CONTINUED_PRESERVING_REJECTED_COMPARISON")
        self.assertEqual(report["aggregate"]["status_of_real_run"],
                         "CONTINUED_PRESERVING_REJECTED_COMPARISON")
        self.assertEqual(len(report["owner_private_node_rows"]), 140)
        self.assertEqual(sum(x["r1_selected"] for x in
                             report["owner_private_node_rows"]), 37)

    def test_invalid_cli_reports_stage_without_sensitive_data(self):
        args = [value for name in (
            "frozen-root", "authentic-root", "original-root",
            "gateway-config", "graph-file", "audit-root")
            for value in ("--" + name, "none")] + [
                "--continuation-summary-sha256", "0"*64]
        with patch.object(scorer, "run", side_effect=scorer.EvaluationStageError(
                "R1_OVERLAY_REPLAY_AND_TRUST")), \
             patch("sys.stdout", new_callable=io.StringIO) as out, \
             patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(scorer.main(args), 1)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(json.loads(err.getvalue()),
                         {"status": "FAIL_CLOSED", "stage":
                          "R1_OVERLAY_REPLAY_AND_TRUST"})


if __name__ == "__main__":
    unittest.main()
