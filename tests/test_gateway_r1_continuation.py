"""R1 original-receipt-safe continuation, synthetic HTTP only, no GT."""
from copy import deepcopy
import io
import json
from pathlib import Path
from types import SimpleNamespace
import socket
import tempfile
import unittest
from unittest.mock import patch

from llmgnn_sara.sara2.policy import Annotation, Pair
from llmgnn_sara.sara3.selection import select_router
from llmgnn_sara.sara3.gateway_run import SyntheticGapGPTHttp, gateway_run
from llmgnn_sara.sara3.gateway_r1_continuation import (
    MAX_NEW, REJECT_CODE, OVERLAY, preflight, execute, main)
from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.inputs import canonical_bytes
from llmgnn_sara.sara3.gateway_continuation import journal_rows
from llmgnn_sara.sara3.gateway_run import gateway_context
from llmgnn_sara.sara3.experiment import digest


class FailAt51:
    """37 routed; first nine blind abstain, 51st call is an invalid Comparison."""
    def __init__(self, model, skip_ids):
        self.base = SyntheticGapGPTHttp(model)
        self.skip = frozenset(skip_ids)
        self.calls = 0

    def __call__(self, wire, key):
        status, raw = self.base(wire, key)
        payload = json.loads(json.loads(wire)["messages"][0]["content"])
        phase, node = payload["phase"], payload["node_id"]
        env = json.loads(raw)
        content = json.loads(env["choices"][0]["message"]["content"])
        self.calls += 1
        if phase == "blind" and node in self.skip:
            content = {
                "schema_version": content["schema_version"], "class_index": None,
                "abstain": True, "primary_topic": None,
                "supporting_evidence": [], "counter_evidence": [],
                "auxiliary_method_warning": None,
                "uncertainty_reason": "Synthetic intended abstention for isolation"}
        if self.calls == 51:
            if phase != "compare":
                raise AssertionError("Test setup: 51st request must be Comparison")
            if not content.get("supporting_evidence"):
                raise AssertionError("Test setup: 51st compare must have evidence")
            content["supporting_evidence"][0]["quote"] = "NONSOURCE_VERBATIM_QUOTE_00000"
        env["choices"][0]["message"]["content"] = canonical_bytes(content).decode()
        return status, canonical_bytes(env)


def fixture():
    pairs = tuple(Pair(Annotation(n, 0, 10 if n < 37 else 90),
                       Annotation(n, 0, 10 if n < 37 else 90),
                       f"A substantial synthetic paper about neural classifiers and topic models "
                       f"with primary research methods, feature learning and statistical optimization for node {n}.")
                  for n in range(140))
    selected = select_router(pairs, 37, "r1_v1")
    first_nine = sorted(selected)[:9]
    cfg = json.loads((Path(__file__).resolve().parents[1] /
                      "configs/gapgpt_rich_v2_output4096_proposed.json").read_text())
    inputs = SimpleNamespace(pairs=pairs, provenance=(),
                             frozen=SimpleNamespace(by_arm=lambda arm: ()))
    return inputs, cfg, selected, first_nine


