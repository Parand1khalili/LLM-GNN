import unittest
from pathlib import Path

from llmgnn_sara.filtering import derive_ps


class FilteringTests(unittest.TestCase):
    def test_class_guard_original_order_and_immutability(self):
        ids, labels, confidences = [9, 2, 7, 4], [0, 0, 1, 2], [50, 50, 10, 10]
        result = derive_ps(ids, labels, confidences, 1)
        self.assertEqual(result["removed_global_node_ids_in_deletion_order"], [9])
        self.assertEqual(result["retained_global_node_ids_in_original_manifest_order"], [2, 7, 4])
        self.assertEqual(ids, [9, 2, 7, 4])
        self.assertEqual(labels, [0, 0, 1, 2])
        self.assertEqual(confidences, [50, 50, 10, 10])

    def test_invalid_values_and_guard_capacity(self):
        for args in (([0, 0], [0, 1], [50, 50], 0),
                     ([0, 1], [0, 1], [50, 50], 1),
                     ([0, 1], [0, 0], [float("nan"), 50], 1),
                     ([0, 1], [False, 0], [50, 50], 1),
                     ([0, 1], [0, 0], [50, 50], True)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                derive_ps(*args)

    def test_sequential_determinism(self):
        args = (list(range(14)), [n % 7 for n in range(14)], [80] * 14, 7)
        a = derive_ps(*args)
        self.assertEqual(a, derive_ps(*args))
        self.assertEqual(len(set(a["retained_pseudo_class_indices_in_order"])), 7)

    def test_actual_frozen_ps_for_both_arms_and_cohorts(self):
        from llmgnn_sara.io.frozen import load_frozen, read_pinned_json
        root = Path(__file__).resolve().parents[1] / ".local_artifacts" / "frozen"
        names = ("b1_final_predictions.json", "narrative_v0_final_predictions.json", "selection_manifest.json",
                 "ps_primary.json", "ps_sensitivity.json")
        if not all((root / name).is_file() for name in names):
            self.skipTest("External pinned frozen/PS artifacts are not installed")
        dataset = load_frozen(*(root / name for name in names[:3]))
        for cohort, pin in (("primary", "fa0a8c79b3c657371dd7cf7417a57174e20ce92b03c50df845873367005eeeed"),
                            ("sensitivity", "8f2d4b026a27f3c01f4bfb021fe1a4b2fd84ab90858da54ec0c4fee0367d9436")):
            expected = read_pinned_json(root / f"ps_{cohort}.json", pin)
            for arm in ("b1", "narrative_v0"):
                rows = [p for p in dataset.by_arm(arm) if cohort != "primary" or
                        p.samples[0].source_kind != "supplementary"]
                with self.subTest(cohort=cohort, arm=arm):
                    actual = derive_ps([p.target_id for p in rows], [p.class_index for p in rows],
                                       [p.confidence_percent for p in rows], expected["remove_count_per_arm"])
                    for field in ("retained_global_node_ids_in_original_manifest_order",
                                  "removed_global_node_ids_in_deletion_order",
                                  "retained_pseudo_class_indices_in_order",
                                  "retained_confidence_percent_in_order"):
                        self.assertEqual(actual[field], expected["selection_by_arm"][arm][field])


if __name__ == "__main__":
    unittest.main()
