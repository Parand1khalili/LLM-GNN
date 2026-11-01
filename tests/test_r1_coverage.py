"""Coverage policy semantics and authentic offline checks, not accuracy tests."""
from dataclasses import asdict
from fractions import Fraction
import hashlib
import io
import os
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

from llmgnn_sara.sara2.policy import Annotation, Pair, pair_from_frozen
from llmgnn_sara.sara3.r1_candidate import risk_terms, route_r1_candidate
from llmgnn_sara.sara3.r1_coverage import (ORIGINAL, NEUTRAL, VERSION, POLICIES,
    coverage_terms, policy_score, rank_policy, route_r1_candidate_v2)
from llmgnn_sara.io.project import load_project_inputs, PINS
from llmgnn_sara.evaluation.r1_coverage import compare_coverage, settings

ROOT = Path(__file__).resolve().parents[1]
FROZEN, AUTHENTIC = ROOT / ".local_artifacts/frozen", ROOT / ".local_artifacts/authentic"


def pair(node=1, text="rule", a=0, b=0):
    return Pair(Annotation(node, a, 95), Annotation(node, b, 95), text)


class CoverageTests(unittest.TestCase):
    def test_missing_is_unobserved_not_mismatch(self):
        for text in ("", "uncovered topic", "123"):
            p = pair(text=text)
            terms = coverage_terms(p)
            self.assertEqual(terms["status"], "NO_ATLAS_MATCH")
            self.assertIsNone(terms["observed_mismatch"])
            self.assertIsNone(terms["observed_ambiguity"])
            self.assertEqual(terms["coverage"], 0)
            self.assertEqual([policy_score(p, v) for v in POLICIES],
                             [Fraction(2, 3), Fraction(1, 3), Fraction(0)])

    def test_missing_disagreement_remains_observed_risk(self):
        p = pair(text="", b=1)
        self.assertEqual([policy_score(p, v) for v in POLICIES],
                         [Fraction(1), Fraction(2, 3), Fraction(1, 3)])

    def test_partial_and_multi_keywords_not_semantic_judgments(self):
        partial = coverage_terms(pair(text="rule neural"))
        multi = coverage_terms(pair(text="rule rules"))
        self.assertEqual(partial["status"], "PARTIAL_COVERAGE")
        self.assertEqual(partial["coverage"], Fraction(1, 4))
        self.assertEqual(multi["status"], "OBSERVED_MULTI_KEYWORD_MATCH")
        self.assertEqual(multi["coverage"], Fraction(1, 2))
        self.assertEqual(coverage_terms(pair(text="RULE rule RULE"))["coverage"], Fraction(1, 4))
        self.assertNotIn("semantic_approval", multi)

    def test_observed_scores_equal_original_and_arm_symmetric(self):
        for text in ("rule neural", "bayesian likelihood", "rule rules neural network"):
            p = pair(text=text, b=1)
            for version in POLICIES:
                self.assertEqual(policy_score(p, version), risk_terms(p)["score"])
                self.assertEqual(policy_score(p, version), policy_score(pair(text=text, a=1), version))

    def test_length_alone_does_not_change_coverage_or_risk(self):
        short = pair(text="rule neural")
        long = pair(text="rule neural " + "uncovered " * 1000)
        self.assertEqual(coverage_terms(short), coverage_terms(long))
        for version in POLICIES:
            self.assertEqual(policy_score(short, version), policy_score(long, version))

    def test_class_order_guard_is_reused(self):
        from llmgnn_sara.sara3.atlas import ATLAS
        with patch("llmgnn_sara.sara3.r1_candidate.ATLAS", tuple(reversed(ATLAS))):
            with self.assertRaises(ValueError):
                coverage_terms(pair())

    def test_two_dimensional_ties_and_id_order(self):
        rows = [pair(i, "" if i < 5 else "rule") for i in range(40)]
        selected = route_r1_candidate_v2(rows)
        self.assertEqual(selected, tuple(range(5, 40)) + (0, 1))
        self.assertEqual(selected, route_r1_candidate_v2(reversed(rows)))
        self.assertEqual(rank_policy(rows, VERSION, coverage_order="none")[:37], tuple(range(37)))
        self.assertEqual(rank_policy(rows, VERSION, coverage_order="low")[:37], tuple(range(37)))

    def test_coverage_never_overrides_greater_observed_risk(self):
        rows = [pair(i, "rule rules induction logic") for i in range(40)]
        rows.append(pair(100, "", b=1))
        self.assertEqual(route_r1_candidate_v2(rows)[0], 100)

    def test_v1_exact_preservation_and_fixed_budget(self):
        rows = [pair(i, ("rule", "", "bayesian")[i % 3], b=i % 2) for i in range(50)]
        self.assertEqual(rank_policy(rows, ORIGINAL)[:37], route_r1_candidate(rows))
        for policy in POLICIES:
            self.assertEqual(len(set(rank_policy(rows, policy)[:37])), 37)
        for rows in ([pair()] * 37, [pair(i) for i in range(36)]):
            with self.assertRaises(ValueError):
                route_r1_candidate_v2(rows)

    def test_prespecified_sensitivity_and_validation(self):
        self.assertEqual(len(settings()), 13)
        p = pair(text="", b=1)
        self.assertEqual(policy_score(p, VERSION, disagreement_weight=Fraction(2)), Fraction(1, 2))
        for options in ({"disagreement_weight": 1.0}, {"disagreement_weight": Fraction(3)},
                        {"neutral_missing": Fraction(0)}, {"neutral_missing": Fraction(1, 4)}):
            with self.assertRaises(ValueError):
                policy_score(p, VERSION, **options)
        with self.assertRaises(ValueError):
            policy_score(p, "unknown")
        with self.assertRaises(ValueError):
            rank_policy([pair(i) for i in range(40)], ORIGINAL, coverage_order="low")

    def test_gt_free_typed_input_and_counterfactual_unread_fields(self):
        class Forbidden:
            def __bool__(self):
                raise AssertionError("GT access")
        source = {"class_index": 0, "confidence_percent_before_tensor_cast": 95,
                  "y": Forbidden(), "correctness": Forbidden()}
        p = pair_from_frozen(1, source, source, "rule")
        self.assertEqual(coverage_terms(p), coverage_terms(pair()))
        with self.assertRaises(TypeError):
            coverage_terms({"gt": 0})


