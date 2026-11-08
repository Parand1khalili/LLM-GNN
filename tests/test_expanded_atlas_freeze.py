"""Public-only safety checks for GT-free freeze and GT-only raw scoring."""
import unittest

from llmgnn_sara.sara2.policy import Annotation, Pair
from llmgnn_sara.sara3.expanded_atlas_freeze import (
    ATLAS_SHA, VERSION, make_vectors, validate_freeze)
from llmgnn_sara.evaluation.expanded_atlas_raw import analyze


def fixture():
    rows = tuple(
        Pair(Annotation(i, i % 7, 92),
             Annotation(i, i % 7 if i % 3 else (i + 1) % 7, 90),
             f"Synthetic paper {i} method and theory.")
        for i in range(140))
    selected = list(range(37))
    vectors = make_vectors(rows, selected)
    item = {
        "schema": VERSION, "status": "FROZEN_GT_NOT_ACCESSED",
        "l2": "NOT_ASSESSED", "atlas_sha256": ATLAS_SHA,
        "selected": selected, "vectors": vectors,
        "source_summary_sha256": "a" * 64,
        "source_run_sha256": "b" * 64,
        "context_sha256": "c" * 64,
        "journal_rows_sha256": "d" * 64,
        "selected_sha256": "e" * 64,
        "phase_counts": {
            "blind_completed": 37, "blind_abstained": 9,
            "comparison_completed": 27, "comparison_rejected": 1,
            "uncertain": 0},
    }
    return item


class ExpandedAtlasFreezeTests(unittest.TestCase):
    def test_router_only_is_exact_alias_and_class_counts_are_matched(self):
        item = fixture()
        validate_freeze(item)
        vectors = item["vectors"]
        self.assertEqual(vectors["Router_only"], vectors["Expanded_V1"])
        for row in vectors["Expanded_V1"]:
            self.assertEqual(row["confidence_percent"] is None,
                             row["class_index"] is None)
            if row["class_index"] is not None:
                self.assertEqual(row["confidence_provenance"],
                                 "HISTORICAL_MIN_BASELINE_CONFIDENCE")
        for k in range(7):
            def count(name):
                return sum(r["class_index"] == k for r in vectors[name])
            self.assertEqual(count("Expanded_V1"), count("Class_count_matched"))
        for n in item["selected"]:
            self.assertIsNone(vectors["Expanded_V1"][n]["class_index"])
        self.assertEqual(vectors, fixture()["vectors"])

    def test_freeze_rejects_gt_or_promoted_rejection(self):
        item = fixture()
        item["ground_truth"] = []
        with self.assertRaises(ValueError):
            validate_freeze(item)
        del item["ground_truth"]
        item["phase_counts"]["comparison_rejected"] = 0
        with self.assertRaises(ValueError):
            validate_freeze(item)

    def test_gt_only_outcomes_not_used_to_modify_frozen_vectors(self):
        item = fixture()
        before = repr(item)
        truth = [i % 7 for i in range(2708)]
        old = {i: item["vectors"]["Narrative"][i]["class_index"] for i in range(140)}
        public, private = analyze(item, truth, old)
        self.assertEqual(repr(item), before)
        self.assertEqual(public["raw_metrics"]["Expanded_V1"]["accepted"],
                         sum(r["class_index"] is not None
                             for r in item["vectors"]["Expanded_V1"]))
        self.assertEqual(len(private["node_outcomes"]), 140)
        self.assertEqual(public["raw_metrics"]["Expanded_V1"],
                         public["raw_metrics"]["Router_only"])
        self.assertIn("Old_V1_R1_to_Expanded_V1", public["paired_comparisons"])
        self.assertFalse(public["independent_holdout"])
        with self.assertRaises(ValueError):
            analyze(item, truth[:-1], old)

    def test_unsafe_legacy_inventory_rejected(self):
        item = fixture()
        truth = [i % 7 for i in range(2708)]
        with self.assertRaises(ValueError):
            analyze(item, truth, {i: None for i in range(139)})


if __name__ == "__main__":
    unittest.main()
