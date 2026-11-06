"""Synthetic-only, offline usage and halt reconciliation tests."""
from contextlib import closing
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from test_gapgpt_gateway import CONFIG, inputs
from llmgnn_sara.sara3.gateway_run import gateway_run, SyntheticGapGPTHttp, gateway_context
from llmgnn_sara.sara3.gateway_usage_report import reconcile
from llmgnn_sara.sara3.experiment import digest
from llmgnn_sara.sara3.inputs import canonical_bytes


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / ".local_artifacts" / "usage"
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.data = inputs()

    def fake(self, transport):
        with patch.object(socket.socket, "connect",
                          side_effect=AssertionError("Network forbidden")):
            return gateway_run(self.data, self.root, router="r0", budget=37,
                               cohort="sensitivity", config=self.config,
                               fake=True, transport=transport)

    def report(self, ids=()):
        _, ctx = gateway_context(self.data, "r0", 37, "sensitivity",
                                 self.config, fake=True)
        return reconcile(self.root, expected_context_sha256=digest(ctx),
                         config=self.config, check_node_ids=ids)

    def test_rejected_usage_is_counted_and_nonattempted_is_not_uncertain(self):
        class RejectOne:
            def __init__(self):
                self.calls = 0
            def __call__(self, wire, key):
                self.calls += 1
                code, raw = SyntheticGapGPTHttp("gpt-6-luna")(wire, key)
                envelope = json.loads(raw)
                content = json.loads(envelope["choices"][0]["message"]["content"])
                content["supporting_evidence"].append(dict(content["supporting_evidence"][0]))
                envelope["choices"][0]["message"]["content"] = canonical_bytes(content).decode()
                envelope["usage"]["completion_tokens_details"] = {"reasoning_tokens": 25}
                return code, canonical_bytes(envelope)
        transport = RejectOne()
        summary = self.fake(transport)
        self.assertEqual(transport.calls, 1)
        self.assertEqual(summary["journal_states"], {"COMPLETED": 0, "REJECTED": 1, "UNCERTAIN": 0})
        self.assertEqual(len(summary["not_attempted_after_halt_node_ids"]), 36)
        report = self.report(summary["not_attempted_after_halt_node_ids"][:2])
        self.assertEqual(report["rejected"]["usage_available"], 1)
        self.assertEqual(report["all_attempts"]["attempts"], 1)
        self.assertEqual(report["unknown_billing_attempts"], 0)
        self.assertEqual(report["rejected"]["reasoning_tokens"], 25)
        self.assertTrue(all(v["status"] == "NOT_ATTEMPTED_AFTER_HALT"
                            for v in report["checked_nodes"].values()))
        p, c = report["all_attempts"]["prompt_tokens"], report["all_attempts"]["completion_tokens"]
        self.assertEqual(report["all_attempts"]["estimated_cost_usd"],
                         str(__import__("decimal").Decimal(p * 10 + c * 50) / __import__("decimal").Decimal(100000000)))
        self.assertEqual(self.fake(SyntheticGapGPTHttp("gpt-6-luna"))["new_dispatches"], 0)

    def test_uncertain_intent_is_never_relabelled_not_attempted(self):
        def timeout(wire, key):
            raise TimeoutError("synthetic")
        summary = self.fake(timeout)
        self.assertEqual(summary["journal_states"]["UNCERTAIN"], 1)
        self.assertEqual(len(summary["not_attempted_after_halt_node_ids"]), 36)
        with closing(sqlite3.connect(self.root / "journal" / "fixture_journal.sqlite")) as db:
            node, = db.execute("SELECT node_id FROM intents WHERE state='UNCERTAIN'").fetchone()
        report = self.report([node] + summary["not_attempted_after_halt_node_ids"][:1])
        self.assertEqual(report["checked_nodes"][str(node)]["blind"], "UNCERTAIN")
        self.assertEqual(report["unknown_billing_attempts"], 1)
        self.assertIsNone(report["all_attempts"]["estimated_cost_usd"])

    def test_tampering_and_binding_mismatch_fail_closed(self):
        self.fake(SyntheticGapGPTHttp("gpt-6-luna"))
        _, context = gateway_context(self.data, "r0", 37, "sensitivity", self.config, fake=True)
        with self.assertRaisesRegex(ValueError, "binding"):
            reconcile(self.root, expected_context_sha256="0" * 64, config=self.config)
        changed = deepcopy(self.config)
        changed["max_calls"] = 73
        with self.assertRaisesRegex(ValueError, "binding"):
            reconcile(self.root, expected_context_sha256=digest(context), config=changed)
        with closing(sqlite3.connect(self.root / "journal" / "fixture_journal.sqlite")) as db:
            receipt, = db.execute("SELECT receipt FROM intents LIMIT 1").fetchone()
        f = self.root / "journal" / (receipt + ".json")
        f.write_bytes(f.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "hash"):
            self.report()


if __name__ == "__main__":
    unittest.main()
