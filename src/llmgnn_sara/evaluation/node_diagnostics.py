"""Post-hoc private diagnostics on already frozen predictions; never trains."""
import json
from itertools import combinations
from collections import Counter
from pathlib import Path
import statistics

from .cora_gt_shadow import _labels_from_original_graph, _expected_graph_names
from ..sara3.audit import PrivateAudit
from ..sara3.experiment import digest
from ..sara3.atlas import semantic_support
from ..io.project import load_project_inputs
from ..downstream.full_run import read_fit

VERSION='sara.posthoc.node_diagnostics.v1'
MISSING='MISSING'


def state(pred, truth):
    return 'MISSING' if pred==MISSING else 'ABSTAINED' if pred is None else 'CORRECT' if pred==truth else 'WRONG'


def metrics(pred, truth):
    if not pred or any(v not in (None,MISSING) and (type(v) is not int or not 0<=v<7) for v in pred.values()):
        raise ValueError('Invalid diagnostic class domain')
    ids=set(pred); counts=Counter(state(pred[i],truth[i]) for i in ids)
    cm=[[0]*9 for _ in range(7)]
    for i in ids:cm[truth[i]][8 if pred[i]==MISSING else 7 if pred[i] is None else pred[i]]+=1
    by=[]
    for k in range(7):
        tp=cm[k][k];fp=sum(cm[j][k] for j in range(7) if j!=k)
        observed=sum(cm[k][:8]);support=sum(cm[k]);fn=observed-tp
        by.append({'class_index':k,'support_all':support,'support_observed':observed,
            'precision':tp/(tp+fp) if tp+fp else 0.,'recall_observed_abstention_as_FN':tp/observed if observed else 0.,
            'recall_all':tp/support if support else 0.,'f1_observed':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.})
    accepted=counts['CORRECT']+counts['WRONG']
    return {'denominator':len(ids),'counts':dict(counts),'accepted':accepted,
        'coverage':accepted/len(ids),'selective_accuracy':counts['CORRECT']/accepted if accepted else None,
        'confusion_columns':list(range(7))+['ABSTAIN','MISSING'],'confusion':cm,'classwise':by}


def paired(a,b,truth):
    ids=set(a)&set(b); c=Counter();events={}
    for i in sorted(ids):
        sa,sb=state(a[i],truth[i]),state(b[i],truth[i]);c[sa+'__'+sb]+=1
        events[i]=[sa,sb,a[i],b[i]]
    common={i for i in ids if a[i] not in (None,MISSING) and b[i] not in (None,MISSING)}
    correct=lambda p:{i for i in ids if state(p[i],truth[i])=='CORRECT'}
    wrong=lambda p:{i for i in ids if state(p[i],truth[i])=='WRONG'}
    jac=lambda x,y:len(x&y)/len(x|y) if x|y else None
    return {'denominator':len(ids),'states':dict(c),'common_accepted':len(common),
        'common_correct_A':sum(a[i]==truth[i] for i in common),'common_correct_B':sum(b[i]==truth[i] for i in common),
        'label_disagreements_common':sum(a[i]!=b[i] for i in common),
        'jaccard_correct':jac(correct(a),correct(b)),'jaccard_error':jac(wrong(a),wrong(b))},events


