"""Read only pinned JSON/CSV. No scientific imports, GT loading or training.

Public output is aggregate-only. --owner additionally writes an allowlisted
GT-free derivative to ignored .qa, NEVER to public/ or dist/.
"""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
MANIFEST = 'd3eaca9ce2e87f98d73af6d7664a80ac377b297fe252ba7911b6ee24693eca7e'
GT_RESULT = 'bf2f25c1fadc231f8921bd06caf324b52aecccb424d26cb569feaab27e42ee7b'
ARM_IDS = ['current_B1','current_v0','current_v1-A','current_v1-B','current_v1-C','current_v1-D','historical_A_B1','historical_B_NARRATIVE','historical_C_BASELINE_FUSION','historical_Expanded_V1','historical_V1_r0','historical_V1_r1_v1','lite','lite_class_count_control','lite_exact_mask_control','lite_router_only']

def require(ok, message):
    if not ok: raise ValueError(message)

def sha(data): return hashlib.sha256(data).hexdigest()
def encode(obj): return (json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True)+'\n').encode()
def digest(obj): return sha(encode(obj))

def pinned(path, expected):
    blob = path.read_bytes()
    require(len(blob) < 2_000_000 and sha(blob) == expected, 'Source hash/size conflict: '+path.name)
    return blob

def number(value, low=0, high=100):
    require(not isinstance(value, bool), "Boolean is not a research metric")
    v = float(value)
    require(math.isfinite(v) and low <= v <= high, 'Nonfinite/out-of-range number')
    return v

