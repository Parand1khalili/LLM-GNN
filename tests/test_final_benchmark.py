import unittest
from copy import deepcopy
from llmgnn_sara.downstream.final_benchmark import make_plan,effective_spec,authorize,CONTRACT
from llmgnn_sara.sara3.experiment import digest

class FinalBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.ids=list(range(140));self.v={i:(i%7 if i<120 else None) for i in self.ids}
    def test_masks_gt_isolation_and_fixed_settings(self):
        p=make_plan(self.ids,self.v)
        self.assertEqual(len(p['train_ids']),120);self.assertEqual(len(p['test_ids']),2568)
        self.assertFalse(set(self.ids)&set(p['test_ids']))
        self.assertEqual(p['pseudo_y'][120],-1)
        self.assertEqual(p['config']['seeds'],list(range(10)))
        self.assertEqual(p['weights'],[1.0]*120)
        self.assertFalse(p['early_stopping']);self.assertIsNone(p['validation'])
    def test_alignment_class_and_duplicate_fail(self):
        for ids,v in [(self.ids+[0],self.v),(self.ids,{**self.v,140:1}),(self.ids,{**self.v,0:7})]:
            with self.assertRaises(ValueError):make_plan(ids,v)
    def test_fingerprint_repeat_and_distinct_labels(self):
        p=make_plan(self.ids,self.v)
        a=effective_spec(p,{'device':'cpu'})
        self.assertEqual(digest(a),digest(effective_spec(deepcopy(p),{'device':'cpu'})))
        q=make_plan(self.ids,{**self.v,0:1})
        self.assertNotEqual(digest(a),digest(effective_spec(q,{'device':'cpu'})))
    def test_wce_not_silently_imputed_and_schedule_frozen(self):
        from llmgnn_sara.downstream.plan import GCNConfig
        self.assertIn('BLOCKED_COMMON_CONFIDENCE',CONTRACT['WCE'])
        self.assertEqual(CONTRACT['loss'],'ce')
        with self.assertRaises(ValueError):GCNConfig(epochs=29)
        with self.assertRaises(ValueError):GCNConfig(seeds=(0,1))
    def test_admission_hash_and_provenance_gate(self):
        p=make_plan(self.ids,self.v);runtime={'device':'cpu'};spec=effective_spec(p,runtime)
        package=dict(schema=CONTRACT['version'],contract=CONTRACT,maximum_new_fits=10,runtime=runtime,
            fits={digest(spec):dict(spec=spec,plan=p)})
        a=dict(package_sha256=digest(package),maximum_new_fits=10,owner_authorized=True,
            allow_experimental_admission=True,allow_training=True,accept_limited_feature_provenance=True,accept_historical_observed_test=True)
        authorize(package,a)
        for key in ('allow_training','accept_limited_feature_provenance','owner_authorized'):
            bad={**a,key:False}
            with self.assertRaises(PermissionError):authorize(package,bad)
        with self.assertRaises(PermissionError):authorize(package,{**a,'package_sha256':'0'*64})
    def test_invalid_freeze_prevents_gt_open(self):
        from unittest.mock import MagicMock,patch
        from llmgnn_sara.evaluation import final_benchmark as evaluation
        audit=MagicMock();audit.read.return_value={}
        with patch.object(evaluation,'PrivateAudit',return_value=audit), \
             patch.object(evaluation,'verify',side_effect=ValueError('CORRUPT_CHECKPOINT')), \
             patch('llmgnn_sara.evaluation.cora_gt_shadow._labels_from_original_graph') as gt, \
             patch('sys.argv',['evaluation','evaluate','--package','x','--approval','y','--training-freeze','z']):
            with self.assertRaises(ValueError):evaluation.main()
        gt.assert_not_called()

if __name__=='__main__':unittest.main()
