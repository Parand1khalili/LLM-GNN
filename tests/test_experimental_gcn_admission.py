"""Opt-in GCN planning: provisional labels stay quarantined by default."""
import copy
import hashlib
import re
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llmgnn_sara.downstream.plan import GCNConfig
from llmgnn_sara.downstream.prospective import (
    VERSION, controlled_gcn_plan, frozen_pair_digest, offline_report_digest)
from llmgnn_sara.io.project import load_project_inputs
from llmgnn_sara.sara2.policy import Annotation, Pair
from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.automated_policy import VERSION as POLICY
from llmgnn_sara.sara3.pipeline import run_offline
from llmgnn_sara.sara3.rich_evidence import RICH_PROMPT_V2, RICH_VERSION

TEXT = ("Bayesian inference uses Gaussian process priors and posterior inference. "
        "Artificial neural networks are auxiliary to the Bayesian model.")


class Fixture:
    offline = True

    def __init__(self, pairs):
        self.by_id = {p.node_id: p for p in pairs}
        self.calls = []

    def _out(self, request, phase):
        self.calls.append((phase, request.node_id))
        text = request.text
        start = re.search(r"[A-Za-z0-9]+", text)
        if start is None:
            return {"schema_version": RICH_VERSION, "class_index": None,
                    "abstain": True, "primary_topic": None, "supporting_evidence": [],
                    "counter_evidence": [], "auxiliary_method_warning": None,
                    "uncertainty_reason": "No eligible source excerpt"}
        quote = text[start.start():start.start() + 180].rstrip('"“”')
        return {"schema_version": RICH_VERSION,
                "class_index": self.by_id[request.node_id].narrative_v0.class_index,
                "abstain": False, "primary_topic": "Synthetic diagnostic topic",
                "supporting_evidence": [{"source_id": "target.text", "quote": quote,
                    "claim": "Fixture only; no scientific meaning inferred"}],
                "counter_evidence": [], "auxiliary_method_warning": None,
                "uncertainty_reason": None}

    def blind(self, request):
        return self._out(request, "blind")

    def compare(self, request):
        return self._out(request, "compare")


def sample():
    return (Pair(Annotation(130, 5, 91), Annotation(130, 6, 83), TEXT),
            Pair(Annotation(682, 6, 90), Annotation(682, 6, 90), TEXT))


def run_sample(rows, budget=1):
    fixture = Fixture(rows)
    with tempfile.TemporaryDirectory() as folder:
        with patch.object(socket.socket, "connect",
                          side_effect=AssertionError("Network forbidden")):
            report = run_offline(rows, budget, verifier=fixture,
                audit=PrivateAudit(Path(folder) / "private"),
                response_version=RICH_VERSION, prompt_version=RICH_PROMPT_V2,
                automated_arbitration_version=POLICY)
    return report, fixture.calls


def admit(rows, report, *, settings=None, **override):
    args = {"admission_version": VERSION,
            "frozen_pairs_sha256": frozen_pair_digest(rows),
            "report_sha256": offline_report_digest(report),
            "config": settings or GCNConfig(node_count=700, strict_historical=False)}
    args.update(override)
    return controlled_gcn_plan(rows, report, **args)


