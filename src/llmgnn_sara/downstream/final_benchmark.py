"""Final frozen Cora CE benchmark. Adapts existing plans, trainer and fit readback.

No GT decoder, provider transport, prompt change or new trainer is defined here.
"""
import argparse
import hashlib
import io
import json
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from . import full_run as old
from .plan import GCNConfig, PseudoLabel, gcn_plan
from .model import train_gcn
from .fusion import graph_inputs
from ..sara3.audit import PrivateAudit
from ..sara3.experiment import digest
from ..sara3.inputs import canonical_bytes
from ..io.project import GRAPH_SHA256
from ..io.frozen import reject_gt

ROOT=Path('.local_artifacts/final_cora_gcn_v1')
SIX='aebcd301608c4b27a877c584ced5afde85b66e103e05c2bd5edf569f472fed8e'
LITE='00daac8087163980123bdcb4796f99c4bb36854ec2382876be4dc75ee6390db5'
ATLAS='677a683959cc80691d726d3e02e23b55e02a0bb01e6e17f4c16c57ca567c4ccc'
HIST='c78ff16df921bfcd661ce7981c5467f31c243bd812466ce0bbca747be576d413'
EXPANDED='789a6aea4715c1e7537ede75d82f5e552859c392a0e27acd8cbbbc03b568da83'
CONTRACT=dict(version='sara.gcn.final_cora_ce.v1',cohort='Sensitivity140',mask='natural',
    loss='ce',PS=False,seeds=list(range(10)),config=json.loads(json.dumps(asdict(GCNConfig()))),
    validation=None,early_stopping=False,checkpoint='last epoch30',
    test='fixed2568 complement ALL140, historically observed, not independent',
    features='original frozen x/edge bytes; no normalization; encoder receipt unavailable',
    confidence='CE adapter uses unit-loss sentinel100; NOT imputed model confidence',
    dedup='exact effective graph/test/train IDs/classes/unit weights/config/runtime; seed separate',
    WCE='NOT_SCHEDULED_BLOCKED_COMMON_CONFIDENCE: Lite switches lack authentic confidence',
    resources=dict(device='cpu',threads=1,maximum_new_fits=160,wall_seconds=7200),
    failure='durable intent; halt on error/uncertain fit; never automatically repeat',
    limitations=['LIMITED_PROVENANCE_EXPLORATORY','EXPLORATORY_NOT_INDEPENDENT'])


def make_plan(ids, vector):
    if set(ids)!=set(vector) or len(ids)!=140 or len(set(ids))!=140:
        raise ValueError('COHORT_ALIGNMENT')
    for n,c in vector.items():
        if type(n) is not int or not 0<=n<2708 or (c is not None and (type(c) is not int or not 0<=c<7)):
            raise ValueError('VECTOR_DOMAIN')
    # Existing CE backend requires an unused numeric confidence slot. Its sentinel
    # never leaves this adapter; original provenance/nulls remain in arm records.
    labels=[PseudoLabel(n,vector[n],100.0) for n in ids if vector[n] is not None]
    return json.loads(json.dumps(gcn_plan(ids,labels,allow_abstention=True)))


def effective_spec(plan,runtime):
    return dict(graph_sha256=GRAPH_SHA256,test_ids_sha256=digest(plan['test_ids']),
        config=plan['config'],train_ids=plan['train_ids'],
        class_indices=[plan['pseudo_y'][n] for n in plan['train_ids']],weights=plan['weights'],runtime=runtime)


