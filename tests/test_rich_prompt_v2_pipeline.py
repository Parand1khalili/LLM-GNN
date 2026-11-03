"""End-to-end prospective prompt opt-in with the existing offline pipeline."""
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llmgnn_sara.sara2.policy import Annotation, Pair
from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.evidence import EvidenceError
from llmgnn_sara.sara3.experiment import VerifiedSelection
from llmgnn_sara.sara3.pipeline import run_offline
from llmgnn_sara.sara3.rich_evidence import RICH_PROMPT_V2, RICH_VERSION

TEXT = "Bayesian inference uses Gaussian process priors and posterior inference."
QUOTE = "Bayesian inference uses Gaussian process priors"


class Fixture:
    offline = True

    def __init__(self):
        self.phases = []

    def blind(self, request):
        self.phases.append("blind")
        return self._response()

    def compare(self, request):
        self.phases.append("compare")
        return self._response()

    def _response(self):
        return {"schema_version": RICH_VERSION, "class_index": 6, "abstain": False,
                "primary_topic": "Bayesian inference",
                "supporting_evidence": [{"source_id": "target.text", "quote": QUOTE,
                                         "claim": "Unreviewed diagnostic claim"}],
                "counter_evidence": [], "auxiliary_method_warning": None,
                "uncertainty_reason": None}


class RichV2OfflineIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.pairs = (Pair(Annotation(130, 6, 91), Annotation(130, 5, 83), TEXT),)

    def test_blind_then_comparison_without_label_promotion(self):
        fixture = Fixture()
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
                result = run_offline(self.pairs, 1, verifier=fixture,
                    audit=PrivateAudit(Path(temp) / "audit"), response_version=RICH_VERSION,
                    prompt_version=RICH_PROMPT_V2)
        self.assertEqual(fixture.phases, ["blind", "compare"])
        self.assertEqual(result["prompt_version"], RICH_PROMPT_V2)
        blind, compare = [x["payload"] for x in result["verifier_inputs"]]
        self.assertEqual(blind["phase"], "blind")
        self.assertNotIn("historical_candidates", blind)
        self.assertNotIn("blind_class_index", blind)
        self.assertEqual(compare["historical_candidates"], [5, 6])
        self.assertEqual(compare["blind_class_index"], 6)
        self.assertIn("Comparison phase only", compare["instructions"])
        self.assertEqual(result["decisions"][0]["reason"], "L2_NOT_ASSESSED")
        self.assertIsNone(result["decisions"][0]["accepted_label"])
        self.assertEqual((result["provider_calls"], result["training_runs"], result["GT_accessed"]), (0, 0, False))

    def test_v1_default_does_not_change(self):
        with tempfile.TemporaryDirectory() as temp:
            result = run_offline(self.pairs, 1, verifier=Fixture(),
                audit=PrivateAudit(Path(temp) / "audit"), response_version=RICH_VERSION)
        self.assertNotIn("prompt_version", result)
        self.assertNotIn("prompt_version", result["verifier_inputs"][0]["payload"])

    def test_invalid_opt_in_and_pinned_manifest_rejected_before_dispatch(self):
        for kwargs, error in (
            ({"prompt_version": RICH_PROMPT_V2}, EvidenceError),
            ({"response_version": RICH_VERSION, "prompt_version": "unknown"}, EvidenceError),
            ({"response_version": RICH_VERSION, "prompt_version": RICH_PROMPT_V2,
              "selection": VerifiedSelection(b"unused", "r0")}, ValueError),
        ):
            fixture = Fixture()
            with self.subTest(kwargs=kwargs), self.assertRaises(error):
                run_offline(self.pairs, 1, verifier=fixture, **kwargs)
            self.assertEqual(fixture.phases, [])


if __name__ == "__main__":
    unittest.main()
