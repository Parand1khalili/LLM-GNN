"""Final GCN verification/freeze, then separately authorized GT-only evaluation."""
import argparse
import hashlib
import json
import statistics
from pathlib import Path
from collections import Counter
from ..downstream.final_benchmark import ROOT,CONTRACT,HIST,EXPANDED,authorize,read_verified
from ..downstream.full_run import runtime
from ..sara3.audit import PrivateAudit
from ..sara3.experiment import digest
from .six_arm import score,write_csv,figure
from .full_gcn import metrics,paired


def verify(package,approval):
    """No labels are opened here; fully readback every new and reused fit."""
    authorize(package,approval)
    if package['runtime']!=runtime(Path.cwd()):raise ValueError('RUNTIME_CHANGED')
    adapter=Path('src/llmgnn_sara/downstream/final_benchmark.py')
    if hashlib.sha256(adapter.read_bytes()).hexdigest()!=package['adapter_sha256']:raise ValueError('ADAPTER_CHANGED')
    proofs=[];initial={s:set() for s in range(10)}
    sources={HIST:PrivateAudit('.local_artifacts/full_gcn_v1').read(HIST),EXPANDED:PrivateAudit('.local_artifacts/expanded_gcn_inventory_v1').read(EXPANDED)}
    for fit,entry in sorted(package['fits'].items()):
        if digest(entry['spec'])!=fit:raise ValueError('SPEC_HASH')
        if fit in package['reuse']:
            source=sources[package['reuse'][fit]['package_sha256']]
            if source['fits'][fit]['spec']!=entry['spec']:raise ValueError('REUSE_NOT_EXACT')
        for seed in range(10):
            r=read_verified(package,fit,seed)
            if r is None:raise ValueError('PENDING_FIT')
            initial[seed].add(r['initial_parameter_sha256'])
            if len(initial[seed])!=1:raise ValueError('INITIAL_PARAMETER_MISMATCH')
            proofs.append(dict(fit_sha256=fit,seed=seed,receipt_sha256=digest(r),artifact_sha256=r['artifact_sha256'],
                status='VERIFIED_EXISTING' if fit in package['reuse'] else 'EXECUTED_VERIFIED',
                duration_seconds=r.get('duration_seconds')))
    if len(proofs)!=package['unique_seed_fits'] or len({(r['fit_sha256'],r['seed']) for r in proofs})!=len(proofs):
        raise ValueError('COVERAGE_COUNTS')
    physical={(p.parent.parent.name,int(p.parent.name)) for p in (ROOT/'fits').glob('*/*/intent.json')}
    completions={(p.parent.parent.name,int(p.parent.name)) for p in (ROOT/'fits').glob('*/*/complete.json')}
    expected={(r['fit_sha256'],r['seed']) for r in proofs if r['status']=='EXECUTED_VERIFIED'}
    if physical!=expected or completions!=expected:raise ValueError('ORPHAN_OR_MISSING_INTENTS')
    return dict(schema='sara.gcn.final.training_freeze.v1',package_sha256=digest(package),
        approval_sha256=digest(approval),proofs=proofs,status='COMPLETE_VERIFIED_GT_NOT_OPENED',
        status_counts=dict(Counter(r['status'] for r in proofs)),
        new_fit_duration_seconds=sum(r['duration_seconds'] or 0 for r in proofs if r['status']=='EXECUTED_VERIFIED'))


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('verify','evaluate'));p.add_argument('--package',required=True);p.add_argument('--approval',required=True);p.add_argument('--training-freeze');a=p.parse_args()
    store=PrivateAudit(ROOT);package=store.read(a.package);approval=store.read(a.approval)
    frozen=verify(package,approval)
    if a.mode=='verify':
        sha=store.write(frozen)
        Path('reports/final_cora_gcn_coverage.json').write_text(json.dumps(dict(training_freeze_sha256=sha,**{k:v for k,v in frozen.items() if k!='proofs'}),indent=2)+'\n',encoding='utf8')
        print(json.dumps(dict(training_freeze_sha256=sha,status=frozen['status'],counts=frozen['status_counts'])))
        return
    if store.read(a.training_freeze)!=frozen:raise ValueError('TRAINING_FREEZE_REPLAY')
    # Distinct command, all predictions/checkpoints frozen and verified BEFORE GT.
    from .cora_gt_shadow import _labels_from_original_graph,_expected_graph_names
    import numpy as np
    truth=_labels_from_original_graph(Path('.local_artifacts/gt_reference/cora_random_sbert.pt'),_expected_graph_names('.local_artifacts/frozen'))
    test=package['test_ids'];scored={};classwise={};confusions={};seedrows=[];raw={}
    for fit in package['fits']:
        directory=Path(package['reuse'][fit]['root']) if fit in package['reuse'] else ROOT/'fits'
        scored[fit]={};classwise[fit]={};confusions[fit]={}
        for seed in range(10):
            with np.load(directory/fit/str(seed)/'fit.npz',allow_pickle=False) as z:pred=z['predictions'].tolist()
            values=metrics([pred[i] for i in test],[truth[i] for i in test]);scored[fit][seed]=values
            detail=score([(truth[i],pred[i]) for i in test])
            classwise[fit][str(seed)]=detail['classes'];confusions[fit][str(seed)]=detail['confusion_matrix_7x8']
    rows=[]
    for arm,record in package['arms'].items():
        fit=record['fit_sha256'];v={int(n):c for n,c in record['vector'].items()}
        raw[arm]=score([(truth[n],v[n]) for n in package['selected_ids']])
        row=dict(Arm=arm,Cohort='Sensitivity140',Loss='CE',PS=False,Mask='Natural',Train_Count=record['accepted'],Test_Count=len(test),Coverage=record['accepted']/140,
            Accuracy=statistics.mean(scored[fit][s]['Accuracy'] for s in range(10)),
            Accuracy_SD=statistics.pstdev(scored[fit][s]['Accuracy'] for s in range(10)),
            Macro_F1=statistics.mean(scored[fit][s]['Macro-F1'] for s in range(10)),
            Macro_F1_SD=statistics.pstdev(scored[fit][s]['Macro-F1'] for s in range(10)),
            Raw_Correct=raw[arm]['correct'],Raw_Wrong=raw[arm]['wrong'],
            Raw_Abstained=len(record['masks']['abstained']),Raw_Unavailable=len(record['masks']['unavailable']),
            Fit_SHA256=fit,Status='COMPLETE_VERIFIED_EXPLORATORY')
        rows.append(row)
        seedrows.extend(dict(Arm=arm,Seed=s,**scored[fit][s]) for s in range(10))
    comparisons={}
    pairs=[('current_v0',a) for a in package['arms'] if a!='current_v0']
    pairs += [('lite_exact_mask_control','lite'),('lite_class_count_control','lite'),('lite_router_only','lite')]
    pairs += [('current_v1-A',a) for a in ('current_v1-B','current_v1-C','current_v1-D')]
    for left,right in pairs:
        comparisons[right+'_minus_'+left]=dict(reference=left,treatment=right,
            right_minus_left=paired(scored[package['arms'][left]['fit_sha256']],scored[package['arms'][right]['fit_sha256']]))
    result=dict(schema='sara.gcn.final_cora.results.v1',package_sha256=a.package,training_freeze_sha256=a.training_freeze,
        rows=rows,per_seed=seedrows,comparisons=comparisons,raw_diagnostics=raw,
        classwise_by_fit=classwise,confusion_by_fit=confusions,contract=CONTRACT,
        evaluator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        limitations=CONTRACT['limitations'])
    sha=store.write(result)
    if store.read(sha)!=result:raise ValueError('RESULT_READBACK')
    Path('reports/final_cora_gcn_results.json').write_text(json.dumps(dict(result_sha256=sha,**result),indent=2)+'\n',encoding='utf8')
    write_csv('reports/final_cora_gcn_results.csv',rows);write_csv('reports/final_cora_gcn_seeds.csv',seedrows)
    write_csv('reports/final_cora_gcn_paired.csv',[dict(comparison=k,metric=m,mean_delta=v['right_minus_left'][m]['mean'],sd_delta=v['right_minus_left'][m]['population_sd']) for k,v in comparisons.items() for m in ('Accuracy','Macro-F1')])
    figure('reports/final_cora_gcn_accuracy.svg','Final Cora CE/noPS GCN benchmark',[(r['Arm'],r['Accuracy']) for r in rows],100,'10-seed mean test accuracy (%)')
    figure('reports/final_cora_gcn_macro_f1.svg','Final Cora CE/noPS GCN benchmark',[(r['Arm'],r['Macro_F1']) for r in rows],1,'10-seed mean test Macro-F1')
    print(json.dumps(dict(result_sha256=sha,rows=rows)))


if __name__=='__main__':main()