def prepare():
    store=PrivateAudit(ROOT)
    from ..annotation.six_arm_recovery import OUT,PROTOCOL,CONFIG,PIN,SUMMARY,snapshot,ROOT as SIX_ROOT,predictions
    six=PrivateAudit(OUT).read(SIX)
    if (six['protocol']!=PROTOCOL or six['config_sha256']!=CONFIG or six['source_manifest_sha256']!=PIN
        or six['execution_summary_sha256']!=SUMMARY or snapshot(SIX_ROOT)!=six['source_files']
        or predictions(six['records'])!=six['predictions']):raise ValueError('SIX_PROVENANCE')
    from ..annotation.sara_lite_freeze import build
    lite=PrivateAudit('.local_artifacts/sara_lite_v1').read(LITE)
    if build()!=lite:raise ValueError('LITE_PROVENANCE')
    from ..sara3.expanded_atlas_freeze import validate_freeze
    atlas=PrivateAudit('.local_artifacts/expanded_atlas_freeze_v1').read(ATLAS);validate_freeze(atlas)
    historical=PrivateAudit('.local_artifacts/full_gcn_v1').read(HIST)
    expanded=PrivateAudit('.local_artifacts/expanded_gcn_inventory_v1').read(EXPANDED)
    rt=old.runtime(Path.cwd())
    if historical['runtime']!=rt or expanded['runtime']!=rt:raise ValueError('RUNTIME_DRIFT')
    ids=historical['selected_ids'];arms={};vectors={}
    def add(name,vector,source,confidence,statuses):
        plan=make_plan(ids,vector);spec=effective_spec(plan,rt);fit=digest(spec)
        arms[name]=dict(source_sha256=source,vector_sha256=digest([[n,vector[n]] for n in ids]),
            vector={str(n):vector[n] for n in ids},confidence_provenance=confidence,
            masks=statuses,plan=plan,fit_sha256=fit,
            accepted=len(plan['train_ids']),class_counts=dict(Counter(str(vector[n]) for n in plan['train_ids'])))
        vectors.setdefault(fit,dict(spec=spec,plan=plan,aliases=[]))['aliases'].append(name)
    for arm in ('B1','v0','v1-A','v1-B','v1-C','v1-D'):
        rows=[r for r in six['predictions'] if r['arm']==arm]
        vector={r['node_id']:r['class_index'] for r in rows}
        add('current_'+arm,vector,SIX,{str(r['node_id']):dict(value=r['vote']['confidence_percent'] if r['vote'] else None,source=r['confidence_provenance']) for r in rows},
            dict(abstained=[],unavailable=sorted(n for n,c in vector.items() if c is None)))
    for arm,name in [('B','lite_router_only'),('C','lite'),('D','lite_exact_mask_control'),('E','lite_class_count_control')]:
        if arm not in lite['vectors']:continue
        vector={int(n):v for n,v in lite['vectors'][arm].items()}
        missing=[n for n,c in vector.items() if c is None]
        unavailable=[int(n) for n,d in lite['decisions'].items() if d['action']=='UNAVAILABLE'] if arm=='C' else []
        v0={r['node_id']:r for r in six['predictions'] if r['arm']=='v0'}
        confidence={str(n):dict(value=v0[n]['vote']['confidence_percent'] if c is not None and c==v0[n]['class_index'] else None,
            source='CONTEMPORANEOUS_NARRATIVE_VOTE' if c is not None and c==v0[n]['class_index'] else 'UNAVAILABLE_REVIEWER_CONFIDENCE') for n,c in vector.items()}
        add(name,vector,LITE,confidence,
            dict(abstained=sorted(set(missing)-set(unavailable)),unavailable=sorted(unavailable)))
    for arm in ('A_B1','B_NARRATIVE','C_BASELINE_FUSION','V1_r0','V1_r1_v1'):
        rows=expanded['arms'][arm];vector={r['node_id']:r['final_class'] for r in rows}
        add('historical_'+arm,vector,EXPANDED,{str(r['node_id']):dict(value=r['confidence_percent'],source=r['confidence_provenance']) for r in rows},dict(abstained=sorted(n for n,c in vector.items() if c is None),unavailable=[]))
    rows=atlas['vectors']['Expanded_V1'];vector={r['node_id']:r['class_index'] for r in rows}
    add('historical_Expanded_V1',vector,ATLAS,{str(r['node_id']):dict(value=r['confidence_percent'],source=r['confidence_provenance']) for r in rows},dict(abstained=sorted(n for n,c in vector.items() if c is None),unavailable=[]))
    graph=graph_inputs('.local_artifacts/gt_reference/cora_random_sbert.pt')
    features=dict(graph_sha256=GRAPH_SHA256,x_sha256=hashlib.sha256(graph.x.numpy().tobytes()).hexdigest(),edge_sha256=hashlib.sha256(graph.edge_index.numpy().tobytes()).hexdigest(),x_shape=list(graph.x.shape))
    reuse={fit:dict(package_sha256=HIST,root='.local_artifacts/full_gcn_v1/fits') for fit in vectors if fit in historical['fits']}
    for fit in vectors:
        if fit not in reuse and fit in expanded['fits']:
            reuse[fit]=dict(package_sha256=EXPANDED,root='.local_artifacts/expanded_gcn_execution_v1/fits')
    package=dict(schema=CONTRACT['version'],contract=CONTRACT,selected_ids=ids,test_ids=historical['test_ids'],
        test_ids_sha256=historical['test_ids_sha256'],arms=arms,fits=vectors,runtime=rt,features=features,
        reuse=reuse,unique_seed_fits=len(vectors)*10,maximum_new_fits=(len(vectors)-len(reuse))*10,
        adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        source_audit=old.source_audit(historical,Path.cwd()),source_pins=dict(six=SIX,lite=LITE,atlas=ATLAS,historical=HIST,expanded=EXPANDED))
    reject_gt(package)
    sha=store.write(package)
    if store.read(sha)!=package:raise ValueError('PACKAGE_READBACK')
    public=dict(package_sha256=sha,arms={a:dict(train_count=v['accepted'],class_counts=v['class_counts'],vector_sha256=v['vector_sha256'],fit_sha256=v['fit_sha256']) for a,v in arms.items()},
        unique_specs=len(vectors),expected_seed_fits=package['unique_seed_fits'],reusable_seed_fits=len(reuse)*10,maximum_new_fits=package['maximum_new_fits'],contract=CONTRACT)
    Path('reports/final_cora_gcn_preflight.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf8')
    print(json.dumps(public))
    return sha


