"""Prospective R2 contract checks; no correctness or human review fixtures."""
from dataclasses import asdict
import hashlib
import io
import os
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

from llmgnn_sara.sara2.policy import Annotation, Pair, pair_from_frozen
from llmgnn_sara.sara3.r2_candidate import ALLOCATIONS, exploration_key, select_r2, route_r2_candidate
from llmgnn_sara.io.project import PINS, load_project_inputs
from llmgnn_sara.evaluation.r2_comparison import compare_r2

ROOT = Path(__file__).resolve().parents[1]
FROZEN, AUTHENTIC = ROOT / ".local_artifacts/frozen", ROOT / ".local_artifacts/authentic"


def pair(node, text="rule", a=0, b=0, confidence=95):
    return Pair(Annotation(node, a, confidence), Annotation(node, b, confidence), text)


class HybridTests(unittest.TestCase):
    def test_primary_budget_order_and_overlap_deduplication(self):
        rows = [pair(i, "" if i < 10 else "rule") for i in range(60)]
        result = select_r2(rows)
        ids = result["selected_node_ids_admission_order"]
        self.assertEqual(len(set(ids)), 37)
        self.assertEqual(ids[:4], sorted(range(10), key=lambda n: (exploration_key(n), n))[:4])
        self.assertEqual(ids[4:21], list(range(10, 27)))
        self.assertGreaterEqual(result["stages"][2]["overlap_skipped"], 21)
        self.assertEqual(result, select_r2(reversed(rows)))
        self.assertEqual(tuple(ids), route_r2_candidate(rows))

    def test_no_unknown_pool_backfills_after_all_stages(self):
        result = select_r2([pair(i) for i in range(45)])
        stages = result["stages"]
        self.assertEqual(stages[0]["shortfall"], 4)
        self.assertEqual(len(stages[-1]["admitted_node_ids"]), 4)
        self.assertEqual(result["selected_node_ids_admission_order"], list(range(37)))

    def test_all_unknown_or_empty_text_exhausts_observed_pool(self):
        for text in ("", "uncovered topic"):
            result = select_r2([pair(i, text) for i in range(45)])
            self.assertEqual(result["stages"][1]["available"], 0)
            self.assertEqual(result["stages"][1]["shortfall"], 17)
            self.assertEqual(len(result["stages"][-1]["admitted_node_ids"]), 17)
            self.assertEqual(len(set(result["selected_node_ids_admission_order"])), 37)

    def test_scarce_unknown_pool_shortfall_is_backfilled_last(self):
        result = select_r2([pair(i, "" if i < 2 else "rule") for i in range(40)])
        self.assertEqual(result["stages"][0]["shortfall"], 2)
        self.assertEqual(len(result["stages"][1]["admitted_node_ids"]), 17)
        self.assertEqual(len(result["stages"][2]["admitted_node_ids"]), 16)
        self.assertEqual(len(result["stages"][3]["admitted_node_ids"]), 2)

    def test_exploration_hash_ties_use_node_ids(self):
        with patch("llmgnn_sara.sara3.r2_candidate.exploration_key", return_value="constant"):
            result = select_r2([pair(i, "") for i in reversed(range(45))])
        self.assertEqual(result["stages"][0]["admitted_node_ids"], [0, 1, 2, 3])
        self.assertEqual(len(result["stages"][0]["cutoff_tied_ids"]), 45)

    def test_small_pools_and_exact37_total(self):
        rows = [pair(i, "rule" if i < 2 else "") for i in range(37)]
        result = select_r2(rows)
        self.assertEqual(len(result["stages"][1]["admitted_node_ids"]), 2)
        self.assertEqual(set(result["selected_node_ids_admission_order"]), set(range(37)))

    def test_observed_and_candidate_order_have_separate_scales(self):
        rows = [pair(i) for i in range(50)] + [pair(100, "bayesian likelihood")]
        rows.append(pair(200, "rule", b=1, confidence=30))
        result = select_r2(rows)
        observed = result["stages"][1]["admitted_node_ids"]
        self.assertEqual(observed[:2], [200, 100])
        self.assertEqual(result["stages"][2]["admitted_node_ids"][0], 15)

    def test_all_prespecified_allocations_reproduce_without_mutation(self):
        rows = tuple(pair(i, "" if i % 3 == 0 else "rule neural", b=i % 2) for i in range(70))
        before = tuple(asdict(p) for p in rows)
        for allocation in ALLOCATIONS:
            self.assertEqual(sum(allocation), 37)
            result = select_r2(rows, allocation)
            self.assertEqual(result, select_r2(reversed(rows), allocation))
            self.assertEqual(len(set(result["selected_node_ids_admission_order"])), 37)
        self.assertEqual(before, tuple(asdict(p) for p in rows))

    def test_invalid_inputs_fail_before_selection(self):
        rows = [pair(i) for i in range(45)]
        for invalid in ((4.0, 17, 16), (True, 18, 18), [4, 17, 16], (0, 18, 19)):
            with self.assertRaises(ValueError):
                select_r2(rows, invalid)
        with self.assertRaises(ValueError):
            select_r2(rows[:36])
        with self.assertRaises(ValueError):
            select_r2(rows + [rows[0]])
        with self.assertRaises(TypeError):
            select_r2([{"gt": 1}] * 40)

    def test_gt_extra_fields_never_read(self):
        class Forbidden:
            def __bool__(self):
                raise AssertionError("GT accessed")
        source = {"class_index": 0, "confidence_percent_before_tensor_cast": 95,
                  "y": Forbidden(), "correctness": Forbidden()}
        adapted = [pair_from_frozen(i, source, source, "rule") for i in range(45)]
        self.assertEqual(select_r2(adapted), select_r2([pair(i) for i in range(45)]))


