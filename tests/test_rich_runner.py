"""Real Rich Prompt V2 offline resume and router integration, no network/GT."""
from dataclasses import replace
import copy
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from llmgnn_sara.io.project import load_project_inputs
from llmgnn_sara.sara2.policy import Annotation, Pair
from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.automated_policy import VERSION as AUTO
from llmgnn_sara.sara3.durable_rich import DurableRichOfflineVerifier
from llmgnn_sara.sara3.experiment import FIXTURE_VERSION
from llmgnn_sara.sara3.pipeline import run_offline
from llmgnn_sara.sara3.rich_evidence import RICH_PROMPT_V2, RICH_VERSION
from llmgnn_sara.sara3.runner import SyntheticRichVerifier, _context, dry_run, offline_run
from llmgnn_sara.sara3.selection import select_router
from llmgnn_sara.downstream.prospective import offline_report_digest

TEXT = ("Bayesian classification uses Gaussian process priors and approximate "
        "posterior inference to characterize probabilistic learning models. "
        "This long abstract is exclusively a synthetic test fixture.")
LABEL = hashlib.sha256(TEXT.encode("utf-8")).digest()[0] % 7


def pairs():
    return (Pair(Annotation(130, (LABEL + 1) % 7, 90),
                 Annotation(130, LABEL, 85), TEXT),
            Pair(Annotation(682, 6, 90), Annotation(682, 6, 92), TEXT))


def fake_inputs(rows=None):
    return SimpleNamespace(pairs=rows or pairs(), provenance=())


def execute(rows, root, *, verifier=None, budget=1, router="r0"):
    selected, context = _context(fake_inputs(rows), router, budget)
    journal = PrivateAudit(Path(root) / "journal")
    phases = PrivateAudit(Path(root) / "phases")
    delegate = verifier or SyntheticRichVerifier()
    durable = DurableRichOfflineVerifier(delegate, context, journal,
                                         maximum_calls=2 * len(selected))
    with patch.object(socket.socket, "connect",
                      side_effect=AssertionError("Network forbidden")):
        run = run_offline(rows, budget, router=router, verifier=durable,
                          audit=phases, response_version=RICH_VERSION,
                          prompt_version=RICH_PROMPT_V2,
                          automated_arbitration_version=AUTO)
    return run, durable, delegate


