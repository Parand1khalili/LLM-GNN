"""Crash/restart safety of the private offline fixture journal; zero provider calls."""
import os
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.durable_fixture import DurableOfflineFixtureVerifier
from llmgnn_sara.sara3.evidence import EvidenceError
from llmgnn_sara.sara3.experiment import (
    FIXTURE_VERSION, MODEL_PLACEHOLDERS, digest, request_identity,
)
from llmgnn_sara.sara3.inputs import verifier_input

TEXT = "Bayesian Gaussian process theory is central to the paper."
QUOTE = "Bayesian Gaussian process theory"
CONTEXT = {
    "mode": "OFFLINE_SYNTHETIC_ONLY", "fixture_version": FIXTURE_VERSION,
    "experiment_version": "fixture-journal-tests", "cohort_sha256": "a" * 64,
    "protocol_sha256": "b" * 64, "model_settings": dict(MODEL_PLACEHOLDERS),
}


class Request:
    def __init__(self, node_id=130, text=TEXT, *, candidates=(6, 5), blind_class=6):
        self.node_id, self.text, self.neighborhood = node_id, text, None
        self.historical_candidates, self.blind_class_index = candidates, blind_class


class Fixture:
    offline = True
    fixture_version = FIXTURE_VERSION

    def __init__(self, *, fail=None, abstain=False):
        self.calls, self.fail, self.abstain = [], fail, abstain

    def blind(self, request):
        return self._result("blind", request)

    def compare(self, request):
        return self._result("compare", request)

    def _result(self, phase, request):
        self.calls.append((phase, request.node_id))
        if self.fail == "timeout":
            raise TimeoutError("PRIVATE_NO_RETRY")
        if self.fail == "invalid":
            return {"class_index": 6, "abstain": False, "evidence": ["Fabricated string"]}
        if self.abstain:
            return {"class_index": None, "abstain": True, "evidence": []}
        return {"class_index": 6, "abstain": False, "evidence": [QUOTE]}


class DurableFixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.audit = PrivateAudit(Path(self.tmp.name) / "private")

    def journal(self, fixture=None, *, context=CONTEXT, maximum_calls=4):
        return DurableOfflineFixtureVerifier(fixture or Fixture(), context, self.audit,
                                             maximum_calls=maximum_calls)

    def test_success_and_comparison_replay_across_restart(self):
        original = Fixture()
        first = self.journal(original)
        response = first.blind(Request())
        self.assertEqual(original.calls, [("blind", 130)])
        fixture = Fixture()
        second = self.journal(fixture)
        self.assertEqual(second.blind(Request()), response)
        self.assertEqual(fixture.calls, [])
        self.assertEqual(second.compare(Request()), response)
        self.assertEqual(fixture.calls, [("compare", 130)])
        resumed_fixture = Fixture()
        third = self.journal(resumed_fixture)
        self.assertEqual(third.compare(Request()), response)
        self.assertEqual(resumed_fixture.calls, [])
        self.assertEqual(len(third.cache), 2)
        self.assertEqual(set(third.states.values()), {"COMPLETED"})

    def test_crash_after_persisting_intent_does_not_send_again(self):
        first = self.journal()
        payload = verifier_input(130, TEXT)
        first._reserve(request_identity(payload, CONTEXT), digest(payload), None, "blind", 130)
        fresh = Fixture()
        resumed = self.journal(fresh)
        with self.assertRaisesRegex(EvidenceError, "TIMEOUT_UNCERTAIN_NO_RETRY"):
            resumed.blind(Request())
        self.assertEqual(fresh.calls, [])
        self.assertEqual(resumed.snapshot()[0]["state"], "UNCERTAIN")

    def test_timeout_remains_uncertain_without_retry(self):
        fixture = Fixture(fail="timeout")
        with self.assertRaises(TimeoutError):
            self.journal(fixture).blind(Request())
        resumed = Fixture()
        with self.assertRaisesRegex(EvidenceError, "TIMEOUT_UNCERTAIN_NO_RETRY"):
            self.journal(resumed).blind(Request())
        self.assertEqual(fixture.calls, [("blind", 130)])
        self.assertEqual(resumed.calls, [])

    def test_bad_quote_rejected_not_promoted_or_retried(self):
        fixture = Fixture(fail="invalid")
        with self.assertRaisesRegex(EvidenceError, "L1_QUOTE_NOT_FOUND"):
            self.journal(fixture).blind(Request())
        resumed = Fixture()
        j = self.journal(resumed)
        with self.assertRaisesRegex(EvidenceError, "VERIFIER_FAILURE_UNCERTAIN"):
            j.blind(Request())
        self.assertEqual(resumed.calls, [])
        self.assertEqual(j.snapshot()[0]["state"], "REJECTED")

    def test_changed_payload_cannot_dispatch_same_node_and_phase(self):
        fixture = Fixture()
        j = self.journal(fixture)
        j.blind(Request())
        with self.assertRaisesRegex(EvidenceError, "TIMEOUT_UNCERTAIN_NO_RETRY"):
            j.blind(Request(text=TEXT + " Modified."))
        self.assertEqual(fixture.calls, [("blind", 130)])

    def test_context_or_budget_changed_is_rejected(self):
        self.journal()
        changed = dict(CONTEXT, protocol_sha256="c" * 64)
        with self.assertRaisesRegex(ValueError, "bound"):
            self.journal(context=changed)
        with self.assertRaisesRegex(ValueError, "bound"):
            self.journal(maximum_calls=5)
        with self.assertRaises(ValueError):
            self.journal(context=dict(CONTEXT, model_settings=dict(MODEL_PLACEHOLDERS, provider="GapGPT")))

    def test_budget_survives_process_restart(self):
        j = self.journal(maximum_calls=1)
        j.blind(Request())
        fixture = Fixture()
        resumed = self.journal(fixture, maximum_calls=1)
        with self.assertRaisesRegex(ValueError, "budget exhausted"):
            resumed.blind(Request(node_id=137))
        self.assertEqual(fixture.calls, [])

    def test_compare_requires_persisted_matching_nonabstaining_blind(self):
        fixture = Fixture()
        j = self.journal(fixture)
        with self.assertRaisesRegex(ValueError, "unavailable"):
            j.compare(Request())
        self.assertEqual(fixture.calls, [])
        j.blind(Request())
        with self.assertRaisesRegex(ValueError, "different class"):
            j.compare(Request(blind_class=5))
        self.assertEqual(fixture.calls, [("blind", 130)])
        other = self.journal(Fixture(abstain=True))
        other.blind(Request(node_id=131))
        with self.assertRaisesRegex(ValueError, "abstaining"):
            other.compare(Request(node_id=131))

    def test_corrupt_receipt_prevents_reuse(self):
        journal = self.journal()
        journal.blind(Request())
        with closing(sqlite3.connect(journal.path)) as db:
            receipt = db.execute("SELECT receipt FROM intents").fetchone()[0]
        (self.audit.root / (receipt + ".json")).write_text("tamper", encoding="utf-8")
        fresh = Fixture()
        with self.assertRaises(ValueError):
            self.journal(fresh).blind(Request())
        self.assertEqual(fresh.calls, [])

    def test_missing_audit_before_dispatch_blocks_resume(self):
        fixture = Fixture()
        j = self.journal(fixture)
        with patch.object(self.audit, "write", side_effect=ValueError("audit unavailable")):
            with self.assertRaises(ValueError):
                j.blind(Request())
        next_fixture = Fixture()
        with self.assertRaises(EvidenceError):
            self.journal(next_fixture).blind(Request())
        self.assertEqual(fixture.calls + next_fixture.calls, [])

    def test_preexisting_unbound_sqlite_is_not_reinitialized(self):
        path = self.audit.root / "fixture_journal.sqlite"
        path.touch()
        if os.name != "nt":
            os.chmod(path, 0o600)
        with self.assertRaisesRegex(ValueError, "Unbound"):
            self.journal()

    def test_insecure_existing_posix_file_is_not_silently_repaired(self):
        if os.name == "nt":
            self.skipTest("Windows uses PrivateAudit ACL inheritance")
        journal = self.journal()
        os.chmod(journal.path, 0o644)
        with self.assertRaisesRegex(ValueError, "permissions"):
            self.journal()

    def test_public_state_contains_no_text_or_training_labels(self):
        journal = self.journal()
        journal.blind(Request())
        journal.compare(Request())
        rows = journal.snapshot()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(set(row) == {"identity", "state"} for row in rows))
        self.assertNotIn(TEXT.encode("utf-8"), journal.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
