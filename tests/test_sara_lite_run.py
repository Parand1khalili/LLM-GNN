import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from llmgnn_sara.annotation.sara_lite_run import call

class LiteRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'private'
        self.e=dict(prompt='synthetic',prompt_sha256=hashlib.sha256(b'synthetic').hexdigest())
        value=dict(action='SWITCH',proposed_class_index=2,support_quotes=['prior cases'],counter_quotes=[],primary_topic='Retrieving and adapting observed examples',reason_code='TARGET_SUPPORT',uncertainty='NONE')
        self.raw=json.dumps(dict(id='synthetic-response',model='gpt-6-luna',usage=dict(prompt_tokens=10,completion_tokens=80),choices=[dict(finish_reason='stop',message=dict(content=json.dumps(value)))])).encode()
    def test_replay_never_dispatches_and_immutable_binding(self):
        a,new=call(self.root,self.e,'synthetic-key','prior cases',0,lambda *a,**k:(200,self.raw));self.assertTrue(new)
        b,new=call(self.root,self.e,'synthetic-key','prior cases',0,lambda *a,**k:self.fail('duplicate'))
        self.assertFalse(new);self.assertEqual(a,b)
        next(self.root.glob('calls/*/intent.json')).write_text('{}')
        with self.assertRaises(ValueError):call(self.root,self.e,'synthetic-key','prior cases',0)
    def test_timeout_missing_key_and_read_only(self):
        with self.assertRaises(ValueError):call(self.root,self.e,'','prior cases',0)
        with self.assertRaises(ValueError):call(self.root,self.e,'synthetic-key','prior cases',0,allow_dispatch=False)
        self.assertEqual(list(self.root.glob('calls/*/intent.json')),[])
        def timeout(*a,**k):raise TimeoutError()
        with self.assertRaises(TimeoutError):call(self.root,self.e,'synthetic-key','prior cases',0,timeout)
        with self.assertRaisesRegex(ValueError,'AMBIGUOUS'):call(self.root,self.e,'synthetic-key','prior cases',0,timeout)
    def test_budget_and_invalid_response(self):
        with patch('llmgnn_sara.annotation.sara_lite_run.RESERVATION',1):
            with self.assertRaisesRegex(ValueError,'BUDGET'):call(self.root,self.e,'synthetic-key','prior cases',0)
        r,_=call(self.root,self.e,'synthetic-key','prior cases',0,lambda *a,**k:(400,b'{}'))
        self.assertEqual(r['status'],'REJECTED');self.assertNotIn('validated',r)

if __name__=='__main__':unittest.main()
