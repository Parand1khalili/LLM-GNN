"""One authorized review per manifest target; no retries or fallback providers."""
import argparse
import getpass
import hashlib
import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from .sara_lite import ROOT, PROTOCOL, BASE, decide
from ..sara3.audit import PrivateAudit
from ..sara3.experiment import digest
from ..sara3.inputs import canonical_bytes
from ..downstream.full_run import exclusive
from ..pilot.canary import post_once, strict_json

MANIFEST='dea21474fc5027237f3ea8e69999eb98dd18e7ebb40e0ead18400600f2e0088a'
APPROVAL=dict(version='sara.lite.owner_approval.v1',manifest_sha256=MANIFEST,
    cap_usd='0.25',max_calls=37,privacy='owner approved sharing these37 target/context inputs',
    provenance='explicit owner chat approval; not provider billing/retention guarantee',
    allowed_returned_models=PROTOCOL['execution']['returned_models'])
RUN=Path(ROOT)/'execution'
RESERVATION=Decimal('0.0053248')


def validate(status,raw,target,baseline):
    if status!=200:raise ValueError('HTTP_REJECTED')
    obj=strict_json(raw)
    if obj.get('model') not in APPROVAL['allowed_returned_models']:raise ValueError('MODEL_IDENTITY')
    if type(obj.get('id')) is not str or not obj['id']:raise ValueError('RESPONSE_ID')
    choices=obj.get('choices');usage=obj.get('usage')
    if type(choices) is not list or len(choices)!=1 or choices[0].get('finish_reason')!='stop':raise ValueError('TRUNCATION')
    if type(usage) is not dict or any(type(usage.get(k)) is not int or not 0<=usage[k]<=cap for k,cap in [('prompt_tokens',32768),('completion_tokens',4096)]):raise ValueError('USAGE')
    decision=decide(strict_json(choices[0]['message']['content']),target,baseline)
    return dict(decision=decision,usage=usage,model=obj['model'],provider_response_id=obj['id'])


