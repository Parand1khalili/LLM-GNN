"""GT-only metrics AFTER expanded numerical coverage is independently verified."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import statistics

from ..downstream import expanded_execute as ex, full_matrix
from ..sara3.audit import PrivateAudit
from ..sara3.experiment import digest
from ..sara3.correction_features import require
from .cora_gt_shadow import _labels_from_original_graph, _expected_graph_names
from .full_gcn import metrics, paired


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--allow-gt-evaluation',action='store_true');args=parser.parse_args()
    require(args.allow_gt_evaluation)
    p,previous=ex.load();store=PrivateAudit(ex.ROOT);apsha=digest(ex.approval(p))
    require(store.read(apsha)==ex.approval(p))
    records=ex.scan(p,previous,apsha)
    gate=ex.check_coverage({(f,s) for f in p['fits'] for s in range(10)},records)
    require(gate['status']=='COMPLETE_VERIFIED')  # Only defined, admissible fit scope.
    gate_sha=store.write(gate)
    import numpy as np
    predictions={}
    for fit in p['fits']:
        predictions[fit]={}
        base=Path('.local_artifacts/full_gcn_v1/fits') if fit in previous['fits'] else ex.ROOT/'fits'
        for seed in range(10):
            directory=base/fit/str(seed);audit=PrivateAudit(directory)
            rec=audit.read(json.loads((directory/'complete.json').read_bytes())['receipt_sha256'])
            blob=(directory/'fit.npz').read_bytes()
            require(hashlib.sha256(blob).hexdigest()==rec['artifact_sha256'])
            with np.load(io.BytesIO(blob),allow_pickle=False) as z:
                predictions[fit][seed]=z['predictions'][previous['test_ids']].tolist()
    # No GT object exists in training or scan. All checkpoints are now frozen.
    truth=_labels_from_original_graph('.local_artifacts/gt_reference/cora_random_sbert.pt',_expected_graph_names('.local_artifacts/frozen'))
    target=[truth[i] for i in previous['test_ids']]
    scores={fit:{seed:metrics(pred,target) for seed,pred in byseed.items()} for fit,byseed in predictions.items()}
    historical=PrivateAudit('.local_artifacts/full_gcn_results_v1').read('7be9973675521a59db735ca21477bd14e8cc2b0d4054323441df992c651d41e9')
    old_rows={r['row_id']:r['fit_sha256'] for r in previous['rows'] if r['status']=='DRAFT_NOT_ADMITTED'}
    checked=set()
    for entry in historical['per_seed']:
        fit=old_rows[entry['row_id']];seed=entry['Seed']
        require(all(scores[fit][seed][key]==entry[key] for key in ('Accuracy','Macro-F1')))
        checked.add((fit,seed))
    require(len(checked)==1870)
    rows=full_matrix.public_rows(p);index={r['row_id']:r for r in p['rows']};seed_rows=[]
    for row in rows:
        source=index[row['row_id']];arm=row['Arm']
        if arm.startswith(('V1_','V2_','V3_','CONSENSUS_')):row['Policy']=arm.rsplit('_r',1)[0]
        if arm.startswith('NO_AGENT_FOR_'):row['Policy']='COVERAGE_MATCHED_NO_AGENT'
        if source['status']!='DRAFT_NOT_ADMITTED':continue
        result=scores[source['fit_sha256']]
        row['fit_sha256']=source['fit_sha256']
        row['Status']='VERIFIED_EXISTING' if source['fit_sha256'] in previous['fits'] else 'EXECUTED_VERIFIED'
        for metric in ('Accuracy','Macro-F1'):
            values=[result[s][metric] for s in range(10)]
            row[metric]=statistics.mean(values);row[metric+'_SD']=statistics.pstdev(values)
        row.update(Mean=row['Accuracy'],SD=row['Accuracy_SD'])
        seed_rows.extend({'row_id':row['row_id'],'fit_sha256':source['fit_sha256'],'Seed':s,**result[s]} for s in range(10))
    # Focused, fully seed-paired V1 vs Narrative/C/coverage-control comparisons.
    comparisons=[]
    for row in rows:
        if row['Arm']!='V1_r1_v1' or row['Accuracy'] is None:continue
        for other in rows:
            same=all(row[k]==other[k] for k in ('Cohort','Protocol','Loss','PS','Mask','Pair'))
            natural=row['Mask']=='natural' and other['Mask']=='coverage_matched_no_agent' and other['Pair']==['NO_AGENT','V1_r1_v1'] and all(row[k]==other[k] for k in ('Cohort','Protocol','Loss','PS'))
            if other['Accuracy'] is None or not ((same and other['Arm'] in ('B_NARRATIVE','C_BASELINE_FUSION')) or natural):continue
            d=paired(scores[other['fit_sha256']],scores[row['fit_sha256']])
            comparisons.append({'treatment_row':row['row_id'],'reference_row':other['row_id'],'reference_arm':other['Arm'],
                'Cohort':row['Cohort'],'Protocol':row['Protocol'],'Loss':row['Loss'],'PS':row['PS'],'Mask':row['Mask'],
                'treatment_minus_reference':d})
    result={'schema':'sara.gcn.expanded.results.v1','package_sha256':ex.PIN,'admission_sha256':apsha,
        'eligible_fit_gate_sha256':gate_sha,'scientific_status':['LIMITED_PROVENANCE_EXPLORATORY','EXPLORATORY_NOT_INDEPENDENT'],
        'aggregate':rows,'per_seed':seed_rows,'v1_paired_comparisons':comparisons,
        'unique_specs':len(scores),'unique_seed_fits':len(scores)*10}
    result['historical_metric_parity_verified_seed_fits']=len(checked)
    sha=store.write(result)
    Path('reports/gcn_missing_experiments_results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    fields=list(dict.fromkeys(k for row in rows for k in row))
    buffer=io.StringIO(newline='');w=csv.DictWriter(buffer,fieldnames=fields);w.writeheader();w.writerows(rows)
    Path('reports/gcn_missing_experiments_results.csv').write_text(buffer.getvalue(),encoding='utf-8',newline='')
    print(json.dumps({'result_sha256':sha,'unique_seed_fits':len(scores)*10,'rows':len(rows),
        'blocked_config_rows':sum(r['Accuracy'] is None for r in rows),'status':'ELIGIBLE_FITS_EVALUATED_GLOBAL_CONFIG_BLOCKERS_REMAIN'}))


if __name__=='__main__':main()