class RichDurableTests(unittest.TestCase):
    def test_dry_run_builds_blind_without_dispatch_or_prior_votes(self):
        report = dry_run(fake_inputs(), "r0", 1)
        self.assertEqual((report["selected_count"], report["provider_calls"],
                          report["maximum_conditional_calls"]), (1, 0, 2))
        self.assertEqual(len(report["blind_payload_sha256"]), 1)
        self.assertEqual(report["GT_accessed"], False)

    def test_two_phase_resume_exact_report_and_zero_new_dispatches(self):
        rows = pairs()
        with tempfile.TemporaryDirectory() as t:
            first, journal, fixture = execute(rows, t)
            self.assertEqual(journal.dispatches, 2)
            self.assertEqual(journal.hits, 0)
            self.assertEqual(fixture.dispatches, 2)
            self.assertEqual(first["selected_node_ids"], [130])
            self.assertEqual(first["provider_calls"], 0)
            self.assertEqual(first["provisional_count"], 1)
            d = first["decisions"][0]
            self.assertEqual((d["decision"], d["accepted"], d["training_class_index"],
                              d["provisional_class_index"], d["l2_status"]),
                             ("PROPOSE", False, None, LABEL, "NOT_ASSESSED"))
            blind = next(x["payload"] for x in first["verifier_inputs"]
                         if x["request_id"] == "offline:130:blind")
            self.assertNotIn("historical_candidates", blind)
            self.assertNotIn("blind_class_index", blind)
            self.assertEqual(list(journal.states.values()), ["COMPLETED", "COMPLETED"])
            second, journal2, fixture2 = execute(rows, t)
            self.assertEqual((journal2.dispatches, journal2.hits,
                              fixture2.dispatches), (0, 2, 0))
            self.assertEqual(first, second)
            self.assertEqual(offline_report_digest(first), offline_report_digest(second))

    def test_incompatible_context_does_not_dispatch(self):
        with tempfile.TemporaryDirectory() as t:
            first, _, _ = execute(pairs(), t)
            changed = (replace(pairs()[0], text=TEXT + " Updated scientific text."), pairs()[1])
            with self.assertRaises(ValueError):
                execute(changed, t)
            ctx = _context(fake_inputs(pairs()), "r0", 1)[1]
            ctx["model_settings"]["model"] = "incompatible"
            with self.assertRaises(ValueError):
                DurableRichOfflineVerifier(SyntheticRichVerifier(), ctx,
                    PrivateAudit(Path(t) / "journal"), maximum_calls=2)
            with self.assertRaises(ValueError):
                execute(pairs(), t, budget=2)

    def test_invalid_l1_is_rejected_and_never_reissued(self):
        class Bad(SyntheticRichVerifier):
            def _respond(self, request):
                raw = super()._respond(request)
                raw["supporting_evidence"][0]["quote"] = "Fabricated citation absent from the article"
                return raw
        with tempfile.TemporaryDirectory() as t:
            run, durable, bad = execute(pairs(), t, verifier=Bad())
            self.assertEqual((durable.dispatches, bad.dispatches), (1, 1))
            self.assertIn("REJECTED", durable.states.values())
            self.assertEqual(run["provisional_count"], 0)
            again, resumed, fake = execute(pairs(), t)
            self.assertEqual((resumed.dispatches, fake.dispatches), (0, 0))
            self.assertIn("REJECTED", resumed.states.values())

    def test_crash_unknown_does_not_auto_retry(self):
        class Fail(SyntheticRichVerifier):
            def blind(self, request):
                self.dispatches += 1
                raise TimeoutError("synthetic crash after possible dispatch")
        with tempfile.TemporaryDirectory() as t:
            run, durable, failed = execute(pairs(), t, verifier=Fail())
            self.assertEqual((durable.dispatches, failed.dispatches), (1, 1))
            self.assertIn("UNCERTAIN", durable.states.values())
            again, resumed, fake = execute(pairs(), t)
            self.assertEqual((resumed.dispatches, fake.dispatches), (0, 0))

    def test_comparison_without_saved_blind_is_denied(self):
        from llmgnn_sara.sara3.pipeline import ComparisonRequest
        rows = pairs()
        with tempfile.TemporaryDirectory() as t:
            selected, ctx = _context(fake_inputs(rows), "r0", 1)
            durable = DurableRichOfflineVerifier(
                SyntheticRichVerifier(), ctx, PrivateAudit(Path(t) / "journal"),
                maximum_calls=2)
            with self.assertRaises(ValueError):
                durable.compare(ComparisonRequest(130, TEXT,
                    tuple(sorted({rows[0].b1.class_index, LABEL})), LABEL))

    def test_unrouted_80_percent_is_reconstruction_not_semantic_approval(self):
        with tempfile.TemporaryDirectory() as t:
            run, durable, _ = execute(pairs(), t)
        d = run["decisions"][1]
        self.assertTrue(d["accepted"])
        self.assertEqual(d["label_source"], "FROZEN_AGREEMENT_RECONSTRUCTED_80")
        self.assertEqual(d["l2_status"], "NOT_APPLICABLE_BASELINE_POLICY")
        self.assertEqual(run["accepted_count"], 1)

    def test_fixed_r1_r2_router_variants_select_37_deterministically(self):
        rows = tuple(Pair(Annotation(i, i % 7, 90), Annotation(i, (i + 1) % 7, 70),
                          TEXT + str(i)) for i in range(140))
        for router in ("r0", "semantic", "r1_v1", "r1_v2", "r2_v1"):
            with self.subTest(router=router):
                selected = select_router(rows, 37, router)
                self.assertEqual((len(selected), len(set(selected))), (37, 37))
                self.assertEqual(selected, select_router(tuple(reversed(rows)), 37, router))
        with self.assertRaises(ValueError):
            select_router(rows, 36, "r2_v1")


    def test_140_synthetic_offline_runner_exports_plan_and_resumes_without_network(self):
        rows = tuple(Pair(Annotation(i, (i + 1) % 7, 89),
                          Annotation(i, i % 7, 86), TEXT + " node " + str(i))
                     for i in range(140))
        class DummyFrozen:
            def by_arm(self, arm):
                return ()
        inputs = SimpleNamespace(pairs=rows, provenance=(), frozen=DummyFrozen())
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / ".local_artifacts" / "synthetic_runner"
            with patch.object(socket.socket, "connect",
                              side_effect=AssertionError("Network forbidden")):
                first = offline_run(inputs, root, router="r0", budget=37)
                second = offline_run(inputs, root, router="r0", budget=37)
            self.assertEqual((first["denominator"], first["selected_count"]), (140, 37))
            self.assertEqual(first["new_fixture_dispatches"], 74)
            self.assertEqual(second["new_fixture_dispatches"], 0)
            self.assertEqual(second["successful_fixture_replays"], 74)
            self.assertEqual(first["private_report_sha256"], second["private_report_sha256"])
            self.assertEqual(first["gc_plan_status"], "PLAN_ONLY")
            self.assertEqual(first["status"], "COMPLETE_SYNTHETIC")
            self.assertEqual(first["GT_accessed"], False)
            self.assertEqual(first["provider_calls"], 0)
            self.assertEqual(first["training_runs"], 0)
            self.assertEqual(sum(first["provisional_class_distribution"].values()),
                             first["provisional_count"])



ROOT = Path(__file__).resolve().parents[1]
FROZEN, AUTHENTIC = ROOT / ".local_artifacts/frozen", ROOT / ".local_artifacts/authentic"


@unittest.skipUnless((FROZEN / "b1_final_predictions.json").is_file()
                     and (AUTHENTIC / "b1_prompts.json").is_file(),
                     "Private pinned Cora inputs not available on this checkout")
class Authentic140RunnerTests(unittest.TestCase):
    def test_synthetic_140_with_exact_37_and_durable_replay(self):
        inputs = load_project_inputs(FROZEN, AUTHENTIC)
        files = list(FROZEN.glob("*.json")) + list(AUTHENTIC.glob("*.json"))
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / ".local_artifacts" / "synthetic_runner"
            first = offline_run(inputs, root, router="r0", budget=37)
            second = offline_run(inputs, root, router="r0", budget=37)
            self.assertEqual(first["status"], "COMPLETE_SYNTHETIC")
            self.assertEqual(first["selected_count"], 37)
            self.assertEqual(first["denominator"], 140)
            self.assertEqual(second["new_fixture_dispatches"], 0)
            self.assertEqual(first["private_report_sha256"],
                             second["private_report_sha256"])
            self.assertEqual(first["provider_calls"], 0)
            self.assertEqual(first["training_runs"], 0)
            self.assertEqual(first["GT_accessed"], False)
            self.assertEqual(sum(first["provisional_class_distribution"].values()),
                             first["provisional_count"])
        self.assertEqual(before, {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in files})


if __name__ == "__main__":
    unittest.main()