def authorize(package,approval):
    reject_gt(package);reject_gt(approval)
    if (package['schema']!=CONTRACT['version'] or package['contract']!=CONTRACT
        or approval.get('package_sha256')!=digest(package) or approval.get('maximum_new_fits')!=package['maximum_new_fits']
        or any(approval.get(k) is not True for k in ('owner_authorized','allow_experimental_admission','allow_training','accept_limited_feature_provenance','accept_historical_observed_test'))):
        raise PermissionError('INDEPENDENT_BENCHMARK_ADMISSION_REQUIRED')
    if package['maximum_new_fits']>160:raise ValueError('RESOURCE_SCOPE')
    for fit,record in package['fits'].items():
        if digest(record['spec'])!=fit or effective_spec(record['plan'],package['runtime'])!=record['spec']:
            raise ValueError('FIT_FINGERPRINT')


def train(package_sha,approval_sha):
    store=PrivateAudit(ROOT);package=store.read(package_sha);approval=store.read(approval_sha)
    authorize(package,approval)
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=package['adapter_sha256']:raise ValueError('ADAPTER_CHANGED')
    if old.runtime(Path.cwd())!=package['runtime']:raise ValueError('RUNTIME_DRIFT')
    graph=graph_inputs('.local_artifacts/gt_reference/cora_random_sbert.pt')
    if hashlib.sha256(graph.x.numpy().tobytes()).hexdigest()!=package['features']['x_sha256']:raise ValueError('FEATURE_HASH')
    import torch,numpy as np
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    initial={s:set() for s in range(10)};completed=reused=0;start=time.monotonic()
    historical=PrivateAudit('.local_artifacts/full_gcn_v1').read(HIST)
    for fit,entry in sorted(package['fits'].items()):
        for seed in range(10):
            if fit in package['reuse']:
                receipt=read_verified(package,fit,seed)
                if receipt is None:raise ValueError('MISSING_REUSE_RECEIPT')
                reused+=1
            else:
                receipt=old.read_fit(ROOT/'fits',package,fit,seed)
                if receipt is None:
                    if time.monotonic()-start>7200:raise RuntimeError('WALL_TIME_LIMIT')
                    output=PrivateAudit(ROOT/'fits'/fit/str(seed))
                    binding=dict(package_sha256=package_sha,fit_sha256=fit,seed=seed)
                    old.exclusive(output.root/'intent.json',canonical_bytes(dict(**binding,state='INTENT_DURABLE_BEFORE_FIT')))
                    t=time.monotonic();result=train_gcn(graph,entry['plan'],seed,allow_training=True)
                    if result['GT_accessed'] or result['evaluation_performed']:raise ValueError('TRAIN_EVAL_LEAKAGE')
                    arrays={'state__'+k:v.detach().cpu().numpy() for k,v in result['model'].state_dict().items()}
                    logits=result['logits'].detach().cpu().numpy();arrays.update(logits=logits,predictions=logits.argmax(1))
                    buf=io.BytesIO();np.savez_compressed(buf,**arrays);blob=buf.getvalue();old.exclusive(output.root/'fit.npz',blob)
                    receipt=dict(**binding,state='COMPLETED',admission_sha256=approval_sha,artifact_sha256=hashlib.sha256(blob).hexdigest(),losses=result['losses'],
                        initial_parameter_sha256=result['initial_parameter_sha256'],final_parameter_sha256=result['final_parameter_sha256'],duration_seconds=time.monotonic()-t,evaluation_performed=False)
                    recsha=output.write(receipt);old.exclusive(output.root/'complete.json',canonical_bytes(dict(receipt_sha256=recsha)))
                    if old.read_fit(ROOT/'fits',package,fit,seed)!=receipt:raise ValueError('READBACK')
                    completed+=1
                else:reused+=1
            initial[seed].add(receipt['initial_parameter_sha256'])
            if len(initial[seed])!=1:raise ValueError('SAME_SEED_INITIALIZATION')
            print(json.dumps(dict(verified=completed+reused,new_fits=completed,reused=reused,total=package['unique_seed_fits'])),flush=True)
    summary=dict(package_sha256=package_sha,approval_sha256=approval_sha,new_fits=completed,reused=reused,verified=completed+reused,status='FITS_COMPLETE_GT_NOT_OPENED',elapsed_seconds=time.monotonic()-start)
    print('TRAINING_FREEZE_SHA256',store.write(summary))


def read_verified(package,fit,seed):
    if fit not in package['reuse']:return old.read_fit(ROOT/'fits',package,fit,seed)
    if package['reuse'][fit]['package_sha256']==HIST:
        historical=PrivateAudit('.local_artifacts/full_gcn_v1').read(HIST)
        return old.read_fit('.local_artifacts/full_gcn_v1/fits',historical,fit,seed)
    from .expanded_execute import verify_new,approval
    expanded=PrivateAudit('.local_artifacts/expanded_gcn_inventory_v1').read(EXPANDED)
    return verify_new(fit,seed,digest(approval(expanded)))


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('prepare','train'));p.add_argument('--package');p.add_argument('--approval');a=p.parse_args()
    if a.mode=='prepare':prepare()
    else:train(a.package,a.approval)


if __name__=='__main__':main()
