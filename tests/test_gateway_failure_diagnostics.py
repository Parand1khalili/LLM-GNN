"""Read-only and GT-free diagnostics against the immutable closeout report."""
import copy
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from llmgnn_sara.sara3 import gateway_failure_diagnostics as diagnostic
from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.automated_policy import VERSION as POLICY_VERSION
from llmgnn_sara.sara3.gateway_closeout import VERSION as FREEZE_VERSION
from test_gateway_closeout import ReadOnlyCloseoutTests


def fixture():
    def node(n, reason, *, b1=0, narr=1, blind=None, compare=None,
             third=None, screened=False):
        d = {"node_id": n, "routed_for_review": True,
             "accepted": False, "training_class_index": None,
             "l2_status": "NOT_ASSESSED", "semantic_validation": "NOT_PERFORMED",
             "provisional_status": "NOT_PROPOSED", "reason": reason,
             "b1_class_index": b1, "narrative_v0_class_index": narr,
             "blind_class_index": blind, "comparison_class_index": compare,
             "third_class_proposal": third,
             "evidence": "PRIVATE ARTICLE TEXT THAT MUST NEVER PRINT"}
        if screened:
            d.update(automated_policy_version=POLICY_VERSION,
                     automated_screen_reason=reason,
                     automated_screen_status=("REJECT"
                         if reason == "THIRD_CLASS_DIAGNOSTIC_ONLY" else "ABSTAIN"))
        return d
    run = {"selected_node_ids": [1, 2, 3],
           "decisions": [
               node(1, "COUNTER_EVIDENCE_UNRESOLVED", blind=0,
                    compare=0, screened=True),
               node(2, "THIRD_CLASS_DIAGNOSTIC_ONLY", blind=4,
                    compare=4, third=4, screened=True),
               node(3, "BLIND_ABSTENTION"),
               {"node_id": 4, "accepted": True,
                "training_class_index": 6, "routed_for_review": False}],
           "provisional_count": 0}
    frozen = {
        "schema": FREEZE_VERSION, "freeze_version": FREEZE_VERSION,
        "arbitration_policy_version": POLICY_VERSION,
        "private_report_reconciled": True,
        "receipt_identity_integrity_verified": True,
        "no_cross_journal_duplicate": True,
        "training_admission": False, "GT_accessed": False,
        "amendment_sha256": "a" * 64, "routed_nodes": 3,
        "cohort_size": 4, "private_report_sha256": "b" * 64,
        "persisted_proposals": 0,
        "automated_concordance": {
            "screened_pairs": 2, "proposals": 0,
            "proposal_reasons": {"PROVISIONAL_CROSS_PHASE_CONCORDANCE": 0},
            "veto_or_abstain_reasons": {
                "COUNTER_EVIDENCE_UNRESOLVED": 1,
                "THIRD_CLASS_DIAGNOSTIC_ONLY": 1,
                "BLIND_ABSTENTION": 1}}}
    report = {"kind": "gapgpt_continuation_private_report",
              "amendment_sha256": "a" * 64, "run": run}
    return frozen, report


class FailureDiagnosticTests(unittest.TestCase):
    def test_candidate_agreement_and_third_class_are_metadata_only(self):
        freeze, report = fixture()
        originals = copy.deepcopy((freeze, report))
        with patch.object(socket.socket, "connect",
                          side_effect=AssertionError("Unexpected network access")):
            result = diagnostic.diagnose(freeze, report, freeze_sha256="f" * 64)
        self.assertEqual((freeze, report), originals)
        self.assertNotIn("PRIVATE ARTICLE TEXT", json.dumps(result))
        self.assertEqual(result["screened_pairs"], 2)
        self.assertEqual(result["routed_nodes"], 3)
        counter = result["target_diagnostics"]["COUNTER_EVIDENCE_UNRESOLVED"]
        self.assertEqual(counter["cross_phase_class_agreement"], 1)
        self.assertEqual(counter["blind_third_class"], 0)
        third = result["target_diagnostics"]["THIRD_CLASS_DIAGNOSTIC_ONLY"]
        self.assertEqual(third["blind_third_class"], 1)
        self.assertEqual(third["comparison_third_class"], 1)
        self.assertEqual(third["both_phases_third_class"], 1)
        self.assertEqual(third["third_class_distribution"], {"4": 1})
        self.assertFalse(result["training_admission"])

    def test_fail_closed_on_report_or_admission_tampering(self):
        for mutation in ("admit", "reason", "third", "freeze", "selection"):
            freeze, report = fixture()
            if mutation == "admit":
                report["run"]["decisions"][0]["accepted"] = True
            elif mutation == "reason":
                report["run"]["decisions"][0]["reason"] = "OTHER"
            elif mutation == "third":
                report["run"]["decisions"][1]["third_class_proposal"] = 1
            elif mutation == "freeze":
                freeze["automated_concordance"]["screened_pairs"] = 3
            elif mutation == "selection":
                report["run"]["selected_node_ids"][1] = 1
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):
                    diagnostic.diagnose(freeze, report, freeze_sha256="f" * 64)

    def test_content_address_checks_detect_modification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "closeout_v1"
            target.mkdir()
            blob = b'{"schema":"example"}\n'
            sha = hashlib.sha256(blob).hexdigest()
            file = target / (sha + ".json")
            file.write_bytes(blob)
            self.assertEqual(
                diagnostic._read_content_addressed(root, ("closeout_v1",), sha),
                {"schema": "example"})
            file.write_bytes(blob + b" ")
            with self.assertRaises(ValueError):
                diagnostic._read_content_addressed(root, ("closeout_v1",), sha)

    def test_reconciles_with_end_to_end_fake_gateway_report(self):
        owner = ReadOnlyCloseoutTests("test_complete_no_redispatch_and_sealed_proposals")
        owner.setUp()
        self.addCleanup(owner.doCleanups)
        frozen = owner.closeout()
        report_sha = owner.execution["private_report_sha256"]
        private = PrivateAudit(owner.root / "continuation_amendment_v1" / "journal")
        report = private.read(report_sha)
        result = diagnostic.diagnose(frozen, report, freeze_sha256="d" * 64)
        self.assertEqual(result["reason_counts"],
                         {**frozen["automated_concordance"]["veto_or_abstain_reasons"],
                          **{k: v for k, v in frozen["automated_concordance"]["proposal_reasons"].items() if v}})
        self.assertEqual(result["screened_pairs"],
                         frozen["automated_concordance"]["screened_pairs"])
        self.assertTrue(result["all_routed_reasons_reconciled"])


if __name__ == "__main__":
    unittest.main()
