"""Synthetic GT isolation and outcome bookkeeping, never project labels."""
import copy
import unittest
import io
from unittest.mock import patch
from llmgnn_sara.sara3.correction_features import VERSION, POLICY, PHASE_FIELDS, ROW_FIELDS, validate
from llmgnn_sara.evaluation.correction_outcomes import analyze, outcome


def fixture():
    rows = []
    for router, ids in (("r0", range(37)), ("r1_v1", range(20, 57))):
        for node in ids:
            phase = dict.fromkeys(PHASE_FIELDS)
            phase.update(state="COMPLETED", l1="PASS", class_index=1, abstain=False)
            row = dict.fromkeys(ROW_FIELDS)
            row.update(router=router, node_id=node, b1_class=0, narrative_class=0,
                       blind=dict(phase), compare=dict(phase), shadow_decision="ABSTAIN",
                       b1_confidence=90, narrative_confidence=90, confidence_min=90,
                       confidence_max=90, confidence_gap=0)
            rows.append(row)
    return {"schema": VERSION, "measurement_status": "GT_FREE_FROZEN_BEFORE_OUTCOME_JOIN",
            "policy_version": POLICY, "sources": {r: dict.fromkeys(
                ("context_sha256", "contract_sha256", "journal_rows_sha256", "selected_ids_sha256"), "a" * 64)
                for r in ("r0", "r1_v1")}, "rows": rows}


class CorrectionTests(unittest.TestCase):
    def test_complete_deterministic_no_mutation_and_overlap(self):
        table = fixture(); before = copy.deepcopy(table)
        validate(table)
        result = analyze(table, [1] * 2708)
        self.assertEqual(result, analyze(table, [1] * 2708))
        self.assertEqual(table, before)
        self.assertEqual(result["aggregate"]["observations"], 74)
        self.assertEqual(result["aggregate"]["paired_outcomes"]["r0:narrative_to_blind"]["CORRECTED_BASELINE_ERROR"], 37)

    def test_leakage_extra_field_invalid_class_and_duplicates_fail(self):
        for change in ("gt", "outcome", "duplicate", "class"):
            table = fixture()
            if change == "gt": table["rows"][0]["gt"] = 0
            elif change == "outcome": table["rows"][0]["narrative_to_blind"] = "CORRECTED"
            elif change == "duplicate": table["rows"][1] = copy.deepcopy(table["rows"][0])
            else: table["rows"][0]["blind"]["class_index"] = 7
            with self.subTest(change=change), self.assertRaises(ValueError): validate(table)

    def test_all_five_outcomes_and_missing_prediction(self):
        self.assertEqual([outcome(0, 1, 1), outcome(0, 1, 0), outcome(0, 0, 0),
                          outcome(0, 1, 2), outcome(0, None, 0)],
                         ["CORRECTED_BASELINE_ERROR", "DAMAGED_CORRECT_BASELINE", "BOTH_CORRECT",
                          "BOTH_INCORRECT", "NO_CLASS_PREDICTION"])
        with self.assertRaises(ValueError): analyze(fixture(), [True] * 2708)

    def test_no_training_authorization_and_unknown_provenance(self):
        from llmgnn_sara.downstream.model import train_gcn
        with self.assertRaises(PermissionError): train_gcn(None, {}, 0)
        table = fixture(); table["sources"]["r0"]["oracle"] = 1
        with self.assertRaises(ValueError): validate(table)

    def test_bad_feature_hash_never_opens_gt(self):
        from llmgnn_sara.evaluation import correction_outcomes as module
        with patch.object(module, "read_pinned_json", side_effect=ValueError("SHA mismatch")), \
             patch.object(module, "_labels_from_original_graph") as gt, patch("sys.stderr", io.StringIO()):
            code = module.main(["--feature-file", "absent", "--feature-sha256", "0" * 64,
                                "--graph-file", "forbidden", "--frozen-root", "absent", "--output", "absent"])
        self.assertEqual(code, 1); gt.assert_not_called()


if __name__ == "__main__": unittest.main()
