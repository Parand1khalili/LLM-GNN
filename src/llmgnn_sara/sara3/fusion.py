"""One final experimental class per node from both baselines and Agent3.

No evaluation, provider, graph labels or training. Prior arbiters are unchanged.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from ..io.frozen import read_pinned_json, reject_gt
from ..io.project import load_project_inputs
from ..sara2.policy import Pair, validated_pairs, CLASSES
from .audit import PrivateAudit
from .correction_features import validate, require, PHASE_FIELDS
from .selection import select_router
from .experiment import digest
from .weighted_arbitration_v2 import FEATURE_SHA

VERSION = "sara.three_agent.fusion.v1"
P1 = "sara.fusion.conservative.v1"
P2 = "sara.fusion.relaxed.v1"
CONTRACT = {"version": VERSION, "policies": [P1, P2], "baseline_min_confidence": 80,
    "P1": "VALID_SUPPORTED_CROSS_PHASE_CONSENSUS_ELSE_BASELINE_AGREEMENT_ELSE_ABSTAIN",
    "P2_priority": ["VALID_SUPPORTED_CROSS_PHASE_CONSENSUS_ANY_CLASS",
        "VALID_DISAGREEING_PHASES_COMPARISON_SELECTS_HISTORICAL_CANDIDATE",
        "VALID_BLIND_HISTORICAL_CANDIDATE_ONLY_IF_COMPARISON_ABSENT_OR_REJECTED",
        "BASELINE_AGREEMENT_MIN80", "ABSTAIN"],
    "completed_comparison_abstention_fallback": False,
    "confidence_gap_rule": None, "warning_counter_topic_graph_seed_veto": False,
    "confidence_origin": "FUSION_MIN_MATCHING_BASELINE_OWN_ARM_FOR_A_B_ELSE_UNAVAILABLE",
    "consensus_reference": "sara.ablation.consensus_only.v1",
    "consensus_reference_sha256": "7de9f37650239e8feb74ba95c2e7476c35f436bc6670dc6005e78ae115f803c3",
    "status": "FROZEN_EXPERIMENTAL_NOT_TRAINING_ADMISSION", "training_authorization": False}


def valid_phase(phase):
    if phase is None: return False
    require(type(phase) is dict and set(phase) == PHASE_FIELDS)
    require(phase["state"] in ("COMPLETED", "REJECTED", "NOT_PERMITTED_ABSTENTION"))
    if phase["state"] != "COMPLETED" or phase["l1"] != "PASS" or phase["abstain"] is not False: return False
    require(type(phase["class_index"]) is int and 0 <= phase["class_index"] < 7)
    count, lengths = phase["support_count"], phase["quote_lengths"]
    return (type(count) is int and count > 0 and type(lengths) is list and len(lengths) == count
            and all(type(n) is int and n > 0 for n in lengths))


def fuse(pair, routed, blind, comparison, policy):
    require(type(pair) is Pair and type(routed) is bool and policy in (P1, P2, "C", "A", "B"))
    for phase in (blind, comparison):
        if phase is not None: reject_gt(phase)
    agreement = pair.agrees and min(pair.b1.confidence, pair.narrative_v0.confidence) >= 80
    label, source = (pair.b1.class_index, "BASELINE_AGREEMENT") if agreement else (None, "ABSTAIN")
    if policy in ("A", "B"):
        label, source = ((pair.b1.class_index, "B1_ONLY") if policy == "A" else
                         (pair.narrative_v0.class_index, "NARRATIVE_ONLY"))
    elif routed and policy != "C":
        bv, cv = valid_phase(blind), valid_phase(comparison)
        if bv and cv and blind["class_index"] == comparison["class_index"]:
            label, source = blind["class_index"], "AGENT3_CONSENSUS"
        elif policy == P2 and bv and cv and comparison["class_index"] in (pair.b1.class_index, pair.narrative_v0.class_index):
            label, source = comparison["class_index"], "AGENT3_COMPARISON_RESOLVER"
        elif (policy == P2 and bv and (comparison is None or comparison["state"] == "REJECTED")
              and blind["class_index"] in (pair.b1.class_index, pair.narrative_v0.class_index)):
            label, source = blind["class_index"], "AGENT3_BLIND_CANDIDATE_FALLBACK"
    matching = [a.confidence for a in (pair.b1, pair.narrative_v0) if a.class_index == label]
    confidence = min(matching) if matching else None
    if policy == "A": confidence = pair.b1.confidence
    if policy == "B": confidence = pair.narrative_v0.confidence
    change = ("KEPT_C" if agreement and label == pair.b1.class_index else
              "REVISED_C" if agreement and label is not None else "DROPPED_C" if agreement else
              "ADDED_TO_C" if label is not None else "ABSTAINED_C")
    return {"node_id": pair.node_id, "final_class": label, "label_source": source,
            "routed": routed, "accepted_experimentally": label is not None,
            "b1_class": pair.b1.class_index, "b1_confidence": pair.b1.confidence,
            "narrative_class": pair.narrative_v0.class_index, "narrative_confidence": pair.narrative_v0.confidence,
            "confidence_percent": confidence,
            "confidence_provenance": ("OWN_FROZEN_BASELINE" if policy in ("A", "B") else
                                      "HISTORICAL_MATCHING_CANDIDATE_MIN_NOT_AGENT_CALIBRATION" if matching else "UNAVAILABLE"),
            "third_class": label is not None and label not in (pair.b1.class_index, pair.narrative_v0.class_index),
            "disagreement_resolution": ("B1" if label == pair.b1.class_index else "NARRATIVE" if label == pair.narrative_v0.class_index
                                        else "THIRD_CLASS" if label is not None else "ABSTAIN") if not pair.agrees else "NOT_APPLICABLE",
            "relative_to_C": change, "training_eligible": False, "l2_status": "NOT_ASSESSED"}


def build(table, pairs):
    validate(table); pairs = validated_pairs(pairs)
    require(len(pairs) == 140 and len({p.node_id for p in pairs}) == 140)
    indexed = {p.node_id: p for p in pairs}
    for r in table["rows"]:
        p = indexed[r["node_id"]]
        require([r["b1_class"], r["b1_confidence"], r["narrative_class"], r["narrative_confidence"]] ==
                [p.b1.class_index, p.b1.confidence, p.narrative_v0.class_index, p.narrative_v0.confidence])
    arms = {name: [fuse(p, False, None, None, kind) for p in pairs]
            for name, kind in (("A_B1", "A"), ("B_NARRATIVE", "B"), ("C_BASELINE_FUSION", "C"))}
    selections = {}
    for router in ("r0", "r1_v1"):
        rows = {r["node_id"]: r for r in table["rows"] if r["router"] == router}
        selected = select_router(pairs, 37, router)
        require(set(selected) == set(rows) and digest(list(selected)) == table["sources"][router]["selected_ids_sha256"])
        selections[router] = list(selected)
        for short, policy in (("D_P1", P1), ("E_P2", P2)):
            arms[short+"_"+router] = [fuse(p, p.node_id in rows,
                rows[p.node_id]["blind"] if p.node_id in rows else None,
                rows[p.node_id]["compare"] if p.node_id in rows else None, policy) for p in pairs]
    return arms, selections


def summarize(rows):
    accepted = [r for r in rows if r["final_class"] is not None]
    return {"accepted": len(accepted), "abstained": len(rows)-len(accepted), "coverage": len(accepted)/len(rows),
            "label_sources": dict(Counter(r["label_source"] for r in rows)),
            "class_distribution": {str(k): sum(r["final_class"] == k for r in accepted) for k in range(7)},
            "relative_to_C": dict(Counter(r["relative_to_C"] for r in rows)),
            "disagreement_resolution": dict(Counter(r["disagreement_resolution"] for r in rows)),
            "third_class": sum(r["third_class"] for r in accepted),
            "agent3_selected": sum(r["label_source"].startswith("AGENT3") for r in accepted)}


def input_provenance(report, table):
    """Supplemental input trace; never changes the already frozen final labels."""
    validate(table)
    phases = {(r["router"], r["node_id"]): r for r in table["rows"]}
    records = {}
    for router in ("r0", "r1_v1"):
        records[router] = []
        for row in report["arms"]["C_BASELINE_FUSION"]:
            source = phases.get((router, row["node_id"]))
            records[router].append({"node_id": row["node_id"], "router_selected": source is not None,
                "b1": [row["b1_class"], row["b1_confidence"]],
                "narrative": [row["narrative_class"], row["narrative_confidence"]],
                "agent3": {p: {k: source[p][k] for k in ("state", "l1", "class_index", "abstain", "support_count")}
                           for p in ("blind", "compare")} if source is not None else None})
    return {"schema": "sara.fusion.input_provenance.v1", "fusion_sha256": digest(report),
            "source_feature_sha256": FEATURE_SHA, "source_input_hashes": report["source_input_hashes"],
            "phase_source_bindings": table["sources"], "records": records}


def validate_report(report, table, inputs):
    arms, selections = build(table, inputs.pairs)
    excluded = [p.target_id for p in inputs.frozen.by_arm("b1") if p.samples[0].source_kind == "supplementary"]
    require(report["schema"] == VERSION and report["contract"] == CONTRACT and report["rule_sha256"] == digest(CONTRACT)
            and report["source_feature_sha256"] == FEATURE_SHA and report["ordered_classes"] == list(CLASSES)
            and report["arms"] == arms and report["router_selections"] == selections and report["training_admissions"] == 0
            and report["cohort_ids"] == [p.node_id for p in inputs.pairs]
            and report["primary_excluded_ids"] == excluded and len(excluded) == 5
            and report["source_input_hashes"] == [list(h) for h in inputs.provenance])


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("features", "frozen-root", "authentic-root", "output"):
        p.add_argument("--"+name, type=Path, required=True)
    a = p.parse_args(argv)
    try:
        table = read_pinned_json(a.features, FEATURE_SHA); inputs = load_project_inputs(a.frozen_root, a.authentic_root)
        require(".local_artifacts" in a.output.absolute().parts); store = PrivateAudit(a.output)
        rule_sha = store.write(CONTRACT)  # Both policies fixed before outputs and GT.
        arms, selections = build(table, inputs.pairs)
        excluded = [p.target_id for p in inputs.frozen.by_arm("b1") if p.samples[0].source_kind == "supplementary"]
        require(len(excluded) == 5)
        report = {"schema": VERSION, "contract": CONTRACT, "rule_sha256": rule_sha,
                  "source_feature_sha256": FEATURE_SHA, "source_input_hashes": [list(h) for h in inputs.provenance],
                  "ordered_classes": list(CLASSES), "cohort_ids": [p.node_id for p in inputs.pairs],
                  "primary_excluded_ids": excluded, "router_selections": selections,
                  "arms": arms, "training_admissions": 0}
        validate_report(report, table, inputs); sha = store.write(report); require(store.read(sha) == report)
        provenance = input_provenance(report, table); provenance_sha = store.write(provenance)
        require(store.read(provenance_sha) == provenance)
        print(json.dumps({"rule_sha256": rule_sha, "fusion_sha256": sha, "input_provenance_sha256": provenance_sha,
                          "summary": {k: summarize(v) for k, v in arms.items()}}))
        return 0
    except Exception:
        print('{"status":"FAIL_CLOSED"}', file=sys.stderr); return 1


if __name__ == "__main__": raise SystemExit(main())
