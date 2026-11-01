"""Synthetic, GT-free tests of reconstructed policies and offline verification."""
from dataclasses import FrozenInstanceError, asdict
import json
import socket
import unittest
from unittest.mock import patch

from llmgnn_sara.sara2.policy import Annotation, CLASSES, Pair, PolicyConfig, pair_from_frozen, route_r0
from llmgnn_sara.sara3.atlas import ATLAS, route_semantic, semantic_support
from llmgnn_sara.sara3.ledger import OfflineLedger
from llmgnn_sara.sara3.pipeline import BlindRequest, LexicalFixtureVerifier, offline_demo, run_offline, validate_result


def pair(node=1, b1=0, v0=0, cb=95, cv=95, text="Explicit rule induction."):
    return Pair(Annotation(node, b1, cb), Annotation(node, v0, cv), text)


class FixtureVerifier:
    offline = True

    def __init__(self, first=0, second=0, failure=None):
        self.first, self.second, self.failure = first, second, failure
        self.calls = []

    def blind(self, request):
        self.calls.append(("blind", asdict(request)))
        if self.failure:
            raise self.failure
        return {"class_index": self.first, "abstain": self.first is None,
                "evidence": [request.text] if self.first is not None else []}

    def compare(self, request):
        self.calls.append(("compare", asdict(request)))
        return {"class_index": self.second, "abstain": self.second is None,
                "evidence": [request.text] if self.second is not None else []}


class PolicyTests(unittest.TestCase):
    def test_annotation_validation(self):
        for args in ((True, 0, 50), (-1, 0, 50), (0, True, 50), (0, 7, 50),
                     (0, 0, True), (0, 0, float('nan')), (0, 0, float('inf')),
                     (0, 0, -1), (0, 0, 101)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                Annotation(*args)

    def test_pair_alignment_and_immutability(self):
        with self.assertRaises(ValueError):
            Pair(Annotation(1, 0, 90), Annotation(2, 0, 90))
        with self.assertRaises(TypeError):
            Pair({"node_id": 1}, Annotation(1, 0, 90))
        with self.assertRaises(FrozenInstanceError):
            pair().text = "changed"

    def test_explicit_reconstruction_not_policy002_claim(self):
        self.assertIn("NOT_HISTORICAL_EQUIVALENT", PolicyConfig().provenance)
        with self.assertRaises(ValueError):
            PolicyConfig(provenance="RECOVERED_EXACT")
        for value in (True, -1, 101, float('nan')):
            with self.assertRaises(ValueError):
                PolicyConfig(value)

    def test_r0_disagreement_then_confidence_then_id(self):
        rows = [pair(7), pair(4, cb=80), pair(2, b1=0, v0=1), pair(3, cb=80)]
        self.assertEqual(route_r0(rows, 4), (2, 3, 4, 7))
        self.assertEqual(route_r0(reversed(rows), 4), (2, 3, 4, 7))

    def test_equal_router_budgets_and_no_duplicates(self):
        rows = [pair(4), pair(2), pair(3)]
        for budget in (0, 1, 3, 5):
            self.assertEqual(len(route_r0(rows, budget)), min(budget, 3))
            self.assertEqual(len(route_semantic(rows, budget)), min(budget, 3))
        with self.assertRaises(ValueError):
            route_r0([pair(), pair()], 1)
        for budget in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                route_r0(rows, budget)

    def test_atlas_public_schema_and_semantic_mismatch(self):
        self.assertEqual(tuple(c.name for c in ATLAS), CLASSES)
        self.assertGreater(semantic_support("Bayesian likelihood")[6], 0)
        rows = [pair(1, text="Explicit rule induction."), pair(2, text="Bayesian likelihood.")]
        self.assertEqual(route_r0(rows, 1), (1,))
        self.assertEqual(route_semantic(rows, 1), (2,))

    def test_counterfactual_gt_extra_fields_are_never_read(self):
        class ForbiddenGroundTruth:
            def __bool__(self):
                raise AssertionError("GT accessed")
            def __int__(self):
                raise AssertionError("GT decoded")
        outputs = []
        for hidden in (ForbiddenGroundTruth(), 0, 6):
            source = {"class_index": 0, "confidence_percent_before_tensor_cast": 95,
                      "y": hidden, "fixed_y": hidden, "correct": hidden}
            candidate = pair_from_frozen(1, source, source)
            outputs.append(run_offline([candidate], 0))
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[1], outputs[2])


