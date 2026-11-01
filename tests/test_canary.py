"""Mocked HTTP only; never uses real environment credentials or provider calls."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
from llmgnn_sara.pilot import canary
from llmgnn_sara.pilot.readiness import ReadinessLedger
from llmgnn_sara.sara3.audit import PrivateAudit,AuditError

KEY='CANARY_TEST_SECRET_123456'
APPROVAL={'privacy':True,'compatibility':True,'declared_limits':True,'usd_reservation':'0.10','dispatch':canary.IDENTITY}

class CanaryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.payload,cls.wire=canary.prepare()
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.audit=PrivateAudit(Path(self.temp.name)/'private')
  self.ledger=ReadinessLedger(self.audit.root/'intent.sqlite')
 def envelope(self,content=None,finish='stop',usage=True):
  if content is None:content=json.dumps({'class_index':None,'abstain':True,'evidence':[]})
  r={'choices':[{'message':{'content':content},'finish_reason':finish}]}
  if usage:r['usage']={'prompt_tokens':1000,'completion_tokens':50}
  return json.dumps(r).encode()
 def run_mock(self,raw=None,status=200,key=KEY,transport=None,approval=APPROVAL):
  return canary.execute(self.payload,self.wire,key,self.audit,self.ledger,approval,
    transport=transport or MagicMock(return_value=(status,raw if raw is not None else self.envelope())))
 def test_success_usage_private_receipts_and_no_label(self):
  result=self.run_mock()
  self.assertEqual(result['status'],'COMPLETED');self.assertEqual(result['l1_status'],'PASS')
  self.assertIsNone(result['accepted_label']);self.assertEqual(result['l2_status'],'NOT_ASSESSED')
  self.assertEqual(result['estimated_cost_usd'],'0.000125')
  self.audit.read(result['result_receipt']);self.audit.read(result['provider_response_receipt'])
  for p in self.audit.root.iterdir():self.assertNotIn(KEY.encode(),p.read_bytes())
 def test_duplicate_after_restart_never_dispatches(self):
  self.run_mock();self.ledger=ReadinessLedger(self.ledger.path)
  post=MagicMock()
  with self.assertRaises(ValueError):self.run_mock(transport=post)
  post.assert_not_called()
 def test_unknown_timeout_counts_and_no_retry(self):
  post=MagicMock(side_effect=TimeoutError(KEY))
  result=self.run_mock(transport=post)
  self.assertEqual(result['status'],'UNCERTAIN');self.assertEqual(self.ledger.snapshot()[0][3],'UNCERTAIN')
  with self.assertRaises(ValueError):self.run_mock(transport=post)
  self.assertEqual(post.call_count,1)
  for p in self.audit.root.iterdir():self.assertNotIn(KEY.encode(),p.read_bytes())
 def test_http_rejection_even_if_body_looks_like_valid_schema(self):
  raw=json.dumps({'class_index':None,'abstain':True,'evidence':[]}).encode()
  result=self.run_mock(raw,status=429)
  self.assertEqual(result['status'],'REJECTED');self.assertEqual(result['reason'],'HTTP_REJECTION_NO_RETRY')
 def test_truncation_and_malformed_are_not_success(self):
  result=self.run_mock(self.envelope(finish='length'))
  self.assertEqual(result['status'],'REJECTED')
 def test_malformed_json_and_fabricated_quote(self):
  result=self.run_mock(self.envelope('{'))
  self.assertEqual(result['status'],'REJECTED')
 def test_fabricated_quote_l1_rejected(self):
  result=self.run_mock(self.envelope(json.dumps({'class_index':0,'abstain':False,'evidence':['invented quotation']})))
  self.assertEqual(result['status'],'REJECTED');self.assertEqual(result['l1_status'],'FAIL')
 def test_secret_echo_raw_and_json_escaped_never_persisted(self):
  key='CANARY_TEST_SECRET_"_123456'
  result=self.run_mock(json.dumps({'echo':key}).encode(),key=key)
  self.assertEqual(result['status'],'REJECTED')
  for p in self.audit.root.iterdir():
   b=p.read_bytes();self.assertNotIn(key.encode(),b);self.assertNotIn(json.dumps(key)[1:-1].encode(),b)
 def test_audit_failure_before_dispatch(self):
  post=MagicMock()
  with patch.object(self.audit,'write',side_effect=AuditError()):
   with self.assertRaises(AuditError):self.run_mock(transport=post)
  post.assert_not_called()
 def test_audit_failure_after_dispatch_stays_uncertain(self):
  post=MagicMock(return_value=(200,self.envelope()))
  original=self.audit.write;calls=[0]
  def write(record):
   calls[0]+=1
   if calls[0]>1:raise AuditError()
   return original(record)
  with patch.object(self.audit,'write',side_effect=write):result=self.run_mock(transport=post)
  self.assertEqual(result['status'],'UNCERTAIN');self.assertEqual(self.ledger.snapshot()[0][3],'UNCERTAIN')
 def test_wrong_scope_approval_payload_and_monetary_reservation_block(self):
  post=MagicMock()
  for approval in ({**APPROVAL,'privacy':False},{**APPROVAL,'usd_reservation':'1.00'},{**APPROVAL,'dispatch':'compare'}):
   with self.assertRaises(ValueError):self.run_mock(transport=post,approval=approval)
  with self.assertRaises(ValueError):canary.execute({**self.payload,'node_id':130},self.wire,KEY,self.audit,self.ledger,APPROVAL,transport=post)
  post.assert_not_called()
 def test_fixed_http_host_tls_no_redirect_retry(self):
  conn=MagicMock();conn.getresponse.return_value.status=302;conn.getresponse.return_value.read.return_value=b''
  with patch.object(canary.http.client,'HTTPSConnection',return_value=conn) as factory:
   status,raw=canary.post_once(self.wire,KEY)
  self.assertEqual(status,302);self.assertEqual(factory.call_args.args,('api.gapapi.com',))
  self.assertEqual(factory.call_args.kwargs['timeout'],120)
  self.assertEqual(conn.request.call_count,1);self.assertEqual(conn.request.call_args.args[:2],('POST','/v1/chat/completions'))
  conn.close.assert_called_once()
 def test_key_from_environment_or_hidden_prompt_and_no_noninteractive_fallback(self):
  with patch.dict(canary.os.environ,{'GAPGPT_API_KEY':KEY},clear=True):self.assertEqual(canary.credential(),KEY)
  with patch.dict(canary.os.environ,{},clear=True),patch.object(canary.sys.stdin,'isatty',return_value=False):
   with self.assertRaises(ValueError):canary.credential()
  with patch.dict(canary.os.environ,{},clear=True),patch.object(canary.sys.stdin,'isatty',return_value=True),patch.object(canary.getpass,'getpass',return_value=KEY) as get:
   self.assertEqual(canary.credential(),KEY);get.assert_called_once()

 def test_unicode_escaped_secret_echo_is_redacted(self):
  escaped=''.join('\\u%04x'%ord(c) for c in KEY)
  raw=('{"echo":"'+escaped+'"}').encode()
  result=self.run_mock(raw)
  self.assertEqual(result['status'],'REJECTED')
  receipt=self.audit.read(result['provider_response_receipt'])
  persisted=bytes.fromhex(receipt['raw_hex'])
  self.assertNotIn(KEY,persisted.decode());self.assertNotIn(escaped,persisted.decode())
 def test_usage_exhaustion_and_wrong_model_fail_closed(self):
  raw=json.loads(self.envelope());raw['usage']['completion_tokens']=513
  result=self.run_mock(json.dumps(raw).encode())
  self.assertEqual(result['status'],'REJECTED')
 def test_returned_model_substitution_is_not_accepted(self):
  raw=json.loads(self.envelope());raw['model']='unapproved-other-model'
  result=self.run_mock(json.dumps(raw).encode())
  self.assertEqual(result['status'],'REJECTED')
  self.assertEqual(result['reason'],'RETURNED_MODEL_MISMATCH')
  self.assertEqual(result['usage'],raw['usage'])
  self.assertIsNone(result['accepted_label'])
 def test_revision_identifier_is_not_silently_authorized_and_usage_survives(self):
  raw=json.loads(self.envelope());raw['model']='gpt-6-luna-2026-09-22'
  result=self.run_mock(json.dumps(raw).encode())
  self.assertEqual(result['reason'],'RETURNED_MODEL_MISMATCH')
  self.assertEqual(result['status'],'REJECTED')
  self.assertEqual(result['estimated_cost_usd'],'0.000125')
  self.assertIsNone(result['accepted_label'])
 def test_missing_usage_is_unknown_not_zero_billing(self):
  result=self.run_mock(self.envelope(usage=False))
  self.assertEqual(result['status'],'COMPLETED');self.assertIsNone(result['usage'])
  self.assertIsNone(result['estimated_cost_usd'])
 def test_noninteractive_cli_rejects_without_key_access_or_dispatch(self):
  with patch.object(canary.sys.stdin,'isatty',return_value=False),patch.object(canary,'credential',side_effect=AssertionError('Key accessed')),patch.object(canary,'execute',side_effect=AssertionError('Dispatch')):
   self.assertEqual(canary.main(),1)

 def test_account_panel_target_has_fresh_identity_and_fixed_host(self):
  approval={**APPROVAL,'dispatch':canary.ACCOUNT_PANEL_IDENTITY}
  conn=MagicMock();conn.getresponse.return_value.status=200;conn.getresponse.return_value.read.return_value=self.envelope()
  with patch.object(canary.http.client,'HTTPSConnection',return_value=conn) as factory:
   result=canary.execute(self.payload,self.wire,KEY,self.audit,self.ledger,approval,target='account-panel')
  self.assertEqual(result['status'],'COMPLETED')
  self.assertEqual(factory.call_args.args,('api.gapgpt.app',))
  self.assertEqual(conn.request.call_args.args[:2],('POST','/v1/chat/completions'))
  self.assertEqual(conn.request.call_args.kwargs['body'],self.wire)
  self.assertEqual(conn.request.call_args.kwargs['headers']['Authorization'],'Bearer '+KEY)
  self.assertEqual(self.ledger.snapshot()[0][0],canary.ACCOUNT_PANEL_IDENTITY)
  with self.assertRaises(ValueError):canary.execute(self.payload,self.wire,KEY,self.audit,self.ledger,approval,target='account-panel')
  self.assertEqual(conn.request.call_count,1)
 def test_old_confirmation_and_arbitrary_host_do_not_authorize_new_target(self):
  post=MagicMock()
  with self.assertRaises(ValueError):canary.execute(self.payload,self.wire,KEY,self.audit,self.ledger,APPROVAL,target='account-panel',transport=post)
  with self.assertRaises(ValueError):canary.post_once(self.wire,KEY,target='unapproved-host')
  post.assert_not_called()
 def test_main_profiles_have_distinct_state_directories(self):
  old=canary.target_settings('historical');new=canary.target_settings('account-panel')
  self.assertNotEqual(old[1],new[1]);self.assertNotEqual(old[2],new[2]);self.assertNotEqual(old[3],new[3])

 def test_explicit_temperature1_derivative_only_changes_generation_setting(self):
  payload,wire=canary.prepare(target='account-panel-temperature1')
  old=json.loads(self.wire);new=json.loads(wire)
  self.assertEqual(payload,self.payload);self.assertEqual(new['messages'],old['messages'])
  self.assertEqual({k for k in old if old[k]!=new[k]},{'temperature'})
  self.assertEqual(new['temperature'],1)
  approval={**APPROVAL,'dispatch':canary.TEMPERATURE1_IDENTITY,'temperature_change':True}
  conn=MagicMock();conn.getresponse.return_value.status=200;conn.getresponse.return_value.read.return_value=self.envelope()
  with patch.object(canary.http.client,'HTTPSConnection',return_value=conn) as factory:
   result=canary.execute(payload,wire,KEY,self.audit,self.ledger,approval,target='account-panel-temperature1')
  self.assertEqual(result['status'],'COMPLETED');self.assertIsNone(result['accepted_label'])
  self.assertEqual(factory.call_args.args,('api.gapgpt.app',));self.assertEqual(conn.request.call_args.kwargs['body'],wire)
  self.assertEqual(self.ledger.snapshot()[0][0],canary.TEMPERATURE1_IDENTITY)
 def test_temperature_change_needs_separate_confirmation(self):
  payload,wire=canary.prepare(target='account-panel-temperature1');post=MagicMock()
  approval={**APPROVAL,'dispatch':canary.TEMPERATURE1_IDENTITY}
  with self.assertRaises(ValueError):canary.execute(payload,wire,KEY,self.audit,self.ledger,approval,target='account-panel-temperature1',transport=post)
  post.assert_not_called()
