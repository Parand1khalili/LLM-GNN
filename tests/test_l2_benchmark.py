"""Benchmark structure/provenance tests, not tests of semantic-judgment accuracy."""
import copy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from llmgnn_sara.io.frozen import InputError, read_pinned_json
from llmgnn_sara.io.project import load_project_inputs
from llmgnn_sara.evaluation.l2_benchmark import (BENCHMARK_SHA256, OUTCOMES, materialize_case,
                                               validate_benchmark, validate_records)

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "configs/l2_development_benchmark.json"
FROZEN, AUTHENTIC = ROOT / ".local_artifacts/frozen", ROOT / ".local_artifacts/authentic"


class PinnedBenchmarkTests(unittest.TestCase):
    def test_pinned_development_scope_no_gold(self):
        obj = read_pinned_json(PATH, BENCHMARK_SHA256)
        self.assertEqual(len(obj["cases"]), 6)
        self.assertFalse(obj["future_holdout_eligible"])
        self.assertEqual(obj["training_use"], "FORBIDDEN")
        self.assertEqual({c["review"]["overall"]["outcome"] for c in obj["cases"]}, OUTCOMES)

    def test_unpinned_edit_rejected(self):
        with tempfile.TemporaryDirectory() as base:
            path = Path(base)/"changed.json"
            path.write_bytes(PATH.read_bytes()+b" ")
            with self.assertRaisesRegex(InputError, "SHA-256 mismatch"):
                read_pinned_json(path, BENCHMARK_SHA256)


@unittest.skipUnless((AUTHENTIC/"b1_prompts.json").is_file(), "External authentic input not supplied")
class BenchmarkRecordsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.obj = read_pinned_json(PATH, BENCHMARK_SHA256)
        cls.texts = {p.node_id: p.text for p in load_project_inputs(FROZEN, AUTHENTIC).pairs}

    def changed_case(self):
        obj = copy.deepcopy(self.obj)
        return obj, obj["cases"][0]

    def test_real_text_provenance_and_outcomes_no_network(self):
        before = copy.deepcopy(self.obj)
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            result = validate_benchmark(PATH, FROZEN, AUTHENTIC)
        self.assertEqual(result["status"], "PASS_STRUCTURE_AND_L1_ONLY")
        self.assertEqual(result["illustrative_outcome_counts"], {"SUPPORTED": 1, "UNSUPPORTED": 3,
                                                               "AMBIGUOUS": 1, "NOT_ASSESSED": 1})
        self.assertEqual(result["independently_reviewed"], 0)
        self.assertFalse(result["gold_standard"])
        self.assertEqual(self.obj, before)

    def test_no_semantic_scoring_or_overall_aggregation(self):
        obj, case = self.changed_case()
        case["review"]["overall"]["outcome"] = "AMBIGUOUS"
        result = validate_records(obj, self.texts)
        self.assertEqual(result["illustrative_outcome_counts"]["AMBIGUOUS"], 2)
        self.assertFalse(result["semantic_accuracy_measured"])

    def test_claims_materialized_l1_not_l2(self):
        for case in self.obj["cases"]:
            data = materialize_case(case, self.texts[case["node_id"]])
            self.assertEqual(data["l1_status"], "PASS")
            self.assertTrue(data["source_text"])
        case = next(c for c in self.obj["cases"] if c["case_id"] == "copyright_is_not_topic_evidence")
        self.assertEqual(materialize_case(case, self.texts[90])["l1_status"], "PASS")

    def test_duplicates_and_missing_dimensions(self):
        obj, case = self.changed_case(); obj["cases"].append(copy.deepcopy(case))
        with self.assertRaises(InputError): validate_records(obj, self.texts)
        obj, case = self.changed_case(); del case["review"]["dimensions"]["quote_claim_support"]
        with self.assertRaises(InputError): validate_records(obj, self.texts)

    def test_invalid_outcome_missing_rationale_and_references(self):
        for change in ({"outcome": "ACCEPT"}, {"outcome": []}, {"rationale": " "},
                       {"evidence_refs": []}, {"evidence_refs": ["unknown"]}, {"evidence_refs": ["topic", "topic"]}):
            obj, case = self.changed_case(); case["review"]["overall"].update(change)
            with self.subTest(change=change), self.assertRaises(InputError): validate_records(obj, self.texts)

    def test_false_independence_and_holdout_claims_rejected(self):
        for field, value in (("kind", "INDEPENDENT"), ("independently_reviewed", True),
                             ("reviewer_id", "unverified-reviewer"), ("basis", "HEURISTIC_SCORED")):
            obj, case = self.changed_case(); case["review"][field] = value
            with self.assertRaises(InputError): validate_records(obj, self.texts)
        obj, case = self.changed_case(); case["future_holdout_eligible"] = True
        with self.assertRaises(InputError): validate_records(obj, self.texts)

    def test_gt_and_correctness_fields_rejected(self):
        class Poison:
            def __int__(self): raise AssertionError("GT decoded")
        for field in ("y", "fixed_y", "e0", "correctness"):
            obj, case = self.changed_case(); case["review"][field] = Poison()
            with self.assertRaisesRegex(InputError, "GT/diagnostic"): validate_records(obj, self.texts)

    def test_quote_bounds_hashes_sources_and_template_refs(self):
        for field, value in (("source_id", "unknown"), ("start", True), ("end", 999999), ("quote_sha256", "0"*64)):
            obj, case = self.changed_case(); case["excerpts"][0][field] = value
            with self.assertRaises(InputError): validate_records(obj, self.texts)
        obj, case = self.changed_case(); case["rich_response_template"]["supporting_evidence"][0]["quote_ref"] = "missing"
        with self.assertRaises(InputError): validate_records(obj, self.texts)

    def test_node_and_source_alignment(self):
        obj, case = self.changed_case(); case["node_id"] = -1
        with self.assertRaises(InputError): validate_records(obj, self.texts)
        obj, case = self.changed_case(); case["target_text_sha256"] = "0"*64
        with self.assertRaises(InputError): validate_records(obj, self.texts)

    def test_unassessed_not_relabelled_as_ambiguous_by_code(self):
        obj = copy.deepcopy(self.obj)
        unassessed = obj["cases"][-1]
        unassessed["review"]["dimensions"]["primary_topic_relevance"]["outcome"] = "AMBIGUOUS"
        unassessed["review"]["dimensions"]["primary_topic_relevance"]["evidence_refs"] = ["title"]
        with self.assertRaises(InputError): validate_records(obj, self.texts)
