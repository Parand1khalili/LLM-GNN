"""Review-only perturbations and unchanged verifier contract; no human data."""
from dataclasses import asdict
import hashlib
import io
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from llmgnn_sara.io.project import PINS, load_project_inputs
from llmgnn_sara.sara2.policy import Annotation, Pair, pair_from_frozen
from llmgnn_sara.sara3.r2_candidate import select_r2
from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.inputs import canonical_bytes, verifier_input
from llmgnn_sara.sara3.pipeline import run_offline
from llmgnn_sara.evaluation.router_robustness import (
    SEEDS, ORDERS, STAGES, review_selection, request_fingerprints, robustness_review)
from llmgnn_sara.evaluation.r2_comparison import compare_r2
from llmgnn_sara.evaluation.routing_experiment import synthetic_source_excerpt

ROOT = Path(__file__).resolve().parents[1]
FROZEN, AUTHENTIC = ROOT / ".local_artifacts/frozen", ROOT / ".local_artifacts/authentic"


def pair(n, text="rule neural"):
    return Pair(Annotation(n, 0, 95), Annotation(n, 1, 85), text)


class PerturbationTests(unittest.TestCase):
    def test_shadow_primary_metadata_matches_production_for_edge_pools(self):
        for mode in ("covered", "unknown", "mixed"):
            rows = [pair(n, "" if mode == "unknown" or (mode == "mixed" and n % 2) else "rule") for n in range(45)]
            self.assertEqual(review_selection(rows), select_r2(rows))

    def test_all24_scenarios_budget_uniqueness_provenance_and_reproducibility(self):
        rows = [pair(n, "" if n % 3 else "rule") for n in range(45)]
        for seed in SEEDS:
            for order in ORDERS:
                result = review_selection(rows, seed, order)
                ids = result["selected_node_ids_admission_order"]
                self.assertEqual(len(set(ids)), 37)
                self.assertEqual(result, review_selection(reversed(rows), seed, order))
                self.assertEqual([s["stage"] for s in result["stages"][:3]], list(order))
                self.assertEqual(ids, [n for s in result["stages"] for n in s["admitted_node_ids"]])

    def test_only_prespecified_variants_and_validated_inputs(self):
        for args in (("arbitrary", STAGES), ("primary", tuple(reversed(STAGES)) + ("extra",))):
            with self.assertRaises(ValueError): review_selection([pair(n) for n in range(40)], *args)
        with self.assertRaises(ValueError): review_selection([pair(n) for n in range(36)])
        with self.assertRaises(TypeError): review_selection([{"gt": 0}] * 40)
        with self.assertRaises(ValueError): review_selection([pair(0)] * 40)

    def test_counterfactual_gt_remains_unread(self):
        class Forbidden:
            def __bool__(self): raise AssertionError("GT accessed")
        source = {"class_index": 0, "confidence_percent_before_tensor_cast": 95,
                  "y": Forbidden(), "correctness": Forbidden()}
        rows = [pair_from_frozen(n, source, source, "rule") for n in range(40)]
        self.assertEqual(review_selection(rows), select_r2(rows))


@unittest.skipUnless((AUTHENTIC / "b1_prompts.json").is_file() and
    (FROZEN / "b1_final_predictions.json").is_file(), "Authentic inputs unavailable")
class AuthenticRobustnessTests(unittest.TestCase):
    def test_review_read_boundary_hashes_and_immutability(self):
        allowed = {FROZEN / n for n in ("b1_final_predictions.json", "narrative_v0_final_predictions.json",
                                       "selection_manifest.json", "preparation_receipt.json")}
        allowed.update(AUTHENTIC / n for n in PINS)
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in allowed}
        allowed.update(ROOT / n for n in ("docs/ROUTER_ROBUSTNESS_SCOPE.md", "docs/R2_CANDIDATE.md"))
        os_open, io_open = os.open, io.open
        def guarded_os(path, *args, **kwargs):
            self.assertIn(Path(path).resolve(), allowed)
            return os_open(path, *args, **kwargs)
        def guarded_io(path, *args, **kwargs):
            if type(path) is not int: self.assertIn(Path(path).resolve(), allowed)
            return io_open(path, *args, **kwargs)
        with patch.object(os, "open", side_effect=guarded_os), patch.object(io, "open", side_effect=guarded_io), \
             patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            inputs = load_project_inputs(FROZEN, AUTHENTIC)
            snapshot = tuple(asdict(p) for p in inputs.pairs)
            report = robustness_review(inputs)
            self.assertEqual(report, robustness_review(inputs))
            self.assertEqual(snapshot, tuple(asdict(p) for p in inputs.pairs))
        self.assertEqual(len(report["scenarios"]), 24)
        self.assertEqual(len(report["canonical_requests_by_node"]), 140)
        self.assertEqual(len(report["source_hashes"]), 9)
        self.assertTrue(report["primary_r2_exact_metadata_match"])
        self.assertTrue(all(n["target_available"] and n["authentic_neighborhood_available"]
                            for n in report["canonical_requests_by_node"].values()))
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before})

    def test_five_selections_keep_actual_runtime_requests_and_conditional_protocol(self):
        inputs = load_project_inputs(FROZEN, AUTHENTIC)
        by_id = {p.node_id: p for p in inputs.pairs}
        comparison = compare_r2(inputs)
        seen_payloads = {}
        class ProtocolFixture:
            offline = True
            def blind(self, request):
                abstain = request.node_id % 3 == 0
                return {"class_index": None if abstain else 0, "abstain": abstain,
                        "evidence": [] if abstain else [synthetic_source_excerpt(request.text)]}
            def compare(self, request):
                abstain = request.node_id % 3 == 1
                return {"class_index": None if abstain else 0, "abstain": abstain,
                        "evidence": [] if abstain else [synthetic_source_excerpt(request.text)]}
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            for index, result in enumerate(comparison["routers"].values()):
                ids = result["selected_node_ids"]
                # Inject the selected IDs at the production selection interface.
                with patch("llmgnn_sara.sara3.pipeline.select_router", return_value=tuple(ids)):
                    run = run_offline(inputs.pairs, 37, "r0", ProtocolFixture(),
                                      audit=PrivateAudit(Path(temp) / str(index)))
                expected_calls = 37 + sum(node % 3 != 0 for node in ids)
                self.assertEqual(run["mock_verifier_calls"], expected_calls)
                self.assertEqual(run["provider_calls"], 0)
                self.assertEqual(run["selected_node_ids"], ids)
                for request in run["verifier_inputs"]:
                    payload = request["payload"]
                    node, phase = payload["node_id"], payload["phase"]
                    p = by_id[node]
                    expected = verifier_input(node, p.text, p.neighborhood,
                        **({"candidates": (p.b1.class_index, p.narrative_v0.class_index), "blind_class": 0}
                           if phase == "compare" else {}))
                    self.assertEqual(payload, expected)
                    key = (node, phase)
                    encoded = canonical_bytes(payload)
                    self.assertEqual(encoded, seen_payloads.setdefault(key, encoded))
                    if phase == "blind":
                        self.assertNotIn("historical_candidates", payload)
                        self.assertNotIn("confidence", payload)
                        self.assertEqual(request["sha256"], request_fingerprints(p)["legacy"]["blind_sha256"])
                for node in ids:
                    phases = [r["payload"]["phase"] for r in run["verifier_inputs"] if r["payload"]["node_id"] == node]
                    self.assertEqual(phases, ["blind"] if node % 3 == 0 else ["blind", "compare"])
                self.assertFalse(any(d["accepted"] for d in run["decisions"] if d["routed_for_review"]))


if __name__ == "__main__":
    unittest.main()