@unittest.skipUnless((AUTHENTIC / "b1_prompts.json").is_file() and
    (FROZEN / "b1_final_predictions.json").is_file(), "Authentic inputs unavailable")
class AuthenticHybridTests(unittest.TestCase):
    def test_real_report_read_boundary_and_determinism(self):
        allowed = {FROZEN / n for n in ("b1_final_predictions.json", "narrative_v0_final_predictions.json",
                                       "selection_manifest.json", "preparation_receipt.json")}
        allowed.update(AUTHENTIC / n for n in PINS)
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in allowed}
        allowed.add(ROOT / "docs/R2_CANDIDATE.md")
        os_open, io_open = os.open, io.open
        def guarded_os(path, *args, **kwargs):
            self.assertIn(Path(path).resolve(), allowed)
            return os_open(path, *args, **kwargs)
        def guarded_io(path, *args, **kwargs):
            if type(path) is not int:
                self.assertIn(Path(path).resolve(), allowed)
            return io_open(path, *args, **kwargs)
        with patch.object(os, "open", side_effect=guarded_os), patch.object(io, "open", side_effect=guarded_io), \
             patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            inputs = load_project_inputs(FROZEN, AUTHENTIC)
            snapshot = tuple(asdict(p) for p in inputs.pairs)
            report = compare_r2(inputs)
            self.assertEqual(report, compare_r2(inputs))
            self.assertEqual(snapshot, tuple(asdict(p) for p in inputs.pairs))
        self.assertEqual(len(report["routers"]), 5)
        self.assertEqual(len(report["pairwise_overlaps"]), 10)
        self.assertEqual(len(report["r2_sensitivity"]), 5)
        for result in report["routers"].values():
            self.assertEqual(len(set(result["selected_node_ids"])), 37)
        self.assertFalse(report["ground_truth_accessed"])
        self.assertFalse(report["human_review_accessed"])
        self.assertFalse(report["production_or_pilot_freeze"])
        self.assertTrue(all(report["input_order_stability"].values()))
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before})


if __name__ == "__main__":
    unittest.main()
