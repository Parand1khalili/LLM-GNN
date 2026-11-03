"""Prospective rich-v2 prompt contract tests; no API, GT or training."""
import json
import unittest

from llmgnn_sara.sara3.rich_evidence import (
    RICH_PROMPT_V2, RICH_VERSION, rich_verifier_input,
    rich_verifier_input_v2, target_source, validate_rich_result,
)
from llmgnn_sara.sara3.evidence import EvidenceError
from llmgnn_sara.sara3.inputs import canonical_bytes, verifier_input

TEXT = "Bayesian inference uses Gaussian process priors and posterior inference."
QUOTE = "Bayesian inference uses Gaussian process priors"


class RichPromptV2Tests(unittest.TestCase):
    def test_blind_is_versioned_and_prior_blind(self):
        payload = rich_verifier_input_v2(130, TEXT)
        self.assertEqual((payload["phase"], payload["prompt_version"]),
                         ("blind", RICH_PROMPT_V2))
        self.assertEqual(payload["response_contract"], RICH_VERSION)
        self.assertNotIn("historical_candidates", payload)
        self.assertNotIn("blind_class_index", payload)
        self.assertNotIn("Comparison phase only", payload["instructions"])
        self.assertIn("EVERY supporting_evidence and counter_evidence", payload["instructions"])
        for phrase in ("target.text", "capitalization", "punctuation",
                       "whitespace", "change case", "abstain"):
            self.assertIn(phrase, payload["instructions"])

    def test_comparison_must_compare_actual_candidates(self):
        payload = rich_verifier_input_v2(1243, TEXT, candidates=(5, 6), blind_class=5)
        self.assertEqual(payload["phase"], "compare")
        self.assertEqual(payload["historical_candidates"], [5, 6])
        self.assertEqual(payload["blind_class_index"], 5)
        self.assertIn("Comparison phase only", payload["instructions"])
        self.assertIn("historical_candidates", payload["instructions"])
        self.assertIn("cannot directly become a training label", payload["instructions"])

    def test_v1_and_legacy_request_bytes_remain_unchanged(self):
        old_legacy = canonical_bytes(verifier_input(130, TEXT))
        old_rich_v1 = canonical_bytes(rich_verifier_input(130, TEXT))
        rich_verifier_input_v2(130, TEXT)
        rich_verifier_input_v2(130, TEXT, candidates=(5, 6), blind_class=5)
        self.assertEqual(canonical_bytes(verifier_input(130, TEXT)), old_legacy)
        self.assertEqual(canonical_bytes(rich_verifier_input(130, TEXT)), old_rich_v1)
        self.assertNotIn("prompt_version", rich_verifier_input(130, TEXT))

    def test_comparison_requires_valid_candidates_and_blind_class(self):
        for kwargs in ({"candidates": (5, 8), "blind_class": 5},
                       {"candidates": (5, 6), "blind_class": None}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                rich_verifier_input_v2(1243, TEXT, **kwargs)

    def test_source_and_schema_provenance_unchanged(self):
        previous = rich_verifier_input(130, TEXT)
        versioned = rich_verifier_input_v2(130, TEXT)
        for field in ("target", "neighborhood", "class_atlas", "response_schema",
                      "approved_source_ids", "response_contract"):
            self.assertEqual(previous[field], versioned[field])
        self.assertNotIn("historical_candidates", versioned)

    def test_l1_stays_case_sensitive_and_not_semantic_judge(self):
        valid = {
            "schema_version": RICH_VERSION, "class_index": 6, "abstain": False,
            "primary_topic": "Bayesian probabilistic reasoning",
            "supporting_evidence": [{"source_id": "target.text", "quote": QUOTE,
                                      "claim": "Unreviewed diagnostic interpretation"}],
            "counter_evidence": [], "auxiliary_method_warning": None,
            "uncertainty_reason": None,
        }
        result = validate_rich_result(valid, (target_source(TEXT),))
        self.assertEqual((result["l1_status"], result["l2_status"]),
                         ("PASS", "NOT_ASSESSED"))
        bad = json.loads(json.dumps(valid))
        bad["supporting_evidence"][0]["quote"] = QUOTE[0].lower() + QUOTE[1:]
        with self.assertRaisesRegex(EvidenceError, "L1_QUOTE_NOT_FOUND"):
            validate_rich_result(bad, (target_source(TEXT),))


if __name__ == "__main__":
    unittest.main()
