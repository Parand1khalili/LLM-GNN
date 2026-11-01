"""Real frozen input integration with deterministic, explicitly synthetic responses."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

from llmgnn_sara.io.frozen import InputError
from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.replay import CASES, main, replay_authentic

ROOT = Path(__file__).resolve().parents[1]
FROZEN, AUTHENTIC = ROOT / ".local_artifacts/frozen", ROOT / ".local_artifacts/authentic"


@unittest.skipUnless((AUTHENTIC / "b1_prompts.json").is_file()
                     and (FROZEN / "b1_final_predictions.json").is_file(), "External authentic inputs not provided")
class AuthenticReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.audit_root = Path(cls.temp.name) / "private replay"
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            cls.report = replay_authentic(FROZEN, AUTHENTIC, cls.audit_root)

    def test_all_cases_and_normalized_abstentions(self):
        report = self.report
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["case_count"], 11)
        self.assertEqual({r["case"] for r in report["cases"]}, {c[0] for c in CASES})
        for row in report["cases"]:
            self.assertIsNone(row["accepted_label"])
            self.assertTrue(row["normalized_abstention"])
            self.assertEqual(row["l2_status"], "NOT_ASSESSED")
        self.assertFalse(report["GT_accessed"])
        self.assertEqual(report["frozen_input_immutability"], "PASS")

    def test_irrelevant_genuine_quote_gets_no_semantic_approval(self):
        row = next(r for r in self.report["cases"] if r["case"] == "irrelevant_genuine_quotation")
        self.assertEqual(row["audit"]["l1_statuses"], ["PASS", "PASS"])
        self.assertEqual(row["reason"], "L2_NOT_ASSESSED")
        self.assertIn("NOT_L2_APPROVAL", row["semantic_diagnostic"])
        self.assertIsNone(row["accepted_label"])

    def test_sources_faults_and_audit_only_proposal(self):
        rows = {r["case"]: r for r in self.report["cases"]}
        self.assertEqual(rows["unknown_source"]["explicit_source_boundary_reason"], "L1_UNKNOWN_SOURCE")
        self.assertEqual(rows["unknown_source"]["reason"], "L1_CLAIM_SCHEMA_INVALID")
        self.assertEqual(rows["audit_write_failure"]["audit"]["records_verified"], 0)
        self.assertEqual(rows["audit_write_failure"]["audit_availability"], "EXPECTED_INJECTED_FAILURE")
        self.assertEqual(rows["uncertain_comparison"]["audit"]["response_records"], 2)
        self.assertEqual(rows["uncertain_comparison"]["audit"]["raw_responses_available"], 1)
        self.assertEqual(rows["third_class"]["audit"]["private_proposals"], 1)

    def test_full140_masks_blind_evidence_and_private_raw(self):
        for router, row in self.report["full140"].items():
            self.assertEqual((row["targets"], row["reviewed"], row["reviewed_accepted"]), (140, 37, 0))
            self.assertEqual(row["mock_calls"], 74)
            self.assertEqual(row["audit"]["raw_responses_available"], 74)
            self.assertEqual(row["training_mask_check"], "PASS")
            audit = PrivateAudit(self.audit_root / ("full140_" + router))
            self.assertEqual(len(list(audit.root.glob("*.json"))), 111)
        self.assertNotIn('"raw_response":', json.dumps(self.report))
        self.assertNotIn("All rights reserved.", json.dumps(self.report))

    def test_cli_replay_is_deterministic_across_audit_roots(self):
        args = ["replay", "--frozen-root", str(FROZEN), "--authentic-root", str(AUTHENTIC),
                "--audit-root", str(Path(self.temp.name) / "second private replay")]
        with patch.object(sys, "argv", args), contextlib.redirect_stdout(io.StringIO()) as output, \
                patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            main()
        self.assertEqual(json.loads(output.getvalue()), self.report)

    def test_hash_admission_rejects_diagnostic_injection_before_audit(self):
        with tempfile.TemporaryDirectory() as base:
            Path(base, "b1_final_predictions.json").write_text('{"y":[0],"correctness":true}', encoding="utf-8")
            with patch("llmgnn_sara.sara3.replay.PrivateAudit", side_effect=AssertionError("Audit reached")), \
                    self.assertRaisesRegex(InputError, "SHA-256 mismatch"):
                replay_authentic(base, AUTHENTIC, Path(base) / "audit")

    def test_historical_p0_and_six_node_seals_unchanged(self):
        for relative, expected in (
            ("manifests/historical_p0.json", "7affacee222dbec3ecb5710b038968543c19d252190ee6eab76c5b03a4307410"),
            (".local_artifacts/pilot-gapapi/SHA256.json", "29fa95c7d34f5826b628509e6bad2baced83ac986ebfbc7cadc4bb36d4c31b41"),
            (".local_artifacts/pilot-gapapi/pilot/SHA256.json", "9fd65d82e3cab296afc503813b97b0c0af9e8f4dcb41cd0be1aa20ac34ef1f96")):
            path = ROOT / relative
            if not path.exists(): self.skipTest("Preserved seal not provided")
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)
