import copy,unittest
from unittest.mock import patch
from llmgnn_sara.annotation.narrative_v1 import evidence,prompts,prefix,sha,SPEC,extract_sources
from llmgnn_sara.annotation.prompts import FrozenPromptTemplate,SENTINEL
class NarrativeTests(unittest.TestCase):
 def setUp(self):
  self.texts=['Target paper topic','First original neighbor article text','Second original neighbor paper'];self.adj=[{1,2},{0},{0}];self.count=len
  self.template=FrozenPromptTemplate('P '+SENTINEL+' Required schema unchanged')
 def build(self):return evidence(0,self.texts[0],(2,1),self.texts,self.adj,self.count)
 def test_deterministic_identical_evidence_and_wrapper(self):
  b=self.build();self.assertEqual(b,self.build());p=prompts(b,self.template,self.count)
  import json
  body=json.dumps(b,ensure_ascii=False,sort_keys=True)
  self.assertTrue(all(body in v and v.endswith(' Required schema unchanged') for v in p.values()))
  self.assertEqual([x['node_id'] for x in b['neighbors']],[2,1])
  self.assertNotEqual(sha(p['v1-A']),sha(p['v1-B']))
 def test_isolated_and_missing(self):
  self.assertEqual(evidence(0,self.texts[0],(),self.texts,[set(),set(),set()],len)['neighbors'],[])
  texts=[self.texts[0],'',self.texts[2]]
  self.assertEqual(len(evidence(0,texts[0],(1,2),texts,self.adj,len)['neighbors']),1)
 def test_alignment_invalid_edge_and_corruption(self):
  with self.assertRaises(ValueError):evidence(0,'modified',(1,),self.texts,self.adj,len)
  with self.assertRaises(ValueError):evidence(0,self.texts[0],(2,),self.texts,[{1},{0},set()],len)
  b=self.build();b['neighbors'][0]['text']='corrupt'
  with self.assertRaises(ValueError):prompts(b,self.template,len)
 def test_directed_or_duplicate_selection_rejected(self):
  with self.assertRaises(ValueError):evidence(0,self.texts[0],(1,),self.texts,[{1},set(),set()],len)
  with self.assertRaises(ValueError):evidence(0,self.texts[0],(1,1),self.texts,self.adj,len)
 def test_budget_and_gt(self):
  self.assertEqual(prefix('abcdef',3,len),'abc')
  b=self.build();b['ground_truth']=0
  with self.assertRaises(ValueError):prompts(b,self.template,len)
  with self.assertRaises(ValueError):prompts(self.build(),self.template,lambda x:10000+len(x))
 def test_source_hash_blocks_before_zip_decode(self):
  import tempfile,pathlib
  with tempfile.TemporaryDirectory() as t:
   f=pathlib.Path(t)/'graph';f.write_bytes(b'corrupt')
   with self.assertRaises(ValueError):extract_sources(f)
if __name__=='__main__':unittest.main()
