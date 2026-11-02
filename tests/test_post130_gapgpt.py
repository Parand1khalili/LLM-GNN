"""Exact identity policy and synthetic outstanding-only post130 regression."""
import copy
import unittest
from unittest.mock import MagicMock,patch
import test_outstanding_gapgpt as base
from llmgnn_sara.pilot import identity,outstanding_gapgpt as pilot


class IdentityPolicyTests(unittest.TestCase):
    def test_exact_identifiers_and_context_only(self):
        settings={'temperature':1,'n':1,'max_tokens':512,'reasoning_effort':'OMITTED'}
        for model in identity.MODELS:
            self.assertTrue(identity.allowed('GapGPT',pilot.prior.ENDPOINT,'gpt-6-luna',model,settings))
        for model in (None,'gpt-6-luna-2026-09-23','gpt-6-luna-2026-09-22.evil','GPT-6-LUNA','gpt-6-luna\n',{'model':'gpt-6-luna'}):
            self.assertFalse(identity.allowed('GapGPT',pilot.prior.ENDPOINT,'gpt-6-luna',model,settings))
        for provider,endpoint,requested in [('Other',pilot.prior.ENDPOINT,'gpt-6-luna'),('GapGPT','https://api.gapapi.com/v1/chat/completions','gpt-6-luna'),('GapGPT',pilot.prior.ENDPOINT,'other')]:
            self.assertFalse(identity.allowed(provider,endpoint,requested,'gpt-6-luna',settings))
        for changed in ({**settings,'temperature':.7},{**settings,'max_tokens':1024},{**settings,'reasoning_effort':'high'},{**settings,'n':True}):
            self.assertFalse(identity.allowed('GapGPT',pilot.prior.ENDPOINT,'gpt-6-luna','gpt-6-luna',changed))


class Post130Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.object(pilot.prior,'verify_no_prior_dispatch'):
            cls.prepared=pilot.prepare(post130=True)
    setUp=base.ContinuationTests.setUp
    start=base.ContinuationTests.start
    envelope=base.ContinuationTests.envelope
    test_crash_start_and_unknown_dispatch_never_resume=base.ContinuationTests.test_crash_start_and_unknown_dispatch_never_resume
    test_audit_failure_before_and_after_dispatch=base.ContinuationTests.test_audit_failure_before_and_after_dispatch

    def test_seven_calls_both_identifiers_and_no_blind130(self):
        import json
        digest=self.start();calls=[]
        def post(wire,key):
            p=json.loads(json.loads(wire)['messages'][0]['content']);calls.append((p['node_id'],p['phase']))
            return self.envelope(wire,model=identity.MODELS[len(calls)%2])
        summary,_=pilot.run(self.contract,base.KEY,self.ledger,self.audit,digest,transport=post)
        self.assertEqual(summary['state'],'FINISHED')
        self.assertEqual(calls,[(130,'compare')]+[(n,p) for n in (682,2396,653) for p in ('blind','compare')])
        self.assertEqual(summary['dispatch_attempts_upper_bound'],7)
        self.assertEqual(summary['reported_usage_totals']['prompt_tokens'],5600)
        self.assertEqual(summary['rows'][2]['blind']['original_ledger_state'],'REJECTED')
        self.assertTrue(summary['rows'][2]['blind']['historical'])
        self.assertIsNone(summary['accepted_label'])

    def test_preserved130_wrong_lineage_or_repeated_blind_blocked(self):
        digest=self.start();step=self.contract['plan'][0];post=MagicMock()
        for payload,dependency in [({**step['payload'],'phase':'blind'},step['dependency']),
                 (step['payload'],{**step['dependency'],'inner_response_sha256':'0'*64})]:
            with self.assertRaises(ValueError):
                pilot.dispatch(self.contract,0,payload,dependency,base.KEY,self.ledger,self.audit,digest,transport=post)
        post.assert_not_called()

    def test_unknown_revision_halts_first_request(self):
        digest=self.start();post=MagicMock(side_effect=lambda wire,key:self.envelope(wire,model='gpt-6-luna-2099-01-01'))
        summary,_=pilot.run(self.contract,base.KEY,self.ledger,self.audit,digest,transport=post)
        self.assertEqual(post.call_count,1)
        self.assertEqual(summary['state_counts']['REJECTED'],1)
        self.assertEqual(summary['rows'][3]['blind']['state'],'NOT_ATTEMPTED')

    def test_future_abstentions_skip_comparisons(self):
        digest=self.start();post=MagicMock(side_effect=lambda wire,key:self.envelope(wire,abstain=True,model='gpt-6-luna'))
        summary,_=pilot.run(self.contract,base.KEY,self.ledger,self.audit,digest,transport=post)
        self.assertEqual(summary['state'],'FINISHED');self.assertEqual(post.call_count,4)
        self.assertEqual(summary['new_phase_denominators'],{'blind':3,'compare':1})

    def test_scope_and_approvals_remain_exact(self):
        for node,phase in ((130,'blind'),(1243,'compare'),(637,'blind')):
            bad=copy.deepcopy(self.contract);bad['plan'][0].update(node=node,phase=phase)
            with self.assertRaises(ValueError):pilot.start(bad,pilot.approvals_for(bad),self.ledger,self.audit)
        bad=copy.deepcopy(self.contract);bad['allowed_returned_models'].append('other')
        with self.assertRaises(ValueError):pilot.start(bad,pilot.approvals_for(bad),self.ledger,self.audit)


if __name__=='__main__':unittest.main()
