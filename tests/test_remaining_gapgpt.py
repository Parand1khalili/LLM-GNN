"""Synthetic provider fixtures only; no real credentials, reviews or network."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from llmgnn_sara.pilot import remaining_gapgpt as batch
from llmgnn_sara.pilot.readiness import ReadinessLedger
from llmgnn_sara.sara3.audit import PrivateAudit, AuditError

KEY = "SYNTHETIC_BATCH_SECRET_12345"
APPROVAL = {"privacy": True, "sealed_wire": True, "declared_limits": True,
            "exact_revision": True, "reservation_usd": "0.10", "dispatch": batch.VERSION}


class RemainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requests, cls.previous = batch.prepare()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.audit = PrivateAudit(Path(self.temp.name) / "private")
        self.ledger = ReadinessLedger(self.audit.root / "intent.sqlite")

    def start(self, approval=None):
        return batch.start(self.ledger, self.audit, APPROVAL if approval is None else approval, self.requests)

    def response(self, wire, *, abstain=True, model=batch.REVISION, finish="stop"):
        request = json.loads(json.loads(wire)["messages"][0]["content"])
        value = {"class_index": None if abstain else 0, "abstain": abstain,
                 "evidence": [] if abstain else [request["target"]["text"][:100]]}
        return 200, json.dumps({"model": model, "choices": [{"finish_reason": finish,
            "message": {"content": json.dumps(value)}}],
            "usage": {"prompt_tokens": 700, "completion_tokens": 100, "total_tokens": 800,
                      "completion_tokens_details": {"reasoning_tokens": 60}}}).encode()

    def test_identity_exact_scope(self):
        for model in (batch.MODEL, batch.REVISION):
            self.assertTrue(batch.identity_allowed("GapGPT", batch.ENDPOINT, batch.MODEL, model))
        for model in (None, "gpt-6-luna-2026-10-01", batch.REVISION + ".evil", "gpt-6-luna\n", {"model": batch.MODEL}):
            self.assertFalse(batch.identity_allowed("GapGPT", batch.ENDPOINT, batch.MODEL, model))
        for scope in (("other", batch.ENDPOINT, batch.MODEL),
                      ("GapGPT", "https://api.gapapi.com/v1/chat/completions", batch.MODEL),
                      ("GapGPT", batch.ENDPOINT, "other-model")):
            self.assertFalse(batch.identity_allowed(*scope, batch.REVISION))

    def test_authentic_inputs_and_only_temperature_changes(self):
        self.assertEqual(tuple(self.requests), batch.NODES)
        self.assertNotIn(637, self.requests)
        for node, (blind, template) in self.requests.items():
            body = json.loads(batch.wire_for(blind))
            self.assertEqual(body["temperature"], 1)
            self.assertEqual(json.loads(body["messages"][0]["content"]), blind)
            self.assertNotIn("historical_candidates", blind)
            self.assertNotIn("reasoning_effort", body)
            self.assertEqual(template["blind_class_index"], "$BLIND_CLASS_INDEX")

    def test_approval_decline_no_start(self):
        for field in ("privacy", "sealed_wire", "declared_limits", "exact_revision"):
            with self.assertRaises(ValueError):
                self.start({**APPROVAL, field: False})
        with self.assertRaises(ValueError):
            self.start({**APPROVAL, "reservation_usd": "0.01"})
        self.assertEqual(self.ledger.snapshot(), [])

    def test_five_abstentions_no_comparisons_and_restart_blocked(self):
        digest = self.start()
        post = MagicMock(side_effect=lambda wire, key: self.response(wire))
        summary, receipt = batch.run(self.requests, self.previous, KEY, self.ledger, self.audit, digest, transport=post)
        self.assertEqual(summary["state"], "FINISHED")
        self.assertEqual(post.call_count, 5)
        self.assertEqual(summary["reported_usage_totals"]["reasoning_tokens"], 300)
        self.assertEqual(summary["state_counts"]["COMPLETED"], 5)
        self.assertEqual([r["node"] for r in summary["rows"]], [637, *batch.NODES])
        self.assertTrue(all(r["compare"]["state"] == "NOT_PERMITTED_BLIND_ABSTENTION" for r in summary["rows"]))
        self.audit.read(receipt)
        ledger = ReadinessLedger(self.ledger.path)
        with self.assertRaises(ValueError):
            batch.start(ledger, self.audit, APPROVAL, self.requests)
        for path in self.audit.root.glob("*.json"):
            self.assertNotIn(KEY.encode(), path.read_bytes())

    def test_ten_calls_actual_comparison_bindings_and_no_labels(self):
        digest = self.start()
        calls = []
        def post(wire, key):
            payload = json.loads(json.loads(wire)["messages"][0]["content"])
            calls.append((payload["node_id"], payload["phase"]))
            if payload["phase"] == "compare":
                self.assertEqual(payload["blind_class_index"], 0)
            return self.response(wire, abstain=False)
        summary, _ = batch.run(self.requests, self.previous, KEY, self.ledger, self.audit, digest, transport=post)
        self.assertEqual(summary["state"], "FINISHED")
        self.assertEqual(calls, [(n, p) for n in batch.NODES for p in ("blind", "compare")])
        for row in summary["rows"][1:]:
            for phase in ("blind", "compare"):
                self.assertIsNone(row[phase]["accepted_label"])
                self.assertEqual(row[phase]["l2_status"], "NOT_ASSESSED")

    def test_unknown_revision_halts_without_skip(self):
        digest = self.start()
        post = MagicMock(side_effect=lambda wire, key: self.response(wire, model="gpt-6-luna-2099-01-01"))
        summary, _ = batch.run(self.requests, self.previous, KEY, self.ledger, self.audit, digest, transport=post)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(summary["rows"][1]["blind"]["reason"], "RETURNED_MODEL_MISMATCH")
        self.assertEqual(summary["state"], "HALTED_REVIEW_REQUIRED_NO_RETRY")
        self.assertEqual(summary["rows"][2]["blind"]["state"], "NOT_ATTEMPTED")

    def test_timeout_and_restart_do_not_repeat(self):
        digest = self.start()
        post = MagicMock(side_effect=TimeoutError(KEY))
        summary, _ = batch.run(self.requests, self.previous, KEY, self.ledger, self.audit, digest, transport=post)
        self.assertEqual(summary["state_counts"]["UNCERTAIN"], 1)
        self.assertIsNone(summary["estimated_cost_usd"])
        self.assertEqual(summary["estimate_missing_count"], 1)
        self.assertEqual(post.call_count, 1)
        with self.assertRaises(ValueError):
            batch.start(ReadinessLedger(self.ledger.path), self.audit, APPROVAL, self.requests)

    def test_crash_after_start_blocks_restart(self):
        self.start()
        with self.assertRaises(ValueError):
            batch.start(ReadinessLedger(self.ledger.path), self.audit, APPROVAL, self.requests)
        self.assertEqual(self.ledger.snapshot(), [])

    def test_audit_failure_before_dispatch(self):
        digest = self.start()
        post = MagicMock()
        with patch.object(self.audit, "write", side_effect=AuditError()):
            with self.assertRaises(AuditError):
                batch.dispatch(1243, "blind", self.requests[1243][0], KEY, self.ledger, self.audit, digest, transport=post)
        post.assert_not_called()

    def test_audit_failure_after_dispatch_stays_uncertain_and_halts(self):
        digest = self.start()
        original = self.audit.write
        def write(record):
            if record.get("kind") == "canary_provider_response":
                raise AuditError()
            return original(record)
        post = MagicMock(side_effect=lambda wire, key: self.response(wire))
        with patch.object(self.audit, "write", side_effect=write):
            summary, _ = batch.run(self.requests, self.previous, KEY, self.ledger, self.audit, digest, transport=post)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(summary["state_counts"]["UNCERTAIN"], 1)
        self.assertEqual(summary["state"], "HALTED_REVIEW_REQUIRED_NO_RETRY")

    def test_duplicate_dispatch_preserves_terminal_state(self):
        digest = self.start()
        post = MagicMock(side_effect=lambda wire, key: self.response(wire))
        batch.dispatch(1243, "blind", self.requests[1243][0], KEY, self.ledger, self.audit, digest, transport=post)
        before = self.ledger.snapshot()
        with self.assertRaises(ValueError):
            batch.dispatch(1243, "blind", self.requests[1243][0], KEY, self.ledger, self.audit, digest, transport=post)
        self.assertEqual(before, self.ledger.snapshot())
        self.assertEqual(post.call_count, 1)

    def test_bad_binding_and_changed_payload_never_dispatch(self):
        digest = self.start()
        post = MagicMock()
        blind = self.requests[1243][0]
        for payload, pin in ((blind, "0"*64), ({**blind, "instructions": "changed"}, digest),
                             ({**blind, "ground_truth": 0}, digest)):
            with self.assertRaises(ValueError):
                batch.dispatch(1243, "blind", payload, KEY, self.ledger, self.audit, pin, transport=post)
        post.assert_not_called()

    def test_truncation_malformed_and_over_token_limit_halt(self):
        digest = self.start()
        post = MagicMock(return_value=self.response(batch.wire_for(self.requests[1243][0]), finish="length"))
        summary, _ = batch.run(self.requests, self.previous, KEY, self.ledger, self.audit, digest, transport=post)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(summary["rows"][1]["blind"]["reason"], "TRUNCATED_OR_NONFINAL")

    def test_budget_exhaustion_no_dispatch(self):
        digest = self.start()
        with closing(sqlite3.connect(self.ledger.path)) as db, db:
            for i in range(10):
                db.execute("INSERT INTO intents VALUES (?,?,?,?,?,?,NULL,NULL)",
                    (f"synthetic{i}", self.ledger.pin, f"synthetic{i}", "COMPLETED", 16384, 512))
        post = MagicMock()
        with self.assertRaises(ValueError):
            batch.dispatch(1243, "blind", self.requests[1243][0], KEY, self.ledger, self.audit, digest, transport=post)
        post.assert_not_called()

    def test_malformed_invalid_and_usage_exhaustion_stop(self):
        for kind in ("malformed", "fabricated", "usage"):
            with self.subTest(kind=kind):
                self.setUp()
                digest = self.start()
                status, raw = self.response(batch.wire_for(self.requests[1243][0]))
                envelope = json.loads(raw)
                if kind == "malformed":
                    envelope["choices"][0]["message"]["content"] = "{"
                elif kind == "fabricated":
                    envelope["choices"][0]["message"]["content"] = json.dumps(
                        {"class_index": 0, "abstain": False, "evidence": ["fabricated unknown quotation"]})
                else:
                    envelope["usage"]["completion_tokens"] = 513
                post = MagicMock(return_value=(status, json.dumps(envelope).encode()))
                summary, _ = batch.run(self.requests, self.previous, KEY, self.ledger, self.audit, digest, transport=post)
                self.assertEqual(post.call_count, 1)
                self.assertEqual(summary["state_counts"]["REJECTED"], 1)

    def test_comparison_after_abstention_forbidden(self):
        digest = self.start()
        first = batch.dispatch(1243, "blind", self.requests[1243][0], KEY, self.ledger, self.audit, digest,
                               transport=lambda wire, key: self.response(wire))
        comparison = batch.materialize_comparison(self.requests[1243][1], 0)
        post = MagicMock()
        with self.assertRaises(ValueError):
            batch.dispatch(1243, "compare", comparison, KEY, self.ledger, self.audit, digest,
                           dependency={}, transport=post)
        post.assert_not_called()

    def test_crash_between_reservation_and_dispatch_blocks_resume(self):
        digest = self.start()
        self.ledger.reserve(f"{batch.VERSION}:1243:blind", self.requests[1243][0], 16384, 512)
        post = MagicMock()
        with self.assertRaises(ValueError):
            batch.run(self.requests, self.previous, KEY, self.ledger, self.audit, digest, transport=post)
        post.assert_not_called()
        self.assertEqual(self.ledger.snapshot()[0][3], "PENDING")

    def test_prior_intent_discovery_and_no_review_access(self):
        root = Path(self.temp.name)
        target = root / ".local_artifacts/gapgpt_fake"
        target.mkdir(parents=True)
        ledger = ReadinessLedger(target / "intent.sqlite")
        ledger.reserve("existing", self.requests[1243][0], 16384, 512)
        with self.assertRaises(ValueError):
            batch.verify_no_prior_dispatch(root, [self.requests[1243][0]])

    def test_missing_key_noninteractive_cli_never_dispatches(self):
        with patch.object(batch.sys.stdin, "isatty", return_value=False), patch.object(batch.canary, "credential") as key:
            self.assertEqual(batch.main(), 1)
            key.assert_not_called()


if __name__ == "__main__":
    unittest.main()
