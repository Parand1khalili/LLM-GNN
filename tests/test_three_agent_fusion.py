"""Synthetic three-agent single-label fusion, masks, confidence and authorization."""
import copy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_correction_features import fixture
from llmgnn_sara.sara2.policy import Pair, Annotation
from llmgnn_sara.sara3 import fusion as f
from llmgnn_sara.downstream import fusion as d
from llmgnn_sara.evaluation import fusion as e


def phase(label=1, **changes):
    p = copy.deepcopy(fixture()["rows"][0]["blind"])
    p.update(class_index=label, support_count=1, quote_lengths=[40], counter_count=0,
             auxiliary_warning=False, uncertainty=False)
    p.update(changes); return p


def pair(b=0, n=1, bc=90, nc=95):
    return Pair(Annotation(0, b, bc), Annotation(0, n, nc))


def synthetic():
    table = fixture()
    pairs = tuple(Pair(Annotation(i, 0 if i < 57 else i % 7, 90),
                       Annotation(i, 0 if i < 57 else i % 7, 95)) for i in range(140))
    for r in table["rows"]:
        r.update(narrative_confidence=95, confidence_max=95, confidence_gap=5,
                 blind=phase(), compare=phase())
    ids = {r: [x["node_id"] for x in table["rows"] if x["router"] == r] for r in ("r0", "r1_v1")}
    for router in ids: table["sources"][router]["selected_ids_sha256"] = f.digest(ids[router])
    frozen = SimpleNamespace(by_arm=lambda arm: [SimpleNamespace(target_id=i, samples=[SimpleNamespace(
        source_kind="supplementary" if i >= 135 else "fresh")]) for i in range(140)])
    inputs = SimpleNamespace(pairs=pairs, frozen=frozen, provenance=(("synthetic", "a"*64),))
    with patch.object(f, "select_router", side_effect=lambda pairs, budget, router: ids[router]):
        arms, selections = f.build(table, pairs)
    report = {"schema": f.VERSION, "contract": f.CONTRACT, "rule_sha256": f.digest(f.CONTRACT),
        "source_feature_sha256": f.FEATURE_SHA, "source_input_hashes": [["synthetic", "a"*64]],
        "ordered_classes": list(f.CLASSES), "cohort_ids": list(range(140)), "primary_excluded_ids": list(range(135, 140)),
        "router_selections": selections, "arms": arms, "training_admissions": 0}
    return table, inputs, report, ids