@unittest.skipUnless((AUTHENTIC / "b1_prompts.json").is_file() and
    (FROZEN / "b1_final_predictions.json").is_file(), "Authentic inputs unavailable")
class AuthenticCoverageTests(unittest.TestCase):
    def test_report_reproducibility_read_boundary_and_immutability(self):
        allowed = {FROZEN / n for n in ("b1_final_predictions.json", "narrative_v0_final_predictions.json",
                                       "selection_manifest.json", "preparation_receipt.json")}
        allowed.update(AUTHENTIC / n for n in PINS)
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in allowed}
        allowed.add(ROOT / "docs/R1_COVERAGE_POLICY.md")
        os_open, io_open = os.open, io.open
        def guarded_os(path, *args, **kwargs):
            self.assertIn(Path(path).resolve(), allowed)
            return os_open(path, *args, **kwargs)
        def guarded_io(path, *args, **kwargs):
            if type(path) is not int:  # os.fdopen reuses an already allowlisted descriptor.
                self.assertIn(Path(path).resolve(), allowed)
            return io_open(path, *args, **kwargs)
        with patch.object(os, "open", side_effect=guarded_os), patch.object(io, "open", side_effect=guarded_io), \
             patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            inputs = load_project_inputs(FROZEN, AUTHENTIC)
            snapshot = tuple(asdict(p) for p in inputs.pairs)
            report = compare_coverage(inputs)
            self.assertEqual(report, compare_coverage(inputs))
            self.assertEqual(snapshot, tuple(asdict(p) for p in inputs.pairs))
        self.assertEqual(report["cohort_size"], 140)
        self.assertEqual(len(report["source_hashes"]), 9)
        self.assertEqual(len(report["pairwise_overlaps"]), 78)
        self.assertEqual(sum(g["count"] for g in report["coverage_groups"].values()), 140)
        self.assertEqual(sum(g["count"] for g in report["length_bins"].values()), 140)
        for result in report["policies_and_sensitivity"].values():
            self.assertEqual(len(set(result["selected_node_ids_ranked"])), 37)
            self.assertLessEqual(result["score_selected"]["max"], 1)
            self.assertLessEqual(len(result["cutoff_score_tied_selected"]), len(result["cutoff_score_tied_ids_ranked"]))
        self.assertFalse(report["ground_truth_accessed"])
        self.assertFalse(report["human_review_accessed"])
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before})


if __name__ == "__main__":
    unittest.main()
