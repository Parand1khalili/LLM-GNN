import tempfile,json,unittest
from pathlib import Path
from unittest.mock import patch
from llmgnn_sara.pilot.readiness import ReadinessLedger, CONTRACT, assert_live_ready
from llmgnn_sara.sara3.inputs import verifier_input
from llmgnn_sara.sara3.audit import PrivateAudit,AuditError

class ReadinessTests(unittest.TestCase):
 def test_bindings_restart_and_budget(self):
  with tempfile.TemporaryDirectory() as root:
   path=Path(root)/"r.sqlite"; l=ReadinessLedger(path)
   p=verifier_input(637,"This paper studies rule learning.")
   l.reserve("a",p,100,512); l.mark_dispatched("a",p)
   l=ReadinessLedger(path); self.assertEqual(l.snapshot()[0][3],"UNCERTAIN")
   with self.assertRaises(ValueError): ReadinessLedger(path,"0"*64)
   with self.assertRaises(ValueError): l.reserve("a",p,100,512)
   with self.assertRaises(ValueError): l.reserve("b",p,100,512,context_sha256="0"*64)
   with self.assertRaises(ValueError): l.mark_dispatched("a",p)
   with self.assertRaises(ValueError): l.settle("a",{**p,"node_id":130},b"{}",PrivateAudit(Path(root)/"audit"))
   with self.assertRaises(ValueError): l.reserve("bad",{**p,"response_schema":{}},100,512)
   for i in range(11): l.reserve(str(i),verifier_input(637,"Rule learning paper "+str(i)),100,512)
   with self.assertRaises(ValueError): l.reserve("over",verifier_input(637,"Rule learning overflow"),100,512)
 def test_parser_audit_and_terminal_states(self):
  samples=[b"{",b"{}",json.dumps({"class_index":0,"abstain":False,"evidence":["fabricated quote"]}).encode(),json.dumps({"class_index":None,"abstain":True,"evidence":[]}).encode(),json.dumps({"class_index":0,"abstain":False,"evidence":["This paper studies rule learning."]}).encode()]
  with tempfile.TemporaryDirectory() as root:
   audit=PrivateAudit(Path(root)/"audit"); l=ReadinessLedger(Path(root)/"r.sqlite")
   for i,raw in enumerate(samples):
    p=verifier_input(637,"This paper studies rule learning. "+str(i)); key=str(i)
    l.reserve(key,p,100,512); l.mark_dispatched(key,p)
    with patch.object(audit,"write",side_effect=AuditError()):
     with self.assertRaises(AuditError): l.settle(key,p,raw,audit)
    self.assertEqual(l.snapshot()[-1][3],"UNCERTAIN")
    result=l.settle(key,p,raw,audit)
    self.assertEqual(result["state"],"REJECTED" if i<3 else "COMPLETED")
    self.assertIsNone(result["accepted_label"])
    row=l.snapshot()[-1]; self.assertNotEqual(row[-1],row[-2]); audit.read(row[-1])
    with self.assertRaises(ValueError): l.settle(key,p,raw,audit)
 def test_caps_and_live_block(self):
  with self.assertRaises(ValueError): assert_live_ready(CONTRACT)
  with tempfile.TemporaryDirectory() as root:
   l=ReadinessLedger(Path(root)/"r.sqlite"); p=verifier_input(637,"Rule learning paper.")
   for a,b in ((16385,512),(100,513),(True,512)):
    with self.assertRaises(ValueError): l.reserve("a",p,a,b)