class VerificationTests(unittest.TestCase):
    def test_first_pass_blind_then_comparison_explicit(self):
        verifier = FixtureVerifier(0, 0)
        result = run_offline([pair()], 1, verifier=verifier)
        self.assertFalse(result["decisions"][0]["accepted"])
        self.assertEqual(result["decisions"][0]["reason"], "L2_NOT_ASSESSED")
        self.assertEqual([c[0] for c in verifier.calls], ["blind", "compare"])
        self.assertEqual(set(verifier.calls[0][1]), {"node_id", "text", "classes", "definitions", "neighborhood"})
        self.assertEqual(verifier.calls[1][1]["historical_candidates"], (0,))

    def test_third_class_is_proposal_only_not_training_label(self):
        result = run_offline([pair(b1=0, v0=1)], 1, verifier=FixtureVerifier(6, 6))
        decision = result["decisions"][0]
        self.assertIsNone(decision["third_class_proposal"])
        self.assertIsNone(decision["training_class_index"])
        self.assertFalse(decision["third_class_training_allowed"])
        self.assertEqual(result["accepted_count"], 0)

    def test_conflict_and_abstention(self):
        cases = [(FixtureVerifier(0, 1), "VERIFIER_CONFLICT"),
                 (FixtureVerifier(None, None), "BLIND_ABSTENTION"),
                 (FixtureVerifier(0, None), "COMPARISON_ABSTENTION")]
        for verifier, reason in cases:
            report = run_offline([pair()], 1, verifier=verifier)
            self.assertEqual(report["decisions"][0]["reason"], reason)
            self.assertIsNone(report["decisions"][0]["training_class_index"])

    def test_comparison_third_class_proposal_also_stays_out_of_training(self):
        report = run_offline([pair()], 1, verifier=FixtureVerifier(0, 6))
        decision = report["decisions"][0]
        self.assertEqual(decision["reason"], "VERIFIER_CONFLICT")
        self.assertIsNone(decision["third_class_proposal"])
        self.assertIsNone(decision["training_class_index"])

    def test_timeout_is_uncertain_and_never_retried(self):
        verifier = FixtureVerifier(failure=TimeoutError("do not log payload"))
        ledger = OfflineLedger()
        report = run_offline([pair()], 1, verifier=verifier, ledger=ledger)
        self.assertEqual(len(verifier.calls), 1)
        self.assertEqual(report["ledger"][0]["state"], "UNCERTAIN")
        self.assertEqual(report["decisions"][0]["reason"], "TIMEOUT_UNCERTAIN_NO_RETRY")
        again = run_offline([pair()], 1, verifier=verifier, ledger=ledger)
        self.assertEqual(len(verifier.calls), 1)
        self.assertFalse(again["decisions"][0]["accepted"])
        self.assertNotIn("do not log payload", json.dumps(report))

    def test_wrong_class_and_evidence_fail_closed(self):
        invalid = [
            {"class_index": 7, "abstain": False, "evidence": ["text"]},
            {"class_index": True, "abstain": False, "evidence": ["text"]},
            {"class_index": 0, "abstain": False, "evidence": []},
            {"class_index": 0, "abstain": False, "evidence": ["fabricated"]},
            {"class_index": 0, "abstain": True, "evidence": []},
            {"class_index": 0, "abstain": False, "evidence": ["text"], "y": 0},
        ]
        for wire in invalid:
            with self.subTest(wire=wire), self.assertRaises((ValueError, TypeError)):
                validate_result(wire, "text")
        rejected = run_offline([pair()], 1, verifier=FixtureVerifier(7, 7))
        self.assertEqual(rejected["ledger"][0]["state"], "REJECTED")
        self.assertFalse(rejected["decisions"][0]["accepted"])

    def test_missing_target_text_is_unknown_not_mock_success(self):
        report = run_offline([pair(text="")], 1, router="semantic")
        self.assertEqual(report["mock_verifier_calls"], 0)
        self.assertEqual(report["completed_review_count"], 0)
        self.assertEqual(report["semantic_evidence_available_count"], 0)
        self.assertEqual(report["decisions"][0]["reason"], "MISSING_TARGET_TEXT")

    def test_live_adapter_is_rejected_before_call(self):
        verifier = FixtureVerifier()
        verifier.offline = False
        with self.assertRaises(ValueError):
            run_offline([pair()], 1, verifier=verifier)
        self.assertEqual(verifier.calls, [])

    def test_default_and_unreviewed_fail_conservative(self):
        rows = [pair(1), pair(2, cb=50), pair(3, b1=0, v0=1)]
        report = run_offline(rows, 0)
        self.assertEqual(report["accepted_count"], 1)
        default = run_offline([pair()], 1)
        self.assertEqual(default["decisions"][0]["reason"], "BLIND_ABSTENTION")

    def test_demo_end_to_end_deterministic_no_network_no_mutation(self):
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network attempted")):
            result = offline_demo()
            self.assertEqual(result, offline_demo())
        self.assertEqual(result["accepted_count"], 1)
        self.assertEqual(result["mock_verifier_calls"], 4)
        self.assertEqual(result["provider_calls"], 0)
        self.assertEqual(result["training_runs"], 0)
        self.assertEqual(result["input_provenance"], "SYNTHETIC_DEMONSTRATION_NOT_HISTORICAL_ARTIFACT")
        self.assertIsNone(result["estimated_cost_usd"])
        rows = [pair()]
        before = repr(rows)
        run_offline(rows, 1, verifier=LexicalFixtureVerifier())
        self.assertEqual(repr(rows), before)

    def test_ledger_rejects_duplicate_and_invalid_transitions(self):
        ledger = OfflineLedger()
        ledger.begin("id", {"request": "synthetic"})
        with self.assertRaises(ValueError):
            ledger.begin("id", {"request": "different"})
        with self.assertRaises(ValueError):
            ledger.settle("id", "RETRY")
        ledger.settle("id", "UNCERTAIN")
        with self.assertRaises(ValueError):
            ledger.settle("id", "COMPLETED")


if __name__ == "__main__":
    unittest.main()
