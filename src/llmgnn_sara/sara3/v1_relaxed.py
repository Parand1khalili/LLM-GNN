"""Opt-in shadow proposals. Provenance is verified by the receipt replay adapter."""
from ..io.frozen import reject_gt
from .experiment import digest
from .rich_evidence import validate_rich_result,target_source

VERSION="sara.arbitration.evidence_gated_third_class.v1"

def decide(node_id, candidates, text, blind, comparison, binding):
    result=dict(policy_version=VERSION,action="REJECT_INVALID_EVIDENCE",
        proposed_class_index=None,source_phase="BLIND_AND_COMPARISON",
        reason_codes=[],l1_status="NOT_ASSESSED",l2_status="NOT_ASSESSED",
        confidence_provenance="UNAVAILABLE_NOT_AGENT_CALIBRATED",
        training_admission_status="SHADOW_PROPOSAL_NOT_TRAINING_ADMITTED")
    try:
        reject_gt(binding)
        if (binding["node_id"]!=node_id or binding["blind_state"]!="COMPLETED"
            or binding["comparison_state"]!="COMPLETED"
            or binding["dependency"]!=digest(blind)
            or binding["blind_response"]!=digest(blind)
            or binding["comparison_response"]!=digest(comparison)
            or binding["schema"]!="sara.relaxed.verified_phase_pair.v1"):
            raise ValueError()
        for field in ("context_sha256","blind_identity","comparison_identity"):
            h=binding[field]
            if type(h)is not str or len(h)!=64 or any(c not in "0123456789abcdef" for c in h):raise ValueError()
        if len(candidates)!=2 or any(type(c)is not int or not 0<=c<7 for c in candidates):raise ValueError()
        first,second=[validate_rich_result(v,(target_source(text),)) for v in (blind,comparison)]
    except (ValueError,KeyError,TypeError):
        return {**result,"reason_codes":["INVALID_OR_UNAVAILABLE_PHASE_OR_BINDING"]}
    result["l1_status"]="PASS"
    features={name:[v["rich_evidence"][name] for v in (first,second)]
        for name in ("primary_topic","auxiliary_method_warning","counter_evidence","uncertainty_reason")}
    features["shared_support_count"]=len(set(first["evidence"]) & set(second["evidence"]))
    result["evidence_features"]=features
    if first["abstain"] or second["abstain"]:
        return {**result,"action":"ABSTAIN","reason_codes":["PHASE_ABSTENTION"]}
    if first["class_index"]!=second["class_index"]:
        return {**result,"action":"ABSTAIN","reason_codes":["PHASE_CLASS_CONFLICT"]}
    if not first["evidence"] or not second["evidence"]:
        return {**result,"reason_codes":["MISSING_SUPPORT"]}
    label=first["class_index"]
    if label in candidates:
        return {**result,"action":"KEEP_BASELINE","reason_codes":["PRESERVE_FROZEN_V1_VECTOR"]}
    return {**result,"action":"PROPOSE_CLASS_SWITCH","proposed_class_index":label,
        "reason_codes":["VALID_THIRD_CLASS_CONCORDANCE","SEMANTIC_SUPPORT_UNASSESSED_WARNINGS_UNRESOLVED"]}
