"""Pinned draft adapter/reuse tests; synthetic fixtures are not scientific results."""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from llmgnn_sara.io.project import load_project_inputs
from llmgnn_sara.sara2.policy import PolicyConfig
from llmgnn_sara.sara3.audit import AuditError, PrivateAudit
from llmgnn_sara.sara3.evidence import EvidenceError
from llmgnn_sara.sara3.experiment import (MANIFEST_SHA256, VerifiedSelection,
    build_manifest, digest, load_selection, request_identity)
from llmgnn_sara.sara3.experiment_cache import CachedOfflineVerifier
from llmgnn_sara.sara3.inputs import canonical_bytes, pair_inputs
from llmgnn_sara.sara3.pipeline import BlindRequest, ComparisonRequest, run_offline
from llmgnn_sara.sara3.rich_evidence import RICH_VERSION
from llmgnn_sara.evaluation.routing_experiment import SyntheticExperimentVerifier, exercise_experiment

ROOT = Path(__file__).resolve().parents[1]
FROZEN, AUTHENTIC = ROOT / ".local_artifacts/frozen", ROOT / ".local_artifacts/authentic"
MANIFEST = ROOT / "manifests/routing_experiment_draft_v1.json"


@unittest.skipUnless((AUTHENTIC / "b1_prompts.json").is_file() and
    (FROZEN / "b1_final_predictions.json").is_file(), "Authentic inputs unavailable")
