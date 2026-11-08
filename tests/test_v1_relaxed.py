import copy,unittest
from llmgnn_sara.sara3.v1_relaxed import decide
from llmgnn_sara.sara3.experiment import digest
from llmgnn_sara.sara3.rich_evidence import RICH_VERSION
TEXT='Bayesian inference uses Gaussian process priors for prediction.'
def value(label=6):
 return dict(schema_version=RICH_VERSION,class_index=label,abstain=False,primary_topic='Bayesian inference',
 supporting_evidence=[dict(source_id='target.text',quote=TEXT,claim='Probabilistic inference')],
 counter_evidence=[],auxiliary_method_warning=None,uncertainty_reason=None)
def binding(a,b):
 return dict(schema='sara.relaxed.verified_phase_pair.v1',node_id=1,blind_state='COMPLETED',comparison_state='COMPLETED',
 dependency=digest(a),blind_response=digest(a),comparison_response=digest(b),context_sha256='a'*64,blind_identity='b'*64,comparison_identity='c'*64)
class RelaxedTests(unittest.TestCase):
 def run_policy(self,a,b,proof=None):
  return decide(1,(0,1),TEXT,a,b,binding(a,b) if proof is None else proof)
 def test_third_with_warnings_and_counter_is_shadow(self):
  a=value();a.update(auxiliary_method_warning='Unresolved method ambiguity',uncertainty_reason='Uncertain')
  a['counter_evidence']=[dict(source_id='target.text',quote=TEXT,claim='Unresolved opposing interpretation')]
  # Same quote in support/counter is duplicate L1, so test warning alone.
  a['counter_evidence']=[dict(source_id='target.text',quote='Gaussian process priors',claim='Unresolved counter evidence')]
  r=self.run_policy(a,value());self.assertEqual(r['action'],'PROPOSE_CLASS_SWITCH')
  self.assertEqual(r['l2_status'],'NOT_ASSESSED');self.assertEqual(r['confidence_provenance'],'UNAVAILABLE_NOT_AGENT_CALIBRATED')
 def test_conflict_and_candidate(self):
  self.assertEqual(self.run_policy(value(),value(5))['action'],'ABSTAIN')
  self.assertEqual(self.run_policy(value(0),value(0))['action'],'KEEP_BASELINE')
 def test_abstention(self):
  a=value();a.update(class_index=None,abstain=True,primary_topic=None,supporting_evidence=[],counter_evidence=[],auxiliary_method_warning=None,uncertainty_reason='Insufficient evidence')
  self.assertEqual(self.run_policy(a,value())['action'],'ABSTAIN')
 def test_corrupt_binding_and_states(self):
  a,b=value(),value();p=binding(a,b)
  for k,v in [('dependency','0'*64),('comparison_state','REJECTED'),('blind_state','UNCERTAIN'),('node_id',2),('schema','wrong'),('comparison_response','0'*64),('context_sha256','x')]:
   with self.subTest(k=k):self.assertEqual(self.run_policy(a,b,{**p,k:v})['action'],'REJECT_INVALID_EVIDENCE')
 def test_fabrication_missing_gt(self):
  a,b=value(),value()
  b['supporting_evidence'][0]['quote']='A fabricated nonexistent quotation'
  self.assertEqual(self.run_policy(a,b)['action'],'REJECT_INVALID_EVIDENCE')
  self.assertEqual(self.run_policy(a,None)['action'],'REJECT_INVALID_EVIDENCE')
  b=value();b['ground_truth']=6
  self.assertEqual(self.run_policy(a,b)['action'],'REJECT_INVALID_EVIDENCE')
if __name__=='__main__':unittest.main()
