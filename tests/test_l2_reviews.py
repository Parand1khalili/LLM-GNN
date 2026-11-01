"""Mechanical review-form fixtures only; never genuine or LLM-generated reviews."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from llmgnn_sara.evaluation.l2_benchmark import BENCHMARK_SHA256, DIMENSIONS
from llmgnn_sara.evaluation.l2_reviews import (blank_review, compare_reviews, import_review,
                                              make_packet, prepare_reviews, validate_review)
from llmgnn_sara.io.frozen import InputError, read_pinned_json
from llmgnn_sara.io.project import load_project_inputs
from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.inputs import canonical_bytes

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT/"configs/l2_development_benchmark.json"
FROZEN, AUTHENTIC = ROOT/".local_artifacts/frozen", ROOT/".local_artifacts/authentic"


def filled_for_schema_test(form, refs, outcome="SUPPORTED"):
    """Synthetic syntax fixture in temporary directories; not a human opinion."""
    record = copy.deepcopy(form)
    record["declarations"] = {k: True for k in record["declarations"]}
    record["reviewed_at_utc"] = "2026-10-31T00:00:00Z"
    for a in (*record["assessments"].values(), record["overall"]):
        a.update(outcome=outcome, rationale="SYNTHETIC_STRUCTURE_TEST_NOT_A_HUMAN_REVIEW",
                 evidence_refs=[] if outcome == "NOT_ASSESSED" else [refs[0]])
    return record


@unittest.skipUnless((AUTHENTIC/"b1_prompts.json").is_file(), "External authorized inputs not provided")
class PacketAndRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = read_pinned_json(BENCHMARK, BENCHMARK_SHA256)["cases"][0]
        texts = {p.node_id: p.text for p in load_project_inputs(FROZEN, AUTHENTIC).pairs}
        cls.text = texts[cls.case["node_id"]]
        cls.packet = make_packet(cls.case, cls.text, "case-001", "reviewer-a")
        cls.digest = hashlib.sha256(canonical_bytes(cls.packet)).hexdigest()
        cls.form = blank_review(cls.packet, cls.digest)

    def valid(self, outcome="SUPPORTED"):
        return filled_for_schema_test(self.form, [e["evidence_id"] for e in self.packet["evidence"]], outcome)

    def test_blinding_counterfactual_and_allowlist(self):
        case = copy.deepcopy(self.case)
        case.update(case_id="LEAK_DESCRIPTIVE_ID", author_id="LEAK_AUTHOR", review={"expected": "LEAK_JUDGMENT"})
        case["rich_response_template"].update(class_index=5, uncertainty_reason="LEAK_AUTHOR_OPINION",
                                               auxiliary_method_warning="LEAK_AUTHOR_OPINION")
        self.assertEqual(make_packet(case, self.text, "case-001", "reviewer-a"), self.packet)
        text = json.dumps(self.packet)
        for forbidden in ("LEAK_", "class_index", "confidence", "node_id", "reviewer-b", "author_id"):
            self.assertNotIn(forbidden, text)
        self.assertNotIn(self.case["case_id"], text)
        self.assertNotIn(self.case["review"]["overall"]["rationale"], text)
        self.assertEqual(self.packet["article"]["text"], self.text)

    def test_blank_forms_are_not_reviews(self):
        self.assertTrue(all(a["outcome"] is None for a in self.form["assessments"].values()))
        self.assertIsNone(self.form["overall"]["outcome"])
        self.assertIsNone(self.form["reviewed_at_utc"])
        with self.assertRaises(InputError): validate_review(self.form, self.packet, self.digest, self.case["author_id"])

    def test_complete_structure_fixture_and_no_inferred_judgment(self):
        record = self.valid()
        self.assertEqual(validate_review(record, self.packet, self.digest, self.case["author_id"]), record)
        unknown = self.valid("NOT_ASSESSED")
        self.assertEqual(validate_review(unknown, self.packet, self.digest, self.case["author_id"]), unknown)

    def test_independence_declarations_and_assignment(self):
        for value in (False, None, 1):
            record = self.valid(); record["declarations"]["human_reviewer"] = value
            with self.assertRaises(InputError): validate_review(record, self.packet, self.digest, self.case["author_id"])
        record = self.valid(); record["reviewer"] = "reviewer-b"
        with self.assertRaises(InputError): validate_review(record, self.packet, self.digest, self.case["author_id"])
        with self.assertRaises(InputError): validate_review(self.valid(), self.packet, self.digest, "reviewer-a")

    def test_bad_fields_timestamps_references_scope_and_gt(self):
        for change in ({"schema_version": "unknown"}, {"case_id": "foreign"},
                       {"scope": "FUTURE_HOLDOUT"}, {"packet_sha256": "0"*64},
                       {"reviewed_at_utc": "2026-02-30T00:00:00Z"}, {"reviewed_at_utc": "2026-10-31"}, {"y": [1]}):
            record = self.valid(); record.update(change)
            with self.subTest(change=change), self.assertRaises(InputError):
                validate_review(record, self.packet, self.digest, self.case["author_id"])
        for change in ({"outcome": "ACCEPT_LABEL"}, {"rationale": " "}, {"evidence_refs": ["unknown"]}):
            record = self.valid(); record["overall"].update(change)
            with self.assertRaises(InputError): validate_review(record, self.packet, self.digest, self.case["author_id"])
        record = self.valid(); del record["assessments"][DIMENSIONS[0]]
        with self.assertRaises(InputError): validate_review(record, self.packet, self.digest, self.case["author_id"])


@unittest.skipUnless((AUTHENTIC/"b1_prompts.json").is_file(), "External authorized inputs not provided")
class ReviewWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/"private session"
        self.result = prepare_reviews(BENCHMARK, FROZEN, AUTHENTIC, self.root, ["reviewer-a", "reviewer-b"])
        self.session_hash = self.result["session_sha256"]
        self.session = PrivateAudit(self.root/"coordinator").read(self.session_hash)
        self.case = self.session["cases"][0]

    def form(self, reviewer, outcome="SUPPORTED"):
        form = PrivateAudit(self.root/"forms"/reviewer).read(self.case["blank_forms"][reviewer])
        packet = PrivateAudit(self.root/"packets"/reviewer).read(self.case["packets"][reviewer])
        return filled_for_schema_test(form, [e["evidence_id"] for e in packet["evidence"]], outcome)

    def admit(self, record):
        path = self.root/"working"/record["reviewer"]/"synthetic-unit-test.json"
        path.write_bytes(canonical_bytes(record))
        return import_review(self.root, self.session_hash, path, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_prepare_only_blank_packets_and_missing_comparison(self):
        self.assertEqual(self.result["packet_count"], 12)
        self.assertEqual(self.result["completed_human_reviews"], 0)
        forms = list((self.root/"working/reviewer-a").glob("*.review.json"))
        self.assertEqual(len(forms), 6)
        self.assertTrue(all(json.loads(p.read_bytes())["overall"]["outcome"] is None for p in forms))
        result = compare_reviews(self.root, self.session_hash)
        self.assertEqual(result["missing_records"], 12)
        self.assertTrue(all(c["overall_comparison"] == "MISSING_REVIEW" for c in result["cases"]))
        with self.assertRaises(InputError): prepare_reviews(BENCHMARK, FROZEN, AUTHENTIC, self.root, ["reviewer-a", "reviewer-b"])

    def test_duplicate_roster_and_case_author_rejected(self):
        for roster in (["reviewer-a", "reviewer-a"], ["reviewer-a", "../escape"],
                       ["reviewer-a", "codex-author-2026-10-31"]):
            with self.assertRaises(InputError): prepare_reviews(BENCHMARK, FROZEN, AUTHENTIC, self.root/"reject", roster)

    def test_import_idempotent_conflicting_record_not_overwritten(self):
        record = self.form("reviewer-a")
        digest = self.admit(record)
        self.assertEqual(self.admit(record), digest)
        record["overall"]["rationale"] = "DIFFERENT_SYNTHETIC_STRUCTURE_TEST_RECORD"
        with self.assertRaises(InputError): self.admit(record)
        self.assertEqual(compare_reviews(self.root, self.session_hash)["missing_records"], 11)

    def test_disagreement_and_deterministic_comparison_no_adjudication(self):
        self.admit(self.form("reviewer-a", "SUPPORTED"))
        self.admit(self.form("reviewer-b", "UNSUPPORTED"))
        result = compare_reviews(self.root, self.session_hash)
        self.assertEqual(result, compare_reviews(self.root, self.session_hash))
        row = next(c for c in result["cases"] if c["case_id"] == self.case["case_id"])
        self.assertEqual(row["overall_comparison"], "DISAGREEMENT")
        self.assertTrue(all(v == "DISAGREEMENT" for v in row["dimension_comparison"].values()))
        self.assertEqual(result["adjudication"], "NOT_PERFORMED")
        self.assertFalse(result["gold_standard"])
        self.assertNotIn("SYNTHETIC_STRUCTURE_TEST", json.dumps(result))

    def test_both_unassessed_is_not_semantic_agreement(self):
        for r in self.session["reviewers"]: self.admit(self.form(r, "NOT_ASSESSED"))
        row = compare_reviews(self.root, self.session_hash)["cases"][0]
        self.assertEqual(row["overall_comparison"], "BOTH_NOT_ASSESSED")

    def test_one_unassessed_is_incomplete_not_disagreement(self):
        self.admit(self.form("reviewer-a", "SUPPORTED"))
        self.admit(self.form("reviewer-b", "NOT_ASSESSED"))
        row = compare_reviews(self.root, self.session_hash)["cases"][0]
        self.assertEqual(row["overall_comparison"], "INCOMPLETE_ASSESSMENT")

    def test_agreement_and_missing_are_separate(self):
        for r in self.session["reviewers"]: self.admit(self.form(r))
        rows = compare_reviews(self.root, self.session_hash)["cases"]
        self.assertEqual(rows[0]["overall_comparison"], "AGREEMENT")
        self.assertEqual(sum(c["overall_comparison"] == "MISSING_REVIEW" for c in rows), 5)

    def test_malformed_private_record_fails_closed(self):
        PrivateAudit(self.root/"reviews/reviewer-a").write({"unexpected": "synthetic malformed record"})
        with self.assertRaises(InputError): compare_reviews(self.root, self.session_hash)
