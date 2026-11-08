"""Synthetic diagnostics only; no historical GT or private files."""
import unittest
from llmgnn_sara.evaluation.node_diagnostics import metrics, paired, MISSING


class DiagnosticTests(unittest.TestCase):
    def test_missing_abstain_common_mask_and_confusion(self):
        truth=[0,1,2,0];a={0:0,1:0,2:None,3:MISSING};b={0:1,1:1,2:None,3:0}
        result=metrics(a,truth)
        self.assertEqual(result['counts'],{'CORRECT':1,'WRONG':1,'ABSTAINED':1,'MISSING':1})
        self.assertEqual(result['confusion'][2][7],1)
        self.assertEqual(result['confusion'][0][8],1)
        common,events=paired(a,b,truth)
        self.assertEqual(common['common_accepted'],2)
        self.assertEqual(common['states']['MISSING__CORRECT'],1)
        self.assertEqual(common['states']['ABSTAINED__ABSTAINED'],1)

    def test_invalid_class_cannot_be_abstention_column(self):
        for invalid in (7,-1,True,'unknown'):
            with self.assertRaises(ValueError):metrics({0:invalid},[0])


if __name__=='__main__':unittest.main()
