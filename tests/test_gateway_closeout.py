"""Offline, network-blocked scientific closeout regression tests."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import unittest
from unittest.mock import patch

from test_gateway_live_continuation import LiveContinuationTests
from llmgnn_sara.sara3 import gateway_closeout
from llmgnn_sara.sara3.experiment import digest
from llmgnn_sara.sara3.gateway_run import SyntheticGapGPTHttp, gateway_context


class ReadOnlyCloseoutTests(unittest.TestCase):
    def setUp(self):
        self.fixture = LiveContinuationTests("test_owner_approval_is_new_and_exact")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.fixture.root
        self.fixture.amendment.update({
            "original_intents": 53, "original_completed": 52,
            "original_rejected_node_id": self.fixture.rejected_node,
            "original_rejected_phase": "compare",
            "maximum_cumulative_calls": 69, "maximum_new_calls": 16})
        self.fixture.approval["amendment_sha256"] = digest(self.fixture.amendment)
        with patch.object(socket.socket, "connect",
                          side_effect=AssertionError("External network forbidden")):
            self.execution = self.fixture._run(SyntheticGapGPTHttp("gpt-6-luna"))
        self.original_bytes = self.fixture.fixture.files()
        self.overlay_journal = self.root / "continuation_amendment_v1" / "journal"
        self.overlay_bytes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in self.overlay_journal.iterdir() if p.is_file()}
        self.options = dict(
            config=self.fixture.config,
            amendment=self.fixture.amendment,
            fake=False,
            frozen_context_sha=self.fixture.context_sha,
            frozen_contract_sha=digest(self.fixture.config),
            allowed_blinds=self.fixture.allowed,
            check_amendment=False)

    def closeout(self):
        result = gateway_closeout.analyze(
            self.fixture.data, self.root, **self.options)
        result.update(gateway_closeout.verify_private_report(
            result, self.root, self.execution["private_report_sha256"],
            {p.node_id for p in self.fixture.data.pairs},
            gateway_context(self.fixture.data, "r0", 37, "sensitivity",
                            self.fixture.config, fake=False)[0]))
        return result

    def test_complete_no_redispatch_and_sealed_proposals(self):
        with patch.object(socket.socket, "connect",
                          side_effect=AssertionError("External network forbidden")):
            summary = self.closeout()
            freeze = gateway_closeout.freeze(summary, self.root)
        self.assertEqual(summary["total_intents"], 69)
        self.assertEqual(summary["intent_states"], {
            "COMPLETED": 68, "REJECTED": 1, "UNCERTAIN": 0})
        self.assertEqual(summary["phase_states"]["blind"]["COMPLETED"], 37)
        self.assertEqual(summary["phase_states"]["compare"]["COMPLETED"], 31)
        self.assertEqual(summary["historical_intents"], 53)
        self.assertEqual(summary["continuation_intents"], 16)
        self.assertEqual(summary["comparison_missing_after_nonabstain"], [])
        self.assertEqual(summary["persisted_proposals"],
                         summary["automated_concordance"]["proposals"])
        self.assertTrue(summary["all_training_class_indices_null"])
        self.assertEqual(summary["persisted_proposals_accepted"], 0)
        self.assertEqual(summary["usage"]["all_attempts"]["attempts"], 69)
        self.assertEqual(self.original_bytes, self.fixture.fixture.files())
        self.assertEqual(self.overlay_bytes, {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in self.overlay_journal.iterdir() if p.is_file()})
        self.assertTrue((self.root / "closeout_v1" / (freeze + ".json")).is_file())
        self.assertEqual(freeze, gateway_closeout.freeze(summary, self.root))

    def test_tampered_continuation_receipt_fails_closed(self):
        db = self.overlay_journal / "fixture_journal.sqlite"
        with sqlite3.connect(db) as con:
            receipt = con.execute(
                "SELECT receipt FROM intents WHERE state='COMPLETED' LIMIT 1").fetchone()[0]
        path = self.overlay_journal / (receipt + ".json")
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            self.closeout()

    def test_duplicate_or_missing_conditional_comparison_fails_closed(self):
        db = self.overlay_journal / "fixture_journal.sqlite"
        with sqlite3.connect(db) as con:
            node = con.execute(
                "SELECT node_id FROM intents WHERE phase='compare' LIMIT 1").fetchone()[0]
            con.execute("DELETE FROM intents WHERE node_id=? AND phase='compare'", (node,))
        with self.assertRaises(ValueError):
            self.closeout()


if __name__ == "__main__":
    unittest.main()