class FusionTests(unittest.TestCase):
    def test_single_class_consensus_third_and_both_baseline_fallback(self):
        r = f.fuse(pair(), True, phase(2), phase(2), f.P1)
        self.assertEqual((r["final_class"], r["label_source"], r["third_class"]), (2, "AGENT3_CONSENSUS", True))
        self.assertIsNone(r["confidence_percent"]); self.assertFalse(r["training_eligible"])
        r = f.fuse(pair(0, 0), True, phase(abstain=True, class_index=None), None, f.P1)
        self.assertEqual((r["final_class"], r["label_source"]), (0, "BASELINE_AGREEMENT"))
        self.assertIsNone(f.fuse(pair(), False, None, None, f.P2)["final_class"])
        self.assertIsNone(f.fuse(pair(0, 0, 79, 99), False, None, None, f.P1)["final_class"])

    def test_relaxed_comparison_and_explicit_rejected_only_fallback(self):
        for label in (0, 1):
            r = f.fuse(pair(), True, phase(2), phase(label), f.P2)
            self.assertEqual((r["final_class"], r["label_source"]), (label, "AGENT3_COMPARISON_RESOLVER"))
        self.assertIsNone(f.fuse(pair(), True, phase(0), phase(2), f.P2)["final_class"])
        rejected = phase(None, state="REJECTED", l1="FAIL", abstain=None)
        for missing in (None, rejected):
            r = f.fuse(pair(), True, phase(1), missing, f.P2)
            self.assertEqual(r["label_source"], "AGENT3_BLIND_CANDIDATE_FALLBACK")
            self.assertIsNone(f.fuse(pair(), True, phase(2), missing, f.P2)["final_class"])
        abstain = phase(None, abstain=True)
        self.assertIsNone(f.fuse(pair(), True, phase(1), abstain, f.P2)["final_class"])

    def test_same_narrative_consensus_can_resolve_low_confidence_not_a_correction(self):
        r = f.fuse(pair(0, 1, 70, 85), True, phase(1), phase(1), f.P1)
        self.assertEqual((r["final_class"], r["relative_to_C"], r["disagreement_resolution"]), (1, "ADDED_TO_C", "NARRATIVE"))

    def test_confidence_is_real_own_arm_or_matching_candidate_not_agent(self):
        for policy, expected in (("A", 90), ("B", 95), ("C", 90)):
            self.assertEqual(f.fuse(pair(0, 0), False, None, None, policy)["confidence_percent"], expected)
        self.assertEqual(f.fuse(pair(), True, phase(1), phase(1), f.P2)["confidence_percent"], 95)

    def test_l1_support_domain_gt_and_uncertainty_fail_closed(self):
        for changed in ({"l1": "FAIL"}, {"support_count": 0}, {"quote_lengths": []}, {"abstain": True}):
            self.assertIsNone(f.fuse(pair(), True, phase(**changed), phase(), f.P1)["final_class"])
        for changed in ({"class_index": 7}, {"state": "UNCERTAIN"}, {"gt": 2}):
            with self.assertRaises(ValueError): f.fuse(pair(), True, phase(**changed), phase(), f.P2)
        r = f.fuse(pair(), True, phase(auxiliary_warning=True, counter_count=3, uncertainty=True), phase(), f.P2)
        self.assertEqual(r["final_class"], 1)

    def test_full_cohort_provenance_canonical_serialization_and_masks(self):
        table, inputs, report, ids = synthetic(); before = copy.deepcopy(report)
        with patch.object(f, "select_router", side_effect=lambda pairs, budget, router: ids[router]):
            f.validate_report(report, table, inputs)
            f.validate_report(json.loads(json.dumps(report, sort_keys=True)), table, inputs)
        grid = d.build_grid(report, f.digest(report))
        self.assertEqual(grid, d.build_grid(json.loads(json.dumps(report, sort_keys=True)), f.digest(report)))
        provenance = f.input_provenance(report, table)
        self.assertEqual(len(provenance["records"]["r0"]), 140)
        self.assertEqual(sum(r["router_selected"] for r in provenance["records"]["r0"]), 37)
        self.assertEqual(provenance["records"]["r0"][0]["agent3"]["blind"]["class_index"], 1)
        self.assertEqual(len(grid["plans"]), 112)
        self.assertEqual(len(grid["test_ids"]), 2568)
        rows = [r for r in grid["plans"] if r["cohort"] == "sensitivity" and r["loss"] == "ce" and not r["PS"] and r["mask_mode"] == "matched_all_arms"]
        self.assertEqual(len({tuple(r["train_ids"]) for r in rows}), 1)
        self.assertEqual(report, before)
        bad = copy.deepcopy(report); bad["arms"]["A_B1"][0]["final_class"] = 7
        with self.assertRaises(ValueError): d.build_grid(bad, f.digest(bad))
        self.assertTrue(all(len(r["train_ids"]) == len(set(r["train_ids"])) for r in grid["plans"]))
        self.assertTrue(all(not set(r["train_ids"]) & set(grid["test_ids"]) for r in grid["plans"]))

    def test_third_confidence_blocks_wce_ps_not_ce_and_fit_dedup(self):
        _, _, report, _ = synthetic(); grid = d.build_grid(report, f.digest(report))
        by = lambda arm, loss, ps: next(r for r in grid["plans"] if r["arm"] == arm and r["loss"] == loss and r["PS"] is ps and r["cohort"] == "sensitivity" and r["mask_mode"] == "natural")
        self.assertEqual(by("D_P1_r0", "ce", False)["status"], "DRAFT_NOT_ADMITTED")
        self.assertEqual(by("D_P1_r0", "wce", False)["status"], "BLOCKED_UNAVAILABLE_FINAL_LABEL_CONFIDENCE")
        self.assertEqual(by("D_P1_r0", "ce", True)["status"], "BLOCKED_UNAVAILABLE_FINAL_LABEL_CONFIDENCE")
        self.assertEqual(by("D_P1_r0", "ce", False)["fit_spec_sha256"], by("E_P2_r0", "ce", False)["fit_spec_sha256"])

    def test_admission_defaults_hashes_test_audit_and_no_training(self):
        table, inputs, report, ids = synthetic(); grid = d.build_grid(report, f.digest(report))
        row = next(r for r in grid["plans"] if r["arm"] == "D_P1_r0" and r["loss"] == "ce" and not r["PS"] and r["mask_mode"] == "natural" and r["cohort"] == "sensitivity")
        with self.assertRaises(PermissionError): d.admit(report, row, table=table, inputs=inputs)
        approval = {"version": d.ADMISSION, "fusion_sha256": f.digest(report), "plan_sha256": f.digest(row),
                    "owner_authorized": True, "allow_experimental_admission": True, "test_audit_sha256": "a"*64,
                    "test_status": "AUDITED_EXPLORATORY_SPLIT"}
        with patch.object(f, "select_router", side_effect=lambda pairs, budget, router: ids[router]):
            plan = d.admit(report, row, table=table, inputs=inputs, approval=approval)
            self.assertEqual(plan["training_runs"], 0)
            self.assertTrue(plan["ce_unit_slot_not_confidence_ids"])
            for field, value in (("owner_authorized", False), ("test_status", "UNVERIFIED"), ("test_audit_sha256", "z"*64), ("fusion_sha256", "0"*64)):
                bad = {**approval, field: value}
                with self.assertRaises(ValueError): d.admit(report, row, table=table, inputs=inputs, approval=bad)
        from llmgnn_sara.downstream.model import train_gcn
        with self.assertRaises(PermissionError): train_gcn(None, plan, 0)

    def test_gt_only_metrics_and_paired_delta_known_synthetic_truth(self):
        _, _, report, _ = synthetic()
        result = e.evaluate(report, [0]*2708)
        result["source_fusion_sha256"] = f.digest(report)
        exported = e.public_summary(result, d.build_grid(report, f.digest(report)), "a"*64, "b"*64)
        self.assertNotIn('"node_id"', json.dumps(exported))
        self.assertNotIn('private_events', json.dumps(exported))
        self.assertEqual(len(exported["gcn_matrix"]), 112)
        self.assertEqual(result["results"]["sensitivity"]["D_P1_r0"]["agent3_selected_vs_references"]["narrative_class"]["harms"], 37)
        summary = e.paired_seed_summary({s: 50+s for s in range(10)}, {s: 51+s for s in range(10)})
        self.assertEqual(summary["paired_delta_pp"], {"mean": 1, "population_sd": 0.0})
        with self.assertRaises(ValueError): e.paired_seed_summary({0: 50}, {0: 51})
        with self.assertRaises(ValueError): e.evaluate(report, [True]*2708)


if __name__ == "__main__": unittest.main()
