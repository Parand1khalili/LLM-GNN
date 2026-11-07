"""Offline inventory/reconstruction only; no evaluator, admission or training."""
import copy
import json
from collections import Counter
from itertools import combinations
from pathlib import Path
import sqlite3

from . import full_matrix as m, full_run as runner
from .ce_preflight import control_labels
from ..sara3 import fusion as f, correction_features as features
from ..sara3 import weighted_arbitration_v2 as v2, evidence_arbitration_v3 as v3
from ..sara3 import graph_support_coverage as direct, consensus_only as consensus
from ..sara3.selection import ROUTERS, select_router
from ..sara3.r1_coverage import rank_policy, NEUTRAL
from ..sara3.audit import PrivateAudit
from ..sara3.experiment import digest
from ..io.frozen import read_pinned_json
from ..io.project import load_project_inputs, GRAPH_SHA256

VERSION = 'sara.gcn.expanded_inventory.v1'


def matrix(arms, report, runtime):
    rows, fits = [], {}
    for cohort in m.CONTRACT['cohorts']:
        excluded = set(report['primary_excluded_ids']) if cohort == 'primary' else set()
        for protocol in m.CONTRACT['protocols']:
            for loss in m.CONTRACT['losses']:
                for ps in m.CONTRACT['PS']:
                    natural=[]
                    for name, labels in arms.items():
                        records=[r for r in labels if r['final_class'] is not None and r['node_id'] not in excluded]
                        row=m.values(records,loss=loss,ps=ps,protocol=protocol)
                        row.update(arm=name,cohort=cohort,protocol=protocol,loss=loss,PS=ps,mask='natural',pair=None)
                        natural.append(row);rows.append(row)
                    for mode, group in [('expanded_all_matched',natural)]+[('pairwise',list(g)) for g in combinations(natural,2)]:
                        ready=all(x['status']=='DRAFT_NOT_ADMITTED' for x in group)
                        common=set.intersection(*(set(x['train_ids']) for x in group)) if ready else set()
                        for row in group:
                            matched=m.subset(row,common) if ready else {**row,'status':'BLOCKED_UNDEFINED_COMMON_POST_PS_MASK'}
                            matched.update(mask=mode,pair=[r['arm'] for r in group] if mode=='pairwise' else None)
                            rows.append(matched)
                    for treatment in natural:
                        if treatment['arm'] in report['arms']:continue
                        control={**treatment,'arm':'NO_AGENT_FOR_'+treatment['arm'],'mask':'coverage_matched_no_agent',
                                 'pair':['NO_AGENT',treatment['arm']]}
                        if treatment['status']=='DRAFT_NOT_ADMITTED':
                            labels,sources=control_labels(report,treatment)
                            baseline={r['node_id']:r for r in report['arms']['C_BASELINE_FUSION']}
                            conf=[min(baseline[i][s+'_confidence'] for s in ('b1','narrative')
                                  if baseline[i][s+'_class']==k) for i,k in zip(treatment['train_ids'],labels)]
                            control.update(class_indices=labels,confidence_percent=conf,weights=m._weights(conf,loss,protocol),
                                label_sources=sources,PS_note='INHERITED_TREATMENT_MASK_NO_SECOND_FILTER',
                                inherited_treatment_PS={k:treatment[k] for k in ('PS_removed_ids','PS_requested','PS_effective')},
                                PS_removed_ids=[],PS_requested=0,PS_effective=0,PS_shortfall=0,
                                pre_PS_count=len(labels),protected_ids=[],missing_confidence_ids=[],
                                class_counts_before=dict(Counter(str(k) for k in labels)),class_counts_after=dict(Counter(str(k) for k in labels)),
                                weight_status=['CE_UNIT_WEIGHT' if loss=='ce' else 'FROZEN_BASELINE_CONFIDENCE']*len(labels))
                        rows.append(control)
    # Keep existing coverage-control definitions and old all-matched estimand unchanged.
    old=m.build(report,runtime=runtime)
    rows.extend(r for r in old['rows'] if r['mask'] in ('coverage_matched_no_agent','matched_all'))
    for row in rows:
        row.pop('fit_sha256',None);row.pop('row_id',None);row['row_id']=digest(row)
        if row['status']!='DRAFT_NOT_ADMITTED':continue
        spec={'graph_sha256':GRAPH_SHA256,'test_ids_sha256':old['test_ids_sha256'],
              'config':{**old['fits'][next(iter(old['fits']))]['spec']['config'],'loss':row['loss']},
              'train_ids':row['train_ids'],'class_indices':row['class_indices'],'weights':row['weights'],'runtime':runtime}
        sha=digest(spec);row['fit_sha256']=sha;fits.setdefault(sha,{'spec':spec,'row_ids':[]})['row_ids'].append(row['row_id'])
    return rows,fits


