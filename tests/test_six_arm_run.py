import unittest,json,tempfile,hashlib
from pathlib import Path
from unittest.mock import patch
from llmgnn_sara.annotation.six_arm_run import call,parse,MODELS
from llmgnn_sara.io.frozen import CLASSES
class RunnerTests(unittest.TestCase):
 def setUp(self):
  self.entry=dict(prompt='Synthetic paper',prompt_sha256=hashlib.sha256(b'Synthetic paper').hexdigest())
  self.cfg=dict(model='gpt-6-luna');self.key='synthetic-secret-key-not-real'
  self.raw=json.dumps(dict(model=MODELS[0],choices=[dict(finish_reason='stop',message=dict(content=json.dumps([dict(answer=CLASSES[i],confidence=c) for i,c in enumerate((60,30,10))])))],usage=dict(prompt_tokens=20,completion_tokens=30))).encode()
 def test_completed_resume_and_corrupt_receipt(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)/'run'
   first,new=call(root,self.entry,self.cfg,self.key,lambda *a,**kw:(200,self.raw));self.assertTrue(new)
   second,new=call(root,self.entry,self.cfg,self.key,lambda *a,**kw:self.fail('duplicate'));self.assertFalse(new);self.assertEqual(first,second)
   intent=next(root.glob('calls/*/intent.json'));intent.write_text('{}')
   with self.assertRaises(ValueError):call(root,self.entry,self.cfg,self.key)
 def test_ambiguous_never_retried(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)/'run'
   def timeout(*a,**kw):raise TimeoutError()
   with self.assertRaises(TimeoutError):call(root,self.entry,self.cfg,self.key,timeout)
   with self.assertRaises(ValueError):call(root,self.entry,self.cfg,self.key,lambda *a,**kw:self.fail('retry'))
 def test_missing_key_budget_and_parse_failure(self):
  with tempfile.TemporaryDirectory() as temp:
   with self.assertRaises(ValueError):call(temp,self.entry,self.cfg,'')
   with patch('llmgnn_sara.annotation.six_arm_run.RESERVATION',16):
    with self.assertRaises(ValueError):call(Path(temp)/'budget',self.entry,self.cfg,self.key)
   with self.assertRaises(ValueError):call(Path(temp)/'bad',self.entry,self.cfg,self.key,lambda *a,**kw:(400,b'{}'))
   with self.assertRaises(ValueError):parse(200,b'{}')
 def test_continue_main_preserves_unresolved_and_no_vote(self):
  from unittest.mock import MagicMock
  import llmgnn_sara.annotation.six_arm_run as runner
  entries=[dict(node_id=i,arm='B1',sample_index=0,draft_identity=str(i)) for i in (1,2,3)]
  store=MagicMock();store.read.return_value={'requests':entries};store.write.return_value='a'*64
  rec={'validated':{'usage':{'prompt_tokens':1,'completion_tokens':1}}}
  with patch.object(runner,'PrivateAudit',return_value=store),patch.object(runner,'call',side_effect=[ValueError('EXISTING_INTENT_UNCERTAIN_OR_REJECTED_NO_RETRY'),(rec,False),(rec,True)]),patch('sys.argv',['run','--stage','full','--continue-unattempted']),patch('builtins.input',side_effect=['APPROVE PRIVACY','15','APPROVE SCALE']),patch.dict('os.environ',{'GAPGPT_API_KEY':'synthetic-fixture'}):
   runner.main()
  result=store.write.call_args.args[0]
  self.assertEqual(result['status'],'PARTIAL_UNRESOLVED_NO_PREDICTION_FREEZE')
  self.assertEqual(result['completed'],2);self.assertEqual(result['new_dispatches'],1)
  self.assertNotIn('predictions',result)

if __name__=='__main__':unittest.main()
