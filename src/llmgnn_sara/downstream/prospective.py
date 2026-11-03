"""Explicit prospective GCN *plan* admission; not L2 approval or training.

The default frozen adapter never converts provisional proposals. This opt-in
adapter consumes a separately pinned report and frozen-candidate snapshot and
rederives the candidate eligibility from the typed B1/Narrative pairs.
"""
import hashlib
import re

from ..sara2.policy import CLASSES, route_r0, validated_pairs
from ..io.frozen import reject_gt
from ..sara3.atlas import route_semantic
from ..sara3.automated_policy import VERSION as ARBITRATION_VERSION
from ..sara3.inputs import canonical_bytes
from .plan import GCNConfig, PseudoLabel, gcn_plan

VERSION = "sara.gcn.experimental_concordance_admission.v1"
REPORT_SCHEMA = "sara.automated_arbitration_result.v2"
LABEL_STATUS = "BASELINE_ELIGIBLE_PROVISIONAL_QUARANTINED"


def frozen_pair_digest(pairs):
    """Hash only frozen predictions/ID/order; never text, graph or GT labels."""
    return hashlib.sha256(canonical_bytes([
        {"node_id": p.node_id,
         "b1": [p.b1.class_index, p.b1.confidence],
         "narrative_v0": [p.narrative_v0.class_index, p.narrative_v0.confidence]}
        for p in validated_pairs(pairs)])).hexdigest()


def offline_report_digest(report):
    """Pin the *entire* immutable offline report before controlled admission."""
    if type(report) is not dict:
        raise ValueError("A complete report is required")
    return hashlib.sha256(canonical_bytes(report)).hexdigest()


