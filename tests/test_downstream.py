"""Synthetic matched-GCN contracts; no real graph, GT or training is loaded."""
import ast
from dataclasses import FrozenInstanceError
import importlib.util
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

from llmgnn_sara.downstream import GCNConfig, PseudoLabel, confidence_weights, gcn_plan, reduce_loss
from llmgnn_sara.downstream.model import GraphInputs, backend_status, build_gcn, synthetic_forward, train_gcn
from llmgnn_sara.evaluation.metrics import evaluate_frozen, matched_summary


class DownstreamContracts(unittest.TestCase):
    def setUp(self):
        self.selected = tuple(range(140))
        self.labels = tuple(PseudoLabel(i, i % 7, 50 + (i % 51)) for i in self.selected)

    def test_canonical_sensitivity_and_primary_share_test_complement(self):
        sensitivity = gcn_plan(self.selected, self.labels)
        primary = gcn_plan(self.selected, self.labels[5:], "primary", excluded_ids=range(5))
        self.assertEqual(sensitivity["train_count"], 140)
        self.assertEqual(primary["train_count"], 135)
        self.assertEqual(primary["common_test_count"], 2568)
        self.assertEqual(primary["test_ids"], sensitivity["test_ids"])
        self.assertTrue(all(primary["pseudo_y"][i] == -1 for i in range(5)))
        self.assertTrue(all(sensitivity["pseudo_y"][i] == -1 for i in sensitivity["test_ids"]))

    def test_manifest_order_is_not_resorted(self):
        selected = tuple(reversed(self.selected))
        plan = gcn_plan(selected, self.labels)
        self.assertEqual(plan["train_ids"], list(selected))

    def test_training_configuration_preserves_frozen_protocol(self):
        plan = gcn_plan(self.selected, self.labels)
        self.assertEqual(plan["config"]["seeds"], tuple(range(10)))
        self.assertEqual(plan["config"]["epochs"], 30)
        self.assertEqual(plan["config"]["num_layers"], 2)
        self.assertEqual(plan["checkpoint_selection"], "last epoch")
        self.assertFalse(plan["early_stopping"])
        self.assertFalse(plan["PS"])
        for kwargs in ({"epochs": 31}, {"seeds": (1, 2)}, {"num_layers": 3},
                       {"dropout": 0.4}, {"learning_rate": 0.02}, {"node_count": 2709}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                GCNConfig(**kwargs)

    def test_pseudolabels_and_configuration_are_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.labels[0].class_index = 6
        with self.assertRaises(FrozenInstanceError):
            GCNConfig().epochs = 1

    def test_rejects_duplicate_outside_and_excluded_labels(self):
        for labels in (self.labels + self.labels[:1],
                       self.labels[:-1] + (PseudoLabel(200, 0, 80),),
                       self.labels[:-1] + (PseudoLabel(139, 7, 80),)):
            with self.assertRaises(ValueError):
                gcn_plan(self.selected, labels)
        with self.assertRaises(ValueError):
            gcn_plan(self.selected, self.labels, "primary", excluded_ids=range(5))

    def test_invalid_cohort_ids_fail_closed(self):
        for ids in (self.selected[:-1], self.selected[:-1] + (0,), self.selected[:-1] + (True,),
                    self.selected[:-1] + (-1,)):
            with self.assertRaises(ValueError):
                gcn_plan(ids, self.labels)
        with self.assertRaises(ValueError):
            gcn_plan(self.selected, self.labels, excluded_ids=(1,))
        with self.assertRaises(ValueError):
            gcn_plan(self.selected, self.labels, "primary", excluded_ids=(200,))

    def test_abstention_never_moves_selected_nodes_into_test(self):
        with self.assertRaises(ValueError):
            gcn_plan(self.selected, self.labels[1:])
        plan = gcn_plan(self.selected, self.labels[1:], allow_abstention=True)
        self.assertEqual(plan["abstained_ids"], [0])
        self.assertNotIn(0, plan["test_ids"])
        self.assertEqual(plan["pseudo_y"][0], -1)
        self.assertEqual(plan["train_count"], 139)
        self.assertEqual(plan["common_test_count"], 2568)

    def test_minmax_weights_and_constant_fallback(self):
        values = [30, 60, 90]
        self.assertEqual(confidence_weights(values), (0.0, 0.5, 1.0))
        self.assertEqual(values, [30, 60, 90])
        self.assertEqual(confidence_weights([88, 88]), (1.0, 1.0))
        self.assertEqual(reduce_loss([2, 4, 6], [0, 0.5, 1]), 8 / 3)
        self.assertNotEqual(reduce_loss([2, 4, 6], [0, 0.5, 1]), 8 / 1.5)
        self.assertEqual(reduce_loss([2, 4]), 3)

    def test_wce_config_selects_fixed_weights(self):
        plan = gcn_plan(self.selected, self.labels, config=GCNConfig(loss="wce"))
        self.assertEqual(plan["pipeline"], "weighted_ce")
        self.assertEqual(plan["weights"], list(confidence_weights(l.confidence_percent for l in self.labels)))
        self.assertEqual(plan["loss_reduction"], "mean(CE_i * w_i)")

    def test_loss_and_pipeline_cannot_disagree(self):
        for loss, pipeline in (("ce", "weighted_ce"), ("wce", "ce")):
            with self.subTest(loss=loss), self.assertRaises(ValueError):
                gcn_plan(self.selected, self.labels, config=GCNConfig(loss=loss), pipeline=pipeline)

    def test_nonfinite_boolean_and_invalid_types_rejected(self):
        for value in (True, float("nan"), float("inf"), -1, 101, "80"):
            with self.assertRaises(ValueError):
                confidence_weights([value])
        for value in (True, float("nan"), float("inf"), -1):
            with self.assertRaises(ValueError):
                reduce_loss([value])
        with self.assertRaises(ValueError):
            reduce_loss([1, 2], [1])
        with self.assertRaises(ValueError):
            PseudoLabel(True, 0, 80)

    def test_gt_injection_and_provider_access_are_not_interfaces(self):
        class Poison:
            def __getattribute__(self, name):
                raise AssertionError("GT/data object access attempted")
        with self.assertRaises(ValueError):
            gcn_plan(self.selected, (Poison(),))
        with self.assertRaises(TypeError):
            PseudoLabel(1, 1, 80, y=6)
        with patch.object(socket.socket, "connect", side_effect=AssertionError("network attempted")):
            first = gcn_plan(self.selected, self.labels)
            second = gcn_plan(self.selected, self.labels)
        self.assertEqual(first, second)
        with self.assertRaises(PermissionError):
            train_gcn(Poison(), Poison(), Poison())

    def test_runtime_sources_do_not_import_evaluation(self):
        source = Path(__file__).parents[1] / "src" / "llmgnn_sara" / "downstream"
        for file in source.glob("*.py"):
            tree = ast.parse(file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn("evaluation", node.module or "")

    def test_reviewed_gcn_class_is_identical_ast_to_recovered_class(self):
        root = Path(__file__).parents[1]
        original = ast.parse((root / "recovered_sources/src/models/nn.py").read_text(encoding="utf-8-sig"))
        rebuilt = ast.parse((root / "src/llmgnn_sara/downstream/model.py").read_text(encoding="utf-8"))
        old = next(n for n in ast.walk(original) if isinstance(n, ast.ClassDef) and n.name == "GCN")
        new = next(n for n in ast.walk(rebuilt) if isinstance(n, ast.ClassDef) and n.name == "GCN")
        self.assertEqual(ast.dump(old, include_attributes=False), ast.dump(new, include_attributes=False))

    def test_optional_backend_status_never_installs(self):
        status = backend_status()
        self.assertFalse(status["installed_automatically"])
        if status["missing"]:
            self.assertEqual(synthetic_forward()["forward"], "NOT_RUN")

    @unittest.skipUnless(importlib.util.find_spec("torch") and importlib.util.find_spec("torch_geometric"),
                         "Torch/PyG not installed; no automatic dependency installation")
    def test_tiny_synthetic_forward_only(self):
        self.assertEqual(synthetic_forward()["forward"], "PASS")


class IsolatedEvaluation(unittest.TestCase):
    def test_evaluation_requires_freeze_and_synthetic_alignment(self):
        with self.assertRaises(PermissionError):
            evaluate_frozen((0, 1), (0, 0), decisions_frozen=False)
        result = evaluate_frozen((0, 1), (0, 0), decisions_frozen=True, num_classes=2)
        self.assertEqual(result["accuracy_percent"], 50)
        with self.assertRaises(ValueError):
            evaluate_frozen((0,), (0, 1), decisions_frozen=True)

    def test_paired_population_sd_uses_same_seeds(self):
        result = matched_summary({0: 60, 1: 70}, {0: 64, 1: 72})
        self.assertEqual(result["paired_delta_pp"], {"mean": 3, "population_sd": 1})
        with self.assertRaises(ValueError):
            matched_summary({0: 60}, {1: 64})
        with self.assertRaises(ValueError):
            matched_summary({0: float("nan")}, {0: 64})


if __name__ == "__main__":
    unittest.main()
