"""Offline post-hoc GT oracle comparison of every current Cora140 router.

All selections are recomputed GT-free; labels are used ONLY for scoring.
The only genuine SARA-3 verifier run is the existing frozen R0 cohort.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from ..io.project import load_project_inputs
from ..sara3.audit import PrivateAudit
from ..sara3.blind_review_pack import FREEZE_SHA256, _material, _safe_path
from ..sara3.gateway_failure_diagnostics import (
    _read_content_addressed, diagnose as verify_first_veto)
from ..sara3.r1_coverage import NEUTRAL, rank_policy
from ..sara3.selection import ROUTERS, select_router
from .cora_gt_shadow import (
    EvaluationStageError, GRAPH_SHA256, _expected_graph_names,
    _labels_from_original_graph, _require)
from .cora_node_journey import build_journey

VERSION = "sara.evaluation.cora140.all_routers_gt_posthoc.v1"
BUDGET = 37
COHORT = 140
EXTRA = "r1_neutral_v1"
ROUTER_NAMES = ("r0", "semantic", "r1_v1", EXTRA, "r1_v2", "r2_v1")
ERROR_CRITERIA = ("b1_wrong", "narrative_wrong", "either_wrong",
                  "both_wrong", "agreed_wrong")


def _router_selections(pairs):
    """Router selection has no access to GT or saved verifier decisions."""
    _require(tuple(ROUTERS) == ("r0", "semantic", "r1_v1", "r1_v2", "r2_v1")
             and set(ROUTER_NAMES) == set(ROUTERS) | {EXTRA})
    _require(type(pairs) is dict and len(pairs) == COHORT
             and all(type(n) is int and 0 <= n < 2708 for n in pairs))
    rows = tuple(pairs.values())
    result = {}
    for name in ROUTER_NAMES:
        if name == EXTRA:
            selected = tuple(rank_policy(rows, NEUTRAL)[:BUDGET])
        else:
            selected = tuple(select_router(rows, BUDGET, name))
        _require(len(selected) == BUDGET and len(set(selected)) == BUDGET
                 and set(selected) <= set(pairs))
        result[name] = selected
    return result


def _pct(num, den):
    return None if den == 0 else round(100 * num / den, 4)


def _detection(rows, chosen, criterion):
    population_errors = sum(row["error_flags_oracle_posthoc"][criterion] for row in rows)
    hits = sum(row["error_flags_oracle_posthoc"][criterion]
               for row in rows if row["node_id"] in chosen)
    missed = population_errors - hits
    false_alarms = BUDGET - hits
    negatives = COHORT - BUDGET - missed
    _require(min(hits, missed, false_alarms, negatives) >= 0
             and hits + missed == population_errors
             and hits + false_alarms == BUDGET
             and missed + negatives == COHORT - BUDGET)
    return {"all_140": population_errors,
            "selected_error": hits, "selected_no_error": false_alarms,
            "missed_error": missed, "not_selected_no_error": negatives,
            "precision_pct": _pct(hits, BUDGET),
            "recall_pct": _pct(hits, population_errors),
            "population_error_prevalence_pct": _pct(population_errors, COHORT),
            "unselected_error_prevalence_pct": _pct(missed, COHORT - BUDGET)}


def compare_routers(selected_r0, decisions, pairs, labels):
    """Verified R0 real outputs plus GT-only routing comparison for six routers."""
    _require(type(selected_r0) in (tuple, list) and len(selected_r0) == BUDGET)
    r0_journey = build_journey(selected_r0, decisions, pairs, labels)
    rows = r0_journey["node_rows_owner_private"]
    _require(len(rows) == COHORT and len({x["node_id"] for x in rows}) == COHORT)
    selections = _router_selections(pairs)
    _require(tuple(selected_r0) == selections["r0"])
    by_node = {row["node_id"]: row for row in rows}
    _require(set(by_node) == set(pairs))
    selected_sets = {name: set(ids) for name, ids in selections.items()}

    stats = {}
    for name, ids in selections.items():
        chosen = selected_sets[name]
        detected = {criterion: _detection(rows, chosen, criterion)
                    for criterion in ERROR_CRITERIA}
        disagreements = sum(not pairs[node].agrees for node in chosen)
        hh_agreements = sum(
            pairs[node].agrees
            and min(pairs[node].b1.confidence,
                    pairs[node].narrative_v0.confidence) >= 80
            for node in chosen)
        per_class = []
        for cls in range(7):
            case_rows = [by_node[node] for node in ids if labels[node] == cls]
            per_class.append({
                "class_index": cls, "selected_truth_support": len(case_rows),
                "b1_errors": sum(x["error_flags_oracle_posthoc"]["b1_wrong"]
                                 for x in case_rows),
                "narrative_errors": sum(
                    x["error_flags_oracle_posthoc"]["narrative_wrong"] for x in case_rows),
                "either_errors": sum(
                    x["error_flags_oracle_posthoc"]["either_wrong"] for x in case_rows),
                "agreed_wrong": sum(
                    x["error_flags_oracle_posthoc"]["agreed_wrong"] for x in case_rows)})
        _require(sum(x["selected_truth_support"] for x in per_class) == BUDGET
                 and sum(x["either_errors"] for x in per_class)
                 == detected["either_wrong"]["selected_error"])
        stats[name] = {
            "selected_count": BUDGET, "selection_budget": BUDGET,
            "GT_free_disagreement_selected": disagreements,
            "GT_free_high_confidence_agreement_selected": hh_agreements,
            "overlap_with_real_R0_review": len(chosen & selected_sets["r0"]),
            "real_agent_verifier_for_this_router":
                ("FROZEN_R0_ONLY" if name == "r0"
                 else "NOT_RUN_FOR_THIS_ROUTER"),
            "oracle_error_discovery_posthoc": detected,
            "per_true_class_oracle_selected": per_class,
        }

    overlap = {}
    for i, a in enumerate(ROUTER_NAMES):
        for b in ROUTER_NAMES[i + 1:]:
            common = selected_sets[a] & selected_sets[b]
            a_only, b_only = selected_sets[a] - common, selected_sets[b] - common
            count = lambda nodes, criterion: sum(
                by_node[node]["error_flags_oracle_posthoc"][criterion]
                for node in nodes)
            overlap[f"{a}__{b}"] = {
                "common_nodes": len(common), "a_only": len(a_only),
                "b_only": len(b_only),
                "common_with_baseline_error": count(common, "either_wrong"),
                "a_only_with_baseline_error": count(a_only, "either_wrong"),
                "b_only_with_baseline_error": count(b_only, "either_wrong"),
                "a_only_with_agreed_wrong": count(a_only, "agreed_wrong"),
                "b_only_with_agreed_wrong": count(b_only, "agreed_wrong"),
                "scope": "ORACLE_ROUTING_ONLY_NO_AGENT_OUTCOME_IMPUTATION",
            }
            _require(len(common) + len(a_only) == BUDGET
                     and len(common) + len(b_only) == BUDGET)

    owner_rows = []
    for node in sorted(by_node):
        record = dict(by_node[node])
        record["router_membership"] = {
            name: {"selected": node in selected_sets[name],
                   "rank_if_selected": (selections[name].index(node) + 1
                                        if node in selected_sets[name] else None),
                   "actual_verifier_execution":
                       ("R0_FROZEN" if name == "r0" and node in selected_sets["r0"]
                        else "NOT_EXECUTED")}
            for name in ROUTER_NAMES}
        # Blind/Comparison fields in the historical record are R0-only, not
        # outputs of R1, R2 or Semantic and never a counterfactual replay.
        owner_rows.append(record)

    public = {
        "schema": VERSION, "cohort_size": COHORT, "budget_each": BUDGET,
        "post_hoc_exploratory": True, "not_independent_holdout": True,
        "router_names": list(ROUTER_NAMES),
        "all_router_selections_recomputed_without_GT": True,
        "GT_only_routing_accuracy": stats,
        "pairwise_selection_and_error_capture": overlap,
        "real_R0_verifier_only": {
            "source": "FROZEN_R0_REAL_37",
            "reviewed_phase_changes": r0_journey["summary"]["reviewed_phase_changes"],
            "narrative_fallback_descriptive_only":
                r0_journey["summary"]["narrative_fallback_descriptive_only"],
            "all_37_correct_and_coverage":
                {name: {"denominator": rec["denominator"],
                        "covered": rec["covered"], "correct": rec["correct"],
                        "selective_accuracy_percent": rec["selective_accuracy_percent"],
                        "correct_over_all_percent": rec["correct_over_all_percent"]}
                 for name, rec in
                 r0_journey["shadow_score_summary"]["all_routed"]["arms"].items()},
        },
        "other_router_verifier_results": "NO_REAL_LLM_RUN_NO_LABEL_CORRECTION_RESULTS",
        "real_R0_reviewed_training_admissions": 0,
        "provider_calls": 0, "GCN_training_runs": 0,
        "interpretation": (
            "R0_IS_THE_ONLY_REAL_VERIFIER_RUN;"
            "R1_VERSIONS_ARE_PROSPECTIVE_RECONSTRUCTIONS_NOT_RECOVERED_HISTORICAL_R1;"
            "POST_HOC_ROUTER_ERROR_DETECTION_CANNOT_PROVE_GCN_IMPROVEMENT"),
    }
    _require(all(value["selected_count"] == BUDGET for value in stats.values()))
    return {"aggregate": public, "node_rows_owner_private": owner_rows}


def run(frozen_root, authentic_root, run_root, gateway_config, graph_file, audit_root):
    stage = "SAFE_PATH_PREFLIGHT"
    try:
        run_root, graph_file, audit_root = map(
            _safe_path, (run_root, graph_file, audit_root))
        _require(".local_artifacts" in run_root.parts
                 and ".local_artifacts" in audit_root.parts
                 and audit_root.parent.is_dir()
                 and audit_root != run_root
                 and audit_root not in run_root.parents
                 and run_root not in audit_root.parents)
        for value in (frozen_root, authentic_root, gateway_config, graph_file):
            path = _safe_path(value)
            _require(audit_root != path and audit_root not in path.parents
                     and path not in audit_root.parents)
        stage = "FROZEN_R0_SOURCE_VERIFICATION"
        freeze = _read_content_addressed(run_root, ("closeout_v1",), FREEZE_SHA256)
        report = _read_content_addressed(
            run_root, ("continuation_amendment_v1", "journal"),
            freeze["private_report_sha256"])
        config_path = _safe_path(gateway_config)
        _require(config_path.is_file() and config_path.stat().st_size <= 16384)
        config = json.loads(config_path.read_text(encoding="utf-8"))
        inputs = load_project_inputs(frozen_root, authentic_root)
        material = _material(inputs, freeze, report, config)
        verify_first_veto(freeze, report, freeze_sha256=FREEZE_SHA256)

        stage = "PINNED_GRAPH_LABELS"
        labels = _labels_from_original_graph(
            graph_file, _expected_graph_names(frozen_root))

        stage = "ALL_ROUTERS_GT_SCORING"
        pairs = {p.node_id: p for p in inputs.pairs}
        selected_r0 = [n for n, _ in material["records"]]
        result = compare_routers(selected_r0, report["run"]["decisions"], pairs, labels)
        result["source_closeout_sha256"] = FREEZE_SHA256
        result["source_graph_sha256"] = GRAPH_SHA256
        result["source_private_report_sha256"] = freeze["private_report_sha256"]

        stage = "PRIVATE_AUDIT_PERSISTENCE"
        audit = PrivateAudit(audit_root)
        sha = audit.write(result)
        _require(audit.read(sha) == result)
        return {"status": "ALL_ROUTER_GT_AUDIT_VERIFIED_PRIVATE",
                "relative_path": sha + ".json", "artifact_sha256": sha,
                "source_closeout_sha256": FREEZE_SHA256,
                "source_graph_sha256": GRAPH_SHA256,
                "aggregate": result["aggregate"]}
    except EvaluationStageError:
        raise
    except Exception:
        raise EvaluationStageError(stage) from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("frozen-root", "authentic-root", "run-root",
                "gateway-config", "graph-file", "audit-root"):
        parser.add_argument("--" + arg, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.frozen_root, args.authentic_root, args.run_root,
                     args.gateway_config, args.graph_file, args.audit_root)
        print(json.dumps(result, sort_keys=True, ensure_ascii=False,
                         indent=2, allow_nan=False))
        return 0
    except EvaluationStageError as err:
        print(json.dumps({"status": "FAIL_CLOSED", "stage": err.stage}),
              file=sys.stderr)
        return 1
    except Exception:
        print(json.dumps({"status": "FAIL_CLOSED"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
