"""Exact frozen Expanded admission/execution. GT-free; no provider transport."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import math

from . import full_run as old, full_matrix as matrix, model
from .plan import GCNConfig
from .fusion import graph_inputs
from .expanded_inventory import matrix as rebuild
from ..sara3.audit import PrivateAudit, _private_windows
from ..sara3.experiment import digest
from ..io.project import GRAPH_SHA256
from ..sara3.inputs import canonical_bytes
from ..sara3.correction_features import require

PIN='789a6aea4715c1e7537ede75d82f5e552859c392a0e27acd8cbbbc03b568da83'
ROOT=Path('.local_artifacts/expanded_gcn_execution_v1')
ADMISSION='sara.gcn.expanded.experimental_admission.v1'


def load():
    p=PrivateAudit('.local_artifacts/expanded_gcn_inventory_v1').read(PIN)
    previous=PrivateAudit('.local_artifacts/full_gcn_v1').read(p['reuse_from_package_sha256'])
    require(old.runtime(Path.cwd())==p['runtime']==previous['runtime'])
    require(hashlib.sha256(Path('src/llmgnn_sara/downstream/expanded_inventory.py').read_bytes()).hexdigest()==p['preparation_source_sha256'])
    frozen=PrivateAudit('.local_artifacts/sara3_three_agent_fusion_v1').read(previous['fusion_sha256'])
    rows,fits=rebuild(p['arms'],frozen,p['runtime'])
    require(rows==p['rows'] and fits==p['fits'] and len(fits)==359)
    return p,previous


def approval(p):
    require(digest(p)==PIN)
    return {'schema':ADMISSION,'package_sha256':PIN,'fit_set_sha256':digest(sorted(p['new_specs'])),
        'arm_vectors_sha256':digest(p['arms']),'maximum_new_seed_fits':1720,
        'owner_authorized':True,'allow_experimental_admission':True,'allow_training':True,
        'limitations':['LIMITED_PROVENANCE_EXPLORATORY','EXPLORATORY_NOT_INDEPENDENT'],
        'provenance':'EXPLICIT_OWNER_EXPANDED_PACKAGE_APPROVAL_2026-11-08',
        'scope':'ONLY_FROZEN_LABELS_UNIQUE_VALID_UNEXECUTED_SPECS_NO_GLOBAL_LABEL_REWRITE'}


def verify_new(fit,seed,approval_sha):
    import numpy as np
    directory=ROOT/'fits'/fit/str(seed)
    if not directory.exists():return None
    store=PrivateAudit(directory)
    if not (directory/'complete.json').exists():
        if list(directory.iterdir()):raise RuntimeError('UNCERTAIN_NO_AUTOMATIC_RETRY')
        return None
    for name in ('intent.json','complete.json','fit.npz'):
        path=directory/name;require(not path.is_symlink())
        import os,stat
        if os.name=='nt':_private_windows(path,store.sid)
        else:require(stat.S_IMODE(path.stat().st_mode)==0o600)
    rec=store.read(json.loads((directory/'complete.json').read_bytes())['receipt_sha256'])
    binding={'package_sha256':PIN,'fit_sha256':fit,'seed':seed,'admission_sha256':approval_sha}
    require(all(rec.get(k)==v for k,v in binding.items()) and rec['state']=='COMPLETED')
    require(json.loads((directory/'intent.json').read_bytes())=={**binding,'state':'INTENT_DURABLE_BEFORE_FIT'})
    require(len(rec['losses'])==30 and all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in rec['losses']))
    require(hashlib.sha256((directory/'fit.npz').read_bytes()).hexdigest()==rec['artifact_sha256'])
    with np.load(directory/'fit.npz',allow_pickle=False) as z:
        logits,pred=z['logits'],z['predictions'];require(logits.shape==(2708,7) and np.isfinite(logits).all())
        require(pred.shape==(2708,) and pred.dtype.kind in 'iu' and np.array_equal(pred,logits.argmax(1)))
        h=hashlib.sha256();keys=[k for k in z.files if k.startswith('state__')];require(keys)
        for k in keys:
            a=z[k];require(a.dtype.kind in 'fiu' and np.isfinite(a).all())
            h.update(k[7:].encode());h.update(str(a.dtype).encode());h.update(str(a.shape).encode());h.update(a.tobytes())
        require(h.hexdigest()==rec['final_parameter_sha256'])
    return rec


def check_coverage(expected,records,blocked_rows=0):
    keys=[(r['fit_sha256'],r['seed']) for r in records]
    errors=[]
    if len(keys)!=len(set(keys)):errors.append('DUPLICATE_RESULT')
    missing=set(expected)-set(keys)
    if missing:errors.append('MISSING_FITS:'+str(len(missing)))
    if set(keys)-set(expected):errors.append('UNEXPECTED_FITS')
    bad=[r for r in records if r['status'] not in ('VERIFIED_EXISTING','EXECUTED_VERIFIED')]
    if bad:errors.append('UNVERIFIED_FITS:'+str(len(bad)))
    if blocked_rows:errors.append('BLOCKED_CONFIG_ROWS:'+str(blocked_rows))
    return {'status':'PARTIAL_BLOCKED' if errors else 'COMPLETE_VERIFIED','errors':errors,
        'eligible_fits_complete':not missing and not bad and len(keys)==len(set(keys)) and set(keys)==set(expected),
        'expected_fits':len(expected),'status_counts':{s:sum(r['status']==s for r in records) for s in
            ('VERIFIED_EXISTING','EXECUTED_VERIFIED','BLOCKED','INVALID')}}


def scan(p,previous,apsha):
    records=[];initial={s:set() for s in range(10)}
    source_rows={r['row_id']:r for r in p['rows']}
    for fit in p['fits']:
        for seed in range(10):
            try:
                rec=old.read_fit('.local_artifacts/full_gcn_v1/fits',previous,fit,seed) if fit in previous['fits'] else verify_new(fit,seed,apsha)
                status=('VERIFIED_EXISTING' if fit in previous['fits'] else 'EXECUTED_VERIFIED') if rec else 'BLOCKED'
                reason='' if rec else 'NOT_EXECUTED'
                if rec:initial[seed].add(rec['initial_parameter_sha256'])
            except Exception as e:
                status='BLOCKED' if isinstance(e,RuntimeError) else 'INVALID'
                reason='UNCERTAIN_INTENT_NO_AUTOMATIC_RETRY' if isinstance(e,RuntimeError) else 'READBACK_OR_FINGERPRINT_MISMATCH:'+type(e).__name__
            records.append({'fit_sha256':fit,'seed':seed,'status':status,'reason':reason,
                'arm_aliases':'|'.join(sorted({source_rows[r]['arm'] for r in p['fits'][fit]['row_ids']})),
                'confidence_source_fingerprints':'|'.join(sorted({digest(source_rows[r]['confidence_percent']) for r in p['fits'][fit]['row_ids']})),
                'package_sha256':PIN})
    for row in records:
        if len(initial[row['seed']])>1:
            row.update(status='INVALID',reason='INITIAL_PARAMETER_HASH_MISMATCH_FOR_SEED')
    for directory,allowed in [(Path('.local_artifacts/full_gcn_v1/fits'),set(previous['fits'])),(ROOT/'fits',set(p['new_specs']))]:
        physical={(f.parent.parent.name,f.parent.name) for name in ('intent.json','complete.json') for f in directory.glob('*/*/'+name)}
        for fit,seed in physical:
            if fit not in allowed or seed not in {str(s) for s in range(10)}:
                records.append({'fit_sha256':fit,'seed':int(seed) if seed.isdigit() else seed,'status':'INVALID',
                    'reason':'UNEXPECTED_PHYSICAL_ARTIFACT','arm_aliases':'','confidence_source_fingerprints':'','package_sha256':PIN})
    return records


def execute(p,previous,apsha):
    import torch,numpy as np
    store=PrivateAudit(ROOT);require(store.read(apsha)==approval(p))
    require(set(p['new_specs'])==set(p['fits'])-set(previous['fits']) and 10*len(p['new_specs'])<=1720)
    graph=graph_inputs('.local_artifacts/gt_reference/cora_random_sbert.pt')
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    reference=next(iter(previous['fits']))
    initial={seed:old.read_fit('.local_artifacts/full_gcn_v1/fits',previous,reference,seed)['initial_parameter_sha256'] for seed in range(10)}
    priority={r['fit_sha256'] for r in p['rows'] if r['status']=='DRAFT_NOT_ADMITTED' and
              (r['arm']=='V1_r1_v1' or r['arm']=='NO_AGENT_FOR_V1_r1_v1')}
    specs=sorted(p['new_specs'],key=lambda f:(f not in priority,f));count=0
    for fit in specs:
        spec=p['fits'][fit]['spec'];require(digest(spec)==fit and spec['graph_sha256']==GRAPH_SHA256)
        cfg=dict(spec['config']);cfg['seeds']=tuple(cfg['seeds']);cfg=GCNConfig(**cfg)
        byid=dict(zip(spec['train_ids'],spec['class_indices']))
        require(len(byid)==len(spec['train_ids']) and set(byid)<=set(previous['selected_ids'])
            and set(byid).isdisjoint(previous['test_ids']) and all(type(k)is int and 0<=k<7 for k in byid.values())
            and len(spec['weights'])==len(byid) and all(type(w)in(int,float) and math.isfinite(w) and 0<=w<=1 for w in spec['weights']))
        for seed in range(10):
            if verify_new(fit,seed,apsha):continue
            out=PrivateAudit(ROOT/'fits'/fit/str(seed));binding={'package_sha256':PIN,'fit_sha256':fit,'seed':seed,'admission_sha256':apsha}
            old.exclusive(out.root/'intent.json',canonical_bytes({**binding,'state':'INTENT_DURABLE_BEFORE_FIT'}))
            result=model._fit(graph,{'train_ids':spec['train_ids'],'pseudo_y':[byid.get(i,-1) for i in range(2708)],'weights':spec['weights']},cfg,seed)
            require(result['initial_parameter_sha256']==initial[seed] and result['GT_accessed'] is False
                    and result['evaluation_performed'] is False)
            arrays={'state__'+k:v.detach().cpu().numpy() for k,v in result['model'].state_dict().items()}
            logits=result['logits'].detach().cpu().numpy();arrays.update(logits=logits,predictions=logits.argmax(1))
            b=io.BytesIO();np.savez_compressed(b,**arrays);blob=b.getvalue();old.exclusive(out.root/'fit.npz',blob)
            rec={**binding,'state':'COMPLETED','artifact_sha256':hashlib.sha256(blob).hexdigest(),
                'losses':result['losses'],'initial_parameter_sha256':result['initial_parameter_sha256'],
                'final_parameter_sha256':result['final_parameter_sha256'],'GT_accessed':False,'evaluation_performed':False}
            sha=out.write(rec);old.exclusive(out.root/'complete.json',canonical_bytes({'receipt_sha256':sha}));require(verify_new(fit,seed,apsha)==rec)
            count+=1
            if count==1 or count%50==0:print(json.dumps({'new_completed':count,'priority_spec':fit in priority,'loss_first':rec['losses'][0],'loss_last':rec['losses'][-1]}),flush=True)
    return count


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('run','gate'));a=parser.parse_args()
    p,previous=load();store=PrivateAudit(ROOT)
    if a.mode=='run':
        apsha=store.write(approval(p));require(store.read(apsha)==approval(p));print('ADMISSION',apsha,flush=True)
        print(json.dumps({'executed_now':execute(p,previous,apsha)}),flush=True)
    else:
        apsha=digest(approval(p));records=scan(p,previous,apsha)
        fit_records=[{**r,'record_kind':'FIT'} for r in records]
        config_records=[{'fit_sha256':'UNDEFINED:'+r['row_id'],'seed':'','status':'BLOCKED',
            'reason':r['status'],'record_kind':'CONFIG_CONSTRAINT'} for r in p['rows'] if r['status']!='DRAFT_NOT_ADMITTED']
        targets=[r for r in p['routers'] if r['status'].startswith('BLOCKED')]
        missing=[{'fit_sha256':'UNDEFINED_ARM:'+r['router']+':'+policy,'seed':'','status':'BLOCKED',
            'reason':r['status'],'record_kind':'MISSING_AGENT_ARM'} for r in targets for policy in
            ('V1','V2','V2_DIRECT','V3','CONSENSUS','P1','P2')]
        missing.extend({'fit_sha256':'UNDEFINED_VERSION:'+name,'seed':'','status':'BLOCKED',
            'reason':'MISSING_COMPLETE_COMPATIBLE_EXECUTABLE_EVIDENCE','record_kind':'MISSING_VERSION'} for name in
            ('LEGACY_SIX_NODE','RICH512_PARTIAL','HISTORICAL_JUDGE002'))
        for row in config_records+missing:
            row.update(arm_aliases='',confidence_source_fingerprints='',package_sha256=PIN)
        target=Path('reports/gcn_experiment_coverage_ledger.csv')
        buffer=io.StringIO(newline='');w=csv.DictWriter(buffer,fieldnames=list(fit_records[0]));w.writeheader();w.writerows(fit_records+config_records+missing)
        # This is a derived current-status report; historical receipts are never overwritten.
        target.write_text(buffer.getvalue(),encoding='utf-8',newline='')
        ledger_sha=store.write({'schema':'sara.gcn.expanded.coverage_ledger.v1','package_sha256':PIN,
            'admission_sha256':apsha,'fit_records':fit_records,'constraint_records':config_records+missing})
        result=check_coverage({(f,s) for f in p['fits'] for s in range(10)},records,len(config_records)+len(missing))
        result.update(config_constraint_rows=len(config_records),missing_agent_arms=len(missing),
            ledger_sha256=ledger_sha,
            definitions='FIT statuses partition3590 real seed specs; UNDEFINED records are blocked configurations/arms without a valid neural fit fingerprint')
        by_spec={fit:[r for r in records if r['fit_sha256']==fit] for fit in p['fits']}
        result['unique_spec_status_counts']={status:sum(len(rs)==10 and all(r['status']==status for r in rs)
            for rs in by_spec.values()) for status in ('VERIFIED_EXISTING','EXECUTED_VERIFIED')}
        result['unique_spec_status_counts'].update(INVALID=sum(any(r['status']=='INVALID' for r in rs) for rs in by_spec.values()),
            BLOCKED=sum(not any(r['status']=='INVALID' for r in rs) and not (len(rs)==10 and len({r['status'] for r in rs})==1 and rs[0]['status'] in ('VERIFIED_EXISTING','EXECUTED_VERIFIED')) for rs in by_spec.values()))
        sha=store.write(result);print(json.dumps({**result,'receipt_sha256':sha}));raise SystemExit(0 if result['status']=='COMPLETE_VERIFIED' else 1)


if __name__=='__main__':main()