class ExperimentalAdmissionContracts(unittest.TestCase):
    def setUp(self):
        self.rows = sample()
        self.report, self.calls = run_sample(self.rows)

    def test_explicit_plan_accepts_proposal_only_after_versioned_pins(self):
        r = self.report
        self.assertEqual(self.calls, [("blind", 130), ("compare", 130)])
        d = r["decisions"][0]
        self.assertEqual((d["decision"], d["provisional_class_index"]), ("PROPOSE", 6))
        self.assertEqual((d["accepted"], d["training_class_index"], d["accepted_label"]),
                         (False, None, None))
        self.assertEqual((r["accepted_count"], r["provisional_count"]), (1, 1))
        self.assertEqual((r["coverage"], r["provisional_coverage"]), (.5, .5))
        self.assertFalse(r["provisional_pseudo_labels"][0]["training_eligible"])
        plan = admit(self.rows, r)
        self.assertEqual((plan["train_ids"], plan["admitted_provisional_ids"],
                          plan["admitted_baseline_ids"]), ([130, 682], [130], [682]))
        self.assertEqual(plan["pseudo_y"][130], 6)
        self.assertEqual(plan["training_runs"], 0)
        self.assertEqual(plan["l2_semantic_validation"], "NOT_PERFORMED")
        self.assertIn("PLAN_ONLY", plan["authorization"])

    def test_default_adapter_refuses_forged_reviewed_acceptance(self):
        from llmgnn_sara.downstream.frozen import plan_from_frozen
        class Dataset:
            predictions = ()
            target_ids = (130, 682)
            def by_arm(self, arm):
                return ()
        decisions = copy.deepcopy(self.report["decisions"])
        decisions[0].update(accepted=True, training_class_index=6, accepted_label=6,
                            abstain=False)
        with self.assertRaises(ValueError):
            plan_from_frozen(Dataset(), "sensitivity", "ce", accepted=decisions)

    def test_repin_does_not_bypass_policy_invariants(self):
        cases = (
            ("accepted", lambda r: r["decisions"][0].update(accepted=True)),
            ("training_label", lambda r: r["decisions"][0].update(training_class_index=6)),
            ("fake_l2", lambda r: r["decisions"][0].update(l2_status="PASS")),
            ("third_class", lambda r: r["decisions"][0].update(provisional_class_index=1)),
            ("fake_screen", lambda r: r["decisions"][0].update(automated_screen_status="REJECT")),
            ("public_promotion", lambda r: r["provisional_pseudo_labels"][0].update(training_eligible=True)),
            ("baseline_confidence", lambda r: r["decisions"][1].update(label_confidence_percent=100)),
            ("no_routing", lambda r: r.update(selected_node_ids=[])),
            ("gt_injection", lambda r: r.update(ground_truth_labels=[6])),
            ("policy_threshold", lambda r: r["policy"].update(agreement_acceptance_percent=60.0)))
        for name, mutate in cases:
            with self.subTest(case=name):
                bad = copy.deepcopy(self.report)
                mutate(bad)
                with self.assertRaises(ValueError):
                    admit(self.rows, bad)

    def test_invalid_version_or_pins_rejected(self):
        for change in ({"report_sha256": "0" * 64},
                       {"frozen_pairs_sha256": "0" * 64},
                       {"admission_version": "unknown"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                admit(self.rows, self.report, **change)

    def test_no_mutation_and_no_network(self):
        before = copy.deepcopy(self.report)
        with patch.object(socket.socket, "connect",
                          side_effect=AssertionError("Network forbidden")):
            self.assertEqual(admit(self.rows, self.report), admit(self.rows, self.report))
        self.assertEqual(self.report, before)

    def test_wce_only_builds_a_plan(self):
        plan = admit(self.rows, self.report,
                     settings=GCNConfig(loss="wce", node_count=700, strict_historical=False))
        self.assertEqual(plan["pipeline"], "weighted_ce")
        self.assertEqual(plan["training_runs"], 0)


ROOT = Path(__file__).resolve().parents[1]
FROZEN, AUTHENTIC = ROOT / ".local_artifacts/frozen", ROOT / ".local_artifacts/authentic"


@unittest.skipUnless((AUTHENTIC / "b1_prompts.json").is_file() and
                     (FROZEN / "b1_final_predictions.json").is_file(),
                     "Private authentic frozen Cora data not available")
class AuthenticCoraProvisionalIntegration(unittest.TestCase):
    def test_140_frozen_37_routed_synthetic_no_gt_or_training(self):
        roots = sorted(list(FROZEN.glob("*.json")) + list(AUTHENTIC.glob("*.json")))
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in roots}
        inputs = load_project_inputs(FROZEN, AUTHENTIC)
        report, calls = run_sample(inputs.pairs, budget=37)
        self.assertEqual((report["target_count"], report["review_count"]), (140, 37))
        self.assertEqual(report["mock_verifier_calls"], len(calls))
        self.assertEqual(report["accepted_count"] + report["abstention_count"], 140)
        self.assertEqual(sum(report["provisional_class_distribution"].values()),
                         report["provisional_count"])
        self.assertTrue(all(d["training_class_index"] is None for d in report["decisions"]
                            if d["routed_for_review"]))
        self.assertEqual((report["GT_accessed"], report["provider_calls"],
                          report["training_runs"]), (False, 0, 0))
        plan = controlled_gcn_plan(inputs.pairs, report, admission_version=VERSION,
            frozen_pairs_sha256=frozen_pair_digest(inputs.pairs),
            report_sha256=offline_report_digest(report), config=GCNConfig())
        self.assertEqual(plan["train_count"],
                         report["accepted_count"] + report["provisional_count"])
        self.assertEqual(plan["common_test_count"], 2568)
        self.assertEqual(before, {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in roots})


if __name__ == "__main__":
    unittest.main()
