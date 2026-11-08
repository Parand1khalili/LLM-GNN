"""Offline tests for exact, non-retrying Expanded Atlas continuation."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from llmgnn_sara.sara2.policy import Annotation, Pair
from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.evidence import EvidenceError
from llmgnn_sara.sara3.expanded_atlas_resume import ExpandedAtlasResumeVerifier
from llmgnn_sara.sara3.experiment import digest
from llmgnn_sara.sara3.gapgpt_live import (
    DurableGapGPTVerifier, VERSION, contract_from_dict)
from llmgnn_sara.sara3.inputs import canonical_bytes
from llmgnn_sara.sara3.pipeline import BlindRequest, ComparisonRequest
from llmgnn_sara.sara3.rich_evidence import RICH_VERSION

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/gapgpt_rich_v2_output4096_proposed.json"
TEXT = 'This paper discusses methods called "example" and neural learning systems.'


def response(quote):
    return {
        "schema_version": RICH_VERSION, "class_index": 1, "abstain": False,
        "primary_topic": "Neural networks",
        "supporting_evidence": [
            {"source_id": "target.text", "quote": quote,
             "claim": "Evidence copied exactly from the target paper"}],
        "counter_evidence": [], "auxiliary_method_warning": None,
        "uncertainty_reason": None,
    }


class Fixture:
    def __init__(self, bad="compare"):
        self.calls = []
        self.bad = bad

    def __call__(self, wire, key):
        payload = json.loads(json.loads(wire)["messages"][0]["content"])
        text = payload["target"]["text"]
        phase = payload["phase"]
        node = int(text.split("NODE")[1].split(" ")[0])
        self.calls.append((node, phase))
        if node == 0 and phase == self.bad:
            quote = 'This paper discusses methods called "example"'
        else:
            quote = "This paper discusses methods called"
        body = {
            "model": "gpt-6-luna",
            "choices": [{"finish_reason": "stop", "message": {
                "role": "assistant", "content": json.dumps(response(quote))}}],
            "usage": {"prompt_tokens": 200, "completion_tokens": 120,
                      "total_tokens": 320},
        }
        return 200, canonical_bytes(body)


class ExpandedAtlasResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.cfg["max_spend_usd"] = "1.00"
        self.cfg = contract_from_dict(self.cfg)
        self.rows = tuple(Pair(Annotation(i, 1, 92),
                              Annotation(i, 1, 91),
                              TEXT + f" NODE{i} additional context.",
                              ) for i in range(37))
        self.selected = list(range(37))
        self.context = {
            "version": VERSION, "gateway_contract_sha256": digest(self.cfg),
            "router": "r1_v1", "budget": 37, "cohort": "sensitivity",
            "selected": self.selected,
        }
        self.audit = PrivateAudit(
            Path(self.tmp.name) / ".local_artifacts" / "atlas" / "journal")
        self.transport = Fixture()
        self.key = "synthetic-key-only-test"

    def verifier(self, cls=DurableGapGPTVerifier):
        return cls(self.cfg, self.context, self.audit,
                   transport=self.transport, key=self.key,
                   authorized_fake=True)

    def blind(self, verifier, i):
        pair = self.rows[i]
        return verifier.blind(BlindRequest(
            pair.node_id, pair.text, neighborhood=pair.neighborhood))

    def compare(self, verifier, i, blind):
        pair = self.rows[i]
        return verifier.compare(ComparisonRequest(
            pair.node_id, pair.text, (1,), blind["class_index"],
            neighborhood=pair.neighborhood))

    def test_rejected_comparison_stays_rejected_and_independent_nodes_continue(self):
        initial = self.verifier()
        first = self.blind(initial, 0)
        with self.assertRaisesRegex(EvidenceError, "L1_QUOTE_NOT_FOUND"):
            self.compare(initial, 0, first)
        self.assertEqual(initial.phase_states()[(0, "compare")], "REJECTED")
        self.assertEqual(len(self.transport.calls), 2)

        resume = self.verifier(ExpandedAtlasResumeVerifier)
        self.assertTrue(resume.halted)
        resume.verify_saved_batch(self.rows, self.selected)
        self.assertFalse(resume.halted)
        saved = self.blind(resume, 0)
        with self.assertRaisesRegex(EvidenceError, "L1_QUOTE_NOT_FOUND"):
            self.compare(resume, 0, saved)
        other = self.blind(resume, 1)
        self.compare(resume, 1, other)
        self.assertEqual(len(self.transport.calls), 4)
        self.assertEqual(resume.phase_states()[(0, "compare")], "REJECTED")
        again = self.verifier(ExpandedAtlasResumeVerifier)
        again.verify_saved_batch(self.rows, self.selected)
        self.blind(again, 1)
        self.assertEqual(len(self.transport.calls), 4)

    def test_uncertain_or_wrong_dependency_fails_before_dispatch(self):
        def timeout(wire, key):
            raise TimeoutError("Synthetic timeout; no network")
        self.transport = timeout
        first = self.verifier()
        with self.assertRaises(TimeoutError):
            self.blind(first, 0)
        verify = self.verifier(ExpandedAtlasResumeVerifier)
        with self.assertRaises(ValueError):
            verify.verify_saved_batch(self.rows, self.selected)

    def test_corrupt_dependency_rejected_without_reissue(self):
        first = self.verifier()
        self.blind(first, 0)
        with self.assertRaises(EvidenceError):
            self.compare(first, 0, self.blind(first, 0))
        with closing(sqlite3.connect(self.audit.root / "fixture_journal.sqlite")) as db:
            with db:
                db.execute("UPDATE intents SET dependency=? WHERE phase='compare'",
                           ("tampered-dependency",))
        verify = self.verifier(ExpandedAtlasResumeVerifier)
        with self.assertRaises(ValueError):
            verify.verify_saved_batch(self.rows, self.selected)
        self.assertEqual(len(self.transport.calls), 2)

    def test_unrelated_rejection_is_not_resumable(self):
        self.transport = Fixture(bad="blind")
        verifier = self.verifier()
        with self.assertRaises(EvidenceError):
            self.blind(verifier, 0)
        resume = self.verifier(ExpandedAtlasResumeVerifier)
        with self.assertRaises((EvidenceError, ValueError)):
            resume.verify_saved_batch(self.rows, self.selected)

if __name__ == "__main__":
    unittest.main()