def main():
    root=Path('.local_artifacts');out=PrivateAudit(root/'expanded_gcn_inventory_v1')
    inputs=load_project_inputs(root/'frozen',root/'authentic')
    table=read_pinned_json(root/'sara3_correction_features_v1'/f'{v2.FEATURE_SHA}.json',v2.FEATURE_SHA)
    cfg=json.loads(Path('configs/gapgpt_rich_v2_output4096_proposed.json').read_text())
    for router in ('r0','r1_v1'):
        folder=root/('sara3_gapgpt_live_cora140_r0_4096_20261105' if router=='r0' else 'sara3_gapgpt_live_cora140_r1_v1_4096_20261107')
        recovered,source=features.extract_run(inputs,folder,cfg,router)
        assert recovered==[r for r in table['rows'] if r['router']==router] and source==table['sources'][router]
    frozen=read_pinned_json(root/'sara3_three_agent_fusion_v1/bc16870399416620ed67f8799ed9bd0f17c2b7cf3c5849b2debe93ac14d96c2c.json','bc16870399416620ed67f8799ed9bd0f17c2b7cf3c5849b2debe93ac14d96c2c')
    f.validate_report(frozen,table,inputs);arms=copy.deepcopy(frozen['arms'])
    baseline=read_pinned_json(root/'sara3_weighted_arbitration_v2'/f'{v3.BASE_REPORT_SHA}.json',v3.BASE_REPORT_SHA)
    x,adj,_=v2.load_graph(root/'gt_reference/cora_random_sbert.pt')
    assert v2.run(table,inputs,x,adj,baseline['config'])==baseline['rows']
    _,direct_rows=direct.audit_and_score(table,inputs,x,adj,baseline['config'],baseline)
    decisions={'V2':baseline['rows'],'V2_DIRECT':direct_rows,'V3':v3.score(table,baseline),'CONSENSUS':consensus.score(table,baseline)}
    for router in ('r0','r1_v1'):
        selected={r['node_id']:r for r in table['rows'] if r['router']==router}
        labels=[]
        for pair in inputs.pairs:
            row=f.fuse(pair,False,None,None,'C')
            if pair.node_id in selected:
                source=selected[pair.node_id]
                assert source['shadow_decision']=='ABSTAIN'  # Current verified V1 zero proposals.
                row.update(final_class=None,confidence_percent=None,label_source='V1_ROUTED_ABSTAIN')
            labels.append(row)
        arms['V1_'+router]=labels
        for policy,records in decisions.items():
            byid={r['node_id']:r for r in records if r['router']==router};labels=[]
            for pair in inputs.pairs:
                row=f.fuse(pair,False,None,None,'B');decision=byid.get(pair.node_id)
                if decision is not None:
                    label=decision['label'];matching=[a.confidence for a in (pair.b1,pair.narrative_v0) if a.class_index==label]
                    confidence=(min(matching) if matching else None) if decision['decision']=='SWITCH_TO_AGENT' else pair.narrative_v0.confidence
                    row.update(final_class=label,confidence_percent=confidence,
                               label_source=policy+':'+decision['decision'],policy_reason=decision['reason'])
                labels.append(row)
            arms[policy+'_'+router]=labels
    for name, labels in arms.items():
        if name in frozen['arms']:continue
        for row in labels:
            k=row['final_class'];row['accepted_experimentally']=k is not None
            row['third_class']=k is not None and k not in (row['b1_class'],row['narrative_class'])
            row['confidence_provenance']='UNAVAILABLE' if row['confidence_percent'] is None else 'FROZEN_BASELINE_SOURCE_NOT_AGENT_CALIBRATION'
            for field in ('relative_to_C','disagreement_resolution'):row.pop(field,None)
    selections={router:list(select_router(inputs.pairs,37,router)) for router in ROUTERS}
    selections['r1_neutral_v1']=list(rank_policy(inputs.pairs,NEUTRAL)[:37])
    known={r['node_id'] for r in table['rows']};router_inventory=[]
    for router,ids in selections.items():
        rows=[r for r in table['rows'] if r['router']==router]
        router_inventory.append({'router':router,'selected_ids':ids,'selected_count':37,
            'authentic_blind_completed':sum(r['blind']['state']=='COMPLETED' for r in rows),
            'authentic_comparison_completed':sum(r['compare']['state']=='COMPLETED' for r in rows),
            'comparison_rejected':sum(r['compare']['state']=='REJECTED' for r in rows),
            'not_permitted_abstention':sum(r['compare']['state']=='NOT_PERMITTED_ABSTENTION' for r in rows),
            'unseen_node_ids':sorted(set(ids)-known),
            'status':'RECONSTRUCTABLE_PRESERVING_REJECTIONS' if rows else 'BLOCKED_NO_ROUTER_BOUND_AUTHENTIC_RESPONSE_SET',
            'cross_router_reuse':'NOT_ASSUMED_REQUIRES_EFFECTIVE_REQUEST_IDENTITY_PROOF'})
    journal_inventory=[]
    for folder in root.iterdir():
        if not folder.is_dir() or not (folder.name.startswith('gapgpt_') or folder.name.startswith('sara3_gapgpt_live_')):continue
        for file in folder.rglob('*.sqlite'):
            with sqlite3.connect(file.resolve().as_uri()+'?mode=ro',uri=True) as db:
                db.execute('PRAGMA query_only=ON')
                tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if 'intents' not in tables:continue
                columns={r[1] for r in db.execute('PRAGMA table_info(intents)')}
                fields=[k for k in ('node_id','phase','state') if k in columns]
                if fields:journal_inventory.append({'path':str(file),'fields':fields,'records':[list(row) for row in db.execute('SELECT '+','.join(fields)+' FROM intents').fetchall()],
                    'scope':'CATALOG_ONLY_NOT_AUTOMATICALLY_ADMITTED_OR_PROTOCOL_COMPATIBLE'})
    old=PrivateAudit(root/'full_gcn_v1').read('c78ff16df921bfcd661ce7981c5467f31c243bd812466ce0bbca747be576d413')
    assert runner.runtime(Path.cwd())==old['runtime']
    rows,fits=matrix(arms,frozen,old['runtime']);reuse=set(fits)&set(old['fits'])
    for sha in reuse:
        assert fits[sha]['spec']==old['fits'][sha]['spec']
        for seed in range(10):assert runner.read_fit(root/'full_gcn_v1/fits',old,sha,seed) is not None
    groups={}
    for arm,labels in arms.items():
        key=digest([[r['node_id'],r['final_class'],r['confidence_percent']] for r in labels]);groups.setdefault(key,[]).append(arm)
    inventory={'schema':VERSION,'routers':router_inventory,'journal_catalog':journal_inventory,'arms':arms,'source_features_sha256':v2.FEATURE_SHA,
        'label_confidence_equivalence_groups':list(groups.values()),'rows':rows,'fits':fits,'runtime':old['runtime'],
        'reuse_from_package_sha256':digest(old),'verified_reusable_specs':sorted(reuse),'new_specs':sorted(set(fits)-reuse),
        'unseen_nodes_union':sorted(set().union(*(set(v['unseen_node_ids']) for v in router_inventory))),
        'blocked_version_policy_crossovers':'LEGACY_6_NODE_OR_512_TOKEN_VERSIONS_NOT_RICH4096_SUBSTITUTES; NO_FULL_COHORT_ADAPTER_ASSUMED',
        'status':'NOT_AUTHORIZED_FOR_ADMISSION_API_TRAINING','scientific_status':['LIMITED_PROVENANCE_EXPLORATORY','EXPLORATORY_NOT_INDEPENDENT']}
    sha=out.write(inventory);assert out.read(sha)==inventory
    summary={'inventory_sha256':sha,'arms':len(arms),'distinct_label_confidence_vectors':len(groups),
        'matrix_rows':len(rows),'status_counts':dict(Counter(r['status'] for r in rows)),
        'fit_specs':len(fits),'verified_reused_specs':len(reuse),'new_specs':len(fits)-len(reuse),
        'new_seed_fits':10*(len(fits)-len(reuse)),'unseen_unique_nodes':len(inventory['unseen_nodes_union']),
        'routers':[{k:v for k,v in r.items() if k not in ('selected_ids','unseen_node_ids')}|{'unseen_count':len(r['unseen_node_ids'])} for r in router_inventory],
        'equivalence_groups':list(groups.values()),'training_runs':0,'new_api_calls':0}
    print(json.dumps(summary))


if __name__=='__main__':main()
