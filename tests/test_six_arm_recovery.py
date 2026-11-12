"""Synthetic-only offline recovery and evaluation boundaries."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llmgnn_sara.annotation import six_arm_recovery as recovery
from llmgnn_sara.annotation.six_arm_run import call
from llmgnn_sara.evaluation.six_arm import paired, score
from llmgnn_sara.io.frozen import CLASSES


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'private'
        self.config = {'model':'gpt-6-luna'}
        self.entries = [dict(arm=a, node_id=0, sample_index=s, prompt='Synthetic text',
            prompt_sha256=hashlib.sha256(b'Synthetic text').hexdigest(), tokens=3)
            for a in recovery.ARMS for s in range(3)]

    def response(self, identity, invalid=False):
        answers = [dict(answer=CLASSES[i], confidence=c) for i,c in enumerate((60,30,10))]
        if invalid:
            answers = answers[:2]
        return json.dumps(dict(id=identity, model='gpt-6-luna',
            choices=[dict(finish_reason='stop', message=dict(content=json.dumps(answers)))],
            usage=dict(prompt_tokens=3, completion_tokens=10))).encode()

    def save(self, entry, invalid=False, response_id=None):
        return call(self.root, entry, self.config, 'synthetic-not-a-key',
            transport=lambda *a,**k:(200,self.response(response_id or recovery.digest(entry),invalid)))

    def test_authentic_completed_recovery_determinism_and_immutability(self):
        for e in self.entries:
            self.save(e)
        before = recovery.snapshot(self.root)
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            rows = recovery.reconcile(self.entries,self.config,self.root)
            first = recovery.predictions(rows)
            self.assertEqual(first,recovery.predictions(list(reversed(rows))))
        self.assertEqual(len(first),6)
        self.assertTrue(all(r['class_index']==0 for r in first))
        self.assertEqual(before,recovery.snapshot(self.root))

    def test_missing_ambiguous_invalid_no_partial_vote(self):
        e = self.entries[0]
        self.assertEqual(recovery.inspect_request(self.root,e,self.config)['status'],'MISSING_NEVER_DISPATCHED')
        def timeout(*a,**kw):
            raise TimeoutError()
        with self.assertRaises(TimeoutError):
            call(self.root,e,self.config,'synthetic-not-a-key',transport=timeout)
        self.assertEqual(recovery.inspect_request(self.root,e,self.config)['status'],'AMBIGUOUS_DISPATCH')
        with self.assertRaises(ValueError):
            self.save(self.entries[1],invalid=True)
        self.save(self.entries[2])
        rows=[recovery.inspect_request(self.root,x,self.config) for x in self.entries[:3]]
        self.assertEqual(rows[1]['status'],'COMPLETED_OUTPUT_INVALID')
        pred=recovery.predictions(rows)[0]
        self.assertEqual(pred['valid_samples'],1)
        self.assertIsNone(pred['class_index'])
        self.assertIsNone(pred['vote'])

    def test_corrupt_receipt_and_wrong_binding_fail(self):
        self.save(self.entries[0])
        directory=next((self.root/'calls').iterdir())
        pointer=json.loads((directory/'complete.json').read_bytes())
        (directory/(pointer['receipt_sha256']+'.json')).write_bytes(b'{}')
        with self.assertRaises(ValueError):
            recovery.inspect_request(self.root,self.entries[0],self.config)
        self.save(self.entries[1])
        binding=recovery.binding_for(self.entries[1],self.config)
        intent=self.root/'calls'/recovery.digest(binding)/'intent.json'
        intent.write_text('{}')
        with self.assertRaisesRegex(ValueError,'INTENT_BINDING'):
            recovery.inspect_request(self.root,self.entries[1],self.config)
        wrong=dict(self.entries[2],prompt='modified synthetic source')
        with self.assertRaisesRegex(ValueError,'PROMPT_HASH'):
            recovery.inspect_request(self.root,wrong,self.config)

    def test_duplicate_response_id_and_sample_manifest_fail(self):
        for e in self.entries:
            self.save(e,response_id='duplicate-synthetic-id')
        with self.assertRaisesRegex(ValueError,'DUPLICATE_PROVIDER_RESPONSE_ID'):
            recovery.reconcile(self.entries,self.config,self.root)
        with self.assertRaises(ValueError):
            recovery.reconcile(self.entries+[self.entries[0]],self.config,self.root)

    def test_zero_two_valid_and_historical_tie(self):
        def rows(count):
            return [dict(arm='B1',node_id=0,sample_index=s,
                status='COMPLETED_VALID' if s<count else 'AMBIGUOUS_DISPATCH',
                validated=dict(parsed=[[CLASSES[s],60]])) for s in range(3)]
        for count in (0,1,2):
            self.assertIsNone(recovery.predictions(rows(count))[0]['class_index'])
        self.assertEqual(recovery.predictions(rows(3))[0]['class_index'],0)

    def test_denominators_missing_is_not_wrong_and_common_pair(self):
        m=score([(0,0),(1,0),(2,None)])
        self.assertEqual((m['correct'],m['wrong'],m['unavailable']),(1,1,1))
        self.assertEqual(m['all_target_accuracy'],1/3)
        self.assertEqual(m['selective_accuracy'],.5)
        p=paired({0:0,1:1,2:2},{0:1,1:1,2:None},{0:0,1:None,2:2})
        self.assertEqual(p['common_complete'],1)
        self.assertEqual(p['common_accuracy_delta_pp'],100)
        with self.assertRaises(ValueError):
            paired({0:0},{0:0},{})

    def test_freeze_module_has_no_gt_or_training_loader(self):
        import ast
        tree=ast.parse(Path(recovery.__file__).read_text())
        names=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        self.assertFalse(any('evaluation' in n or 'downstream' in n for n in names))
        self.assertEqual(recovery.PROTOCOL['new_api_calls'],0)
        self.assertEqual(recovery.PROTOCOL['training_runs'],0)

    def test_bad_freeze_stops_before_gt(self):
        from unittest.mock import MagicMock
        from llmgnn_sara.evaluation import six_arm
        store=MagicMock()
        store.read.return_value={'schema':'forged-version'}
        with patch.object(six_arm,'PrivateAudit',return_value=store), \
             patch.object(six_arm,'_labels_from_original_graph',side_effect=AssertionError('GT opened')) as gt, \
             patch('sys.argv',['offline-eval','--freeze','a'*64]):
            with self.assertRaises((ValueError,KeyError)):
                six_arm.main()
        gt.assert_not_called()


if __name__=='__main__':
    unittest.main()