class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = load_project_inputs(FROZEN, AUTHENTIC)
        cls.manifest = build_manifest(cls.inputs)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.audit = PrivateAudit(Path(self.temp.name) / "private")

    def selection(self, arm="r1_v2"):
        return load_selection(MANIFEST, MANIFEST_SHA256, arm, self.inputs)

    def test_pinned_manifest_reproducible_and_explicitly_not_live(self):
        self.assertEqual(hashlib.sha256(MANIFEST.read_bytes()).hexdigest(), MANIFEST_SHA256)
        self.assertEqual(json.loads(MANIFEST.read_bytes()), self.manifest)
        self.assertEqual(self.manifest["status"], "DRAFT")
        self.assertEqual(self.manifest["live_execution"], "NOT_AUTHORIZED_FOR_LIVE_EXECUTION")
        self.assertEqual(len(self.manifest["source_hashes"]), 9)
        self.assertEqual(len(self.manifest["requests_by_node"]), 140)
        self.assertEqual(len(self.manifest["arms"]), 5)
        self.assertTrue(all(v is None for v in self.manifest["execution_context"]["model_settings"].values()))

    def test_all_five_hash_verified_selections_exact_and_unique(self):
        for arm, record in self.manifest["arms"].items():
            chosen = self.selection(arm).resolve(self.inputs.pairs, 37, None, PolicyConfig())
            self.assertEqual(chosen, tuple(record["selected_ids"]))
            self.assertEqual(len(set(chosen)), 37)
            self.assertEqual(digest(list(chosen)), record["selection_sha256"])

    def test_manifest_tamper_or_unapproved_hash_fails(self):
        with self.assertRaises(ValueError): load_selection(MANIFEST, "0" * 64, "r0", self.inputs)
        with self.assertRaises(ValueError): self.selection("unknown")
        altered = replace(self.selection(), manifest_bytes=MANIFEST.read_bytes() + b" ")
        with self.assertRaises(ValueError): altered.resolve(self.inputs.pairs, 37, None, PolicyConfig())

    def test_changed_inputs_order_schema_policy_and_budget_fail_before_verifier(self):
        selected = self.selection()
        changed = (replace(self.inputs.pairs[0], text="changed text"), *self.inputs.pairs[1:])
        for rows, budget, schema, config in ((changed,37,None,PolicyConfig()),
            (tuple(reversed(self.inputs.pairs)),37,None,PolicyConfig()),
            (self.inputs.pairs,36,None,PolicyConfig()), (self.inputs.pairs,37,RICH_VERSION,PolicyConfig()),
            (self.inputs.pairs,37,None,PolicyConfig(90))):
            with self.assertRaises(ValueError): selected.resolve(rows,budget,schema,config)
        verifier = SyntheticExperimentVerifier(self.inputs.pairs)
        with patch.object(verifier, "blind", side_effect=AssertionError("Dispatch before admission")):
            with self.assertRaises(ValueError): run_offline(changed,37,verifier=verifier,selection=selected)
            with self.assertRaises(ValueError): run_offline(self.inputs.pairs,37,"semantic",verifier,selection=selected)
            with self.assertRaises(ValueError): run_offline(self.inputs.pairs,37,verifier=verifier,selection={})

    def test_accounting_counts_union_not_sum_and_unknown_costs(self):
        m=self.manifest; a=m["accounting"]
        union={n for arm in m["primary_arms"] for n in m["arms"][arm]["selected_ids"]}
        self.assertEqual(a["primary_union_blind_identities"],len(union))
        self.assertEqual(a["primary_union_maximum_generation_calls"],2*len(union))
        self.assertEqual(a["primary_standalone_sum_maximum_calls"],222)
        self.assertIsNone(a["actual_response_dependent_calls"])
        self.assertIsNone(a["costs"])
        self.assertTrue(all(r["comparison_identity"] is None for r in m["requests_by_node"].values()))

    def test_identity_covers_full_effective_payload_context_and_dependency(self):
        blind, comparison = pair_inputs(self.inputs.pairs[0])
        context = self.manifest["execution_context"]
        identity = request_identity(blind,context)
        changed=json.loads(canonical_bytes(blind)); changed["instructions"] += " changed"
        self.assertNotEqual(identity,request_identity(changed,context))
        changed_context=json.loads(canonical_bytes(context)); changed_context["model_settings"]["temperature"]=0
        self.assertNotEqual(identity,request_identity(blind,changed_context))
        with self.assertRaises(ValueError): request_identity(comparison,context)
        comparison["blind_class_index"]=0
        self.assertNotEqual(request_identity(comparison,context,blind_response_sha256="a"*64),
                            request_identity(comparison,context,blind_response_sha256="b"*64))
        with self.assertRaises(ValueError): request_identity(blind,{**context,"mode":"LIVE"})
        with self.assertRaises(ValueError): request_identity({**blind,"gt":0},context)

    def cache(self, verifier=None):
        return CachedOfflineVerifier(verifier or SyntheticExperimentVerifier(self.inputs.pairs),
                                     self.manifest["execution_context"],self.audit)

    def test_cache_success_audit_binding_and_mutation_isolation(self):
        p=next(p for p in self.inputs.pairs if p.node_id%4==3)
        request=BlindRequest(p.node_id,p.text,neighborhood=p.neighborhood)
        cache=self.cache(); first=cache.blind(request); expected=json.loads(canonical_bytes(first))
        first["evidence"]=[]
        self.assertEqual(cache.blind(request),expected)
        self.assertEqual(cache.dispatches,1); self.assertEqual(cache.hits,1)
        compare=ComparisonRequest(p.node_id,p.text,(p.b1.class_index,p.narrative_v0.class_index),
                                  expected["class_index"],neighborhood=p.neighborhood)
        cache.compare(compare); cache.compare(compare)
        self.assertEqual(cache.dispatches,2); self.assertEqual(cache.hits,2)

    def test_comparison_without_actual_blind_fails(self):
        p=self.inputs.pairs[0]
        request=ComparisonRequest(p.node_id,p.text,(p.b1.class_index,),0,neighborhood=p.neighborhood)
        with self.assertRaises(ValueError): self.cache().compare(request)

    def test_uncertain_dispatch_not_retried(self):
        verifier=SyntheticExperimentVerifier(self.inputs.pairs)
        p=self.inputs.pairs[0]; request=BlindRequest(p.node_id,p.text,neighborhood=p.neighborhood)
        cache=self.cache(verifier)
        with patch.object(verifier,"blind",side_effect=TimeoutError("PRIVATE_NO_LOG")) as call:
            with self.assertRaises(TimeoutError): cache.blind(request)
            with self.assertRaises(EvidenceError): cache.blind(request)
            self.assertEqual(call.call_count,1)
        self.assertEqual(len(cache.cache),0)

    def test_malformed_raw_is_private_but_not_reusable(self):
        verifier=SyntheticExperimentVerifier(self.inputs.pairs)
        p=self.inputs.pairs[0]; request=BlindRequest(p.node_id,p.text,neighborhood=p.neighborhood)
        cache=self.cache(verifier)
        raw={"class_index":0,"abstain":True,"evidence":[]}
        with patch.object(verifier,"blind",return_value=raw) as call:
            with self.assertRaises(EvidenceError): cache.blind(request)
            with self.assertRaises(EvidenceError): cache.blind(request)
            self.assertEqual(call.call_count,1)
        records=[self.audit.read(p.stem) for p in self.audit.root.glob('*.json')]
        self.assertTrue(any(r.get('raw_response')==raw for r in records))
        self.assertEqual(len(cache.cache),0)

    def test_audit_failure_blocks_dispatch_and_reuse_tamper_fails(self):
        p=self.inputs.pairs[0]; request=BlindRequest(p.node_id,p.text,neighborhood=p.neighborhood)
        cache=self.cache()
        with patch.object(self.audit,"write",side_effect=AuditError()):
            with self.assertRaises(AuditError): cache.blind(request)
        self.assertEqual(cache.dispatches,0)
        fresh=self.cache(); fresh.blind(request)
        with patch.object(self.audit,"read",side_effect=AuditError()):
            with self.assertRaises(AuditError): fresh.blind(request)

    def test_end_to_end_three_arms_without_gt_network_or_input_mutation(self):
        before=digest([asdict(p) for p in self.inputs.pairs])
        manifest_before=MANIFEST.read_bytes()
        with patch.object(socket.socket,"connect",side_effect=AssertionError("Network forbidden")):
            report=exercise_experiment(self.inputs,MANIFEST)
        self.assertEqual(manifest_before,MANIFEST.read_bytes())
        self.assertEqual(before,digest([asdict(p) for p in self.inputs.pairs]))
        self.assertEqual(len(report["arms"]),3)
        self.assertEqual(report["provider_calls"],0)
        self.assertGreater(report["synthetic_execution"]["cache_hits"],0)
        self.assertEqual(report["synthetic_execution"]["noncompleted_identities"],0)
        all_reasons=set()
        for arm in report["arms"].values():
            self.assertEqual(arm["accepted_reviewed"],0)
            self.assertEqual(arm["l2_status"],"NOT_ASSESSED")
            self.assertTrue(arm["decision_node_ids_unique"])
            all_reasons.update(arm["reason_counts"])
        self.assertTrue({"THIRD_CLASS_PROPOSAL_ONLY","BLIND_ABSTENTION","COMPARISON_ABSTENTION","L2_NOT_ASSESSED"} <= all_reasons)


if __name__ == "__main__":
    unittest.main()
