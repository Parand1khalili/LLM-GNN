"""Offline-only Slice 2 continuation tests. No paid transport or GT."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from test_gapgpt_gateway import CONFIG, inputs
from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.experiment import digest
from llmgnn_sara.sara3.gateway_run import (
    SyntheticGapGPTHttp, gateway_context, gateway_run)
from llmgnn_sara.sara3.gateway_continuation import (
    SyntheticContinuationVerifier, inspect)
from llmgnn_sara.sara3.inputs import canonical_bytes
from llmgnn_sara.sara3.pipeline import run_offline
from llmgnn_sara.sara3.rich_evidence import RICH_PROMPT_V2, RICH_VERSION
from llmgnn_sara.sara3.automated_policy import VERSION as ARBITRATION


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / ".local_artifacts" / "original"
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.data = inputs()

    def halted(self):
        class RejectComparison:
            def __init__(self):
                self.calls = 0
            def __call__(self, wire, key):
                self.calls += 1
                status, raw = SyntheticGapGPTHttp("gpt-6-luna")(wire, key)
                if self.calls == 4:
                    data = json.loads(raw)
                    result = json.loads(data["choices"][0]["message"]["content"])
                    result["counter_evidence"] = [dict(result["supporting_evidence"][0])]
                    data["choices"][0]["message"]["content"] = canonical_bytes(result).decode()
                    return status, canonical_bytes(data)
                return status, raw
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            result = gateway_run(self.data, self.root, router="r0", budget=37,
                                 cohort="sensitivity", config=self.cfg,
                                 fake=True, transport=RejectComparison())
        self.assertEqual(result["journal_states"]["REJECTED"], 1)
        return result

    def context(self):
        _, ctx = gateway_context(self.data, "r0", 37, "sensitivity", self.cfg, fake=True)
        return ctx

    def check(self, reject=None):
        return inspect(self.data, self.root, config=self.cfg,
                       expected_context_sha256=digest(self.context()), fake=True,
                       expected_rejection=reject)

    def fingerprints(self):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (self.root / "journal").iterdir() if p.is_file()}

    def test_replay_rejected_and_conditional_overlay_without_original_mutation(self):
        halt = self.halted()
        before = self.fingerprints()
        report = self.check()
        rejected_node = report["rejected_phases"][0]["node_id"]
        self.assertEqual(self.check((rejected_node, "compare")), report)
        self.assertEqual((report["original_intents"],
                          report["completed_replayed_and_l1_verified"],
                          report["rejected_preserved"]), (4, 3, 1))
        self.assertEqual(report["remaining_logical_capacity"], 70)
        self.assertEqual(report["maximum_possible_new_calls"], 70)
        self.assertEqual(before, self.fingerprints())
        overlay = PrivateAudit(self.root / "continuation_v1" / "journal")
        verifier = SyntheticContinuationVerifier(
            self.cfg, self.context(), self.root, overlay, transport=SyntheticGapGPTHttp("gpt-6-luna"),
            original_count=report["original_intents"])
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            run = run_offline(self.data.pairs, 37, "r0", verifier,
                              audit=PrivateAudit(self.root / "continuation_v1" / "phases"),
                              response_version=RICH_VERSION, prompt_version=RICH_PROMPT_V2,
                              automated_arbitration_version=ARBITRATION)
        self.assertEqual(verifier.dispatches, 70)
        self.assertEqual(verifier.hits, 3)
        self.assertEqual(len(verifier.phase_states()), 74)
        self.assertEqual(run["decisions"][next(i for i,d in enumerate(run["decisions"])
                         if d["node_id"] == rejected_node)]["provisional_status"], "NOT_PROPOSED")
        self.assertEqual(before, self.fingerprints())
        # A replay never sends a second request; the rejected terminal stays rejected.
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            replay = run_offline(self.data.pairs, 37, "r0", verifier,
                                 audit=PrivateAudit(self.root / "continuation_v1" / "phases"),
                                 response_version=RICH_VERSION, prompt_version=RICH_PROMPT_V2,
                                 automated_arbitration_version=ARBITRATION)
        self.assertEqual(verifier.dispatches, 70)
        self.assertEqual(before, self.fingerprints())

    def test_fail_closed_on_uncertainty_and_wrong_binding(self):
        self.halted()
        wrong = deepcopy(self.cfg)
        wrong["max_calls"] = 73
        with self.assertRaises(ValueError):
            inspect(self.data, self.root, config=wrong,
                    expected_context_sha256=digest(self.context()), fake=True)
        audit = PrivateAudit(self.root / "continuation_v1" / "journal")
        def timeout(wire, key):
            raise TimeoutError("synthetic timeout")
        verifier = SyntheticContinuationVerifier(self.cfg, self.context(), self.root,
            audit, transport=timeout, original_count=4)
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            run_offline(self.data.pairs, 37, "r0", verifier,
                        audit=PrivateAudit(self.root / "continuation_v1" / "phases"),
                        response_version=RICH_VERSION, prompt_version=RICH_PROMPT_V2,
                        automated_arbitration_version=ARBITRATION)
        self.assertEqual(sum(s == "UNCERTAIN" for s in verifier.phase_states().values()), 1)
        renewed = SyntheticContinuationVerifier(self.cfg, self.context(), self.root,
            audit, transport=SyntheticGapGPTHttp("gpt-6-luna"), original_count=4)
        self.assertTrue(renewed.halted)
        self.assertEqual(renewed.dispatches, 0)

    def test_original_receipt_tamper_fails_closed(self):
        self.halted()
        target = next(p for p in (self.root / "journal").glob("*.json")
                      if json.loads(p.read_text()).get("kind") == "gapgpt_gateway_response")
        target.write_bytes(target.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            self.check()


if __name__ == "__main__":
    unittest.main()
