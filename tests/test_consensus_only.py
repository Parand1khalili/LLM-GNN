"""Synthetic ablation tests; no real GT or semantic review."""
import copy
import io
import unittest
from unittest.mock import patch

import test_evidence_arbitration_v3 as fixtures
from llmgnn_sara.sara3 import consensus_only as policy
from llmgnn_sara.evaluation import consensus_only as evaluation


class ConsensusTests(unittest.TestCase):
    def setUp(self):
        helper = fixtures.EvidenceV3Tests(); helper.setUp()
        self.cfg, self.row = helper.cfg, helper.row
        self.helper = helper

    def test_all_diagnostics_are_non_gating_and_third_class_allowed(self):
        self.row.update(topic_consistent=False, shared_support=0)
        for phase in (self.row["blind"], self.row["compare"]):
            phase.update(auxiliary_warning=True, counter_count=1, uncertainty=True)
        for optional in ({"P": None, "N": None}, {"P": 0, "N": 0}, {"P": 1, "N": 1}):
            result = policy.decide(self.row, optional, self.cfg)
            self.assertEqual((result["decision"], result["label"], result["third_class"]), ("SWITCH_TO_AGENT", 1, True))
            self.assertIsNone(result["score"])
            self.assertFalse(result["training_eligible"])
            self.assertEqual(result["l2_status"], "NOT_ASSESSED")

    def test_invalid_phases_quotes_class_and_same_label(self):
        for key, value in (("state", "REJECTED"), ("l1", "FAIL"), ("abstain", True), ("class_index", 7), ("support_count", 0)):
            row = copy.deepcopy(self.row); row["compare"][key] = value
            self.assertEqual(policy.decide(row, {"P": None, "N": None}, self.cfg)["decision"], "NO_VALID_AGENT_RESPONSE")
        self.row["compare"]["class_index"] = 2
        self.assertEqual(policy.decide(self.row, {"P": 1, "N": 1}, self.cfg)["decision"], "KEEP_NARRATIVE")
        self.row["compare"]["class_index"] = 1; self.row["narrative_class"] = 1
        self.assertEqual(policy.decide(self.row, {"P": 1, "N": 1}, self.cfg)["decision"], "KEEP_NARRATIVE")

    def test_determinism_control_immutability_gt_and_forged_report(self):
        before = copy.deepcopy(self.row)
        self.assertEqual(policy.decide(self.row, {"P": None, "N": None}, self.cfg), policy.decide(self.row, {"P": None, "N": None}, self.cfg))
        self.assertEqual(self.row, before)
        self.row["gt"] = 1
        with self.assertRaises(ValueError): policy.decide(self.row, {"P": None, "N": None}, self.cfg)
        table, baseline, _ = self.helper.report_fixture()
        report = {"schema": policy.VERSION, "contract": policy.CONTRACT, "rule_sha256": policy.digest(policy.CONTRACT),
                  "source_feature_sha256": policy.v3.base.FEATURE_SHA, "base_report_sha256": policy.v3.BASE_REPORT_SHA,
                  "training_admissions": 0, "rows": policy.score(table, baseline)}
        policy.validate_report(report, table, baseline)
        report["rows"][0]["training_eligible"] = True
        with self.assertRaises(ValueError): policy.validate_report(report, table, baseline)

    def test_lexical_categories_never_claim_semantic_validity(self):
        for a, b, kind in (("Topic", " topic ", "NORMALIZED_IDENTICAL"),
                            ("a,b", "a b", "TOKEN_IDENTICAL_FORMATTING_DIFFERENCE"),
                            ("a b", "b a", "TOKEN_REORDERING"),
                            ("a b", "a b c", "CONTIGUOUS_TOKEN_EXTENSION"),
                            ("neural learning", "probabilistic inference", "TOKEN_REPLACEMENT_ADDITION_OR_DELETION")):
            result = policy.topic_difference(a, b)
            self.assertEqual(result["lexical_category"], kind)
            self.assertEqual(result["semantic_status"], "NOT_ASSESSED")

    def test_synthetic_fix_harm_shared_quote_and_empty_strata(self):
        rows = [{"node_id": 0, "narrative_class": 0, "label": 1}, {"node_id": 1, "narrative_class": 0, "label": 1}]
        result = evaluation.stratum(rows, [1, 0])
        self.assertEqual((result["fixes"], result["harms"], result["net"]), (1, 1, 0))
        self.assertEqual(evaluation.stratum([], [])['denominator'], 0)

    def test_bad_hash_and_forged_diagnostic_stop_before_gt(self):
        args = sum((["--"+name, "absent"] for name in ("report", "features", "base-report", "diagnostic", "graph", "frozen-root", "output")), [])
        for mocked in (ValueError(), {"diagnostic_sha256": "0"*64}):
            with patch.object(evaluation, "read_pinned_json", **({"side_effect": mocked} if isinstance(mocked, Exception) else {"return_value": mocked})), \
                 patch.object(evaluation.previous.base_evaluation, "_labels_from_original_graph") as gt, patch("sys.stderr", io.StringIO()):
                self.assertEqual(evaluation.main(args+["--report-sha256", "0"*64]), 1)
            gt.assert_not_called()

    def test_audit_missing_journal_fails_before_response_read(self):
        table, baseline, _ = self.helper.report_fixture()
        table['sources']['r0']['context_sha256'] = policy.digest({})
        table['sources']['r0']['contract_sha256'] = policy.digest({})
        with patch.object(policy, 'contract_from_dict', return_value={"max_calls": 74}), \
             patch.object(policy, 'gateway_context', return_value=((), {})), \
             patch.object(policy, 'journal_rows', side_effect=ValueError()), patch.object(policy, 'replay') as replay:
            with self.assertRaises(ValueError): policy.audit_candidates(table, policy.score(table, baseline), type('Inputs', (), {'pairs': ()})(), {'r0': 'absent'}, {})
        replay.assert_not_called()


if __name__ == "__main__": unittest.main()
