"""Three-node blind-only amendment; synthetic provider responses only."""
import copy
import json
import unittest
from unittest.mock import MagicMock,patch
import test_outstanding_gapgpt as base
from llmgnn_sara.pilot import outstanding_gapgpt as pilot


class BlindOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.object(pilot.prior,'verify_no_prior_dispatch'):
            cls.prepared=pilot.prepare(blind_only=True)
    setUp=base.ContinuationTests.setUp
    start=base.ContinuationTests.start
    envelope=base.ContinuationTests.envelope
    test_crash_start_and_unknown_dispatch_never_resume=base.ContinuationTests.test_crash_start_and_unknown_dispatch_never_resume
    test_audit_failure_before_and_after_dispatch=base.ContinuationTests.test_audit_failure_before_and_after_dispatch

    def test_three_blinds_only_valid_or_abstaining_and_exact_totals(self):
        for abstain in (False,True):
            self.setUp();digest=self.start();calls=[]
            def post(wire,key):
                p=json.loads(json.loads(wire)['messages'][0]['content']);calls.append((p['node_id'],p['phase']))
                return self.envelope(wire,abstain=abstain,model=pilot.identity_policy.MODELS[len(calls)%2])
            history=copy.deepcopy(self.contract['preserved_130_comparison'])
            summary,_=pilot.run(self.contract,base.KEY,self.ledger,self.audit,digest,transport=post)
            self.assertEqual(summary['state'],'FINISHED')
            self.assertEqual(calls,[(682,'blind'),(2396,'blind'),(653,'blind')])
            self.assertEqual(summary['new_phase_denominators'],{'blind':3,'compare':0})
            self.assertEqual(summary['reported_usage_totals']['prompt_tokens'],2400)
            self.assertEqual(summary['reported_usage_totals']['completion_tokens'],300)
            self.assertEqual(summary['estimated_cost_usd'],'0.00039')
            self.assertEqual(summary['rows'][2]['compare'],history)
            self.assertTrue(all(r['blind']['abstain']==abstain for r in summary['rows'][3:]))
            self.assertTrue(all(r['compare']['state']=='NOT_PERMITTED_BLIND_ONLY_AMENDMENT' for r in summary['rows'][3:]))
            self.assertFalse(summary['paired_protocol_complete'])
            self.assertIsNone(summary['accepted_label'])

    def test_scope_cannot_admit_comparison_or_previous_nodes(self):
        for node,phase in ((682,'compare'),(130,'blind'),(1243,'compare'),(637,'blind')):
            bad=copy.deepcopy(self.contract);bad['plan'][0].update(node=node,phase=phase)
            with self.assertRaises(ValueError):pilot.start(bad,pilot.approvals_for(bad),self.ledger,self.audit)
        bad=copy.deepcopy(self.contract);bad['maximum_calls']=4
        with self.assertRaises(ValueError):pilot.start(bad,pilot.approvals_for(bad),self.ledger,self.audit)

    def test_rejection_stops_without_skipping_node(self):
        for kind in ('evidence','malformed','identity','http'):
            self.setUp();digest=self.start()
            status,raw=self.envelope(pilot.prior.wire_for(self.contract['plan'][0]['payload']))
            e=json.loads(raw)
            if kind=='evidence':e['choices'][0]['message']['content']=json.dumps({'class_index':0,'abstain':False,'evidence':['Fabricated unsupported quotation']})
            if kind=='malformed':e['choices'][0]['message']['content']='{'
            if kind=='identity':e['model']='gpt-6-luna-unknown'
            if kind=='http':status=429
            post=MagicMock(return_value=(status,json.dumps(e).encode()))
            summary,_=pilot.run(self.contract,base.KEY,self.ledger,self.audit,digest,transport=post)
            self.assertEqual(post.call_count,1)
            self.assertEqual(summary['state_counts']['REJECTED'],1)
            self.assertEqual(summary['rows'][4]['blind']['state'],'NOT_ATTEMPTED')

    def test_missing_fresh_approvals_and_noninteractive_blocked(self):
        for field in ('amendment','privacy','outstanding_list','declared_limits'):
            approval={**pilot.approvals_for(self.contract),field:False}
            with self.assertRaises(ValueError):pilot.start(self.contract,approval,self.ledger,self.audit)
        with patch.object(pilot.sys.stdin,'isatty',return_value=False),patch.object(pilot.canary,'credential') as key:
            self.assertEqual(pilot.main(blind_only=True),1);key.assert_not_called()


if __name__=='__main__':unittest.main()
