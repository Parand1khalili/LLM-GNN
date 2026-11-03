"""Real offline pipeline tests with synthetic evidence; never a semantic oracle."""
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llmgnn_sara.sara2.policy import Annotation, Pair
from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.automated_policy import VERSION
from llmgnn_sara.sara3.pipeline import run_offline
from llmgnn_sara.sara3.rich_evidence import RICH_PROMPT_V2, RICH_VERSION

TEXT = ("Bayesian inference uses Gaussian process priors and posterior inference. "
        "Artificial neural networks are auxiliary to the Bayesian model. "
        "Copyright notice covers this scientific journal.")
QUOTE = "Bayesian inference uses Gaussian process priors"
COUNTER = "Artificial neural networks are auxiliary to the Bayesian model"

class Verifier:
    offline = True

    def __init__(self, *, blind=6, compare=6, flagged=None, counter=False, invalid_phase=None, quote=QUOTE):
        self.calls = []
        self.blind_class = blind
        self.compare_class = compare
        self.flagged = flagged
        self.counter = counter
        self.invalid_phase = invalid_phase
        self.quote = quote

    def _response(self, label, phase):
        if label is None:
            return {"schema_version": RICH_VERSION, "class_index": None,
                    "abstain": True, "primary_topic": None,
                    "supporting_evidence": [], "counter_evidence": [],
                    "auxiliary_method_warning": None,
                    "uncertainty_reason": "Not enough evidence"}
        quote = "Invented unsupported phrase" if self.invalid_phase == phase else self.quote
        return {"schema_version": RICH_VERSION, "class_index": label,
                "abstain": False, "primary_topic": "Bayesian inference",
                "supporting_evidence": [{"source_id": "target.text", "quote": quote,
                    "claim": "Unreviewed automatic proposal"}],
                "counter_evidence": ([{"source_id": "target.text", "quote": COUNTER,
                    "claim": "Potential conflicting secondary emphasis"}] if self.counter else []),
                "auxiliary_method_warning": (self.flagged if self.flagged == "Auxiliary technique is incidental" else None),
                "uncertainty_reason": (self.flagged if self.flagged == "Ambiguous primary topic" else None)}

    def blind(self, request):
        self.calls.append(("blind", request.node_id))
        return self._response(self.blind_class, "blind")

    def compare(self, request):
        self.calls.append(("compare", request.node_id))
        return self._response(self.compare_class, "compare")

class AutomaticArbitrationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.target = Pair(Annotation(130, 5, 91), Annotation(130, 6, 83), TEXT)

    def execute(self, verifier, pairs=None, budget=1, **kwargs):
        with tempfile.TemporaryDirectory() as temp:
            audit = PrivateAudit(Path(temp) / "audit")
            with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
                report = run_offline(pairs if pairs is not None else (self.target,), budget,
                    verifier=verifier, audit=audit, response_version=RICH_VERSION,
                    prompt_version=RICH_PROMPT_V2,
                    automated_arbitration_version=VERSION, **kwargs)
                receipts = list(audit.root.glob("*.json"))
        return report, receipts

    def test_positive_accepts_only_existing_candidate_and_is_not_semantic_l2(self):
        fixture = Verifier()
        report, receipts = self.execute(fixture)
        self.assertEqual(fixture.calls, [("blind", 130), ("compare", 130)])
        d = report["decisions"][0]
        self.assertEqual((d["decision"], d["training_class_index"], d["label_source"]),
                         ("ACCEPT", 6, "NARRATIVE_V0_CANDIDATE"))
        self.assertEqual((d["b1_class_index"], d["narrative_v0_class_index"],
                          d["blind_class_index"], d["comparison_class_index"]), (5, 6, 6, 6))
        self.assertEqual((d["l1_status"], d["l2_status"], d["semantic_validation"]),
                         ("PASS", "NOT_ASSESSED", "NOT_PERFORMED"))
        self.assertTrue(d["verification_completed"])
        self.assertEqual(report["accepted_count"], 1)
        self.assertEqual(len(report["provisional_pseudo_labels"]), 1)
        self.assertEqual(report["label_status"], "PROVISIONAL_UNVALIDATED_NOT_GCN_AUTHORIZED")
        self.assertTrue(len(receipts) >= 3)
        self.assertEqual((report["provider_calls"], report["training_runs"], report["GT_accessed"]),
                         (0, 0, False))

    def test_real_but_unrelated_notice_with_explicit_warning_is_not_accepted(self):
        fixture = Verifier(quote="Copyright notice covers this scientific journal.",
                           flagged="Auxiliary technique is incidental")
        report, _ = self.execute(fixture)
        self.assertEqual(report["decisions"][0]["l1_status"], "PASS")
        self.assertEqual(report["decisions"][0]["automated_screen_reason"], "AUXILIARY_METHOD_WARNING")
        self.assertEqual(report["accepted_count"], 0)

    def test_counter_evidence_blocks_automatic_acceptance(self):
        report, _ = self.execute(Verifier(counter=True))
        self.assertEqual(report["decisions"][0]["automated_screen_reason"], "COUNTER_EVIDENCE_UNRESOLVED")
        self.assertEqual(report["accepted_count"], 0)

    def test_uncertainty_blocks_automatic_acceptance(self):
        report, _ = self.execute(Verifier(flagged="Ambiguous primary topic"))
        self.assertEqual(report["decisions"][0]["automated_screen_reason"], "EXPLICIT_UNCERTAINTY")
        self.assertEqual(report["accepted_count"], 0)

    def test_third_class_never_enters_training(self):
        report, _ = self.execute(Verifier(blind=1, compare=1))
        d = report["decisions"][0]
        self.assertEqual((d["decision"], d["third_class_proposal"]), ("REJECT", 1))
        self.assertIsNone(d["training_class_index"])
        self.assertEqual(report["accepted_count"], 0)

    def test_blind_comparison_disagreement_rejected(self):
        report, _ = self.execute(Verifier(blind=6, compare=5))
        self.assertEqual(report["decisions"][0]["automated_screen_reason"], "BLIND_COMPARISON_CONFLICT")
        self.assertEqual(report["accepted_count"], 0)

    def test_l1_bad_blind_cannot_dispatch_comparison(self):
        fixture = Verifier(invalid_phase="blind")
        report, _ = self.execute(fixture)
        self.assertEqual(fixture.calls, [("blind", 130)])
        self.assertEqual(report["decisions"][0]["l1_status"], "FAIL")
        self.assertEqual(report["accepted_count"], 0)

    def test_l1_bad_comparison_cannot_be_accepted(self):
        report, _ = self.execute(Verifier(invalid_phase="compare"))
        self.assertEqual(report["decisions"][0]["l1_status"], "FAIL")
        self.assertEqual(report["accepted_count"], 0)

    def test_abstaining_blind_never_compares(self):
        verifier = Verifier(blind=None)
        report, _ = self.execute(verifier)
        self.assertEqual(verifier.calls, [("blind", 130)])
        self.assertEqual(report["decisions"][0]["reason"], "BLIND_ABSTENTION")

    def test_unrouted_baseline_keeps_declared_reconstructed_policy(self):
        other = Pair(Annotation(682, 6, 90), Annotation(682, 6, 90), TEXT)
        report, _ = self.execute(Verifier(), pairs=(self.target, other))
        chosen = {d["node_id"]: d for d in report["decisions"]}
        self.assertEqual(chosen[682]["label_source"], "FROZEN_AGREEMENT_RECONSTRUCTED_80")
        self.assertFalse(chosen[682]["routed_for_review"])
        self.assertEqual(chosen[682]["l1_status"], "NOT_APPLICABLE")

    def test_opt_in_is_versioned_and_gate_remains_available(self):
        for extras in ({"precomparison_l2_gate": True},
                       {"automated_arbitration_version": "invalid"}):
            fixture = Verifier()
            with tempfile.TemporaryDirectory() as temp:
                with self.assertRaises(ValueError):
                    run_offline((self.target,), 1, verifier=fixture,
                        audit=PrivateAudit(Path(temp) / "audit"),
                        response_version=RICH_VERSION, prompt_version=RICH_PROMPT_V2,
                        **({"automated_arbitration_version": VERSION, **extras}))
            self.assertEqual(fixture.calls, [])

if __name__ == "__main__":
    unittest.main()
