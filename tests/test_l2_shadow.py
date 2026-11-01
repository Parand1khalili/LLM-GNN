"""Synthetic schema fixtures only, never genuine/LLM-simulated human judgments."""
import copy,hashlib,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from llmgnn_sara.evaluation.l2_shadow import bind_response,ingest,compare,digest
from llmgnn_sara.evaluation.l2_reviews import PACKET_VERSION,RUBRIC,SCOPE,blank_review
from llmgnn_sara.sara3.audit import PrivateAudit,AuditError
from llmgnn_sara.sara3.pipeline import run_offline
from llmgnn_sara.sara2.policy import Pair,Annotation
from llmgnn_sara.downstream.frozen import plan_from_frozen

class ShadowTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.audit=PrivateAudit(Path(self.temp.name)/"private")
  self.text="This paper studies rule learning."
  self.raw={"class_index":0,"abstain":False,"evidence":[self.text]}
  self.binding=bind_response(self.audit,"case-001",self.raw,self.text)
 def fixture(self,reviewer="synthetic-a"):
  packet={"schema_version":PACKET_VERSION,"case_id":"case-001","assigned_reviewer":reviewer,"scope":SCOPE,"rubric":RUBRIC,
   "article":{"source_id":"target.text","text":self.text,"sha256":hashlib.sha256(self.text.encode()).hexdigest()},
   "evidence":[{"evidence_id":"e01","source_id":"target.text","quote":self.text,"quote_sha256":hashlib.sha256(self.text.encode()).hexdigest()}],
   "proposal":{"primary_topic":"Synthetic schema example","supporting_evidence":[{"evidence_ref":"e01","claim":"Synthetic schema-only claim"}],"counter_evidence":[]}}
  review=blank_review(packet,digest(packet));review["reviewed_at_utc"]="2026-11-01T00:00:00Z"
  review["declarations"]={k:True for k in review["declarations"]}
  for j in (*review["assessments"].values(),review["overall"]): j.update(outcome="AMBIGUOUS",rationale="SYNTHETIC_STRUCTURE_TEST_NOT_HUMAN_REVIEW",evidence_refs=["e01"])
  return packet,review
 def admit(self,p,r,kind="SYNTHETIC_TEST_ONLY"):
  return ingest(self.audit,self.binding,p,r,"synthetic-author",provenance_kind=kind)
 def test_valid_independent_fixture_comparison_missing_and_no_accuracy(self):
  p,r=self.fixture();a=self.admit(p,r);p,r=self.fixture("synthetic-b");b=self.admit(p,r)
  self.assertEqual(a["state"],"ASSESSED")
  result=compare(self.audit,a["receipt"],b["receipt"])
  self.assertEqual(result["status"],"AGREEMENT");self.assertIsNone(result["accuracy"])
  self.assertEqual(compare(self.audit)["status"],"MISSING_ASSESSMENT")
  self.assertEqual(compare(self.audit,a["receipt"],a["receipt"])["status"],"INVALID_OR_UNAVAILABLE")
 def test_unassessed_is_not_approval(self):
  p,r=self.fixture()
  for j in (*r["assessments"].values(),r["overall"]): j["outcome"]="NOT_ASSESSED"
  self.assertEqual(self.admit(p,r)["state"],"NOT_ASSESSED")
  self.assertEqual(self.admit(p,None)["state"],"NOT_ASSESSED")
 def test_hash_provenance_evidence_and_leakage_rejected(self):
  p,r=self.fixture()
  self.assertEqual(self.admit(p,r,"AUTHENTICATED_INDEPENDENT_GOLD")["state"],"INVALID")
  for mutation in ("hash","leak","quote","reference","blind"):
   q,s=copy.deepcopy((p,r))
   if mutation=="hash": s["packet_sha256"]="0"*64
   if mutation=="leak": q["node_id"]=637
   if mutation=="quote": q["evidence"][0]["quote"]="fabricated quotation"
   if mutation=="reference": s["overall"]["evidence_refs"]=["unknown"]
   if mutation=="blind": s["declarations"]["no_other_review_seen"]=False
   self.assertEqual(self.admit(q,s)["state"],"INVALID",mutation)
 def test_audit_failure_is_unavailable(self):
  p,r=self.fixture()
  with patch.object(self.audit,"write",side_effect=AuditError()): self.assertEqual(self.admit(p,r)["state"],"UNAVAILABLE")
 def test_invalid_l1_never_becomes_assessed(self):
  self.binding=bind_response(self.audit,"case-001",{**self.raw,"evidence":["invented quotation"]},self.text)
  p,r=self.fixture();self.assertEqual(self.admit(p,r)["state"],"INVALID")
 def test_noninterference_and_no_training_promotion(self):
  pair=Pair(Annotation(637,0,95),Annotation(637,0,95),self.text)
  class Fixture:
   offline=True
   def blind(_,request):return copy.deepcopy(self.raw)
   def compare(_,request):return copy.deepcopy(self.raw)
  audit=PrivateAudit(Path(self.temp.name)/"pipeline")
  before=run_offline([pair],1,verifier=Fixture(),audit=audit)
  p,r=self.fixture();self.admit(p,r)
  after=run_offline([pair],1,verifier=Fixture(),audit=audit)
  self.assertEqual(before,after)
  d=copy.deepcopy(after["decisions"][0]);d.update(accepted=True,accepted_label=0,training_class_index=0,abstain=False,l2_status="SUPPORTED")
  dataset=SimpleNamespace(by_arm=lambda _:(),predictions=())
  with self.assertRaises(ValueError):plan_from_frozen(dataset,"sensitivity","ce",[d])
