"""Synthetic node-level diagnostics; no GT file, API, private data or training."""
from collections import Counter
from types import SimpleNamespace
import unittest

from llmgnn_sara.sara2.policy import Annotation, Pair
from llmgnn_sara.sara3.atlas import ATLAS
from llmgnn_sara.sara3.correction_features import (
    PHASE_FIELDS, ROW_FIELDS, VERSION as OLD_FEATURE_VERSION)
from llmgnn_sara.sara3.expanded_atlas_freeze import (
    ATLAS_SHA, VERSION as FREEZE_VERSION, make_vectors)
from llmgnn_sara.evaluation.joint_baseline_failure import (
    _route_outcome, analyze, ROUTERS)


def phase(cls=None, state="COMPLETED", abstain=False):
    value = dict.fromkeys(PHASE_FIELDS)
    value.update(state=state, l1="PASS" if state=="COMPLETED" else "NOT_ASSESSED",
                 class_index=None if abstain or state != "COMPLETED" else cls,
                 abstain=abstain if state=="COMPLETED" else None,
                 support_count=0, counter_count=0, quote_lengths=[],
                 auxiliary_warning=False, uncertainty=False,
                 topic_digest=None, third_class=False)
    return value


VOCAB = tuple(c.keywords + tuple(f"syntheticword{j}" for j in range(8)) for c in ATLAS)


def dataset():
    truth = [i % 7 for i in range(2708)]
    rows = []
    for i in range(140):
        label = truth[i]
        b = (label + 1) % 7 if i < 38 else label
        n = ((label + 2) % 7 if i in (36, 37) else b)
        rows.append(Pair(Annotation(i, b, 92),
                         Annotation(i, n, 90),
                         f"Paper {i} discusses networks, logic and Bayesian inference."))
    selected = list(range(10, 47))
    frozen = {
        "schema": FREEZE_VERSION,
        "status": "FROZEN_GT_NOT_ACCESSED",
        "l2": "NOT_ASSESSED",
        "atlas_sha256": ATLAS_SHA,
        "selected": selected,
        "vectors": make_vectors(rows, selected),
        "source_summary_sha256": "a" * 64,
        "source_run_sha256": "b" * 64,
        "context_sha256": "c" * 64,
        "journal_rows_sha256": "d" * 64,
        "selected_sha256": "e" * 64,
        "phase_counts": {"blind_completed": 37, "blind_abstained": 9,
                         "comparison_completed": 27, "comparison_rejected": 1,
                         "uncertain": 0},
    }
    selected_by_router = {"r0": list(range(37)),
                          "r1_v1": list(range(20, 57))}
    feat = {
        "schema": OLD_FEATURE_VERSION,
        "measurement_status": "GT_FREE_FROZEN_BEFORE_OUTCOME_JOIN",
        "policy_version": "sara.arbitration.automated_concordance.v1",
        "sources": {
            name: {field: "a" * 64 for field in (
                "context_sha256", "contract_sha256", "journal_rows_sha256",
                "selected_ids_sha256")}
            for name in ("r0", "r1_v1")},
        "rows": [],
    }
    for router, nodes in selected_by_router.items():
        for node in nodes:
            p=rows[node]
            item=dict.fromkeys(ROW_FIELDS)
            item.update(router=router, node_id=node, b1_class=p.b1.class_index,
                        narrative_class=p.narrative_v0.class_index,
                        b1_confidence=92, narrative_confidence=90,
                        confidence_min=90, confidence_max=92,
                        confidence_gap=2, baseline_agrees=p.agrees,
                        blind=phase(truth[node] if node == 5 else p.b1.class_index),
                        compare=phase(p.b1.class_index),
                        shadow_decision="ABSTAIN")
            feat["rows"].append(item)
    expanded = {
        node: {
            "blind": phase(truth[node] if node==10 else rows[node].b1.class_index),
            "compare": phase(rows[node].b1.class_index),
            "v1_reason": "THIRD_CLASS_DIAGNOSTIC_ONLY" if node==10 else "PRIMARY_TOPIC_DRIFT",
        }
        for node in selected
    }
    return SimpleNamespace(pairs=tuple(rows)), truth, feat, expanded, frozen


class JointFailureTests(unittest.TestCase):
    def test_detection_generation_and_admission_are_separate(self):
        inputs, truth, historical, expanded, freeze = dataset()
        public, private = analyze(inputs, truth, historical, expanded, freeze, expanded_vocab=VOCAB)
        self.assertEqual(public["joint_wrong_count"], 38)
        self.assertEqual(public["same_wrong_class_count"], 36)
        self.assertEqual(public["policy_constraint"][
            "automated_v1_can_accept_correct_class_for_joint_wrong"], 0)
        self.assertEqual(public["routing"]["r0"]["selected_joint_wrong"], 37)
        self.assertEqual(public["routing"]["r1_v1"]["selected_joint_wrong"], 18)
        self.assertEqual(public["routing"]["expanded_r1_v1"]["selected_joint_wrong"], 28)
        self.assertEqual(public["routing"]["expanded_r1_v1"]["any_phase_correct"], 1)
        self.assertEqual(public["routing"]["expanded_r1_v1"][
            "failure_stages"]["CORRECT_PHASE_BUT_NOT_ADMITTED"], 1)
        self.assertEqual(len(private), 38)
        self.assertEqual(private[0]["node_id"], 0)
        self.assertEqual(public["provider_calls"], 0)
        self.assertEqual(public["training_runs"], 0)

    def test_wrong_baseline_never_accepted_as_correct_third_class(self):
        inputs, truth, historical, expanded, freeze = dataset()
        public, private = analyze(inputs, truth, historical, expanded, freeze, expanded_vocab=VOCAB)
        node = next(r for r in private if r["node_id"] == 10)
        self.assertTrue(node["routed"]["expanded_r1_v1"]["blind_correct"])
        self.assertEqual(node["routed"]["expanded_r1_v1"]["stage"],
                         "CORRECT_PHASE_BUT_NOT_ADMITTED")
        self.assertEqual(node["routed"]["expanded_r1_v1"]["policy_reason"],
                         "THIRD_CLASS_DIAGNOSTIC_ONLY")

    def test_incomplete_or_misaligned_inputs_fail_closed(self):
        inputs, truth, historical, expanded, freeze = dataset()
        with self.assertRaises(ValueError):
            analyze(inputs, truth[:-1], historical, expanded, freeze, expanded_vocab=VOCAB)
        with self.assertRaises(ValueError):
            analyze(inputs, truth, historical, {**expanded, 99: expanded[10]}, freeze, expanded_vocab=VOCAB)
        with self.assertRaises(ValueError):
            analyze(inputs, truth, historical, expanded, freeze, expanded_vocab=VOCAB, expected_joint_wrong=37)
        historical["rows"][0]["node_id"] = 999
        with self.assertRaises(ValueError):
            analyze(inputs, truth, historical, expanded, freeze, expanded_vocab=VOCAB)

    def test_not_selected_never_claims_agent_failure(self):
        inputs, truth, historical, expanded, freeze = dataset()
        p=inputs.pairs[0]
        out = _route_outcome(p, truth[0], False, None)
        self.assertEqual(out["stage"], "NOT_SELECTED")
        self.assertFalse(out["any_phase_correct"])


if __name__ == "__main__":
    unittest.main()
