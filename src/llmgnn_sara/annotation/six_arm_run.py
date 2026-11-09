"""Owner-approved sequential six-arm execution with immutable per-call intents."""
import argparse,getpass,json,os,hashlib
from pathlib import Path
from decimal import Decimal
from dataclasses import asdict
from ..sara3.audit import PrivateAudit
from ..sara3.inputs import canonical_bytes
from ..sara3.experiment import digest
from ..pilot.canary import post_once
from ..downstream.full_run import exclusive
from ..io.frozen import CLASSES
from .voting import vote_parsed_samples

PIN='33169f5a87a53e86a0eea81447fd250200afce05159f03e5e0be8e74856fae1c'
ROOT=Path('.local_artifacts/six_arm_paid_t1_v1')
MODELS=('gpt-6-luna','gpt-6-luna-2026-09-22')
RESERVATION=Decimal('0.0053248')

def parse(status,raw):
    if status!=200:raise ValueError('HTTP_REJECTED')
    obj=json.loads(raw)
    if obj.get('model') not in MODELS:raise ValueError('MODEL_IDENTITY_MISMATCH')
    choices=obj.get('choices');usage=obj.get('usage')
    if not isinstance(choices,list) or len(choices)!=1 or choices[0].get('finish_reason')!='stop':raise ValueError('TRUNCATED_OR_INVALID')
    if not isinstance(usage,dict) or any(type(usage.get(k))is not int or usage[k]<0 for k in ('prompt_tokens','completion_tokens')):raise ValueError('USAGE_UNAVAILABLE')
    if usage['prompt_tokens']>32768 or usage['completion_tokens']>4096:raise ValueError('USAGE_OVER_DECLARED_CAP')
    samples=json.loads(choices[0]['message']['content'])
    if not isinstance(samples,list) or len(samples)!=3:raise ValueError('PARSER_SCHEMA')
    parsed=[]
    for s in samples:
        if set(s)!={'answer','confidence'} or s['answer'] not in CLASSES or type(s['confidence'])not in(int,float) or not 0<=s['confidence']<=100:raise ValueError('PARSER_SCHEMA')
        parsed.append([s['answer'],s['confidence']])
    if abs(sum(s[1] for s in parsed)-100)>1e-6:raise ValueError('PARSER_CONFIDENCE_SUM')
    return dict(parsed=parsed,model=obj['model'],usage=usage,provider_response_id=obj.get('id'))

