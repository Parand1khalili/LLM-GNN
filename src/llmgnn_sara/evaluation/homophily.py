"""Post-hoc GT-only local homophily. No inference or training imports."""
import json,statistics,hashlib,struct,zipfile
import re
from pathlib import Path
from collections import Counter
from ..sara3.audit import PrivateAudit
from ..sara3.experiment import digest
from ..io.project import GRAPH_SHA256
from ..io.project import load_project_inputs
from .cora_gt_shadow import _labels_from_original_graph,_expected_graph_names
from .v1_relaxed import ROOT

PROTOCOL={"version":"sara.homophily.diagnostic.v1","neighbors":"unique undirected direct; exclude self loops",
 "strata":"heterophilic h<0.5; mixed h=0.5; homophilic h>0.5; isolated undefined",
 "degree_bins":[[0,0],[1,2],[3,5],[6,10],[11,2707]],"status":"EXPLORATORY_NOT_INDEPENDENT"}

def measure(edges,labels,node_count):
    if len(labels)!=node_count or any(type(y)is not int or not 0<=y<7 for y in labels):
        raise ValueError("Graph-label alignment")
    adjacency=[set() for _ in labels];directed=set();loops=duplicates=0
    for a,b in edges:
        if type(a)is not int or type(b)is not int or not 0<=a<node_count or not 0<=b<node_count:raise ValueError("Edge domain")
        if a==b:loops+=1;continue
        if (a,b) in directed:duplicates+=1
        directed.add((a,b));adjacency[a].add(b);adjacency[b].add(a)
    rows=[]
    for i,ns in enumerate(adjacency):
        h=sum(labels[n]==labels[i] for n in ns)/len(ns) if ns else None
        rows.append(dict(node_id=i,degree=len(ns),homophily=h,stratum="isolated" if h is None else "heterophilic" if h<.5 else "mixed" if h==.5 else "homophilic"))
    return rows,adjacency,dict(self_loops_removed=loops,duplicate_directed_edges=duplicates,
        unique_directed_edges=len(directed),reciprocal_directed_edges=sum((b,a) in directed for a,b in directed),
        undirected_edges=sum(map(len,adjacency))//2)

def summary(rows):
    hs=[r['homophily'] for r in rows if r['homophily'] is not None]
    return dict(count=len(rows),isolated=len(rows)-len(hs),mean=statistics.mean(hs) if hs else None,
        median=statistics.median(hs) if hs else None,strata=dict(Counter(r['stratum'] for r in rows)),
        mean_degree=statistics.mean(r['degree'] for r in rows) if rows else None)

def main():
    store=PrivateAudit('.local_artifacts/homophily_v1')
    protocol_sha=store.write(PROTOCOL)
    frozen=PrivateAudit(ROOT).read('771eccefde1845f7d6beb53c3aff4bb5e792e0b524f124c792d700ca4c819cc1')
    assert frozen['source_freeze_sha256']=='677a683959cc80691d726d3e02e23b55e02a0bb01e6e17f4c16c57ca567c4ccc'
    graph=Path('.local_artifacts/gt_reference/cora_random_sbert.pt');blob=graph.read_bytes()
    assert hashlib.sha256(blob).hexdigest()==GRAPH_SHA256
    with zipfile.ZipFile(graph) as z: raw=z.read('cora_random_sbert/data/1')
    values=struct.unpack('<21716q',raw);edges=list(zip(values[:10858],values[10858:]))
    truth=_labels_from_original_graph(graph,_expected_graph_names('.local_artifacts/frozen'))
    rows,adj,graph_info=measure(edges,truth,2708);byid={r['node_id']:r for r in rows}
    vectors={k:{r['node_id']:r['class_index'] for r in v} for k,v in frozen['vectors'].items()}
    ids=sorted(vectors['C']);groups={}
    for a,b,name in [(True,True,'both_correct'),(False,False,'both_wrong'),(False,True,'only_b1_wrong'),(True,False,'only_narrative_wrong')]:
        groups[name]=[i for i in ids if (vectors['B1'][i]==truth[i])==a and (vectors['Narrative'][i]==truth[i])==b]
    inventory=PrivateAudit('.local_artifacts/expanded_gcn_inventory_v1').read('789a6aea4715c1e7537ede75d82f5e552859c392a0e27acd8cbbbc03b568da83')
    atlas=PrivateAudit('.local_artifacts/expanded_atlas_ablation').read('6b624adac49e9a8e3a78de6d7628e4fc1b654b21b5307a33ebd9b5ef4a007fe0')
    selections={r['router']:set(r['selected_ids']) for r in inventory['routers'] if r['router'] in ('r0','r1_v1')}
    selections['expanded']=set(atlas['expanded']['ids'])
    for router,selection in selections.items():
        for selected in (True,False):groups[router+('_selected' if selected else '_unselected')]=[i for i in ids if (i in selection)==selected]
    for method in ('B1','Narrative','C','Expanded_V1','V1_Relaxed'):
        for state in ('correct','wrong','abstain'):
            groups[method+'_'+state]=[i for i in ids if ('abstain' if vectors[method][i] is None else 'correct' if vectors[method][i]==truth[i] else 'wrong')==state]
    phase_predictions=[]
    for record in frozen['phase_bindings'].values():
        if record['state']=='COMPLETED' and record['value'] is not None:
            v=record['value'];node=record['payload']['node_id']
            if not v['abstain']:phase_predictions.append((node,record['payload']['phase'],v['class_index']))
    for phase in ('blind','compare'):
        for correct in (True,False):
            groups['agent_'+phase+('_correct' if correct else '_wrong')]=[n for n,p,c in phase_predictions if p==phase and (c==truth[n])==correct]
    groups['fusion_removed_errors']=[i for i in ids if vectors['C'][i] is None and (vectors['B1'][i]!=truth[i] or vectors['Narrative'][i]!=truth[i])]
    groups['fusion_retained_errors']=[i for i in ids if vectors['C'][i] is not None and vectors['C'][i]!=truth[i]]
    proposals=[d for d in frozen['decisions'] if d['action']=='PROPOSE_CLASS_SWITCH']
    original_pairs={p.node_id:p for p in load_project_inputs('.local_artifacts/frozen','.local_artifacts/authentic').pairs}
    for correct in (True,False):groups['third_'+('correct' if correct else 'wrong')]=[d['node_id'] for d in proposals if (d['proposed_class_index']==truth[d['node_id']])==correct]
    private=[]
    for i in ids:
        phases=[v for v in frozen['phase_bindings'].values() if v['payload']['node_id']==i]
        pair=original_pairs[i];words=set(re.findall('[a-z]+',pair.text.lower()))
        private.append(dict(**byid[i],ground_truth=truth[i],predictions={k:v[i] for k,v in vectors.items()},
            b1_confidence=pair.b1.confidence,narrative_confidence=pair.narrative_v0.confidence,
            target_text_length=len(pair.text),
            atlas_hits={k:[len(words & set(v)) for v in atlas[k]['vocab']] for k in ('old','expanded')},
            neighbor_gt_distribution=dict(Counter(truth[n] for n in adj[i])),
            phases=phases if i in {d['node_id'] for d in proposals} else [],
            decision=next((d for d in proposals if d['node_id']==i),None)))
    for row in private:
        if row['decision']:
            label=row['decision']['proposed_class_index'];ns=adj[row['node_id']]
            row['proposed_class_neighbor_gt_fraction']=sum(truth[n]==label for n in ns)/len(ns) if ns else None
            row['v1_reason']='THIRD_CLASS_DIAGNOSTIC_ONLY'
            row['inference_available_fields']=['baseline_predictions','baseline_confidence','phase_responses','evidence','target_text_length','atlas_hits','degree']
            row['posthoc_only_fields']=['ground_truth','homophily','neighbor_gt_distribution','proposed_class_neighbor_gt_fraction']
    private_sha=store.write(dict(protocol_sha256=protocol_sha,rows=private))
    aggregates={k:summary([byid[i] for i in group]) for k,group in groups.items()}
    degree_tables={k:{str(bounds):summary([byid[i] for i in group if bounds[0]<=byid[i]['degree']<=bounds[1]]) for bounds in PROTOCOL['degree_bins']} for k,group in groups.items()}
    error_rates={}
    for stratum in ('heterophilic','mixed','homophilic','isolated'):
        subset=[i for i in ids if byid[i]['stratum']==stratum]
        error_rates[stratum]={k:dict(accepted=sum(v[i] is not None for i in subset),wrong=sum(v[i] is not None and v[i]!=truth[i] for i in subset),total=len(subset)) for k,v in vectors.items()}
    proposal_features={}
    for correct in (True,False):
        subset=[r for r in private if r['decision'] and (r['decision']['proposed_class_index']==truth[r['node_id']])==correct]
        proposal_features[str(correct)]=dict(count=len(subset),
            mean_text_length=statistics.mean(r['target_text_length'] for r in subset) if subset else None,
            counter_present=sum(any(r['decision']['evidence_features']['counter_evidence']) for r in subset),
            auxiliary_present=sum(any(r['decision']['evidence_features']['auxiliary_method_warning']) for r in subset),
            uncertainty_present=sum(any(r['decision']['evidence_features']['uncertainty_reason']) for r in subset),
            shared_quote_present=sum(r['decision']['evidence_features']['shared_support_count']>0 for r in subset),
            literal_topic_agreement=sum(len(set(r['decision']['evidence_features']['primary_topic']))==1 for r in subset))
    result=dict(protocol=PROTOCOL,protocol_sha256=protocol_sha,graph_sha256=GRAPH_SHA256,graph=graph_info,
        proposal_features=proposal_features,
        aggregates=aggregates,degree_conditioned=degree_tables,error_rates=error_rates,private_sha256=private_sha,
        limitations=['LIMITED_PROVENANCE_EXPLORATORY','EXPLORATORY_NOT_INDEPENDENT'])
    sha=store.write(result);Path('reports/homophily_aggregate.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    text=['# مطالعهٔ پسینی Homophily و خطاهای SARA-3','','همسایگی مستقیم پس از حذف Self-loop و یکتاسازی و اجتماع دو جهت سنجیده شد. برچسب همسایه فقط در این Evaluator خوانده شد. مرزها پیش از خواندن GT ثبت شدند؛ h<0.5 heterophilic، h=0.5 mixed و h>0.5 homophilic. نود منزوی undefined است.','','Protocol SHA '+protocol_sha,'','Result SHA '+sha,'','|گروه|N|میانگین h|میانه h|میانگین Degree|','|---|---:|---:|---:|---:|']
    for k,v in aggregates.items():text.append(f"|{k}|{v['count']}|{v['mean']}|{v['median']}|{v['mean_degree']}|")
    text+=['','## تفسیر و آزمایش آینده','','مقایسهٔ Degree-conditioned توصیفی است. گروه‌های کوچک و نودهای دارای همسایهٔ مشترک مستقل نیستند؛ آزمون معنی‌داری یا ادعای علّی انجام نشد. H=0.5 مرز قراردادی است و بهینه نشده است.','','Detection، تولید کلاس، پذیرش و GCN چهار خروجی جدا دارند. V1-Relaxed پنج امتناع را به دو درست و سه غلط تبدیل کرد؛ صحت Quote یا توافق دو فاز، تأیید معنایی نیست. از پنج نتیجه قاعدهٔ جدیدی ساخته نشد.','','برای آزمون بعدی، روی CiteSeer با دسترسی و پروتکل مستقل، واژگان/Policy و بودجه را پیشاپیش ثبت کنید؛ کنترل بدون Agent با Mask برابر و کلاس‌های Baseline لازم است. ارزیابی متن و شواهد روی Development مستقل از Test، پیش‌نیاز طراحی گیت معنایی است. هزینه و مجوز API/Training باید جدا تعیین شود.','','جزئیات پنج پیشنهاد و Ground Truth فقط در Artifact خصوصی با ACL مالک نگهداری شدند. هیچ بهبود GCN اندازه‌گیری نشده است. LIMITED_PROVENANCE_EXPLORATORY / EXPLORATORY_NOT_INDEPENDENT']
    Path('docs/SARA3_HOMOPHILY_FAILURE_ANALYSIS_FA.md').write_text('\n'.join(text)+'\n',encoding='utf8')
    # Aggregate-only standalone figure; no node positions or identifiers.
    chosen=['both_correct','both_wrong','only_b1_wrong','only_narrative_wrong','third_correct','third_wrong']
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="320"><rect width="900" height="320" fill="white"/><text x="20" y="25">Mean local GT homophily (post-hoc)</text>']
    for j,k in enumerate(chosen):
        h=aggregates[k]['mean'] or 0;x=35+j*145;height=h*200
        svg.append(f'<rect x="{x}" y="{240-height}" width="90" height="{height}" fill="#276b8b"/><text x="{x}" y="{230-height}">{h:.3f}</text><text x="{x}" y="265" font-size="10">{k}</text>')
    svg.append('</svg>');Path('reports/homophily_groups.svg').write_text(''.join(svg),encoding='utf8')
    print(json.dumps(dict(result_sha256=sha,groups={k:aggregates[k] for k in chosen},graph=graph_info)))
if __name__=='__main__':main()