def build():
    pins = json.loads((HERE/'scripts/benchmark-pins.json').read_text())
    repository_pins=json.loads((HERE/'scripts/benchmark-repository-pins.json').read_text())
    require(set(repository_pins)==set(pins), 'Repository source identities')
    sources={}
    for name,h in pins.items():
        blob=(ROOT/name).read_bytes()
        require(len(blob)<2_000_000 and sha(blob) in {h,repository_pins[name]}, 'Source hash/size conflict: '+name)
        require(sha(blob.replace(b'\r\n',b'\n'))==repository_pins[name], 'Non-newline source conflict: '+name)
        sources[name]=blob
    rows = lambda name:list(csv.DictReader(io.StringIO(sources['reports/'+name].decode('utf-8-sig'))))
    results, seeds = rows('final_cora_gcn_results.csv'), rows('final_cora_gcn_seeds.csv')
    require([r['Arm'] for r in results] == ARM_IDS and len(seeds) == 160, 'Arm/seed identities')
    require(set(results[0]) == set('Arm Cohort Loss PS Mask Train_Count Test_Count Coverage Accuracy Accuracy_SD Macro_F1 Macro_F1_SD Raw_Correct Raw_Wrong Raw_Abstained Raw_Unavailable Fit_SHA256 Status'.split()), 'Unexpected results columns')
    require(all(set(s)=={'Arm','Seed','Accuracy','Macro-F1'} for s in seeds), 'Unexpected seed columns')
    require(all(s['Arm'] in ARM_IDS for s in seeds), 'Unknown seed arm')
    provenance=json.loads(sources['reports/final_cora_gcn_provenance.json'])
    require(provenance['package_sha256']==MANIFEST and provenance['arm_count']==16 and provenance['unique_specs']==15 and provenance['new_seed_fits']==110 and provenance['reused_seed_fits']==40, 'Benchmark accounting')
    manifest=json.loads(pinned(ROOT/f'.local_artifacts/final_cora_gcn_v1/{MANIFEST}.json', MANIFEST))
    require(manifest['features']['graph_sha256']==provenance['features']['graph_sha256'], 'Graph mismatch')
    atlas=json.loads((HERE/'public/data/atlas.v2.json').read_text())
    target_ids=sorted(n['id'] for n in atlas['nodes'] if n['target'])
    require(target_ids==sorted(manifest['selected_ids']), 'Target ID mapping mismatch')
    owner={'schema':'graphscope.owner.v1','manifestSHA':MANIFEST,'classOrder':atlas['classes'],'targetIds':target_ids,'arms':[]}
    arms=[]
    for r in results:
        name=r['Arm']; a=manifest['arms'][name]; plan=a['plan']; vector=a['vector']
        require(plan['GT_accessed'] is False and plan['PS'] is False and plan['config']['loss']=='ce', 'GT/config boundary')
        require(r['Cohort']=='Sensitivity140' and r['Loss']=='CE' and r['PS']=='False' and r['Mask']=='Natural' and int(r['Test_Count'])==2568, 'Contract mismatch')
        require(sorted(map(int,vector))==target_ids and all(c is None or type(c) is int and 0<=c<7 for c in vector.values()), 'Vector identity/class mapping')
        ids=sorted(int(n) for n,c in vector.items() if c is not None)
        require(ids==sorted(plan['train_ids']) and len(ids)==int(r['Train_Count'])==a['accepted'], 'Mask mismatch')
        ss=sorted([dict(seed=int(s['Seed']),accuracy=number(s['Accuracy']),macroF1=number(s['Macro-F1'],0,1)) for s in seeds if s['Arm']==name],key=lambda s:s['seed'])
        require([s['seed'] for s in ss]==list(range(10)), 'Seed missing/duplicate')
        for key,col in [('accuracy','Accuracy'),('macroF1','Macro_F1')]:
            values=[s[key] for s in ss]
            require(abs(statistics.mean(values)-number(r[col]))<1e-9 and abs(statistics.pstdev(values)-number(r[col+'_SD']))<1e-9, 'Seed statistics mismatch')
        raw=dict(correct=int(r['Raw_Correct']),wrong=int(r['Raw_Wrong']),abstained=int(r['Raw_Abstained']),unavailable=int(r['Raw_Unavailable']))
        require(all(v>=0 for v in raw.values()) and sum(raw.values())==140 and raw['correct']+raw['wrong']==len(ids), 'Raw denominator')
        require(abs(number(r['Coverage'],0,1)-len(ids)/140)<1e-12 and r['Fit_SHA256']==a['fit_sha256'], 'Coverage/spec mismatch')
        mask_sha=digest(ids)
        arms.append(dict(id=name,cohort=r['Cohort'],loss='CE',postFilter=False,mask='Natural',trainCount=len(ids),testCount=2568,coverage=len(ids)/140,accuracy=number(r['Accuracy']),sd=number(r['Accuracy_SD']),macroF1=number(r['Macro_F1'],0,1),macroF1SD=number(r['Macro_F1_SD'],0,1),raw=raw,seeds=ss,fitSHA=r['Fit_SHA256'],vectorSHA=a['vector_sha256'],maskSHA=mask_sha,sourceSHA=a['source_sha256'],aliasOf='historical_C_BASELINE_FUSION' if name=='historical_V1_r0' else None))
        owner['arms'].append(dict(id=name,maskSHA=mask_sha,vectorSHA=a['vector_sha256'],labels=[vector[str(n)] for n in target_ids],confidence=[a['confidence_provenance'][str(n)]['value'] for n in target_ids]))
    # Independently join the published raw metrics; never open node-level GT.
    raw_sources={r['arm']:r for r in rows('six_arm_metrics.csv')}
    for a in arms[:6]:
        key=a['id'].replace('current_',''); rr=raw_sources[key]
        require(all(a['raw'][k]==int(rr[k]) for k in a['raw']), 'Six-arm raw report mismatch')
    for code,name in [('A','current_v0'),('B','lite_router_only'),('C','lite'),('D','lite_exact_mask_control'),('E','lite_class_count_control')]:
        rr=next(r for r in rows('sara_lite_metrics.csv') if r['arm']==code); aa=next(a for a in arms if a['id']==name)
        require(all(aa['raw'][k]==int(rr[k]) for k in aa['raw']), 'Lite raw report mismatch')
    pairs=rows('final_cora_gcn_paired.csv')
    for p in pairs:
        left,right=p['comparison'].split('_minus_'); aa=next(a for a in arms if a['id']==left); bb=next(a for a in arms if a['id']==right)
        metric='accuracy' if p['metric']=='Accuracy' else 'macroF1'
        ds=[a[metric]-b[metric] for a,b in zip(aa['seeds'],bb['seeds'])]
        require(abs(statistics.mean(ds)-float(p['mean_delta']))<1e-9 and abs(statistics.pstdev(ds)-float(p['sd_delta']))<1e-9, 'Paired source mismatch')
    require(len({a['fitSHA'] for a in arms})==15, 'Distinct fit count')
    wces=[r for r in rows('gcn_missing_experiments_results.csv') if r['Arm']=='V1_r1_v1' and r['Cohort']=='sensitivity' and r['Loss']=='wce' and r['PS']=='False' and r['Mask']=='natural' and r['Protocol']=='historical_confidence.v1']
    require(len(wces)==1,'Historical WCE identity')
    w=wces[0]
    historical_wce=dict(id='historical_V1_r1_v1_WCE',loss='WCE',cohort='Sensitivity140',accuracy=number(w['Accuracy']),sd=number(w['Accuracy_SD']),trainCount=int(w['Train Count']),fitSHA=w['fit_sha256'],source='reports/gcn_missing_experiments_results.csv')
    lite=json.loads(sources['reports/sara_lite_freeze.json'])
    public=dict(schema='graphscope.benchmark.v3',snapshotDate='2026-11-13',graphSHA=provenance['features']['graph_sha256'],manifestSHA=MANIFEST,gtResultSHA=GT_RESULT,testSHA=provenance['test_ids_sha256'],classOrder=atlas['classes'],status='LIMITED_PROVENANCE_EXPLORATORY / EXPLORATORY_NOT_INDEPENDENT',newFits=110,reusedFits=40,uniqueSpecs=15,arms=arms,sources=[dict(path=p,sha256=h,repositorySHA256=repository_pins[p]) for p,h in pins.items()],ownerSHA=digest(owner),liteActions=lite['actions'],historicalWCE=historical_wce)
    return public,owner

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--owner',action='store_true');args=parser.parse_args()
    public,owner=build(); blob=encode(public)
    (HERE/'public/data/benchmark.v3.json').write_bytes(blob)
    (HERE/'src/benchmark-pin.ts').write_text("export const BENCHMARK_SHA256 = '"+sha(blob)+"';\n",encoding='utf-8')
    if args.owner:
        (HERE/'.qa').mkdir(exist_ok=True);(HERE/'.qa/owner-evidence.json').write_bytes(encode(owner))
    print('PASS: 16 arms / 15 specs / 160 arm-seed rows / 150 distinct fits; aggregate-only public export')

if __name__=='__main__': main()