def call(root,entry,config,key,transport=post_once):
    if hashlib.sha256(entry['prompt'].encode()).hexdigest()!=entry['prompt_sha256']:raise ValueError('PROMPT_HASH_MISMATCH')
    wire=canonical_bytes(dict(model=config['model'],temperature=1,n=1,max_tokens=4096,messages=[dict(role='user',content=entry['prompt'])]))
    if len(wire)>32768 or not key:raise ValueError('WIRE_OR_CREDENTIAL_INVALID')
    binding=dict(entry_sha256=digest(entry),wire_sha256=hashlib.sha256(wire).hexdigest(),config_sha256=digest(config))
    identity=digest(binding);audit=PrivateAudit(Path(root)/'calls'/identity)
    complete=audit.root/'complete.json';intent=audit.root/'intent.json'
    if complete.exists():
        rec=audit.read(json.loads(complete.read_bytes())['receipt_sha256'])
        if rec['binding']!=binding or json.loads(intent.read_bytes())!=binding:raise ValueError('RECEIPT_BINDING')
        raw=bytes.fromhex(rec['raw_hex'])
        if hashlib.sha256(raw).hexdigest()!=rec['raw_sha256'] or parse(rec['http_status'],raw)!=rec['validated']:raise ValueError('RECEIPT_INTEGRITY')
        return rec,False
    if intent.exists():
        if json.loads(intent.read_bytes())!=binding:raise ValueError('INTENT_BINDING_MISMATCH')
        raise ValueError('EXISTING_INTENT_UNCERTAIN_OR_REJECTED_NO_RETRY')
    if len(list(Path(root).glob('calls/*/intent.json')))>=2520 or RESERVATION*(1+len(list(Path(root).glob('calls/*/intent.json'))))>Decimal('15'):raise ValueError('BUDGET_EXHAUSTED')
    exclusive(intent,canonical_bytes(binding))
    # Intent remains durable on timeout, crash, parser failure or audit failure.
    status,raw=transport(wire,key,target='account-panel-temperature1')
    if type(raw)is not bytes:raise ValueError('INVALID_RESPONSE_BYTES')
    if key.encode() in raw:raw=raw.replace(key.encode(),b'[REDACTED]');status=0
    rec=dict(binding=binding,http_status=status,raw_hex=raw.hex(),raw_sha256=hashlib.sha256(raw).hexdigest(),state='REJECTED')
    try:rec['validated']=parse(status,raw);rec['state']='COMPLETED'
    except Exception:
        audit.write(rec);raise ValueError('RESPONSE_REJECTED_STOP_NO_RETRY') from None
    sha=audit.write(rec);exclusive(complete,canonical_bytes(dict(receipt_sha256=sha)))
    return rec,True

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['smoke','full'],default='smoke')
    p.add_argument('--continue-unattempted',action='store_true',help='Preserve unresolved intents without dispatching them; no complete prediction freeze')
    args=p.parse_args()
    source=PrivateAudit('.local_artifacts/narrative_six_arm').read(PIN)
    config=dict(endpoint='https://api.gapgpt.app/v1/chat/completions',model='gpt-6-luna',temperature=1,n=1,max_tokens=4096,input_cap=32768,max_calls=2520,cap_usd='15',reasoning_effort='OMITTED',owner_approved=True,prices='OWNER_PROVISIONAL_UNVERIFIED',retention='UNVERIFIED_OWNER_RISK_ACCEPTANCE_REQUIRED')
    store=PrivateAudit(ROOT);cfgsha=store.write(config)
    entries=source['requests'];nodes=sorted({e['node_id'] for e in entries},key=lambda n:hashlib.sha256(f'six-arm-smoke-v1|{n}'.encode()).hexdigest())[:2]
    ordered=sorted(entries,key=lambda e:(e['node_id'] not in nodes,nodes.index(e['node_id']) if e['node_id'] in nodes else e['node_id'],e['arm'],e['sample_index']))
    if args.stage=='smoke':ordered=[e for e in ordered if e['node_id'] in nodes]
    print('GapGPT|gpt-6-luna|temperature1|reasoning_effort omitted|max2520 total|USD15 reservation not billing guarantee')
    print('This stage calls upper bound:',len(ordered))
    if input('Approve article sharing and unverified retention; type APPROVE PRIVACY: ')!='APPROVE PRIVACY':raise ValueError('NOT_APPROVED')
    if input('Confirm aggregate USD15; type 15: ')!='15':raise ValueError('NOT_APPROVED')
    if args.stage=='full' and input('After reviewing smoke results type APPROVE SCALE: ')!='APPROVE SCALE':raise ValueError('NOT_APPROVED')
    key=os.environ.get('GAPGPT_API_KEY')
    if not key:
        import sys
        if not sys.stdin.isatty():raise ValueError('SECURE_TERMINAL_REQUIRED')
        key=getpass.getpass('GapGPT API key (hidden): ')
    records=[];new=0;unresolved=[];completed_entries=[]
    for entry in ordered:
        try:rec,sent=call(ROOT,entry,config,key)
        except ValueError as error:
            if not args.continue_unattempted or str(error)!='EXISTING_INTENT_UNCERTAIN_OR_REJECTED_NO_RETRY':raise
            unresolved.append(entry['draft_identity'])
            continue
        records.append(rec);completed_entries.append(entry);new+=int(sent)
        if len(records)%25==0:print(json.dumps(dict(completed=len(records),new_dispatches=new,unresolved=len(unresolved))),flush=True)
    result=dict(config_sha256=cfgsha,source_manifest_sha256=PIN,stage=args.stage,completed=len(records),new_dispatches=new,input_tokens=sum(r['validated']['usage']['prompt_tokens'] for r in records),output_tokens=sum(r['validated']['usage']['completion_tokens'] for r in records),billing='NOT_VERIFIED')
    result['estimated_cost_usd']=str((Decimal(result['input_tokens'])*Decimal('.10')+Decimal(result['output_tokens'])*Decimal('.50'))/1000000)
    result['unresolved_request_ids']=unresolved
    result['status']='PARTIAL_UNRESOLVED_NO_PREDICTION_FREEZE' if unresolved else 'COMPLETED'
    if args.stage=='full' and not unresolved:
        predictions=[]
        for node in sorted({e['node_id'] for e in ordered}):
            for arm in sorted({e['arm'] for e in ordered}):
                samples=[r['validated']['parsed'] for e,r in zip(completed_entries,records) if e['node_id']==node and e['arm']==arm]
                predictions.append(dict(node_id=node,arm=arm,**asdict(vote_parsed_samples(samples))))
        result['predictions']=predictions
    sha=store.write(result);print(json.dumps({k:v for k,v in result.items() if k!='predictions'}));print('PRIVATE_FREEZE_SHA256',sha)
if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('STOPPED: inspect private intents. No automatic retry; no credential diagnostics.')
