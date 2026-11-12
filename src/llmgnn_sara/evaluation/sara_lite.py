"""GT-only scoring after authentic SARA-Lite prediction/control freeze."""
import argparse,json,struct,zipfile
from pathlib import Path
from ..annotation.sara_lite import ROOT
from ..annotation.sara_lite_freeze import build
from ..sara3.audit import PrivateAudit
from .six_arm import score,paired
from .cora_gt_shadow import _labels_from_original_graph,_expected_graph_names
from .homophily import measure


def main():
    p=argparse.ArgumentParser();p.add_argument('--freeze',required=True);args=p.parse_args()
    frozen=PrivateAudit(ROOT).read(args.freeze)
    if build()!=frozen:raise ValueError('AUTHENTIC_FREEZE_REPLAY')
    # GT is opened only after full offline receipt/vector replay above.
    graph=Path('.local_artifacts/gt_reference/cora_random_sbert.pt')
    labels=_labels_from_original_graph(graph,_expected_graph_names('.local_artifacts/frozen'))
    vectors={a:{int(n):v for n,v in rows.items()} for a,rows in frozen['vectors'].items()}
    truth={n:labels[n] for n in vectors['A']}
    metrics={a:score([(truth[n],v[n]) for n in truth]) for a,v in vectors.items()}
    unavailable=sum(d['action']=='UNAVAILABLE' for d in frozen['decisions'].values())
    metrics['C']['unavailable']=unavailable
    metrics['C']['abstained']=sum(d['action']=='ABSTAIN' for d in frozen['decisions'].values())
    for a,m in metrics.items():
        if a!='C':m['abstained']=m.pop('unavailable');m['unavailable']=0
    comparisons={a+'_minus_A':paired(truth,vectors['A'],v) for a,v in vectors.items() if a!='A'}
    comparisons['C_minus_D_primary']=paired(truth,vectors['D'],vectors['C'])
    with zipfile.ZipFile(graph) as z:values=struct.unpack('<21716q',z.read('cora_random_sbert/data/1'))
    hs,_,_=measure(zip(values[:10858],values[10858:]),list(labels),2708)
    strata={s:{a:score([(truth[n],v[n]) for n in truth if hs[n]['stratum']==s]) for a,v in vectors.items()}
            for s in ('homophilic','mixed','heterophilic','isolated')}
    selected={int(n) for n in frozen['decisions']}
    switches=[int(n) for n,d in frozen['decisions'].items() if d['action']=='SWITCH']
    result=dict(freeze_sha256=args.freeze,metrics=metrics,comparisons=comparisons,strata=strata,
        switches=len(switches),switch_correct=sum(vectors['C'][n]==truth[n] for n in switches),
        router=dict(selected=len(selected),selected_baseline_wrong=sum(vectors['A'][n]!=truth[n] for n in selected),
            unselected=len(truth)-len(selected),unselected_baseline_wrong=sum(vectors['A'][n]!=truth[n] for n in truth if n not in selected)),
        actual_billing_usd=None,limitations=['LIMITED_PROVENANCE_EXPLORATORY','EXPLORATORY_NOT_INDEPENDENT'])
    store=PrivateAudit(ROOT+'/gt_evaluation');sha=store.write(result)
    Path('reports/sara_lite_evaluation.json').write_text(json.dumps(dict(result_sha256=sha,**result),indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(result_sha256=sha,metrics={a:{k:m[k] for k in ('correct','wrong','abstained','unavailable')} for a,m in metrics.items()})))


if __name__=='__main__':main()
