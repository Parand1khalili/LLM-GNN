"""Read-only authentic replay and GT-free immutable shadow freeze."""
import argparse,json,hashlib
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from . import expanded_atlas_freeze as original
from .audit import PrivateAudit
from .experiment import digest
from .v1_relaxed import decide,VERSION
from ..io.project import load_project_inputs

PIN="677a683959cc80691d726d3e02e23b55e02a0bb01e6e17f4c16c57ca567c4ccc"
ROOT=Path(".local_artifacts/v1_relaxed_shadow")
SCHEMA="sara.relaxed.shadow.v1"

def main():
    inputs=load_project_inputs(original.ROOT/"frozen",original.ROOT/"authentic")
    saved=PrivateAudit(original.ROOT/"expanded_atlas_freeze_v1").read(PIN)
    original.validate_freeze(saved)
    cfg=json.loads(Path("configs/gapgpt_rich_v2_output4096_proposed.json").read_text());cfg["max_spend_usd"]="1.00"
    atlas=PrivateAudit(original.ROOT/"expanded_atlas_ablation").read(original.ATLAS_SHA)
    phases={};real=original.replay
    def collect(audit,row,expected_id,payload,wire,dependency,context_sha,text,config,**kwargs):
        value=real(audit,row,expected_id,payload,wire,dependency,context_sha,text,config,**kwargs)
        phases[expected_id]=dict(value=value,state=row[1][3],payload=payload,dependency=dependency,
            context=context_sha,receipt_sha256=row[1][4])
        return value
    with patch.object(original,"replay",collect):
        rebuilt=original.freeze(inputs,cfg,atlas,original.ROOT/"expanded_atlas_agent3_v1",saved["source_summary_sha256"])
    if digest(rebuilt)!=PIN:raise ValueError("Source freeze mismatch")
    pairs={p.node_id:p for p in inputs.pairs};decisions=[]
    for node in saved["selected"]:
        matches={x["payload"]["phase"]:(identity,x) for identity,x in phases.items() if x["payload"]["node_id"]==node}
        bi,b=matches["blind"];ci,c=matches.get("compare",(None,None))
        binding=dict(schema="sara.relaxed.verified_phase_pair.v1",node_id=node,
            blind_state=b["state"],comparison_state=c["state"] if c else "MISSING",
            dependency=c["dependency"] if c else None,blind_response=digest(b["value"]),
            comparison_response=digest(c["value"]) if c else None,
            context_sha256=b["context"],blind_identity=bi,comparison_identity=ci)
        pair=pairs[node]
        decision=decide(node,(pair.b1.class_index,pair.narrative_v0.class_index),pair.text,b["value"],c["value"] if c else None,binding)
        if b["value"]["abstain"] and c is None:
            decision.update(action="ABSTAIN",reason_codes=["BLIND_ABSTENTION_NO_COMPARISON_PERMITTED"],l1_status="PASS")
        decisions.append(dict(node_id=node,**decision))
    vector=[dict(r) for r in saved["vectors"]["Expanded_V1"]]
    changes={r["node_id"]:r for r in decisions if r["action"]=="PROPOSE_CLASS_SWITCH"}
    for row in vector:
        if row["node_id"] in changes:
            row.update(class_index=changes[row["node_id"]]["proposed_class_index"],
                confidence_percent=None,confidence_provenance="UNAVAILABLE_NOT_AGENT_CALIBRATED")
    coverage=[]
    for row in vector:
        pair=pairs[row['node_id']]
        strongest=max((pair.b1,pair.narrative_v0),key=lambda a:a.confidence)
        coverage.append(dict(node_id=row['node_id'],class_index=strongest.class_index if row['class_index'] is not None else None,
            confidence_percent=strongest.confidence if row['class_index'] is not None else None,
            confidence_provenance='FROZEN_HIGHER_CONFIDENCE_B1_FIRST_TIE' if row['class_index'] is not None else 'NO_ACCEPTED_LABEL'))
    needed=Counter(r['class_index'] for r in vector if r['class_index'] is not None)
    chosen=set();shortfall={}
    for cls,count in sorted(needed.items()):
        options=[r['node_id'] for r in saved['vectors']['C'] if r['class_index']==cls]
        options.sort(key=lambda node:(hashlib.sha256(f'v1-relaxed-class-control-v1|{node}'.encode()).hexdigest(),node))
        if len(options)<count:shortfall[str(cls)]=count-len(options)
        chosen.update(options[:count])
    class_control=None if shortfall else [dict(r) if r['node_id'] in chosen else
        dict(node_id=r['node_id'],class_index=None,confidence_percent=None,confidence_provenance='NO_ACCEPTED_LABEL') for r in saved['vectors']['C']]
    vectors={**saved['vectors'],'V1_Relaxed':vector,'Coverage_no_agent':coverage}
    if class_control is not None:vectors['Class_count_no_agent']=class_control
    old=PrivateAudit(original.ROOT/'expanded_gcn_inventory_v1').read('789a6aea4715c1e7537ede75d82f5e552859c392a0e27acd8cbbbc03b568da83')
    vectors['Old_V1_R1']=[dict(node_id=r['node_id'],class_index=r['final_class'],confidence_percent=r['confidence_percent'],confidence_provenance=r['confidence_provenance']) for r in old['arms']['V1_r1_v1']]
    result=dict(schema=SCHEMA,policy_version=VERSION,source_freeze_sha256=PIN,
        source_code_sha256={f:hashlib.sha256(Path(__file__).with_name(f).read_bytes()).hexdigest()
            for f in ("v1_relaxed.py","v1_relaxed_shadow.py")},
        vectors=vectors,decisions=decisions,
        vector_fingerprints={k:digest(sorted(v,key=lambda r:r['node_id'])) for k,v in vectors.items()},
        class_control_shortfall=shortfall,
        phase_bindings=phases,l2_status="NOT_ASSESSED",training_admission="NOT_GRANTED",
        downstream=dict(status="BLOCKED_INDEPENDENT_ADMISSION_REQUIRED",seeds=list(range(10)),
            CE="DRAFT",WCE="BLOCKED_MISSING_THIRD_CLASS_CONFIDENCE",
            controls="Coverage/class-count controls require sufficient frozen baseline-only candidates; no synthetic labels"),
        scientific_status=["LIMITED_PROVENANCE_EXPLORATORY","EXPLORATORY_NOT_INDEPENDENT"])
    store=PrivateAudit(ROOT);sha=store.write(result);assert store.read(sha)==result
    print(json.dumps(dict(shadow_sha256=sha,proposals=len(changes),phases=len(phases))))
if __name__=="__main__":main()