class R1ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.inputs, self.cfg, self.selected, self.first_nine = fixture()
        network = patch.object(socket.socket, "connect",
                               side_effect=AssertionError("No outbound networking"))
        network.start()
        self.addCleanup(network.stop)

    def seed(self, root):
        transport = FailAt51(self.cfg["model"], self.first_nine)
        result = gateway_run(self.inputs, root, router="r1_v1",
                             budget=37, cohort="sensitivity",
                             config=self.cfg, fake=True, transport=transport)
        self.assertEqual(result["status"], "BLOCKED_NO_AUTOMATIC_RETRY")
        self.assertEqual(result["attempted_calls"], 51)
        self.assertEqual(result["journal_states"], {
            "COMPLETED": 50, "REJECTED": 1, "UNCERTAIN": 0})
        self.assertEqual(result["rejection_codes"], {REJECT_CODE: 1})
        self.assertEqual(result["blind_completed"], 30)
        self.assertEqual(result["comparison_completed"], 20)
        return result

    def test_read_only_verified_preflight_and_no_GT(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ".local_artifacts" / "r1_original"
            self.seed(root)
            original = sorted(p.name for p in (root/"journal").iterdir())
            val = preflight(self.inputs, root, config=self.cfg, fake=True)
            self.assertEqual(val["status"],
                             "READ_ONLY_R1_CONTINUATION_PROPOSED_NOT_AUTHORIZED")
            self.assertEqual(val["maximum_new_calls"], 14)
            self.assertEqual(val["maximum_total_calls"], 65)
            self.assertEqual(val["never_attempted_blind_count"], 7)
            self.assertEqual(val["preserved_rejection_code"], REJECT_CODE)
            self.assertEqual(val["amendment_template"]["original_report_sha256"], None)
            self.assertEqual(val["approval_template"]["spend_approved"], False)
            self.assertEqual(sorted(p.name for p in (root/"journal").iterdir()), original)
            self.assertFalse((root/OVERLAY).exists())

    def test_scoped_completion_replays_50_successes_and_preserves_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ".local_artifacts" / "r1_original"
            self.seed(root)
            _, ctx = gateway_context(
                self.inputs, "r1_v1", 37, "sensitivity", self.cfg, fake=True)
            original, original_phases = journal_rows(
                root, digest(ctx), self.cfg["max_calls"])
            checked = preflight(self.inputs, root, config=self.cfg, fake=True)
            original_hash = checked["amendment_template"]["original_journal_rows_sha256"]
            approval = checked["approval_template"]
            approval.update({name: True for name in (
                "data_sharing_approved", "spend_approved",
                "explicit_continuation_dispatch_approved")})
            fake = SyntheticGapGPTHttp(self.cfg["model"])
            result = execute(
                self.inputs, root, config=self.cfg,
                amendment=checked["amendment_template"], approval=approval,
                key="synthetic-local-key-unknown",
                _testing_fake=True, _testing_transport=fake)
            self.assertEqual(result["status"],
                             "CONTINUED_PRESERVING_REJECTED_COMPARISON")
            self.assertEqual(result["new_dispatches"], 14)
            self.assertEqual(result["new_intents"], 14)
            self.assertEqual(result["total_intents"], 65)
            self.assertEqual(result["blinds_completed"], 37)
            self.assertEqual(result["comparisons_completed"], 27)
            again, again_phases = journal_rows(
                root, digest(ctx), self.cfg["max_calls"])
            self.assertEqual(again, original)
            self.assertEqual(again_phases, original_phases)
            report = PrivateAudit(root / OVERLAY / "journal").read(
                result["private_combined_report_sha256"])
            self.assertEqual(report["kind"], "gapgpt_r1_v1_continuation_private_report")
            self.assertEqual(report["run"]["original_response_reused_count"], 50)
            self.assertEqual(report["run"]["original_rejected_preserved"], 1)
            self.assertEqual(report["run"]["original_journal_rows_sha256"], original_hash)
            self.assertEqual(report["run"]["provider_calls"], 0)  # fake-only test
            self.assertEqual(len(report["run"]["decisions"]), 140)
            with self.assertRaises(ValueError):
                execute(self.inputs, root, config=self.cfg,
                        amendment=checked["amendment_template"], approval=approval,
                        key="synthetic-local-key-unknown",
                        _testing_fake=True, _testing_transport=fake)

    def test_missing_approval_bad_amendment_and_fake_forbidden_in_public_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ".local_artifacts" / "r1_original"
            self.seed(root)
            checked = preflight(self.inputs, root, config=self.cfg, fake=True)
            with self.assertRaises(ValueError):
                execute(self.inputs, root, config=self.cfg,
                        amendment=checked["amendment_template"],
                        approval=checked["approval_template"],
                        key="synthetic-local-key-unknown",
                        _testing_fake=True,
                        _testing_transport=SyntheticGapGPTHttp(self.cfg["model"]))
            self.assertFalse((root/OVERLAY).exists())
            bad = deepcopy(checked["amendment_template"])
            bad["maximum_new_calls"] = 15
            approved = deepcopy(checked["approval_template"])
            approved.update({n: True for n in (
                "data_sharing_approved", "spend_approved",
                "explicit_continuation_dispatch_approved")})
            with self.assertRaises(ValueError):
                execute(self.inputs, root, config=self.cfg,
                        amendment=bad, approval=approved,
                        key="synthetic-local-key-unknown",
                        _testing_fake=True,
                        _testing_transport=SyntheticGapGPTHttp(self.cfg["model"]))
            self.assertFalse((root/OVERLAY).exists())
            args = ["--mode", "live", "--frozen-root", "missing",
                    "--authentic-root", "missing", "--output-root", str(root),
                    "--gateway-config", "missing"]
            with patch("sys.stdout", new_callable=io.StringIO) as out, \
                 patch("sys.stderr", new_callable=io.StringIO) as err:
                self.assertEqual(main(args), 1)
            self.assertEqual(out.getvalue(), "")
            self.assertEqual(json.loads(err.getvalue()), {"status": "FAIL_CLOSED"})


if __name__ == "__main__":
    unittest.main()
