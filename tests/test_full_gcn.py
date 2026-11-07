"""Full matrix and synthetic fit fixtures; never real Cora fitting or GT access."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_three_agent_fusion import synthetic
from llmgnn_sara.downstream import full_matrix as m, full_run as r, model
from llmgnn_sara.evaluation import full_gcn as e
from llmgnn_sara.sara3.experiment import digest
from llmgnn_sara.sara3.audit import PrivateAudit


class MatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, _, cls.report, _ = synthetic()
        cls.package = m.build(cls.report, runtime={'fixture': 'SYNTHETIC_ONLY'})

    def test_matrix_all_conditions_and_deduplication_without_gt(self):
        p = self.package
        self.assertEqual(len(p['rows']), 960)
        self.assertEqual(len({x['row_id'] for x in p['rows']}), 960)
        self.assertEqual(p['unique_seed_fits'], 10*len(p['fits']))
        for protocol in m.CONTRACT['protocols']:
            for cohort in ('primary','sensitivity'):
                for loss in ('ce','wce'):
                    for ps in (False,True):
                        natural = [x for x in p['rows'] if (x['protocol'],x['cohort'],x['loss'],x['PS'],x['mask'])
                                   == (protocol,cohort,loss,ps,'natural')]
                        self.assertEqual([x['arm'] for x in natural], m.CONTRACT['arms'])
        self.assertEqual(m.build(self.report,runtime={'fixture':'SYNTHETIC_ONLY'}),p)
        for fit in p['fits'].values():
            self.assertTrue(set(fit['spec']['train_ids']).isdisjoint(p['test_ids']))
        for change in ({'gt':[0]}, {'correctness':True}):
            with self.assertRaises(ValueError): m.build({**self.report, **change},runtime={})
        for flag in ('oracle','debug_gt_label','filter_all_wrong_labels'):
            with self.assertRaises(ValueError):m.reject_controls({'nested':{flag:True}})

    def test_missing_confidence_weights_are_not_confidence(self):
        records=[{'node_id':i,'final_class':i%2,'confidence_percent':c} for i,c in enumerate([20,60,None])]
        hist=m.values(records,loss='wce',ps=False,protocol=m.HISTORICAL)
        self.assertTrue(hist['status'].startswith('BLOCKED'))
        ext=m.values(records,loss='wce',ps=False,protocol=m.EXTENSION)
        self.assertEqual(ext['weights'],[0.,1.,1.])
        self.assertEqual(ext['confidence_percent'],[20,60,None])
        self.assertEqual(ext['weight_status'][-1],'UNWEIGHTED_MISSING_CONFIDENCE')
        constant=m.values([{**x,'confidence_percent':80 if x['confidence_percent'] is not None else None}
                           for x in records],loss='wce',ps=False,protocol=m.EXTENSION)
        self.assertEqual(constant['weights'],[1.,1.,1.])
        unknown=m.values([{**x,'confidence_percent':None} for x in records],loss='wce',ps=True,protocol=m.EXTENSION)
        self.assertEqual(unknown['weights'],[1.,1.,1.]);self.assertEqual(unknown['PS_effective'],0)
        self.assertEqual(unknown['confidence_percent'],[None,None,None])

    def test_protected_ps_budget_guard_no_mutation_and_bad_values(self):
        records=[{'node_id':i,'final_class':i%2,'confidence_percent':90-i if i<8 else None} for i in range(10)]
        before=copy.deepcopy(records)
        result=m.values(records,loss='wce',ps=True,protocol=m.EXTENSION)
        self.assertEqual(result['PS_requested'],2)
        self.assertEqual(result['PS_effective'],2)
        self.assertEqual(result['protected_ids'],[8,9])
        self.assertTrue({8,9} <= set(result['train_ids']))
        self.assertTrue(set(result['PS_removed_ids']).isdisjoint({8,9}))
        self.assertEqual(records,before)
        for field,value in (('final_class',7),('confidence_percent',float('nan')),('node_id',True)):
            bad=copy.deepcopy(records);bad[0][field]=value
            with self.assertRaises(ValueError):m.values(bad,loss='ce',ps=False,protocol=m.EXTENSION)
        # Seven singleton scored classes cannot be deleted. Budget shortfall is explicit.
        singleton=[{'node_id':i,'final_class':i,'confidence_percent':50} for i in range(7)]
        capped=m.values(singleton,loss='ce',ps=True,protocol=m.EXTENSION)
        self.assertEqual((capped['PS_requested'],capped['PS_effective'],capped['PS_shortfall']),(2,0,2))
        self.assertEqual(m.values(singleton,loss='ce',ps=True,protocol=m.HISTORICAL)['status'],'BLOCKED_PS_CLASS_GUARD_CAPACITY')

    def test_pairwise_and_coverage_masks_and_public_output(self):
        p=self.package
        for row in p['rows']:
            if row['status']!='DRAFT_NOT_ADMITTED':continue
            if row['mask']=='coverage_matched_no_agent':
                treatment=next(x for x in p['rows'] if (x['arm'],x['cohort'],x['protocol'],x['loss'],x['PS'],x['mask'])
                    ==(row['pair'][1],row['cohort'],row['protocol'],row['loss'],row['PS'],'natural'))
                self.assertEqual(row['train_ids'],treatment['train_ids'])
            elif row['mask']=='pairwise':
                peers=[x for x in p['rows'] if (x['cohort'],x['protocol'],x['loss'],x['PS'],x['mask'],x['pair'])
                       ==(row['cohort'],row['protocol'],row['loss'],row['PS'],'pairwise',row['pair'])]
                self.assertEqual(len(peers),2)
                self.assertEqual(set(peers[0]['train_ids']),set(peers[1]['train_ids']))
        public=json.dumps(m.public_rows(p))
        self.assertNotIn('node_id',public);self.assertNotIn('class_indices',public)
        self.assertTrue(all(x['Accuracy'] is None for x in m.public_rows(p)))

    def test_approval_independent_gates_and_no_gt_fitting(self):
        p=self.package
        audit={'schema':r.AUDIT,'package_sha256':digest(p),'graph_sha256':r.GRAPH_SHA256,
               'test_ids_sha256':p['test_ids_sha256'],'runtime':p['runtime'],
               'status':'LIMITED_PROVENANCE_EXPLORATORY','test_status':'HISTORICALLY_OBSERVED_NOT_INDEPENDENT'}
        blank=r.approval_template(p,audit)
        with self.assertRaises(PermissionError):r.authorize(p,audit,None)
        with self.assertRaises(ValueError):r.authorize(p,audit,blank)
        approved={k:True if type(v)is bool else v for k,v in blank.items()}
        r.authorize(p,audit,approved)
        for key in ('audit_sha256','package_sha256'):
            with self.assertRaises(ValueError):r.authorize(p,audit,{**approved,key:'0'*64})
        with self.assertRaises(ValueError):r.authorize(p,audit,{**approved,'gt':[1]})
        with self.assertRaises(PermissionError):model.train_matrix_fit(None,p,next(iter(p['fits'])),0)
        with patch.object(model,'_fit',return_value='synthetic') as fit:
            sha=next(iter(p['fits']))
            self.assertEqual(model.train_matrix_fit(None,p,sha,0,allow_training=True),'synthetic')
            labels=fit.call_args.args[1]['pseudo_y']
            self.assertTrue(all(labels[i]==-1 for i in p['test_ids']))
            with self.assertRaises(ValueError):model.train_matrix_fit(None,{**p,'gt':[0]},sha,0,allow_training=True)

    def test_synthetic_metrics_and_paired_deltas_not_real_results(self):
        self.assertEqual(e.metrics([0,1],[0,1]),{'Accuracy':100.,'Macro-F1':2/7})
        left={s:{'Accuracy':50.,'Macro-F1':.5} for s in range(10)}
        right={s:{'Accuracy':51.,'Macro-F1':.6} for s in range(10)}
        self.assertEqual(e.paired(left,right)['Accuracy']['mean'],1.)
        with self.assertRaises(ValueError):e.paired({0:left[0]},right)
        with self.assertRaises(ValueError):e.metrics([7],[0])


@unittest.skipUnless(importlib.util.find_spec('torch') and importlib.util.find_spec('numpy'), 'Optional Torch/NumPy unavailable')
class FitRecoveryTests(unittest.TestCase):
    def fixture(self):
        import torch
        _,_,report,_=synthetic();p=m.build(report,runtime={'fixture':'SYNTHETIC_ONLY'})
        sha=next(iter(p['fits']));p['fits']={sha:p['fits'][sha]};p['unique_seed_fits']=10
        audit={'schema':r.AUDIT,'package_sha256':digest(p),'graph_sha256':r.GRAPH_SHA256,
               'test_ids_sha256':p['test_ids_sha256'],'runtime':p['runtime'],
               'status':'LIMITED_PROVENANCE_EXPLORATORY','test_status':'HISTORICALLY_OBSERVED_NOT_INDEPENDENT'}
        approved={k:True if type(v)is bool else v for k,v in r.approval_template(p,audit).items()}
        graph=model.GraphInputs(torch.zeros((2708,1)),torch.zeros((2,0),dtype=torch.long))
        return p,sha,audit,approved,graph

    def test_no_automatic_replay_after_failure_or_audit_loss(self):
        p,sha,audit,approved,graph=self.fixture()
        with tempfile.TemporaryDirectory() as temp:
            output=PrivateAudit(Path(temp)/'private').root
            with self.assertRaises(RuntimeError):
                r.execute(p,audit,approved,graph,output,fitter=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('SYNTHETIC_CRASH')))
            with self.assertRaises(RuntimeError):r.read_fit(output,p,sha,0)
            with patch.object(model,'train_matrix_fit') as fit:
                with self.assertRaises(RuntimeError):r.execute(p,audit,approved,graph,output)
                fit.assert_not_called()

    def test_freeze_readback_reuse_tamper_and_audit_failure(self):
        import torch
        p,sha,audit,approved,graph=self.fixture()
        def fake(graph,package,fit_sha,seed,**kwargs):
            net=torch.nn.Linear(1,7)
            return {'model':net,'logits':torch.zeros((2708,7)),'losses':[1.]*30,'seed':seed,
                    'GT_accessed':False,'evaluation_performed':False,'initial_parameter_sha256':'a'*64,
                    'final_parameter_sha256':model._parameter_hash(net)}
        with tempfile.TemporaryDirectory() as temp:
            output=PrivateAudit(Path(temp)/'private').root
            with patch.object(torch,'load',side_effect=AssertionError('NO_PICKLE')):
                self.assertEqual(r.execute(p,audit,approved,graph,output,fitter=fake)['completed_seed_fits'],10)
                self.assertEqual(r.execute(p,audit,approved,graph,output,fitter=lambda *a,**k:self.fail('duplicate'))['verified_reused_seed_fits'],10)
            artifact=output/sha/'0'/'fit.npz'; artifact.write_bytes(artifact.read_bytes()+b'changed')
            with self.assertRaises(ValueError):r.read_fit(output,p,sha,0)
        with tempfile.TemporaryDirectory() as temp:
            output=PrivateAudit(Path(temp)/'private').root
            with patch.object(PrivateAudit,'write',side_effect=ValueError('SYNTHETIC_AUDIT_FAILURE')):
                with self.assertRaises(ValueError):r.execute(p,audit,approved,graph,output,fitter=fake)
            with self.assertRaises(RuntimeError):r.read_fit(output,p,sha,0)


if __name__=='__main__':unittest.main()
