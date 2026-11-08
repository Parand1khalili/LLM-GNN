import copy,json,unittest
from llmgnn_sara.annotation.six_arm_preflight import build
from llmgnn_sara.annotation.narrative_v1 import evidence,prompts,sha
from llmgnn_sara.sara3.experiment import digest
from llmgnn_sara.annotation.prompts import FrozenPromptTemplate,SENTINEL
class SixArmTests(unittest.TestCase):
 def setUp(self):
  self.template=FrozenPromptTemplate('P '+SENTINEL+' SAME_SCHEMA')
  bundle=evidence(0,'Target',(1,),['Target','Authentic neighbor'],[{1},{0}],len)
  p=prompts(bundle,self.template,len)
  self.row=dict(evidence=bundle,evidence_sha256=digest(bundle),prompts=p,prompt_sha256={k:sha(v) for k,v in p.items()})
 def test_four_instructions_same_evidence_schema_and_frozen_AB(self):
  p=build(self.row,self.template,len);self.assertEqual(set(p),{'v1-A','v1-B','v1-C','v1-D'})
  for k,v in p.items():
   self.assertIn(json.dumps(self.row['evidence'],ensure_ascii=False,sort_keys=True),v)
   self.assertTrue(v.endswith(' SAME_SCHEMA'))
  self.assertEqual({k:p[k] for k in ('v1-A','v1-B')},self.row['prompts'])
 def test_corrupt_evidence_and_prompt(self):
  row=copy.deepcopy(self.row);row['evidence']['target']['text']='forged'
  with self.assertRaises(ValueError):build(row,self.template,len)
  row=copy.deepcopy(self.row);row['prompts']['v1-A']='modified'
  with self.assertRaises(ValueError):build(row,self.template,len)
 def test_token_ceiling(self):
  with self.assertRaises(ValueError):build(self.row,self.template,lambda x:5000)
if __name__=='__main__':unittest.main()
