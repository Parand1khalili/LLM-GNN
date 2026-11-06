"""Synthetic-only blind-pack contracts; no Windows project data or human reviews."""
import copy
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from test_gapgpt_gateway import inputs as synthetic_inputs
from llmgnn_sara.sara3 import blind_review_pack as review
from llmgnn_sara.sara3.audit import AuditError, PrivateAudit
from llmgnn_sara.sara3.gateway_run import gateway_context
from llmgnn_sara.sara3.inputs import canonical_bytes
from llmgnn_sara.sara3.rich_evidence import rich_verifier_input_v2

CONFIG = Path(__file__).resolve().parents[1] / "configs/gapgpt_rich_v2_output4096_proposed.json"


class BlindReviewPackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / ".local_artifacts"
        self.run = self.root / "source_run"
        (self.run / "closeout_v1").mkdir(parents=True)
        (self.run / "continuation_amendment_v1" / "journal").mkdir(parents=True)
        self.output = self.root / "independent_review"
        base = synthetic_inputs()
        self.data = synthetic_inputs(tuple(replace(p, text=p.text + '\r\nCafé Ω … "quoted"  ')
                                           for p in base.pairs))
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.selected, context = gateway_context(self.data, "r0", 37, "sensitivity", self.config, fake=False)
        self.context = review._sha(context)
        pairs = {p.node_id: p for p in self.data.pairs}
        requests = []
        for node in self.selected:
            p = pairs[node]
            payload = rich_verifier_input_v2(node, p.text, p.neighborhood)
            requests.append({"request_id": f"offline:{node}:blind", "payload": payload,
                             "sha256": review._sha(payload)})
        # Deliberately toxic internal metadata must never reach either reviewer.
        self.report = {"kind": "gapgpt_continuation_private_report", "amendment_sha256": "a" * 64,
                       "run": {"selected_node_ids": list(self.selected), "router": "r0",
                               "review_budget": 37, "verifier_inputs": requests,
                               "decisions": [{"node_id": 0, "reason": "PRIVATE_VETO_SENTINEL",
                                              "b1_prediction": "PRIVATE_PREDICTION_SENTINEL"}]}}
        self.freeze = {"schema": review.CLOSEOUT_VERSION, "freeze_version": review.CLOSEOUT_VERSION,
                       "context_sha256": self.context,
                       "contract_sha256": review._sha(self.config),
                       "cohort_size": 140, "routed_nodes": 37, "total_intents": 67,
                       "intent_states": {"COMPLETED": 66, "REJECTED": 1, "UNCERTAIN": 0},
                       "phase_states": {"blind": {"COMPLETED": 37}, "compare": {"COMPLETED": 29}},
                       "receipt_identity_integrity_verified": True, "private_report_reconciled": True,
                       "GT_accessed": False, "training_admission": False,
                       "automated_concordance": {"proposals": 0}, "amendment_sha256": "a" * 64}
        self.pin_context = patch.object(review, "FROZEN_CONTEXT_SHA256", self.context)
        self.pin_context.start(); self.addCleanup(self.pin_context.stop)
        self.loader = patch.object(review, "load_project_inputs", return_value=self.data)
        self.loader.start(); self.addCleanup(self.loader.stop)
        self.network = patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden"))
        self.network.start(); self.addCleanup(self.network.stop)
        self.publish_fixture()

    def publish_fixture(self):
        report_sha = review._sha(self.report)
        (self.run / "continuation_amendment_v1" / "journal" / (report_sha + ".json")).write_bytes(
            canonical_bytes(self.report))
        self.freeze["private_report_sha256"] = report_sha
        self.freeze_sha = review._sha(self.freeze)
        (self.run / "closeout_v1" / (self.freeze_sha + ".json")).write_bytes(canonical_bytes(self.freeze))
        review.FREEZE_SHA256 = self.freeze_sha
        self.addCleanup(setattr, review, "FREEZE_SHA256",
                        "03625722e672f25acb1001b59a4f4a72dd18ab0286ddb9a58a402b73895a1abb")

    def prepare(self, **kwargs):
        return review.prepare(self.root / "frozen", self.root / "authentic", self.run,
                              CONFIG, self.output, **kwargs)

    def records(self, summary):
        return {name: json.loads((self.output / info["relative_path"]).read_text(encoding="utf-8"))
                for name, info in summary["files"].items()}

    def snapshot(self, path):
        return {str(f.relative_to(path)): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in path.rglob("*") if f.is_file()}

    def test_complete_blinded_packs_blank_forms_and_private_provenance(self):
        sources = self.snapshot(self.run)
        summary = self.prepare()
        self.assertEqual(summary["status"], "CREATED_PRIVATE")
        self.assertEqual(summary["case_count"], 37)
        docs = self.records(summary)
        a, b, owner = (docs[k] for k in (*review.REVIEWERS, "owner_private"))
        expected = {review._keyed(owner["private_seed_hex"], f"case:{n}")[:32]: n for n in self.selected}
        self.assertEqual({r["case_id"]: r["node_id"] for r in owner["cases"]}, expected)
        by_id = {p.node_id: p for p in self.data.pairs}
        for pack in (a, b):
            review.validate_pack(pack)
            self.assertEqual(set(expected), {c["case_id"] for c in pack["cases"]})
            self.assertEqual(len(pack["classes"]), 7)
            for case in pack["cases"]:
                self.assertEqual(case["target_text"], by_id[expected[case["case_id"]]].text)
                self.assertTrue(all(case["response_template"][k] is None for k in review.TEMPLATE_FIELDS))
            serialized = json.dumps(pack)
            for forbidden in ("node_id", "PRIVATE_VETO_SENTINEL", "PRIVATE_PREDICTION_SENTINEL",
                              "b1_prediction", "narrative_v0_prediction", "routing_score",
                              "provider_metadata", "private_seed", "sha256"):
                self.assertNotIn(forbidden, serialized)
        self.assertEqual({c["case_id"]: c for c in a["cases"]}, {c["case_id"]: c for c in b["cases"]})
        self.assertNotEqual([c["case_id"] for c in a["cases"]], [c["case_id"] for c in b["cases"]])
        self.assertEqual(owner["ordered_selected_nodes_sha256"], review._sha(list(self.selected)))
        self.assertEqual(owner["class_atlas_sha256"], review._sha(a["classes"]))
        for name, info in summary["files"].items():
            file = self.output / info["relative_path"]
            self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(), info["sha256"])
            PrivateAudit(file.parent).read(file.stem)  # Existing Windows ACL / POSIX checks.
        self.assertEqual(self.snapshot(self.run), sources)
        for flag in ("provider_calls", "completed_reviews", "GCN_training_runs", "training_admissions"):
            self.assertEqual(summary[flag], 0)
        self.assertFalse(summary["GT_accessed"])

    def test_safe_replay_is_byte_identical_and_read_only(self):
        first = self.prepare()
        before = self.snapshot(self.output)
        for verify in (False, True):
            with patch.object(review.secrets, "token_hex", side_effect=AssertionError("No new seed")), \
                 patch.object(PrivateAudit, "write", side_effect=AssertionError("Replay may not write")):
                result = self.prepare(verify_only=verify)
            self.assertEqual(result["status"], "VERIFIED_EXISTING")
            self.assertEqual(first["files"], result["files"])
            self.assertEqual(before, self.snapshot(self.output))

    def test_case_ids_and_orders_are_secret_keyed_not_small_node_hashes(self):
        with patch.object(review.secrets, "token_hex", return_value="1" * 64):
            first = self.records(self.prepare())
        material = review._material(self.data, self.freeze, self.report, self.config)
        second = review._packet(material, "2" * 64, "reviewer_a")
        ids = {c["case_id"] for c in first["reviewer_a"]["cases"]}
        self.assertFalse(ids.intersection(c["case_id"] for c in second["cases"]))
        self.assertFalse(ids.intersection(hashlib.sha256(str(n).encode()).hexdigest()[:32] for n in range(2708)))
        for reviewer in review.REVIEWERS:
            self.assertEqual(first[reviewer], review._packet(material, "1" * 64, reviewer))

    def test_modified_source_bytes_and_context_fail_before_output(self):
        freeze_file = self.run / "closeout_v1" / (self.freeze_sha + ".json")
        freeze_file.write_bytes(freeze_file.read_bytes() + b" ")
        with self.assertRaises(ValueError): self.prepare()
        self.assertFalse(self.output.exists())
        freeze_file.write_bytes(canonical_bytes(self.freeze))
        with patch.object(review, "FROZEN_CONTEXT_SHA256", "f" * 64):
            with self.assertRaises(ValueError): self.prepare()
        self.assertFalse(self.output.exists())

    def test_wrong_selection_atlas_source_or_report_fails_closed(self):
        original = copy.deepcopy(self.report)
        for change in ("order", "missing", "duplicate", "outside", "text", "atlas", "payload_hash"):
            self.report = copy.deepcopy(original)
            run = self.report["run"]
            request = run["verifier_inputs"][0]
            if change == "order": run["selected_node_ids"].reverse()
            elif change == "missing": run["verifier_inputs"].pop()
            elif change == "duplicate": run["verifier_inputs"].append(copy.deepcopy(request))
            elif change == "outside": request["payload"]["node_id"] = 2707
            elif change == "text": request["payload"]["target"]["text"] = ""
            elif change == "atlas": request["payload"]["class_atlas"][0]["definition"] += " changed"
            else: request["sha256"] = "0" * 64
            if change != "payload_hash": request["sha256"] = review._sha(request["payload"])
            self.publish_fixture()
            with self.subTest(change=change):
                with self.assertRaises(ValueError): self.prepare()
                self.assertFalse(self.output.exists())

    def test_gt_field_is_rejected_and_loader_is_only_gt_free_admission(self):
        self.report["run"]["fixed_y"] = [1] * 140
        self.publish_fixture()
        with self.assertRaises(ValueError): self.prepare()
        self.assertFalse(self.output.exists())
        self.loader.stop()
        with patch.object(review, "load_project_inputs", side_effect=AssertionError("GT-free loader not reached")):
            with self.assertRaises(ValueError): self.prepare()

    def test_nested_reviewer_leakage_and_nonblank_answers_rejected_before_write(self):
        real_packet = review._packet
        for mutation in ("top", "case", "class", "form", "filled"):
            def bad_packet(*args):
                p = real_packet(*args)
                if mutation == "top": p["node_id"] = 1
                elif mutation == "case": p["cases"][0]["routing_score"] = 1
                elif mutation == "class": p["classes"] = copy.deepcopy(p["classes"]); p["classes"][0]["b1_confidence"] = 100
                elif mutation == "form": p["cases"][0]["response_template"]["veto_reason"] = "PRIVATE"
                else: p["cases"][0]["response_template"]["selected_class_index"] = 0
                return p
            with self.subTest(mutation=mutation), patch.object(review, "_packet", side_effect=bad_packet):
                with self.assertRaises(ValueError): self.prepare()
                self.assertFalse(self.output.exists())

    def test_incomplete_or_tampered_existing_pack_fails_without_overwrite(self):
        with self.assertRaises(ValueError): self.prepare(verify_only=True)
        summary = self.prepare()
        owner = self.output / summary["files"]["owner_private"]["relative_path"]
        original = owner.read_bytes()
        owner.write_bytes(original + b" ")
        before = self.snapshot(self.output)
        with self.assertRaises(ValueError): self.prepare()
        self.assertEqual(before, self.snapshot(self.output))
        owner.write_bytes(original)  # Restore synthetic fixture only.
        extra = self.output / "reviewer_b" / "unexpected.json"
        extra.write_text("{}")
        before = self.snapshot(self.output)
        with self.assertRaises(ValueError): self.prepare()
        self.assertEqual(before, self.snapshot(self.output))

    def test_audit_failure_leaves_incomplete_output_never_repaired(self):
        before = self.snapshot(self.run)
        with patch.object(PrivateAudit, "write", side_effect=AuditError()):
            with self.assertRaises(ValueError): self.prepare()
        partial = self.snapshot(self.output)
        with self.assertRaises(ValueError): self.prepare()
        self.assertEqual(partial, self.snapshot(self.output))
        self.assertEqual(before, self.snapshot(self.run))

    def test_unsafe_paths_reparse_points_and_source_overlap_rejected(self):
        for output in (Path(self.temp.name) / "public", self.run / "review", self.root):
            with self.subTest(output=output), self.assertRaises(ValueError):
                review.prepare(self.root / "frozen", self.root / "authentic", self.run, CONFIG, output)
        with patch.object(Path, "is_symlink", return_value=True):
            with self.assertRaises(ValueError): self.prepare()
        if hasattr(Path, "is_junction"):
            with patch.object(Path, "is_junction", return_value=True):
                with self.assertRaises(ValueError): self.prepare()

    def test_cli_summary_and_errors_never_echo_private_source_or_exceptions(self):
        args = ["--frozen-root", str(self.root / "frozen"), "--authentic-root", str(self.root / "authentic"),
                "--run-root", str(self.run), "--gateway-config", str(CONFIG), "--output", str(self.output)]
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            self.assertEqual(review.main(args), 0)
        summary = json.loads(stdout.getvalue())
        self.assertEqual(summary["case_count"], 37)
        self.assertEqual(stderr.getvalue(), "")
        self.assertNotIn("Bayesian inference", stdout.getvalue())
        self.assertNotIn("PRIVATE_PREDICTION_SENTINEL", stdout.getvalue())
        with patch.object(review, "prepare", side_effect=ValueError("PRIVATE ARTICLE AND KEY")), \
             patch("sys.stdout", io.StringIO()), patch("sys.stderr", stderr := io.StringIO()):
            self.assertEqual(review.main(args), 1)
        self.assertEqual(json.loads(stderr.getvalue()), {"status": "FAIL_CLOSED"})


if __name__ == "__main__":
    unittest.main()
