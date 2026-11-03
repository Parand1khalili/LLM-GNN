"""Controlled, synthetic decisions; never a semantic benchmark or human L2."""
import copy
from dataclasses import dataclass
import unittest
from llmgnn_sara.sara3.automated_policy import VERSION, screen_validated

@dataclass(frozen=True)
class Annotation:
    class_index: int

@dataclass(frozen=True)
class Pair:
    b1: Annotation
    narrative_v0: Annotation
    @property
    def agrees(self):
        return self.b1.class_index == self.narrative_v0.class_index


def outcome(label=6):
    return {"class_index": label, "abstain": False, "l1_status": "PASS",
            "l2_status": "NOT_ASSESSED", "rich_evidence": {
                "primary_topic": "Bayesian inference", "counter_evidence": [],
                "supporting_evidence": [{"source_id": "target.text",
                    "quote": "Bayesian inference uses Gaussian process priors"}],
                "auxiliary_method_warning": None, "uncertainty_reason": None}}

class AutomaticScreenTests(unittest.TestCase):
    def test_positive_disagreement_candidate_is_provisional_not_l2_pass(self):
        p = Pair(Annotation(5), Annotation(6))
        r = screen_validated(p, outcome(), outcome())
        self.assertEqual((r["action"], r["class_index"], r["label_source"]),
                         ("ACCEPT", 6, "NARRATIVE_V0_CANDIDATE"))
        self.assertEqual(r["policy_version"], VERSION)
        self.assertEqual((r["l2_status"], r["semantic_validation"]),
                         ("NOT_ASSESSED", "NOT_PERFORMED"))

    def test_agreeing_baselines_can_be_retained_without_claiming_gt(self):
        r = screen_validated(Pair(Annotation(6), Annotation(6)), outcome(), outcome())
        self.assertEqual(r["action"], "ACCEPT")
        self.assertEqual(r["label_source"], "B1_AND_NARRATIVE_CONCORDANCE")

    def test_abstain_and_mismatched_classes(self):
        a, b = outcome(), outcome()
        a["abstain"] = True
        self.assertEqual(screen_validated(Pair(Annotation(5), Annotation(6)), a, b)["action"], "ABSTAIN")
        a, b = outcome(5), outcome(6)
        self.assertEqual(screen_validated(Pair(Annotation(5), Annotation(6)), a, b)["reason"], "BLIND_COMPARISON_CONFLICT")

    def test_third_class_is_never_accepted(self):
        r = screen_validated(Pair(Annotation(5), Annotation(6)), outcome(1), outcome(1))
        self.assertEqual((r["action"], r["third_class_proposal"]), ("REJECT", 1))
        self.assertIsNone(r["class_index"])

    def test_untrusted_or_missing_l1_never_promotes(self):
        for key, value in (("l1_status", "FAIL"), ("l2_status", "PASS"),
                           ("rich_evidence", None)):
            a = outcome()
            a[key] = value
            r = screen_validated(Pair(Annotation(5), Annotation(6)), a, outcome())
            self.assertEqual((r["action"], r["reason"]),
                             ("REJECT", "L1_OR_PROVENANCE_NOT_VALIDATED"))

    def test_counter_evidence_and_auxiliary_warning_and_uncertainty(self):
        for key, value, reason in (
            ("counter_evidence", [{"source_id": "target.text", "quote": "opposing evidence"}], "COUNTER_EVIDENCE_UNRESOLVED"),
            ("auxiliary_method_warning", "The neural technique is incidental", "AUXILIARY_METHOD_WARNING"),
            ("uncertainty_reason", "Multiple primary topics", "EXPLICIT_UNCERTAINTY")):
            b = outcome()
            b["rich_evidence"][key] = value
            result = screen_validated(Pair(Annotation(5), Annotation(6)), outcome(), b)
            self.assertEqual((result["action"], result["reason"]), ("ABSTAIN", reason))

    def test_topic_drift_and_missing_common_quote(self):
        b = outcome()
        b["rich_evidence"]["primary_topic"] = "Neural architectures"
        self.assertEqual(screen_validated(Pair(Annotation(5), Annotation(6)), outcome(), b)["reason"], "PRIMARY_TOPIC_DRIFT")
        b = outcome()
        b["rich_evidence"]["supporting_evidence"][0]["quote"] = "Another valid source quote"
        self.assertEqual(screen_validated(Pair(Annotation(5), Annotation(6)), outcome(), b)["reason"], "NO_COMMON_TARGET_EVIDENCE")

    def test_no_gt_or_accuracy_inputs_and_no_mutation(self):
        p = Pair(Annotation(5), Annotation(6))
        a, b = outcome(), outcome()
        originals = copy.deepcopy((a, b))
        screen_validated(p, a, b)
        self.assertEqual((a, b), originals)
        self.assertNotIn("accuracy", screen_validated(p, a, b))

if __name__ == "__main__":
    unittest.main()
