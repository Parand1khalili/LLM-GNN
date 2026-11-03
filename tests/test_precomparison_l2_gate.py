"""Prospective L2 checkpoint: complete Blind L1 before any Comparison.

These are synthetic offline fixtures, not human semantic assessments or GCN labels.
"""
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llmgnn_sara.sara2.policy import Annotation, Pair
from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.pipeline import run_offline
from llmgnn_sara.sara3.rich_evidence import RICH_VERSION, RICH_PROMPT_V2

TEXT = "Bayesian inference uses Gaussian process priors and posterior inference."
QUOTE = "Bayesian inference uses Gaussian process priors"


class Verifier:
    offline = True

    def __init__(self, *, class_index=6, abstain=False, wrong_quote=False):
        self.calls = []
        self.class_index, self.abstain, self.wrong_quote = class_index, abstain, wrong_quote

    def blind(self, request):
        self.calls.append(("blind", request.node_id))
        return self._response()

    def compare(self, request):
        self.calls.append(("compare", request.node_id))
        return self._response()

    def _response(self):
        if self.abstain:
            return {"schema_version": RICH_VERSION, "class_index": None,
                    "abstain": True, "primary_topic": None,
                    "supporting_evidence": [], "counter_evidence": [],
                    "auxiliary_method_warning": None,
                    "uncertainty_reason": "Insufficient direct topical evidence"}
        return {"schema_version": RICH_VERSION, "class_index": self.class_index,
                "abstain": False, "primary_topic": "Bayesian inference",
                "supporting_evidence": [{"source_id": "target.text",
                    "quote": "A fabricated statement" if self.wrong_quote else QUOTE,
                    "claim": "Synthetic, not a human validation"}],
                "counter_evidence": [], "auxiliary_method_warning": None,
                "uncertainty_reason": None}


class L2PrecomparisonGateTests(unittest.TestCase):
    def setUp(self):
        self.pairs = (Pair(Annotation(130, 6, 91), Annotation(130, 5, 83), TEXT),)

    def run_fixture(self, verifier, *, gate=True):
        with tempfile.TemporaryDirectory() as temp:
            audit = PrivateAudit(Path(temp) / "audit")
            with patch.object(socket.socket, "connect",
                              side_effect=AssertionError("Network forbidden")):
                return run_offline(self.pairs, 1, verifier=verifier, audit=audit,
                    response_version=RICH_VERSION, prompt_version=RICH_PROMPT_V2,
                    precomparison_l2_gate=gate)

    def test_valid_blind_is_queued_and_no_compare_or_label_promotion(self):
        verifier = Verifier()
        report = self.run_fixture(verifier)
        self.assertEqual(verifier.calls, [("blind", 130)])
        self.assertEqual(report["l2_pending_node_ids"], [130])
        self.assertEqual(report["precomparison_l2_gate"], "STOP_AFTER_BLIND_L1_FOR_HUMAN_REVIEW")
        self.assertEqual(report["mock_verifier_calls"], 1)
        self.assertEqual([x["payload"]["phase"] for x in report["verifier_inputs"]], ["blind"])
        self.assertNotIn("historical_candidates", report["verifier_inputs"][0]["payload"])
        self.assertEqual([x["state"] for x in report["ledger"]], ["COMPLETED"])
        decision = report["decisions"][0]
        self.assertEqual((decision["reason"], decision["l2_status"]),
                         ("L2_PENDING_BEFORE_COMPARISON", "NOT_ASSESSED"))
        self.assertFalse(decision["accepted"])
        self.assertIsNone(decision["training_class_index"])
        self.assertFalse(decision["verification_completed"])
        self.assertEqual((report["provider_calls"], report["training_runs"], report["GT_accessed"]),
                         (0, 0, False))

    def test_abstain_does_not_enter_l2_or_comparison(self):
        verifier = Verifier(abstain=True)
        report = self.run_fixture(verifier)
        self.assertEqual(verifier.calls, [("blind", 130)])
        self.assertEqual(report["l2_pending_node_ids"], [])
        self.assertEqual(report["decisions"][0]["reason"], "BLIND_ABSTENTION")
        self.assertEqual(report["accepted_count"], 0)

    def test_fabricated_quote_is_not_reviewable_and_no_comparison(self):
        verifier = Verifier(wrong_quote=True)
        report = self.run_fixture(verifier)
        self.assertEqual(verifier.calls, [("blind", 130)])
        self.assertEqual(report["l2_pending_node_ids"], [])
        self.assertEqual(report["decisions"][0]["reason"], "L1_QUOTE_NOT_FOUND")
        self.assertIsNone(report["decisions"][0]["accepted_label"])

    def test_third_class_proposal_is_audit_only_even_with_valid_quote(self):
        verifier = Verifier(class_index=0)
        report = self.run_fixture(verifier)
        self.assertEqual(verifier.calls, [("blind", 130)])
        self.assertEqual(report["l2_pending_node_ids"], [130])
        self.assertEqual(report["decisions"][0]["reason"], "L2_PENDING_BEFORE_COMPARISON")
        self.assertEqual(report["accepted_count"], 0)

    def test_gate_needs_explicit_rich_v2_and_boolean_flag(self):
        for kwargs, error in (
            ({"precomparison_l2_gate": True}, ValueError),
            ({"response_version": RICH_VERSION, "precomparison_l2_gate": True}, ValueError),
            ({"response_version": RICH_VERSION, "prompt_version": RICH_PROMPT_V2,
              "precomparison_l2_gate": 1}, TypeError),
        ):
            verifier = Verifier()
            with self.subTest(kwargs=kwargs), self.assertRaises(error):
                run_offline(self.pairs, 1, verifier=verifier, **kwargs)
            self.assertEqual(verifier.calls, [])

    def test_ungated_contract_still_runs_comparison(self):
        verifier = Verifier()
        report = self.run_fixture(verifier, gate=False)
        self.assertEqual(verifier.calls, [("blind", 130), ("compare", 130)])
        self.assertNotIn("l2_pending_node_ids", report)
        self.assertNotIn("precomparison_l2_gate", report)
        self.assertEqual(report["decisions"][0]["reason"], "L2_NOT_ASSESSED")


if __name__ == "__main__":
    unittest.main()
