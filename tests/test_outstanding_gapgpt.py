"""Synthetic continuation transport only. Never writes historical pilot stores."""
from contextlib import closing
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from llmgnn_sara.pilot import outstanding_gapgpt as continuation
from llmgnn_sara.pilot import remaining_gapgpt as prior
from llmgnn_sara.pilot.readiness import ReadinessLedger
from llmgnn_sara.sara3.audit import PrivateAudit, AuditError
from llmgnn_sara.evaluation.routing_experiment import synthetic_source_excerpt

KEY = "SYNTHETIC_CONTINUATION_KEY_12345"


class ContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Only synthetic fixture admission bypasses existing outstanding intents.
        with patch.object(prior, "verify_no_prior_dispatch"):
            cls.prepared = continuation.prepare()

    def setUp(self):
        self.contract = copy.deepcopy(self.prepared)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.audit = PrivateAudit(Path(self.temp.name) / "private")
        self.ledger = ReadinessLedger(self.audit.root / "intent.sqlite")

    def start(self):
        return continuation.start(self.contract, continuation.approvals_for(self.contract), self.ledger, self.audit)

    def envelope(self, wire, *, abstain=False, model=prior.REVISION, finish="stop"):
        request = json.loads(json.loads(wire)["messages"][0]["content"])
        value = {"class_index": None if abstain else 0, "abstain": abstain,
                 "evidence": [] if abstain else [synthetic_source_excerpt(request["target"]["text"])]}
        return 200, json.dumps({"model": model, "choices": [{"finish_reason": finish,
            "message": {"content": json.dumps(value)}}], "usage": {"prompt_tokens": 800,
            "completion_tokens": 100, "total_tokens": 900, "completion_tokens_details": {"reasoning_tokens": 60}}}).encode()

    def test_bound_plan_excludes_preserved_blinds(self):
        plan = self.contract["plan"]
        self.assertEqual([(s["node"], s["phase"]) for s in plan],
            [(1243, "compare")] + [(n, p) for n in continuation.NODES for p in ("blind", "compare")])
        self.assertEqual(self.contract["maximum_calls"], 9)
        self.assertEqual(self.contract["preserved_1243"]["original_ledger_state"], "REJECTED")
        self.assertEqual(plan[0]["payload"]["blind_class_index"], self.contract["preserved_1243"]["class_index"])
        self.assertEqual(plan[0]["dependency"], self.contract["preserved_1243"]["lineage"])
        self.assertIsNone(self.contract["preserved_1243"]["accepted_label"])

    def test_all_nine_requests_in_order_and_budget_totals(self):
        digest = self.start()
        calls = []
        def post(wire, key):
            payload = json.loads(json.loads(wire)["messages"][0]["content"])
            calls.append((payload["node_id"], payload["phase"]))
            return self.envelope(wire)
        summary, receipt = continuation.run(self.contract, KEY, self.ledger, self.audit, digest, transport=post)
        self.assertEqual(summary["state"], "FINISHED")
        self.assertEqual(calls, [(s["node"], s["phase"]) for s in self.contract["plan"]])
        self.assertEqual(summary["dispatch_attempts_upper_bound"], 9)
        self.assertEqual(summary["reported_usage_totals"]["prompt_tokens"], 7200)
        self.assertEqual(summary["reported_usage_totals"]["reasoning_tokens"], 540)
        self.assertEqual(summary["estimated_cost_usd"], "0.00117")
        self.assertEqual(sum(r[4] for r in self.ledger.snapshot()), 9*16384)
        self.assertEqual(sum(r[5] for r in self.ledger.snapshot()), 9*512)
        self.audit.read(receipt)
        self.assertTrue(summary["rows"][1]["blind"]["historical"])
        self.assertIsNone(summary["accepted_label"])
        for p in self.audit.root.glob("*.json"):
            self.assertNotIn(KEY.encode(), p.read_bytes())

    def test_new_abstentions_skip_only_their_comparisons(self):
        digest = self.start()
        post = MagicMock(side_effect=lambda wire, key: self.envelope(wire, abstain=True))
        summary, _ = continuation.run(self.contract, KEY, self.ledger, self.audit, digest, transport=post)
        self.assertEqual(summary["state"], "FINISHED")
        self.assertEqual(post.call_count, 5)
        self.assertTrue(all(row["compare"]["state"] == "NOT_PERMITTED_BLIND_ABSTENTION"
                            for row in summary["rows"][2:]))

    def test_wrong_preserved_response_dependency_never_dispatches(self):
        digest = self.start()
        step = self.contract["plan"][0]
        post = MagicMock()
        wrong = {**step["dependency"], "inner_response_sha256": "0"*64}
        with self.assertRaises(ValueError):
            continuation.dispatch(self.contract, 0, step["payload"], wrong, KEY, self.ledger, self.audit, digest, transport=post)
        post.assert_not_called()

    def test_repeat_blind_and_wrong_sequence_blocked(self):
        digest = self.start()
        step = self.contract["plan"][0]
        post = MagicMock()
        for payload, ordinal in (({**step["payload"], "phase": "blind"}, 0),
                                 ({**step["payload"], "node_id": 637}, 0),
                                 (self.contract["plan"][1]["payload"], 1)):
            with self.assertRaises(ValueError):
                continuation.dispatch(self.contract, ordinal, payload, step["dependency"], KEY,
                                      self.ledger, self.audit, digest, transport=post)
        post.assert_not_called()

    def test_crash_start_and_unknown_dispatch_never_resume(self):
        digest = self.start()
        with self.assertRaises(ValueError):
            self.start()
        post = MagicMock(side_effect=TimeoutError(KEY))
        summary, _ = continuation.run(self.contract, KEY, self.ledger, self.audit, digest, transport=post)
        self.assertEqual(summary["state_counts"]["UNCERTAIN"], 1)
        self.assertIsNone(summary["estimated_cost_usd"])
        self.assertEqual(post.call_count, 1)
        with self.assertRaises(ValueError):
            continuation.run(self.contract, KEY, self.ledger, self.audit, digest, transport=post)
        self.assertEqual(post.call_count, 1)

    def test_rejected_malformed_truncated_or_new_revision_halts(self):
        for kind in ("malformed", "evidence", "truncated", "revision", "http"):
            with self.subTest(kind=kind):
                self.setUp()
                digest = self.start()
                status, raw = self.envelope(prior.wire_for(self.contract["plan"][0]["payload"]))
                envelope = json.loads(raw)
                if kind == "malformed": envelope["choices"][0]["message"]["content"] = "{"
                if kind == "evidence":
                    envelope["choices"][0]["message"]["content"] = json.dumps(
                        {"class_index": 0, "abstain": False, "evidence": ["fabricated unknown evidence"]})
                if kind == "truncated": envelope["choices"][0]["finish_reason"] = "length"
                if kind == "revision": envelope["model"] = prior.MODEL
                if kind == "http": status = 429
                post = MagicMock(return_value=(status, json.dumps(envelope).encode()))
                summary, _ = continuation.run(self.contract, KEY, self.ledger, self.audit, digest, transport=post)
                self.assertEqual(post.call_count, 1)
                self.assertEqual(summary["state"], "HALTED_REVIEW_REQUIRED_NO_RETRY")
                self.assertEqual(summary["state_counts"]["REJECTED"], 1)
                self.assertEqual(summary["rows"][2]["blind"]["state"], "NOT_ATTEMPTED")

    def test_audit_failure_before_and_after_dispatch(self):
        digest = self.start()
        post = MagicMock()
        step = self.contract["plan"][0]
        with patch.object(self.audit, "write", side_effect=AuditError()):
            with self.assertRaises(AuditError):
                continuation.dispatch(self.contract, 0, step["payload"], step["dependency"], KEY,
                                      self.ledger, self.audit, digest, transport=post)
        post.assert_not_called()
        original = self.audit.write
        def write(record):
            if record.get("kind") == "canary_provider_response": raise AuditError()
            return original(record)
        post = MagicMock(side_effect=lambda wire, key: self.envelope(wire))
        with patch.object(self.audit, "write", side_effect=write):
            summary, _ = continuation.run(self.contract, KEY, self.ledger, self.audit, digest, transport=post)
        self.assertEqual(summary["state_counts"]["UNCERTAIN"], 1)
        self.assertEqual(post.call_count, 1)

    def test_fresh_approvals_required_and_contract_changes_rejected(self):
        for field in ("amendment", "privacy", "outstanding_list", "declared_limits"):
            approval = {**continuation.approvals_for(self.contract), field: False}
            with self.assertRaises(ValueError):
                continuation.start(self.contract, approval, self.ledger, self.audit)
        bad = copy.deepcopy(self.contract); bad["plan"][0]["phase"] = "blind"
        with self.assertRaises(ValueError):
            continuation.start(bad, continuation.approvals_for(bad), self.ledger, self.audit)

    def test_duplicate_intent_and_postapproval_contract_tampering_block(self):
        digest = self.start()
        step = self.contract["plan"][0]
        post = MagicMock(side_effect=lambda wire, key: self.envelope(wire))
        continuation.dispatch(self.contract, 0, step["payload"], step["dependency"], KEY,
                              self.ledger, self.audit, digest, transport=post)
        snapshot = self.ledger.snapshot()
        with self.assertRaises(ValueError):
            continuation.dispatch(self.contract, 0, step["payload"], step["dependency"], KEY,
                                  self.ledger, self.audit, digest, transport=post)
        changed = copy.deepcopy(self.contract); changed["source_manifest_sha256"] = "0"*64
        with self.assertRaises(ValueError):
            continuation.dispatch(changed, 1, changed["plan"][1]["payload"], None, KEY,
                                  self.ledger, self.audit, digest, transport=post)
        self.assertEqual(snapshot, self.ledger.snapshot())
        self.assertEqual(post.call_count, 1)

    def test_nine_call_reservation_exhaustion_blocks_network(self):
        digest = self.start()
        with closing(sqlite3.connect(self.ledger.path)) as db, db:
            for i in range(9):
                db.execute("INSERT INTO intents VALUES (?,?,?,?,?,?,NULL,NULL)",
                           (f"synthetic{i}", self.ledger.pin, f"synthetic{i}", "COMPLETED", 16384, 512))
        post = MagicMock(); step = self.contract["plan"][0]
        with self.assertRaises(ValueError):
            continuation.dispatch(self.contract, 0, step["payload"], step["dependency"], KEY,
                                  self.ledger, self.audit, digest, transport=post)
        post.assert_not_called()

    def test_noninteractive_entry_never_reads_key(self):
        with patch.object(continuation.sys.stdin, "isatty", return_value=False), patch.object(continuation.canary, "credential") as key:
            self.assertEqual(continuation.main(), 1)
            key.assert_not_called()

    def test_changed_diagnostic_hash_or_rule_blocks_admission(self):
        original = prior._read_receipts
        blind = prior.sealed_inputs()[0][1243][0]
        for field in ("inner_response_sha256", "rule_source_sha256", "rule_version"):
            def read(path):
                records = copy.deepcopy(original(path))
                if path.name == "gapgpt_1243_l1_reassessment":
                    for record in records.values(): record[field] = "forged"
                return records
            with self.subTest(field=field), patch.object(prior, "_read_receipts", side_effect=read):
                with self.assertRaises(ValueError):
                    continuation.preserved_1243(continuation.ROOT, blind)


if __name__ == "__main__":
    unittest.main()
