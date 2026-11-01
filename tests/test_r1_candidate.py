"""Behavioral tests, not semantic accuracy tests; no human review access."""
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path
import hashlib
import os
import socket
import unittest
from unittest.mock import patch

from llmgnn_sara.sara2.policy import Annotation, Pair, pair_from_frozen
from llmgnn_sara.sara3.atlas import ATLAS
from llmgnn_sara.sara3.r1_candidate import VERSION, risk_terms, route_r1_candidate
from llmgnn_sara.io.project import load_project_inputs, PINS
from llmgnn_sara.evaluation.router_comparison import compare_routers

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / ".local_artifacts/frozen"
AUTHENTIC = ROOT / ".local_artifacts/authentic"


def pair(node=1, a=0, b=0, text="rule", confidence=95):
    return Pair(Annotation(node, a, confidence), Annotation(node, b, confidence), text)


class CandidateTests(unittest.TestCase):
    def test_interpretation_and_equal_weights(self):
        self.assertEqual(risk_terms(pair())["score"], 0)
        mismatch = risk_terms(pair(text="bayesian"))
        self.assertEqual(mismatch["candidate_mismatch"], 1)
        self.assertEqual(mismatch["score"], Fraction(1, 3))
        tie = risk_terms(pair(text="rule neural"))
        self.assertEqual(tie["lexical_ambiguity"], 1)
        self.assertEqual(tie["score"], Fraction(1, 3))
        mixed = risk_terms(pair(b=1))
        self.assertEqual(mixed["disagreement"], 1)
        self.assertEqual(mixed["candidate_mismatch"], Fraction(1, 2))
        self.assertEqual(mixed["score"], Fraction(1, 2))

    def test_missing_is_explicit_maximal_uncertainty(self):
        for text in ("", "opaque subject", "123"):
            terms = risk_terms(pair(text=text))
            self.assertEqual(terms["evidence_status"], "NO_ATLAS_KEYWORD_MATCH")
            self.assertEqual(terms["score"], Fraction(2, 3))
        self.assertEqual(risk_terms(pair(b=1, text=""))["score"], 1)

    def test_range_and_class_index_alignment(self):
        for index, entry in enumerate(ATLAS):
            text = " ".join(entry.keywords)
            self.assertEqual(risk_terms(pair(a=index, b=index, text=text))["score"], 0)
            for a in range(7):
                for b in range(7):
                    terms = risk_terms(pair(a=a, b=b, text=text))
                    self.assertTrue(all(0 <= terms[k] <= 1 for k in
                        ("score", "disagreement", "candidate_mismatch", "lexical_ambiguity")))

    def test_reordered_atlas_rejected(self):
        with patch("llmgnn_sara.sara3.r1_candidate.ATLAS", tuple(reversed(ATLAS))):
            with self.assertRaises(ValueError):
                risk_terms(pair())

    def test_fixed_budget_exact_ties_and_order_independence(self):
        rows = [pair(i) for i in range(50)]
        self.assertEqual(route_r1_candidate(rows), tuple(range(37)))
        self.assertEqual(route_r1_candidate(reversed(rows)), tuple(range(37)))
        with self.assertRaises(ValueError):
            route_r1_candidate(rows[:36])
        with self.assertRaises(ValueError):
            route_r1_candidate(rows + [rows[0]])

    def test_arm_symmetry_confidence_not_used_and_repeat_tokens(self):
        first = risk_terms(pair(a=0, b=1, text="rule neural neural"))
        self.assertEqual(first, risk_terms(pair(a=1, b=0, text="RULE neural", confidence=0)))

    def test_gt_mapping_rejected_and_counterfactual_adapter_isolation(self):
        with self.assertRaises(TypeError):
            risk_terms({"gt": 0})
        class Forbidden:
            def __bool__(self):
                raise AssertionError("GT accessed")
        source = {"class_index": 0, "confidence_percent_before_tensor_cast": 95,
                  "y": Forbidden(), "correctness": Forbidden()}
        expected = risk_terms(pair())
        self.assertEqual(risk_terms(pair_from_frozen(1, source, source, "rule")), expected)


@unittest.skipUnless((FROZEN / "b1_final_predictions.json").is_file()
                     and (AUTHENTIC / "b1_prompts.json").is_file(), "Authentic inputs unavailable")
class AuthenticRouterTests(unittest.TestCase):
    def test_authentic_determinism_provenance_immutability_and_read_boundary(self):
        allowed = {FROZEN / name for name in ("b1_final_predictions.json",
            "narrative_v0_final_predictions.json", "selection_manifest.json", "preparation_receipt.json")}
        allowed.update(AUTHENTIC / name for name in PINS)
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in allowed}
        original_open = os.open
        def guarded_open(path, *args, **kwargs):
            self.assertIn(Path(path).resolve(), allowed)
            return original_open(path, *args, **kwargs)
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")), \
             patch.object(os, "open", side_effect=guarded_open):
            inputs = load_project_inputs(FROZEN, AUTHENTIC)
            snapshot = tuple(asdict(p) for p in inputs.pairs)
            report = compare_routers(inputs)
            self.assertEqual(report, compare_routers(inputs))
            self.assertEqual(snapshot, tuple(asdict(p) for p in inputs.pairs))
        self.assertEqual(report["cohort_size"], 140)
        self.assertEqual(len(report["source_hashes"]), 9)
        self.assertEqual(len(report["r1_terms_by_node"]), 140)
        self.assertEqual(report["provider_calls"], 0)
        self.assertFalse(report["ground_truth_accessed"])
        for router in report["routers"].values():
            self.assertEqual(router["count"], 37)
            self.assertEqual(len(set(router["selected_node_ids_ranked"])), 37)
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in allowed})
        self.assertIn(VERSION, report["routers"])


if __name__ == "__main__":
    unittest.main()