def controlled_gcn_plan(pairs, report, *, admission_version, frozen_pairs_sha256,
                        report_sha256, cohort="sensitivity", excluded_ids=(),
                        config=None):
    """Make an untrained matched GCN plan from explicit experimental candidates.

    Requires an externally prespecified report digest and frozen-pair digest.
    This is *not* proof of semantic accuracy or authorization to train. All
    selected and excluded nodes retain the matched test complement.
    """
    if admission_version != VERSION:
        raise ValueError("Explicit versioned experimental admission required")
    if (type(frozen_pairs_sha256) is not str or not re.fullmatch(r"[0-9a-f]{64}", frozen_pairs_sha256)
            or type(report_sha256) is not str or not re.fullmatch(r"[0-9a-f]{64}", report_sha256)):
        raise ValueError("Explicit valid 64-hex source pins are required")
    rows = validated_pairs(pairs)
    if frozen_pair_digest(rows) != frozen_pairs_sha256 or offline_report_digest(report) != report_sha256:
        raise ValueError("Frozen or run report SHA-256 differs")
    reject_gt(report)
    if (report.get("result_schema") != REPORT_SCHEMA or report.get("label_status") != LABEL_STATUS
            or report.get("automated_arbitration_version") != ARBITRATION_VERSION
            or report.get("GT_accessed") is not False or report.get("provider_calls") != 0
            or report.get("training_runs") != 0 or report.get("target_count") != len(rows)
            or report.get("ordered_classes") != list(CLASSES)
            or report.get("policy") != {"agreement_acceptance_percent": 80.0,
                 "provenance": "RECONSTRUCTED_POLICY_NOT_HISTORICAL_EQUIVALENT"}):
        raise ValueError("Incompatible or unverified offline proposal report")
    if report.get("router") not in ("r0", "semantic") or type(report.get("review_budget")) is not int:
        raise ValueError("Only unchanged prospective routing is eligible")
    if not rows:
        raise ValueError("Empty experimental cohort")
    selected = (route_r0 if report["router"] == "r0" else route_semantic)(rows, report["review_budget"])
    if report.get("selected_node_ids") != list(selected) or report.get("review_count") != len(selected):
        raise ValueError("Router selection differs from the frozen candidates")
    decisions = report.get("decisions")
    if (type(decisions) is not list or len(decisions) != len(rows)
            or [d.get("node_id") for d in decisions if type(d) is dict] != [p.node_id for p in rows]):
        raise ValueError("One ordered decision per frozen node is required")
    selected_set = set(selected)
    labels, provisional, baseline = [], [], []
    for p, decision in zip(rows, decisions):
        if (type(decision.get("accepted")) is not bool
                or decision.get("routed_for_review") is not (p.node_id in selected_set)):
            raise ValueError("Routed/accepted decision does not match frozen selection")
        expected_confidence = lambda k: min(
            x.confidence for x in (p.b1, p.narrative_v0) if x.class_index == k)
        if p.node_id not in selected_set:
            keep = p.agrees and min(p.b1.confidence, p.narrative_v0.confidence) >= 80
            if (decision.get("accepted") is not keep
                    or decision.get("training_class_index") != (p.b1.class_index if keep else None)
                    or decision.get("accepted_label") != (p.b1.class_index if keep else None)
                    or decision.get("reason") != ("UNREVIEWED_AGREEMENT" if keep else "UNREVIEWED_ABSTENTION")
                    or decision.get("provisional_class_index") is not None
                    or decision.get("provisional_status") != "NOT_PROPOSED"
                    or decision.get("l2_status") != "NOT_APPLICABLE_BASELINE_POLICY"):
                raise ValueError("Unrouted baseline reconstruction changed")
            if keep:
                if decision.get("label_confidence_percent") != expected_confidence(p.b1.class_index):
                    raise ValueError("Frozen baseline confidence differs")
                labels.append(PseudoLabel(p.node_id, p.b1.class_index, expected_confidence(p.b1.class_index)))
                baseline.append(p.node_id)
            continue
        if (decision.get("accepted") is not False or decision.get("training_class_index") is not None
                or decision.get("accepted_label") is not None or decision.get("abstain") is not True
                or decision.get("l2_status") != "NOT_ASSESSED"
                or decision.get("semantic_validation") != "NOT_PERFORMED"):
            raise ValueError("Provisional result cannot claim training/L2 acceptance")
        if decision.get("provisional_status") != "PROPOSED":
            if decision.get("provisional_class_index") is not None:
                raise ValueError("Non-proposal has an unexpected class")
            continue
        k = decision.get("provisional_class_index")
        source = ("B1_AND_NARRATIVE_CONCORDANCE" if p.agrees else
                  "B1_CANDIDATE" if k == p.b1.class_index else "NARRATIVE_V0_CANDIDATE")
        if (type(k) is not int or k not in (p.b1.class_index, p.narrative_v0.class_index)
                or decision.get("blind_class_index") != k or decision.get("comparison_class_index") != k
                or decision.get("decision") != "PROPOSE" or decision.get("automated_screen_status") != "ACCEPT"
                or decision.get("automated_screen_reason") != "PROVISIONAL_CROSS_PHASE_CONCORDANCE"
                or decision.get("automated_policy_version") != ARBITRATION_VERSION
                or decision.get("l1_status") != "PASS" or decision.get("third_class_proposal") is not None
                or decision.get("provisional_label_source") != source
                or decision.get("provisional_confidence_percent") != expected_confidence(k)
                or decision.get("training_use") != "PROVISIONAL_UNVALIDATED_GCN_ADMISSION_FORBIDDEN"):
            raise ValueError("Provisional claim does not match pinned two-phase contract")
        labels.append(PseudoLabel(p.node_id, k, expected_confidence(k)))
        provisional.append(p.node_id)
    expected_public = [
        {"node_id": d["node_id"], "provisional_class_index": d["provisional_class_index"],
         "historical_confidence_percent": d["provisional_confidence_percent"],
         "provisional_label_source": d["provisional_label_source"],
         "l2_status": d["l2_status"], "training_eligible": False}
        for d in decisions if d["provisional_status"] == "PROPOSED"]
    if (report.get("provisional_pseudo_labels") != expected_public
            or report.get("provisional_count") != len(provisional)
            or report.get("accepted_count") != len(baseline)
            or report.get("coverage") != len(baseline) / len(rows)):
        raise ValueError("Reported candidate totals differ from decisions")
    if not labels:
        raise ValueError("No baseline or provisional candidates to plan")
    settings = config if config is not None else GCNConfig()
    plan = gcn_plan(tuple(p.node_id for p in rows), labels, cohort=cohort,
                    excluded_ids=excluded_ids, config=settings, allow_abstention=True)
    plan.update({"experimental_admission_version": VERSION,
                 "protocol_status": "EXPERIMENTAL_LABELS_MATCHED_GCN_CONFIG",
                 "source_report_sha256": report_sha256,
                 "source_frozen_pairs_sha256": frozen_pairs_sha256,
                 "admitted_provisional_ids": [i for i in provisional if i in plan["train_ids"]],
                 "admitted_baseline_ids": [i for i in baseline if i in plan["train_ids"]],
                 "l2_semantic_validation": "NOT_PERFORMED",
                 "proposal_truth_status": "UNKNOWN",
                 "authorization": "PLAN_ONLY_SEPARATE_APPROVAL_REQUIRED_FOR_GCN_TRAINING"})
    return plan
