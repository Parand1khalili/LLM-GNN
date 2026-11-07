"""R1 continued GT-only scorer must fail closed before reading GT on fake sources."""
import io
from copy import deepcopy
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
from llmgnn_sara.sara3.gateway_run import SyntheticGapGPTHttp, gateway_run, approval_template
from llmgnn_sara.sara3.gateway_r1_continuation import preflight, execute, OVERLAY
from llmgnn_sara.sara3.audit import PrivateAudit

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

    def test_mocked_live_original_and_continuation_full_gt_provenance_flow(self):
        """All 65 calls via mock: full provider-shaped live + owner-only GT."""
        inputs, cfg, selected, skip = fixture()
        key = "synthetic-local-key-unknown"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ".local_artifacts"
            original = root / "original_r1"
            cfg_file = root / "gateway.json"
            cfg_file.parent.mkdir(parents=True, exist_ok=True)
            cfg_file.write_text(json.dumps(cfg))
            graph = root / "owner_original_graph_test_dummy.pt"
            graph.write_bytes(b"synthetic graph sentinel - never deserialize")
            original_transport = FailAt51(cfg["model"], skip)
            batch_approval = approval_template(inputs, "r1_v1", 37, "sensitivity", cfg)
            for key_name in ("data_sharing_approved", "spend_approved",
                             "explicit_batch_dispatch_approved"):
                batch_approval[key_name] = True
            with patch.object(socket.socket, "connect",
                              side_effect=AssertionError("External networking forbidden")), \
                 patch("llmgnn_sara.sara3.gapgpt_live.post_once",
                       side_effect=lambda wire, key, **kwargs: original_transport(wire, key)):
                real_shaped = gateway_run(
                    inputs, original, router="r1_v1", budget=37,
                    cohort="sensitivity", config=cfg, fake=False,
                    approval=batch_approval, key=key)
                self.assertEqual(real_shaped["status"], "BLOCKED_NO_AUTOMATIC_RETRY")
                self.assertEqual(real_shaped["attempted_calls"], 51)
                checked = preflight(inputs, original, config=cfg, fake=False)
                amendment = checked["amendment_template"]
                self.assertIsNotNone(amendment["original_summary_sha256"])
                self.assertIsNotNone(amendment["original_report_sha256"])
                self.assertEqual(amendment["original_intents"], 51)
                consent = checked["approval_template"]
                for flag in ("data_sharing_approved", "spend_approved",
                             "explicit_continuation_dispatch_approved"):
                    consent[flag] = True
                new_transport = SyntheticGapGPTHttp(cfg["model"])
                with patch("llmgnn_sara.sara3.gapgpt_live.post_once",
                           side_effect=lambda wire, key, **kwargs: new_transport(wire, key)):
                    continued = execute(
                        inputs, original, config=cfg, amendment=amendment,
                        approval=consent, key=key)
                self.assertEqual(continued["status"],
                                 "CONTINUED_PRESERVING_REJECTED_COMPARISON")
                self.assertEqual(continued["total_intents"], 65)
                self.assertEqual(continued["new_dispatches"], 14)
                truth = [n % 7 for n in range(2708)]
                with patch.object(scorer, "load_project_inputs", return_value=inputs), \
                     patch.object(scorer, "_expected_graph_names",
                                  return_value=("synthetic",)), \
                     patch.object(scorer, "_labels_from_original_graph",
                                  return_value=truth):
                    result = scorer.run(
                        root / "frozen", root / "authentic",
                        original, cfg_file,
                        continued["private_summary_sha256"],
                        graph, root / "r1_owner_private_score")
                self.assertEqual(
                    result["status"],
                    "R1_CONTINUED_GT_NODE_JOURNEY_VERIFIED_PRIVATE")
                self.assertEqual(result["aggregate"]["real_live_attempts_total"], 65)
                self.assertEqual(result["aggregate"]["new_live_dispatches"], 14)
                self.assertEqual(result["aggregate"]["r1_review_coverage_and_accuracy"]
                                 ["blind"]["covered"], 28)
                self.assertEqual(result["aggregate"]["reviewed_training_admissions"], 0)
                # Even perfectly rehashed tampering must fail before GT access.
                audit = PrivateAudit(original / OVERLAY / "journal")
                bad_report = deepcopy(audit.read(
                    continued["private_combined_report_sha256"]))
                target = bad_report["run"]["selected_node_ids"][0]
                altered = next(d for d in bad_report["run"]["decisions"]
                               if d["node_id"] == target)
                current = altered["blind_class_index"]
                altered["blind_class_index"] = ((current + 1) % 7
                                                if current is not None else 0)
                altered_sha = audit.write(bad_report)
                bad_summary = deepcopy(audit.read(
                    continued["private_summary_sha256"]))
                bad_summary["private_combined_report_sha256"] = altered_sha
                bad_summary_sha = audit.write(bad_summary)
                with patch.object(scorer, "load_project_inputs", return_value=inputs), \
                     patch.object(scorer, "_expected_graph_names",
                                  return_value=("synthetic",)), \
                     patch.object(scorer, "_labels_from_original_graph",
                                  side_effect=AssertionError("GT accessed before trust")):
                    with self.assertRaises(scorer.EvaluationStageError) as raised:
                        scorer.run(root/"frozen", root/"authentic",
                                   original, cfg_file, bad_summary_sha, graph,
                                   root/"r1_rejected_bad_report")
                self.assertEqual(raised.exception.stage,
                                 "R1_OVERLAY_REPLAY_AND_TRUST")

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
