import unittest
import tempfile
import json
import hashlib
import io
from pathlib import Path
from unittest.mock import patch
import importlib.util
from llmgnn_sara.downstream.expanded_execute import check_coverage
from llmgnn_sara.downstream import expanded_execute as ex
from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.inputs import canonical_bytes


class CoverageTests(unittest.TestCase):
    def test_unbound_package_cannot_receive_admission(self):
        with self.assertRaises(ValueError):ex.approval({'schema':'forged'})

    def test_complete_and_missing_or_falsely_complete(self):
        expected={('a',0),('b',0)}
        rows=[{'fit_sha256':'a','seed':0,'status':'VERIFIED_EXISTING'},
              {'fit_sha256':'b','seed':0,'status':'EXECUTED_VERIFIED'}]
        self.assertEqual(check_coverage(expected,rows)['status'],'COMPLETE_VERIFIED')
        self.assertFalse(check_coverage(expected,rows[:1])['eligible_fits_complete'])
        self.assertEqual(check_coverage(expected,rows,1)['status'],'PARTIAL_BLOCKED')
        self.assertTrue(check_coverage(expected,rows,1)['eligible_fits_complete'])

    def test_corruption_pending_duplicate_and_unexpected_fail(self):
        row={'fit_sha256':'a','seed':0,'status':'VERIFIED_EXISTING'}
        for rows in ([row,row],[{**row,'status':'INVALID'}],[{**row,'status':'PENDING'}],
                     [{**row,'fit_sha256':'unknown'}]):
            self.assertEqual(check_coverage({('a',0)},rows)['status'],'PARTIAL_BLOCKED')

    @unittest.skipUnless(importlib.util.find_spec('numpy'),'Optional NumPy unavailable')
    def test_real_checkpoint_hash_and_uncertain_intent(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as temp:
            root=PrivateAudit(Path(temp)/'private').root;fit='f'*64;ap='a'*64
            out=PrivateAudit(root/'fits'/fit/'0')
            binding={'package_sha256':ex.PIN,'fit_sha256':fit,'seed':0,'admission_sha256':ap}
            ex.old.exclusive(out.root/'intent.json',canonical_bytes({**binding,'state':'INTENT_DURABLE_BEFORE_FIT'}))
            with patch.object(ex,'ROOT',root):
                with self.assertRaises(RuntimeError):ex.verify_new(fit,0,ap)
                weight=np.ones((1,),dtype=np.float32);h=hashlib.sha256()
                h.update(b'weight');h.update(b'float32');h.update(b'(1,)');h.update(weight.tobytes())
                buffer=io.BytesIO();np.savez_compressed(buffer,state__weight=weight,
                    logits=np.zeros((2708,7),dtype=np.float32),predictions=np.zeros(2708,dtype=np.int64))
                blob=buffer.getvalue();ex.old.exclusive(out.root/'fit.npz',blob)
                rec={**binding,'state':'COMPLETED','losses':[1.]*30,'initial_parameter_sha256':'0'*64,
                     'final_parameter_sha256':h.hexdigest(),'artifact_sha256':hashlib.sha256(blob).hexdigest()}
                sha=out.write(rec);ex.old.exclusive(out.root/'complete.json',canonical_bytes({'receipt_sha256':sha}))
                self.assertEqual(ex.verify_new(fit,0,ap),rec)
                with self.assertRaises(ValueError):ex.verify_new(fit,0,'b'*64)
                (out.root/'fit.npz').write_bytes(blob+b'changed')
                with self.assertRaises(ValueError):ex.verify_new(fit,0,ap)


if __name__=='__main__':unittest.main()
