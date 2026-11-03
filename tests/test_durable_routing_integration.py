"""Authentic-frozen inputs, synthetic verifier; crash-durable offline replay."""
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llmgnn_sara.evaluation.routing_experiment import exercise_experiment
from llmgnn_sara.io.project import load_project_inputs

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / ".local_artifacts/frozen"
AUTHENTIC = ROOT / ".local_artifacts/authentic"
MANIFEST = ROOT / "manifests/routing_experiment_draft_v1.json"


@unittest.skipUnless(
    (AUTHENTIC / "b1_prompts.json").is_file()
    and (FROZEN / "b1_final_predictions.json").is_file(),
    "External pinned authentic inputs not supplied")
class DurableRoutingIntegrationTests(unittest.TestCase):
    def test_three_arm_replay_after_restart_does_not_redispatch(self):
        inputs = load_project_inputs(FROZEN, AUTHENTIC)
        with tempfile.TemporaryDirectory() as temp:
            private = Path(temp) / "private_fixture"
            with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
                first = exercise_experiment(inputs, MANIFEST, journal_root=private)
                second = exercise_experiment(inputs, MANIFEST, journal_root=private)
            self.assertEqual(first["arms"], second["arms"])
            self.assertEqual(first["synthetic_execution"]["underlying_synthetic_dispatches"], 114)
            self.assertEqual(second["synthetic_execution"]["underlying_synthetic_dispatches"], 0)
            self.assertEqual(second["synthetic_execution"]["completed_unique_identities"], 114)
            self.assertEqual(second["synthetic_execution"]["noncompleted_identities"], 0)
            self.assertEqual(second["provider_calls"], 0)
            self.assertEqual(second["training_runs"], 0)
            self.assertFalse(second["ground_truth_accessed"])
            self.assertEqual(second["journal_persistence"], "SQLITE_FAIL_CLOSED_OFFLINE_FIXTURE_ONLY")


if __name__ == "__main__":
    unittest.main()
