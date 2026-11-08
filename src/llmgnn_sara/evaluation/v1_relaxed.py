"""Explicit GT-only diagnostic evaluation after a pinned shadow freeze."""
import argparse,json,hashlib
from pathlib import Path
from ..sara3.audit import PrivateAudit
from ..sara3.v1_relaxed_shadow import ROOT,SCHEMA,PIN
from ..sara3.v1_relaxed import VERSION
from .cora_gt_shadow import _labels_from_original_graph,_expected_graph_names
from .node_diagnostics import metrics,paired

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--shadow-sha256',required=True);args=parser.parse_args()
    frozen=PrivateAudit(ROOT).read(args.shadow_sha256)
    if frozen['schema']!=SCHEMA or frozen['policy_version']!=VERSION or frozen['source_freeze_sha256']!=PIN:raise ValueError('Freeze version mismatch')
    for name,sha in frozen['source_code_sha256'].items():
        if hashlib.sha256((Path('src/llmgnn_sara/sara3')/name).read_bytes()).hexdigest()!=sha:raise ValueError('Source mismatch')
    vectors={k:{r['node_id']:r['class_index'] for r in v} for k,v in frozen['vectors'].items()}
    if any(len(v)!=140 or set(v)!=set(vectors['C']) for v in vectors.values()):raise ValueError('Vector alignment mismatch')
    truth=_labels_from_original_graph('.local_artifacts/gt_reference/cora_random_sbert.pt',_expected_graph_names('.local_artifacts/frozen'))
    results={k:metrics(v,truth) for k,v in vectors.items()}
    changes={k:paired(vectors[k],vectors['V1_Relaxed'],truth)[0] for k in ('Narrative','C','Old_V1_R1','Expanded_V1','Router_only')}
    proposals=[r for r in frozen['decisions'] if r['action']=='PROPOSE_CLASS_SWITCH']
    both=[i for i in vectors['C'] if vectors['B1'][i]!=truth[i] and vectors['Narrative'][i]!=truth[i]]
    result=dict(schema='sara.relaxed.gt_only.v1',shadow_sha256=args.shadow_sha256,
        scientific_status=frozen['scientific_status'],metrics=results,changes=changes,
        third_class=dict(count=len(proposals),correct=sum(r['proposed_class_index']==truth[r['node_id']] for r in proposals)),
        joint_error_diagnostic=dict(count=len(both),proposed=sum(r['node_id'] in both for r in proposals)),
        training_runs=0,api_calls=0)
    sha=PrivateAudit('.local_artifacts/v1_relaxed_evaluation').write(result)
    Path('reports/v1_relaxed_aggregate.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(result_sha256=sha,third_class=result['third_class'],raw={k:v['counts'] for k,v in results.items()})))
if __name__=='__main__':main()