def main():
    root=Path('.local_artifacts');store=PrivateAudit(root/'node_diagnostics_v1')
    expanded=PrivateAudit(root/'expanded_gcn_inventory_v1').read('789a6aea4715c1e7537ede75d82f5e552859c392a0e27acd8cbbbc03b568da83')
    package=PrivateAudit(root/'full_gcn_v1').read('c78ff16df921bfcd661ce7981c5467f31c243bd812466ce0bbca747be576d413')
    features=PrivateAudit(root/'sara3_correction_features_v1').read(expanded['source_features_sha256'])
    inputs=load_project_inputs(root/'frozen',root/'authentic')
    # All methods/settings fixed before historical GT is decoded in this process.
    settings=[('natural','ce',False),('natural','wce',False),('natural','ce',True),
              ('matched_all','ce',False),('coverage_matched_no_agent','ce',False)]
    planned=[r for r in package['rows'] if r['cohort']=='primary' and r['protocol']=='missing_confidence_aware.v1'
        and (r['mask_mode'] if 'mask_mode' in r else r['mask'],r['loss'],r['PS']) in settings
        and r['status']=='DRAFT_NOT_ADMITTED']
    raw={arm:{r['node_id']:r['final_class'] for r in rows} for arm,rows in expanded['arms'].items()}
    source_rows={(r['router'],r['node_id']):r for r in features['rows']}
    for router in ('r0','r1_v1'):
        for phase in ('blind','compare'):
            raw[router+'_'+phase]={pair.node_id:(source_rows[router,pair.node_id][phase]['class_index']
                if source_rows[router,pair.node_id][phase]['state']=='COMPLETED' else MISSING)
                if (router,pair.node_id) in source_rows else MISSING for pair in inputs.pairs}
    truth=_labels_from_original_graph(root/'gt_reference/cora_random_sbert.pt',_expected_graph_names(root/'frozen'))
    public={'schema':VERSION,'status':'POST_HOC_DIAGNOSTIC_NOT_NEW_FULL_GCN_EVALUATION',
        'limitations':['LIMITED_PROVENANCE_EXPLORATORY','EXPLORATORY_NOT_INDEPENDENT'],
        'raw':{},'raw_pairs':[],'router':{},'gcn':[],'gcn_pairs':[],'method_sources':{}}
    private={'schema':VERSION,'raw_node_table':[],'raw_pair_events':{},'router_node_sets':{},'gcn_nodes':{}}
    for arm,pred in raw.items():
        public['raw'][arm]={}
        for cohort,ids in [('sensitivity',package['selected_ids']),('primary',[i for i in package['selected_ids'] if i not in package['primary_excluded_ids']])]:
            public['raw'][arm][cohort]=metrics({i:pred[i] for i in ids},truth)
        public['method_sources'][arm]={'expanded_inventory_sha256':digest(expanded),'source_feature_sha256':expanded['source_features_sha256'],
            'prepared_only_GCN_not_executed':arm not in package['contract']['arms'],'prediction_sha256':digest(pred)}
        rows={r['node_id']:r for r in expanded['arms'].get(arm,[])}
        for i,prediction in pred.items():
            router='r1_v1' if 'r1_v1' in arm else 'r0' if 'r0' in arm else None
            feature=source_rows.get((router,i))
            private['raw_node_table'].append({'method':arm,'node_id':i,'ground_truth':truth[i],
                'prediction':prediction,'status':state(prediction,truth[i]),'confidence':rows.get(i,{}).get('confidence_percent'),
                'confidence_provenance':rows.get(i,{}).get('confidence_provenance','UNAVAILABLE_FOR_PHASE'),
                'selected':feature is not None if router else None,'phase_details':feature,
                'label_source':rows.get(i,{}).get('label_source','AUTHENTIC_PHASE_OR_MISSING'), 'L2':'NOT_ASSESSED'})
    for a,b in combinations(raw,2):
        for cohort,ids in [('sensitivity',package['selected_ids']),('primary',[i for i in package['selected_ids'] if i not in package['primary_excluded_ids']])]:
            summary,events=paired({i:raw[a][i] for i in ids},{i:raw[b][i] for i in ids},truth)
            public['raw_pairs'].append({'A':a,'B':b,'cohort':cohort,**summary})
            private['raw_pair_events'][a+'__'+b+'__'+cohort]=events
    for router in ('r0','r1_v1'):
        selected={r['node_id'] for r in features['rows'] if r['router']==router};unselected=set(package['selected_ids'])-selected
        def errors(ids):return sum(raw['A_B1'][i]!=truth[i] or raw['B_NARRATIVE'][i]!=truth[i] for i in ids)
        groups={}
        for scope,ids in [('selected',selected),('unselected',unselected)]:
            for coverage,subset in [('no_atlas',{p.node_id for p in inputs.pairs if max(semantic_support(p.text))==0}),('atlas_observed',{p.node_id for p in inputs.pairs if max(semantic_support(p.text))>0})]:
                use=ids&subset;groups[scope+'_'+coverage]={'count':len(use),'baseline_any_error':errors(use)}
        public['router'][router]={'selected':len(selected),'selected_any_error':errors(selected),'unselected':len(unselected),
            'unselected_any_error':errors(unselected),'enrichment':(errors(selected)/len(selected))/(errors(unselected)/len(unselected)) if errors(unselected) else None,
            'atlas_strata':groups,'phase_states':{p:dict(Counter(r[p]['state'] for r in features['rows'] if r['router']==router)) for p in ('blind','compare')}}
        private['router_node_sets'][router]={'selected':sorted(selected),'unselected':sorted(unselected)}
    import numpy as np
    cache={};gcn_pred={}
    for row in planned:
        fit=row['fit_sha256']
        if fit not in cache:
            cache[fit]={}
            for seed in range(10):
                assert read_fit(root/'full_gcn_v1/fits',package,fit,seed)
                with np.load(root/'full_gcn_v1/fits'/fit/str(seed)/'fit.npz',allow_pickle=False) as z:
                    predictions=z['predictions']
                    cache[fit][seed]={i:int(predictions[i]) for i in package['test_ids']}
        key=row['row_id'];gcn_pred[key]=cache[fit]
        nodes=[]
        for i in package['test_ids']:
            correct=sum(cache[fit][s][i]==truth[i] for s in range(10))
            nodes.append({'node_id':i,'ground_truth':truth[i],'correct_seeds':correct,
                'stability':'ALWAYS_CORRECT' if correct==10 else 'ALWAYS_WRONG' if correct==0 else 'SEED_DEPENDENT',
                'predictions':[cache[fit][s][i] for s in range(10)]})
        private['gcn_nodes'][key]=nodes
        public['gcn'].append({k:row[k] for k in ('arm','cohort','loss','PS','mask','row_id','fit_sha256')}|
            {'train_count':len(row['train_ids']),'stability':dict(Counter(x['stability'] for x in nodes))})
    for a,b in combinations(planned,2):
        same=all(a[k]==b[k] for k in ('mask','loss','PS'))
        control=a['mask']=='natural' and b['mask']=='coverage_matched_no_agent' and b['pair']==['NO_AGENT',a['arm']] and a['loss']==b['loss'] and a['PS']==b['PS']
        if not same and not control:continue
        values=[]
        for seed in range(10):
            summary,events=paired(gcn_pred[a['row_id']][seed],gcn_pred[b['row_id']][seed],truth)
            values.append(summary);private.setdefault('gcn_pair_events',{})[a['row_id']+'__'+b['row_id']+'__'+str(seed)]=events
        public['gcn_pairs'].append({'A':a['row_id'],'B':b['row_id'],'seed_summaries':values,
            'fixes_B_vs_A_mean':statistics.mean(v['states'].get('WRONG__CORRECT',0) for v in values),
            'harms_B_vs_A_mean':statistics.mean(v['states'].get('CORRECT__WRONG',0) for v in values)})
    private_sha=store.write(private);public['private_diagnostic_sha256']=private_sha
    sha=store.write(public)
    Path('reports/sara3_node_diagnostics_v1.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'public_sha256':sha,'private_sha256':private_sha,'raw_methods':len(raw),'gcn_rows':len(planned),'unique_gcn_specs_read':len(cache)}))


if __name__=='__main__':main()
