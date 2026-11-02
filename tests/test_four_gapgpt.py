"""Four-node scope regression, temporary audits and synthetic transport only."""
import copy
import json
import unittest
from unittest.mock import MagicMock, patch
import test_outstanding_gapgpt as base
from llmgnn_sara.pilot import outstanding_gapgpt as pilot


class FourTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.object(pilot.prior, "verify_no_prior_dispatch"):
            cls.prepared = pilot.prepare(four_only=True)

    setUp = base.ContinuationTests.setUp
    start = base.ContinuationTests.start
    envelope = base.ContinuationTests.envelope
    test_crash_start_and_unknown_dispatch_never_resume = base.ContinuationTests.test_crash_start_and_unknown_dispatch_never_resume
    test_audit_failure_before_and_after_dispatch = base.ContinuationTests.test_audit_failure_before_and_after_dispatch

    def test_eight_calls_preserve_all_historical_failures(self):
        self.assertEqual(self.contract["version"], pilot.FOUR_VERSION)
        self.assertEqual(self.contract["maximum_calls"], 8)
        history = copy.deepcopy(self.contract["preserved_1243_comparison"])
        digest = self.start(); calls = []
        def post(wire, key):
            p = json.loads(json.loads(wire)["messages"][0]["content"])
            calls.append((p["node_id"], p["phase"]))
            return self.envelope(wire)
        summary, _ = pilot.run(self.contract, base.KEY, self.ledger, self.audit, digest, transport=post)
        self.assertEqual(summary["state"], "FINISHED")
        self.assertEqual(calls, [(n,p) for n in pilot.NODES for p in ("blind","compare")])
        self.assertEqual(summary["rows"][1]["compare"], history)
        self.assertEqual(summary["new_phase_denominators"], {"blind":4,"compare":4})
        self.assertEqual(summary["new_nodes_with_intents"], 4)
        self.assertEqual(summary["reported_usage_totals"]["prompt_tokens"], 6400)
        self.assertEqual(summary["reported_usage_totals"]["completion_tokens"], 800)
        self.assertEqual(summary["estimated_cost_usd"], "0.00104")
        self.assertEqual(sum(r[4] for r in self.ledger.snapshot()), 8*16384)
        self.assertIsNone(summary["accepted_label"])

    def test_all_abstain_four_blinds_no_comparisons(self):
        digest=self.start();post=MagicMock(side_effect=lambda wire,key:self.envelope(wire,abstain=True))
        summary,_=pilot.run(self.contract,base.KEY,self.ledger,self.audit,digest,transport=post)
        self.assertEqual(post.call_count,4)
        self.assertEqual(summary["state"],"FINISHED")
        self.assertEqual(summary["new_phase_denominators"],{"blind":4,"compare":0})

    def test_first_failure_halts_without_next_node(self):
        digest=self.start();status,raw=self.envelope(pilot.prior.wire_for(self.contract["plan"][0]["payload"]))
        e=json.loads(raw);e['choices'][0]['message']['content']=json.dumps({'class_index':0,'abstain':False,'evidence':['Fabricated unknown evidence']})
        post=MagicMock(return_value=(status,json.dumps(e).encode()))
        summary,_=pilot.run(self.contract,base.KEY,self.ledger,self.audit,digest,transport=post)
        self.assertEqual(post.call_count,1)
        self.assertEqual(summary["state_counts"]["REJECTED"],1)
        self.assertEqual(summary['rows'][3]['blind']['state'],'NOT_ATTEMPTED')

    def test_old_nodes_and_missing_approvals_rejected(self):
        for node in (637,1243):
            bad=copy.deepcopy(self.contract);bad['plan'][0]['node']=node
            with self.assertRaises(ValueError):pilot.start(bad,pilot.approvals_for(bad),self.ledger,self.audit)
        for field in ('privacy','outstanding_list','declared_limits','amendment'):
            approval={**pilot.approvals_for(self.contract),field:False}
            with self.assertRaises(ValueError):pilot.start(self.contract,approval,self.ledger,self.audit)

    def test_prior_comparison_wrong_blind_lineage_rejected(self):
        requests,_=pilot.prior.sealed_inputs()
        preserved=self.contract['preserved_1243']
        payload=pilot.materialize_comparison(requests[1243][1],preserved['class_index'])
        bad={**preserved['lineage'],'inner_response_sha256':'0'*64}
        with self.assertRaises(ValueError):pilot.rejected_comparison(pilot.ROOT,payload,bad)

    def test_noninteractive_never_loads_credentials(self):
        with patch.object(pilot.sys.stdin,'isatty',return_value=False),patch.object(pilot.canary,'credential') as key:
            self.assertEqual(pilot.main(four_only=True),1)
            key.assert_not_called()


if __name__=='__main__':unittest.main()
