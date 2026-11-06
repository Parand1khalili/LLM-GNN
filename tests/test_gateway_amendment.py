"""Slice 3: synthetic-only 53+16 continuation and explicit fail-closed gates."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from test_gapgpt_gateway import inputs, ROOT
from llmgnn_sara.sara3 import gateway_continuation as continuation
from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.gateway_run import gateway_run, gateway_context, SyntheticGapGPTHttp
from llmgnn_sara.sara3.pipeline import run_offline
from llmgnn_sara.sara3.inputs import canonical_bytes
from llmgnn_sara.sara3.rich_evidence import RICH_VERSION, RICH_PROMPT_V2
from llmgnn_sara.sara3.automated_policy import VERSION as ARBITRATION
from llmgnn_sara.sara3.runner import SyntheticRichVerifier

CONFIG = ROOT / "configs/gapgpt_rich_v2_output4096_proposed.json"


class AmendmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / ".local_artifacts" / "original"
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.rows = inputs()

    def historical_53(self):
        class History:
            def __init__(self):
                self.calls, self.blinds = 0, []
            def __call__(self, wire, key):
                self.calls += 1
                content = json.loads(json.loads(wire)["messages"][0]["content"])
                node = content["node_id"]
                phase = content["phase"]
                status, raw = SyntheticGapGPTHttp("gpt-6-luna")(wire, key)
                data = json.loads(raw)
                response = json.loads(data["choices"][0]["message"]["content"])
                if phase == "blind":
                    self.blinds.append(node)
                    if len(self.blinds) <= 5:
                        response = SyntheticRichVerifier()._respond(SimpleNamespace(text=""))
                if self.calls == 53:
                    if phase != "compare":
                        raise AssertionError("53rd call must be a comparison")
                    response["counter_evidence"] = [dict(response["supporting_evidence"][0])]
                data["choices"][0]["message"]["content"] = canonical_bytes(response).decode()
                return status, canonical_bytes(data)
        with patch.object(socket.socket, "connect",
                          side_effect=AssertionError("Network forbidden")):
            output = gateway_run(self.rows, self.root, router="r0", budget=37,
                                 cohort="sensitivity", config=self.cfg,
                                 fake=True, transport=History())
        self.assertEqual(output["journal_states"], {"COMPLETED":52,"REJECTED":1,"UNCERTAIN":0})
        self.assertEqual(output["attempted_calls"], 53)
        self.assertEqual(len(output["not_attempted_after_halt_node_ids"]), 8)
        return output

    def files(self):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (self.root / "journal").iterdir() if p.is_file()}

    def verifier(self, allowed, transport, amendment=None):
        overlay = PrivateAudit(self.root / "continuation_overlay" / "journal")
        with (patch.object(continuation, "FROZEN_BLINDS", tuple(allowed)),
              patch.object(continuation, "amendment_preflight",
                           return_value={"original_intents":53})):
            return continuation.AmendedSyntheticContinuationVerifier(
                self.rows, self.cfg, self.root, overlay,
                amendment=amendment or {}, transport=transport)

    def test_exact_eight_new_blinds_and_conditional_comparisons_no_redelivery(self):
        original = self.historical_53()
        before = self.files()
        allowed = original["not_attempted_after_halt_node_ids"]
        transport = SyntheticGapGPTHttp("gpt-6-luna")
        verifier = self.verifier(allowed, transport)
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            result = run_offline(self.rows.pairs, 37, "r0", verifier,
                 audit=PrivateAudit(self.root / "continuation_overlay" / "phases"),
                 response_version=RICH_VERSION, prompt_version=RICH_PROMPT_V2,
                 automated_arbitration_version=ARBITRATION)
        self.assertEqual(verifier.dispatches, 16)
        self.assertEqual(transport.dispatches, 16)
        self.assertEqual(len(verifier.phase_states()), 69)
        self.assertEqual(sum(s == "REJECTED" for s in verifier.phase_states().values()), 1)
        self.assertEqual(sum(s == "UNCERTAIN" for s in verifier.phase_states().values()), 0)
        self.assertEqual(before, self.files())
        self.assertTrue(all(d["provisional_status"] == "NOT_PROPOSED"
                for d in result["decisions"] if d["reason"] == "L1_DUPLICATE_EVIDENCE"))
        # Restart replays 52+16 completed; rejected is never retried.
        again = self.verifier(allowed, SyntheticGapGPTHttp("gpt-6-luna"))
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            run_offline(self.rows.pairs, 37, "r0", again,
                 audit=PrivateAudit(self.root / "continuation_overlay" / "phases"),
                 response_version=RICH_VERSION, prompt_version=RICH_PROMPT_V2,
                 automated_arbitration_version=ARBITRATION)
        self.assertEqual(again.dispatches, 0)
        self.assertEqual(before, self.files())

    def test_uncertain_stops_no_retry_and_tampering_fails_closed(self):
        original = self.historical_53()
        allowed = original["not_attempted_after_halt_node_ids"]
        def timeout(wire, key):
            raise TimeoutError("synthetic")
        verifier = self.verifier(allowed, timeout)
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            run_offline(self.rows.pairs, 37, "r0", verifier,
                 audit=PrivateAudit(self.root / "continuation_overlay" / "phases"),
                 response_version=RICH_VERSION, prompt_version=RICH_PROMPT_V2,
                 automated_arbitration_version=ARBITRATION)
        self.assertEqual(verifier.dispatches, 1)
        self.assertEqual(sum(s == "UNCERTAIN" for s in verifier.phase_states().values()), 1)
        restarted = self.verifier(allowed, SyntheticGapGPTHttp("gpt-6-luna"))
        self.assertTrue(restarted.halted)
        self.assertEqual(restarted.dispatches, 0)
        before = self.files()
        target = next(p for p in (self.root / "journal").glob("*.json")
                      if json.loads(p.read_text()).get("kind") == "gapgpt_gateway_response")
        target.write_bytes(target.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            continuation.inspect(self.rows, self.root, config=self.cfg,
                expected_context_sha256=continuation.digest(
                    gateway_context(self.rows, "r0", 37, "sensitivity", self.cfg, fake=True)[1]),
                fake=True)
        self.assertNotEqual(before, self.files())

    def test_scope_budget_and_amendment_fail_closed(self):
        original = self.historical_53()
        allowed = original["not_attempted_after_halt_node_ids"]
        expected = json.loads((ROOT / "configs/sara3_gapgpt_continuation_amendment_v1.json").read_text(encoding="utf-8"))
        self.assertFalse(expected["owner_dispatch_approval"])
        self.assertEqual(expected["maximum_cumulative_calls"], 69)
        self.assertEqual(expected["maximum_new_calls"], 16)
        with self.assertRaises(ValueError):
            continuation.amendment_preflight(self.rows, self.root,
                config=self.cfg, amendment={**expected, "owner_dispatch_approval":True},
                fake=True)
        # A fake amended guard cannot reserve work for original nodes.
        v = self.verifier(allowed, SyntheticGapGPTHttp("gpt-6-luna"))
        old_node = next(n for n in original["selected_node_ids"] if n not in allowed)
        with self.assertRaises(ValueError):
            v._reserve("0"*64, "0"*64, None, "blind", old_node)
        with self.assertRaises(ValueError):
            v._budget_accepts_new_intent(16)


if __name__ == "__main__":
    unittest.main()
