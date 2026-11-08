import unittest,hashlib
from llmgnn_sara.sara3.evidence import EXACT_FIRST,EvidenceError,EvidenceSource,validate_claims
class ExactFirstTests(unittest.TestCase):
 def claim(self,q,text):
  s=EvidenceSource('target.text','text',text,hashlib.sha256(text.encode()).hexdigest())
  return validate_claims([dict(source_id=s.source_id,field=s.field,source_sha256=s.sha256,quote=q)],(s,))
 def test_default_historical_and_versioned_exact_boundary(self):
  q='The method is called "example"'
  with self.assertRaises(EvidenceError):self.claim(q,q)
  token=EXACT_FIRST.set(True)
  try:self.assertTrue(self.claim(q,q))
  finally:EXACT_FIRST.reset(token)
  with self.assertRaises(EvidenceError):self.claim(q,q)
 def test_nonexistent_still_rejected(self):
  token=EXACT_FIRST.set(True)
  try:
   with self.assertRaises(EvidenceError):self.claim('A fabricated source quotation','The authenticated paper text')
  finally:EXACT_FIRST.reset(token)
if __name__=='__main__':unittest.main()
