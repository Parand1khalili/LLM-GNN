"""Post-hoc, owner-private node-by-node R0 triage and SARA-3 review journey.

A deliberately isolated GT-only evaluator. R0 (NOT the verifier) selects the
37 reviewed nodes from the 140 frozen B1/Narrative predictions. No inference,
rerouting, arbitration changes, model calls, GT feedback or GCN execution.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from ..io.project import load_project_inputs
from ..sara2.policy import risk, route_r0
from ..sara3.audit import PrivateAudit
from ..sara3.blind_review_pack import FREEZE_SHA256, _material, _safe_path
from ..sara3.gateway_failure_diagnostics import (
    _read_content_addressed, diagnose as verify_first_veto)
from .cora_gt_shadow import (
    EvaluationStageError, GRAPH_SHA256, _expected_graph_names,
    _labels_from_original_graph, _require, score)

VERSION = "sara.evaluation.cora140.node_journey.v1"
CRITERIA = ("b1_wrong", "narrative_wrong", "either_wrong", "both_wrong",
            "agreed_wrong", "b1_narrative_disagree")
BASELINES = ("b1", "narrative_v0")
PHASES = ("blind", "comparison")


def _outcome(prediction, baseline, truth):
    """Mutually exclusive paired outcomes; no label means never reviewed."""
    if prediction is None:
        return "NO_CLASS_PREDICTION"
    if baseline == truth and prediction == truth:
        return "BOTH_CORRECT"
    if baseline != truth and prediction == truth:
        return "CORRECTED_BASELINE_ERROR"
    if baseline == truth and prediction != truth:
        return "DAMAGED_CORRECT_BASELINE"
    return "BOTH_INCORRECT"


def build_journey(selected, decisions, pairs, labels):
    """Pure post-hoc derivation; frozen inputs and labels supplied by verified caller."""
    frozen_score = score(selected, decisions, pairs, labels,
                         freeze_sha256=FREEZE_SHA256, graph_sha256=GRAPH_SHA256)
    _require(len(pairs) == 140 and len(decisions) == 140 and len(selected) == 37)
    ordered = route_r0(tuple(pairs.values()), len(pairs))
    _require(len(ordered) == 140 and list(ordered[:37]) == list(selected))
    ranks = {node: index + 1 for index, node in enumerate(ordered)}
    by_decision = {d["node_id"]: d for d in decisions}
    _require(len(by_decision) == 140 and set(by_decision) == set(pairs))
    routed = set(selected)
    rows = []

    for node in ordered:
        pair, decision = pairs[node], by_decision[node]
        chosen = node in routed
        _require(decision["routed_for_review"] is chosen)
        truth = labels[node]
        b1, narrative = pair.b1.class_index, pair.narrative_v0.class_index
        flags = {
            "b1_wrong": b1 != truth,
            "narrative_wrong": narrative != truth,
            "either_wrong": b1 != truth or narrative != truth,
            "both_wrong": b1 != truth and narrative != truth,
            "agreed_wrong": b1 == narrative and b1 != truth,
            "b1_narrative_disagree": b1 != narrative,
        }
        blind = decision.get("blind_class_index") if chosen else None
        comp = decision.get("comparison_class_index") if chosen else None
        _require(decision.get("b1_class_index") == b1
                 and decision.get("narrative_v0_class_index") == narrative)
        if not chosen:
            _require(blind is None and comp is None)
        row = {
            "node_id": node, "r0_rank": ranks[node],
            "r0_risk_score": risk(pair), "r0_selected_for_review": chosen,
            "r0_selection_basis": "B1_NARRATIVE_DISAGREEMENT_AND_MIN_CONFIDENCE",
            "ground_truth_class_index": truth,
            "b1_class_index": b1, "b1_confidence_percent": pair.b1.confidence,
            "narrative_v0_class_index": narrative,
            "narrative_v0_confidence_percent": pair.narrative_v0.confidence,
            "error_flags_oracle_posthoc": flags,
            "blind_class_index": blind,
            "comparison_class_index": comp,
            "blind_matches_gt": None if blind is None else blind == truth,
            "comparison_matches_gt": None if comp is None else comp == truth,
            "frozen_decision_reason": decision.get("reason"),
            "frozen_arbitration_reason": decision.get("reason") if chosen else None,
            "frozen_training_class_index": decision.get("training_class_index"),
            "frozen_training_admitted": bool(decision.get("accepted")),
            "frozen_training_class_matches_gt": (
                None if decision.get("training_class_index") is None
                else decision["training_class_index"] == truth),
            "b1_to_blind": _outcome(blind, b1, truth) if chosen else "NOT_REVIEWED",
            "b1_to_comparison": _outcome(comp, b1, truth) if chosen else "NOT_REVIEWED",
            "narrative_to_blind": _outcome(blind, narrative, truth) if chosen else "NOT_REVIEWED",
            "narrative_to_comparison": _outcome(comp, narrative, truth) if chosen else "NOT_REVIEWED",
        }
        _require(row["frozen_training_admitted"] ==
                 (row["frozen_training_class_index"] is not None))
        if chosen:
            _require(row["frozen_training_admitted"] is False)
        rows.append(row)

    def triage(k):
        t = sum(x["error_flags_oracle_posthoc"][k] for x in rows)
        s = sum(x["error_flags_oracle_posthoc"][k] for x in rows if x["r0_selected_for_review"])
        return {"criterion": k, "all_140": t, "selected_true_positive": s,
                "selected_false_positive": 37 - s, "missed_false_negative": t - s,
                "not_selected_true_negative": 103 - (t - s),
                "precision_denominator": 37, "recall_denominator": t}
    routing = {k: triage(k) for k in CRITERIA}

    review = {}
    reviewed = [x for x in rows if x["r0_selected_for_review"]]
    for baseline in BASELINES:
        for phase in PHASES:
            col = f"{baseline.split('_v0')[0]}_to_{phase}"
            if baseline == "narrative_v0":
                col = f"narrative_to_{phase}"
            counts = Counter(x[col] for x in reviewed)
            _require(sum(counts.values()) == 37)
            review[f"{baseline}_to_{phase}"] = {
                "denominator": 37,
                **{name: counts[name] for name in (
                    "NO_CLASS_PREDICTION", "BOTH_CORRECT",
                    "CORRECTED_BASELINE_ERROR", "DAMAGED_CORRECT_BASELINE",
                    "BOTH_INCORRECT")},
                "net_corrections_on_covered": (counts["CORRECTED_BASELINE_ERROR"]
                                                - counts["DAMAGED_CORRECT_BASELINE"]),
            }

    # Observable, deliberately unconditional fallback policies (NOT Arbitration V2).
    # The same frozen unselected predictions are retained; no fitted thresholds.
    fallback = {}
    for phase in PHASES:
        before = sum(row["narrative_v0_class_index"] == row["ground_truth_class_index"]
                     for row in rows)
        after = sum(
            ((row[f"{phase}_class_index"]
              if row["r0_selected_for_review"] and row[f"{phase}_class_index"] is not None
              else row["narrative_v0_class_index"]) == row["ground_truth_class_index"])
            for row in rows)
        fallback[phase] = {"scope": "ALL_140", "baseline_narrative_correct": before,
                           "replace_when_phase_has_class_correct": after,
                           "net_delta_correct": after - before,
                           "not_v1_admission_not_GCN_result": True}
    _require(fallback["blind"]["net_delta_correct"]
             == review["narrative_v0_to_blind"]["net_corrections_on_covered"])
    _require(fallback["comparison"]["net_delta_correct"]
             == review["narrative_v0_to_comparison"]["net_corrections_on_covered"])

    summary = {
        "schema": VERSION, "post_hoc_exploratory": True,
        "router": "r0", "who_flagged_for_review": "R0_NOT_SARA3",
        "cohort_nodes": 140, "routed_nodes": 37,
        "unrouted_nodes": 103, "r0_oracle_routing": routing,
        "reviewed_phase_changes": review,
        "narrative_fallback_descriptive_only": fallback,
        "observed_frozen_v1_training_admissions": 0,
        "interpretation": (
            "R0_IS_A_SELECTION_POLICY_NOT_AGENT_SUSPICION;"
            "ORACLE_GT_ROUTING_METRICS_ARE_POST_HOC;"
            "OBSERVED_CORRECTIONS_ARE_NOT_PROSPECTIVE_ADMISSIONS_OR_GCN_IMPROVEMENT"),
    }
    return {"summary": summary, "node_rows_owner_private": rows,
            "shadow_score_summary": frozen_score}


def run(frozen_root, authentic_root, run_root, gateway_config, graph_file, audit_root):
    stage = "SAFE_PATH_PREFLIGHT"
    try:
        run_root, graph_file = _safe_path(run_root), _safe_path(graph_file)
        audit_root = _safe_path(audit_root)
        _require(".local_artifacts" in run_root.parts
                 and ".local_artifacts" in audit_root.parts
                 and audit_root.parent.is_dir()
                 and audit_root != run_root
                 and audit_root not in run_root.parents
                 and run_root not in audit_root.parents)
        for item in (frozen_root, authentic_root, graph_file, gateway_config):
            path = _safe_path(item)
            _require(audit_root != path and audit_root not in path.parents
                     and path not in audit_root.parents)

        stage = "FROZEN_PRIVATE_SOURCES"
        freeze = _read_content_addressed(run_root, ("closeout_v1",), FREEZE_SHA256)
        private_sha = freeze.get("private_report_sha256")
        report = _read_content_addressed(
            run_root, ("continuation_amendment_v1", "journal"), private_sha)
        config_file = _safe_path(gateway_config)
        _require(config_file.is_file() and config_file.stat().st_size <= 16384)
        config = json.loads(config_file.read_text(encoding="utf-8"))
        inputs = load_project_inputs(frozen_root, authentic_root)
        material = _material(inputs, freeze, report, config)
        verify_first_veto(freeze, report, freeze_sha256=FREEZE_SHA256)

        stage = "GRAPH_TRUST_AND_CLASS_MAPPING"
        original_names = _expected_graph_names(frozen_root)
        labels = _labels_from_original_graph(graph_file, original_names)

        stage = "NODE_JOURNEY_RECONCILIATION"
        selected = [node for node, _ in material["records"]]
        pairs = {p.node_id: p for p in inputs.pairs}
        result = build_journey(selected, report["run"]["decisions"], pairs, labels)
        result["source_closeout_sha256"] = FREEZE_SHA256
        result["source_graph_sha256"] = GRAPH_SHA256
        result["source_private_report_sha256"] = private_sha

        stage = "PRIVATE_REPORT_PERSISTENCE"
        audit = PrivateAudit(audit_root)
        digest = audit.write(result)
        _require(audit.read(digest) == result)
        return {"status": "OWNER_PRIVATE_NODE_JOURNEY_VERIFIED",
                "artifact_sha256": digest,
                "relative_path": digest + ".json",
                "source_closeout_sha256": FREEZE_SHA256,
                "source_graph_sha256": GRAPH_SHA256,
                "summary": result["summary"],
                "provider_calls": 0, "GCN_training_runs": 0,
                "training_admissions": 0}
    except EvaluationStageError:
        raise
    except Exception:
        raise EvaluationStageError(stage) from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("frozen-root", "authentic-root", "run-root", "gateway-config",
                "graph-file", "audit-root"):
        parser.add_argument("--" + arg, required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = run(args.frozen_root, args.authentic_root,
                     args.run_root, args.gateway_config,
                     args.graph_file, args.audit_root)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except EvaluationStageError as failure:
        print(json.dumps({"status": "FAIL_CLOSED", "stage": failure.stage}),
              file=sys.stderr)
        return 1
    except Exception:
        print(json.dumps({"status": "FAIL_CLOSED"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