def call(root,entry,key,target,baseline,transport=post_once,allow_dispatch=True):
    if not key or hashlib.sha256(entry['prompt'].encode()).hexdigest()!=entry['prompt_sha256']:
        raise ValueError('CREDENTIAL_OR_PROMPT')
    wire=canonical_bytes(dict(model='gpt-6-luna',temperature=1,n=1,max_tokens=4096,
        messages=[dict(role='user',content=entry['prompt'])]))
    binding=dict(manifest_sha256=MANIFEST,approval_sha256=digest(APPROVAL),entry_sha256=digest(entry),
        wire_sha256=hashlib.sha256(wire).hexdigest(),target_sha256=hashlib.sha256(target.encode()).hexdigest(),baseline=baseline)
    audit=PrivateAudit(Path(root)/'calls'/digest(binding))
    intent=audit.root/'intent.json';complete=audit.root/'complete.json'
    if intent.exists():
        if json.loads(intent.read_bytes())!=binding:raise ValueError('INTENT_BINDING')
        if not complete.exists():raise ValueError('AMBIGUOUS_NO_RETRY')
        record=audit.read(json.loads(complete.read_bytes())['receipt_sha256'])
        raw=bytes.fromhex(record['raw_hex'])
        if record['binding']!=binding or hashlib.sha256(raw).hexdigest()!=record['raw_sha256']:raise ValueError('RECEIPT_BINDING')
        if record['status']=='COMPLETED' and validate(record['http_status'],raw,target,baseline)!=record['validated']:raise ValueError('REPLAY')
        if record['status'] not in ('COMPLETED','REJECTED'):raise ValueError('TERMINAL_STATE')
        return record,False
    if not allow_dispatch:raise ValueError('READ_ONLY_MISSING_RECEIPT')
    count=len(list(Path(root).glob('calls/*/intent.json')))
    if count>=37 or RESERVATION*(count+1)>Decimal(APPROVAL['cap_usd']):raise ValueError('BUDGET')
    exclusive(intent,canonical_bytes(binding))
    status,raw=transport(wire,key,target='account-panel-temperature1')
    if key.encode() in raw:raw=raw.replace(key.encode(),b'[REDACTED]');status=0
    record=dict(binding=binding,http_status=status,raw_hex=raw.hex(),raw_sha256=hashlib.sha256(raw).hexdigest(),status='REJECTED')
    try:record['validated']=validate(status,raw,target,baseline);record['status']='COMPLETED'
    except Exception:pass  # Persist authentic invalid output; never repair it.
    sha=audit.write(record);exclusive(complete,canonical_bytes(dict(receipt_sha256=sha)))
    return record,True


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=('smoke','full'),default='smoke');args=p.parse_args()
    store=PrivateAudit(ROOT);manifest=store.read(MANIFEST)
    if manifest['protocol_sha256']!=digest(PROTOCOL):raise ValueError('PROTOCOL')
    frozen=PrivateAudit('.local_artifacts/six_arm_offline_analysis').read(BASE)
    from .six_arm_recovery import snapshot,ROOT as SOURCE_ROOT
    if snapshot(SOURCE_ROOT)!=frozen['source_files']:raise ValueError('SOURCE_CHANGED')
    from ..io.project import load_project_inputs
    pairs={p.node_id:p for p in load_project_inputs('.local_artifacts/frozen','.local_artifacts/authentic').pairs}
    baseline={r['node_id']:r['class_index'] for r in frozen['predictions'] if r['arm']=='v0'}
    entries=sorted(manifest['requests'],key=lambda e:hashlib.sha256(f'lite-smoke|{e["node_id"]}'.encode()).hexdigest())
    if len(entries)!=37 or len({e['node_id'] for e in entries})!=37:raise ValueError('COHORT')
    run=PrivateAudit(RUN);run.write(APPROVAL)
    print('GapGPT | gpt-6-luna | temperature1 | one review/node | max37 INCLUDING smoke2 | aggregate USD0.25')
    print('Declared reservation USD0.1970176; not provider billing guarantee. Retention not independently verified.')
    if args.stage=='full':
        # Validate smoke first, with a transport that cannot issue a request.
        for e in entries[:2]:
            def blocked(*a,**k):raise ValueError('SMOKE_MISSING')
            r,new=call(RUN,e,'offline-replay-placeholder',pairs[e['node_id']].text,baseline[e['node_id']],blocked,allow_dispatch=False)
            if new or r['status']!='COMPLETED':raise ValueError('SMOKE_NOT_VALID')
        if input('After reviewing smoke type APPROVE LITE SCALE: ')!='APPROVE LITE SCALE':raise ValueError('NOT_APPROVED')
    if input('Confirm scoped privacy and USD0.25; type APPROVE LITE V1: ')!='APPROVE LITE V1':raise ValueError('NOT_APPROVED')
    key=os.environ.get('GAPGPT_API_KEY')
    if not key:
        if not sys.stdin.isatty():raise ValueError('SECURE_LOCAL_TERMINAL_REQUIRED')
        key=getpass.getpass('GapGPT API key (hidden): ')
    records=[];new=0
    for e in entries[:2] if args.stage=='smoke' else entries:
        r,sent=call(RUN,e,key,pairs[e['node_id']].text,baseline[e['node_id']]);records.append(r);new+=sent
        print(json.dumps(dict(processed=len(records),new_dispatches=new,status=r['status'])),flush=True)
        if r['status']=='REJECTED' and args.stage=='smoke':raise ValueError('REJECTED_SMOKE_REVIEW_REQUIRED')
    summary=dict(stage=args.stage,manifest_sha256=MANIFEST,approval_sha256=digest(APPROVAL),
        processed=len(records),new_dispatches=new,input_tokens=sum(r['validated']['usage']['prompt_tokens'] for r in records if 'validated' in r),
        output_tokens=sum(r['validated']['usage']['completion_tokens'] for r in records if 'validated' in r),
        rejected=sum(r['status']=='REJECTED' for r in records),usage_scope='validated responses only; rejected usage unknown here',billing='NOT_VERIFIED')
    print(json.dumps(summary));print('PRIVATE_RECEIPT_SHA256',run.write(summary))


if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('LITE_BLOCKED: inspect private receipts; never retry an ambiguous intent.') from None
