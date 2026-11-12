"""Offline prediction/control freeze. Never dispatches and never opens GT."""
import json
import hashlib
from collections import Counter
from pathlib import Path
from .sara_lite import ROOT,BASE,PROTOCOL
from .sara_lite_run import RUN,MANIFEST,APPROVAL,call
from ..sara3.audit import PrivateAudit
from ..sara3.experiment import digest
from ..io.project import load_project_inputs


def controls(baseline,selected,decisions):
    if set(decisions)!=set(selected) or not set(selected)<=set(baseline):raise ValueError('CONTROL_ALIGNMENT')
    lite=dict(baseline)
    for n,d in decisions.items():lite[n]=d['class_index']
    matched={n:(baseline[n] if lite[n] is not None else None) for n in baseline}
    counts=Counter(c for c in lite.values() if c is not None);chosen={}
    for c,count in counts.items():
        available=sorted((n for n in baseline if baseline[n]==c),key=lambda n:hashlib.sha256(f'lite-class-control|{n}'.encode()).hexdigest())
        if len(available)<count:
            return dict(A=baseline,B={n:(None if n in selected else c) for n,c in baseline.items()},C=lite,D=matched),dict(status='BLOCKED_CLASS_CAPACITY')
        chosen.update({n:c for n in available[:count]})
    return dict(A=baseline,B={n:(None if n in selected else c) for n,c in baseline.items()},C=lite,D=matched,
        E={n:chosen.get(n) for n in baseline}),dict(status='AVAILABLE',selection='prespecified per-class SHA order; different IDs, not causal mask match')


def build():
    store=PrivateAudit(ROOT);manifest=store.read(MANIFEST)
    if manifest['protocol_sha256']!=digest(PROTOCOL):raise ValueError('PROTOCOL')
    base=PrivateAudit('.local_artifacts/six_arm_offline_analysis').read(BASE)
    from .six_arm_recovery import snapshot,ROOT as OLD_ROOT
    if snapshot(OLD_ROOT)!=base['source_files']:raise ValueError('SOURCE_INTEGRITY')
    pairs={p.node_id:p for p in load_project_inputs('.local_artifacts/frozen','.local_artifacts/authentic').pairs}
    baseline={r['node_id']:r['class_index'] for r in base['predictions'] if r['arm']=='v0'}
    decisions={};receipts={}
    for e in manifest['requests']:
        n=e['node_id']
        def forbidden(*a,**k):raise AssertionError('NETWORK_FORBIDDEN')
        try:
            record,sent=call(RUN,e,'offline-only-placeholder',pairs[n].text,baseline[n],forbidden,allow_dispatch=False)
            if sent:raise ValueError('UNEXPECTED_DISPATCH')
            receipts[str(n)]=record
            d=record.get('validated',{}).get('decision')
            decisions[n]=d if record['status']=='COMPLETED' else dict(action='UNAVAILABLE',class_index=None)
        except ValueError as err:
            if str(err) not in ('AMBIGUOUS_NO_RETRY','READ_ONLY_MISSING_RECEIPT'):raise
            receipts[str(n)]=dict(status=str(err))
            decisions[n]=dict(action='UNAVAILABLE',class_index=None)
    vectors,capacity=controls(baseline,manifest['selected_ids'],decisions)
    result=dict(schema='sara.lite.prediction_freeze.v1',manifest_sha256=MANIFEST,
        protocol_sha256=digest(PROTOCOL),approval_sha256=digest(APPROVAL),
        baseline_sha256=BASE,receipts=receipts,decisions={str(n):v for n,v in decisions.items()},
        vectors={k:{str(n):c for n,c in v.items()} for k,v in vectors.items()},class_count_control=capacity,
        l2_status='NOT_ASSESSED',training_admission='NOT_ADMITTED',
        status='PARTIAL' if any(d['action']=='UNAVAILABLE' for d in decisions.values()) else 'COMPLETED')
    result['vectors_sha256']=digest(result['vectors'])
    return result


def main():
    result=build();sha=PrivateAudit(ROOT).write(result)
    public=dict(freeze_sha256=sha,status=result['status'],manifest_sha256=MANIFEST,
        actions=dict(Counter(d['action'] for d in result['decisions'].values())),class_count_control=result['class_count_control'])
    Path('reports/sara_lite_freeze.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf8')
    print(json.dumps(public))


if __name__=='__main__':main()
