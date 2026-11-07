"""Owner-only GT evaluation of a separately approved REAL R1-v1 GapGPT run.

Never dispatches HTTP or changes GT-free inference/Arbitration/admission.
The historical R0 live freeze is distinct from this prospective R1 arm.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from ..downstream.prospective import frozen_pair_digest
from ..io.project import load_project_inputs
from ..sara3.audit import PrivateAudit
from ..sara3.blind_review_pack import _safe_path
from ..sara3.gateway_failure_diagnostics import _read_content_addressed
from ..sara3.gateway_run import CONTRACT, gateway_context
from ..sara3.gapgpt_live import contract_from_dict
from ..sara3.selection import select_router
from ..sara3.rich_evidence import RICH_PROMPT_V2, RICH_VERSION
from ..sara3.automated_policy import VERSION as ARBITRATION_VERSION
from .cora_gt_shadow import (
    EvaluationStageError, GRAPH_SHA256, _expected_graph_names,
    _labels_from_original_graph, _require)

VERSION = "sara.evaluation.cora140.r1_v1_real_posthoc.v1"
BUDGET, COHORT = 37, 140
ROUTER = "r1_v1"
CRITERIA = ("b1_wrong", "narrative_wrong", "either_wrong",
            "both_wrong", "agreed_wrong", "baseline_disagreement")
PAIRED = ("BOTH_CORRECT", "CORRECTED_BASELINE_ERROR",
          "DAMAGED_CORRECT_BASELINE", "BOTH_INCORRECT", "NO_CLASS_PREDICTION")


def _pct(n, d):
    return None if not d else round(100 * n / d, 4)


def _oracle(truth, b1, narrative):
    return {
        "b1_wrong": b1 != truth,
        "narrative_wrong": narrative != truth,
        "either_wrong": b1 != truth or narrative != truth,
        "both_wrong": b1 != truth and narrative != truth,
        "agreed_wrong": b1 == narrative and b1 != truth,
        "baseline_disagreement": b1 != narrative,
    }


def _paired(prediction, baseline, truth):
    if prediction is None:
        return "NO_CLASS_PREDICTION"
    if baseline == truth:
        return "BOTH_CORRECT" if prediction == truth else "DAMAGED_CORRECT_BASELINE"
    return "CORRECTED_BASELINE_ERROR" if prediction == truth else "BOTH_INCORRECT"


def _bucket(rows):
    """Stratified coverage/correctness and paired correction counts, all inclusive."""
    result = {"n": len(rows), "arms": {}, "narrative_paired": {}}
    for arm, field in (("b1", "b1_class_index"),
                       ("narrative", "narrative_class_index"),
                       ("blind", "blind_class_index"),
                       ("comparison", "comparison_class_index")):
        covered = sum(x[field] is not None for x in rows)
        correct = sum(x[field] == x["gt_class_index"] for x in rows)
        result["arms"][arm] = {
            "covered": covered, "correct": correct,
            "unavailable": len(rows) - covered,
            "selective_accuracy_percent": _pct(correct, covered),
            "per_true_class": [
                {"class_index": cls,
                 "support": sum(x["gt_class_index"] == cls for x in rows),
                 "covered": sum(x["gt_class_index"] == cls and x[field] is not None
                                for x in rows),
                 "correct": sum(x["gt_class_index"] == cls and
                                x[field] == cls for x in rows)}
                for cls in range(7)]}
    for phase in ("blind", "comparison"):
        counts = Counter(x[f"narrative_vs_{phase}"] for x in rows)
        result["narrative_paired"][phase] = {
            **{kind: counts[kind] for kind in PAIRED},
            "net_correct": counts["CORRECTED_BASELINE_ERROR"] -
                           counts["DAMAGED_CORRECT_BASELINE"]}
    return result


def analyze(selected, decisions, pairs, labels, *, status):
    """Pure node-by-node scoring after validating pinned live provenance."""
    _require(status in ("COMPLETE_LIVE_UNASSESSED", "BLOCKED_NO_AUTOMATIC_RETRY"))
    _require(type(pairs) is dict and len(pairs) == COHORT
             and type(labels) in (list, tuple) and len(labels) == 2708
             and all(type(x) is int and 0 <= x < 7 for x in labels)
             and type(decisions) is list and len(decisions) == COHORT)
    expected = select_router(tuple(pairs.values()), BUDGET, ROUTER)
    _require(list(selected) == list(expected))
    _require(len({d["node_id"] for d in decisions}) == COHORT
             and {d["node_id"] for d in decisions} == set(pairs))
    by_id = {d["node_id"]: d for d in decisions}
    selected_set = set(expected)
    rows = []
    for rank, node in enumerate(sorted(pairs)):
        pair, decision = pairs[node], by_id[node]
        truth = labels[node]
        routed = node in selected_set
        _require(decision.get("routed_for_review") is routed
                 and decision.get("b1_class_index") == pair.b1.class_index
                 and decision.get("narrative_v0_class_index") == pair.narrative_v0.class_index)
        accepted = decision.get("accepted")
        training = decision.get("training_class_index")
        _require(type(accepted) is bool and
                 accepted == (training is not None) and
                 (training is None or type(training) is int and 0 <= training < 7))
        if routed:
            _require(not accepted and training is None
                     and decision.get("l2_status") == "NOT_ASSESSED"
                     and decision.get("semantic_validation") == "NOT_PERFORMED")
        if routed:
            _require(type(decision.get("reason")) is str)
        blind = decision.get("blind_class_index")
        comp = decision.get("comparison_class_index")
        _require((blind is None or type(blind) is int and 0 <= blind < 7)
                 and (comp is None or type(comp) is int and 0 <= comp < 7)
                 and (routed or blind is None and comp is None))
        row = {
            "node_id": node, "r1_selected": routed,
            "r1_rank": list(expected).index(node) + 1 if routed else None,
            "gt_class_index": truth,
            "b1_class_index": pair.b1.class_index,
            "b1_confidence": pair.b1.confidence,
            "narrative_class_index": pair.narrative_v0.class_index,
            "narrative_confidence": pair.narrative_v0.confidence,
            "oracle_flags_posthoc": _oracle(truth, pair.b1.class_index,
                                           pair.narrative_v0.class_index),
            "blind_class_index": blind, "comparison_class_index": comp,
            "blind_correct": None if blind is None else blind == truth,
            "comparison_correct": None if comp is None else comp == truth,
            "decision_reason": decision.get("reason"),
            "frozen_training_class_index": training,
            "frozen_training_class_correct": None if training is None else training == truth,
            "b1_vs_blind": _paired(blind, pair.b1.class_index, truth) if routed else "NOT_REVIEWED",
            "narrative_vs_blind": _paired(blind, pair.narrative_v0.class_index, truth) if routed else "NOT_REVIEWED",
            "b1_vs_comparison": _paired(comp, pair.b1.class_index, truth) if routed else "NOT_REVIEWED",
            "narrative_vs_comparison": _paired(comp, pair.narrative_v0.class_index, truth) if routed else "NOT_REVIEWED",
        }
        rows.append(row)
    chosen = [row for row in rows if row["r1_selected"]]
    _require(len(chosen) == BUDGET)
    discovery = {}
    for criterion in CRITERIA:
        n = sum(row["oracle_flags_posthoc"][criterion] for row in rows)
        tp = sum(row["oracle_flags_posthoc"][criterion] for row in chosen)
        discovery[criterion] = {
            "all_140": n, "true_positive": tp,
            "false_positive": BUDGET - tp, "false_negative": n - tp,
            "true_negative": COHORT - BUDGET - (n - tp),
            "precision_percent": _pct(tp, BUDGET),
            "recall_percent": _pct(tp, n),
        }
    arms = {}
    for arm, col in (("b1", "b1_class_index"),
                     ("narrative", "narrative_class_index"),
                     ("blind", "blind_class_index"),
                     ("comparison", "comparison_class_index")):
        covered = sum(row[col] is not None for row in chosen)
        correct = sum(row[col] == row["gt_class_index"] for row in chosen)
        arms[arm] = {"denominator": BUDGET, "covered": covered,
                     "abstained_or_unavailable": BUDGET - covered,
                     "correct": correct, "coverage_percent": _pct(covered, BUDGET),
                     "selective_accuracy_percent": _pct(correct, covered),
                     "correct_over_all_percent": _pct(correct, BUDGET)}
    changes = {}
    for baseline in ("b1", "narrative"):
        for phase in ("blind", "comparison"):
            key = f"{baseline}_vs_{phase}"
            counts = Counter(row[key] for row in chosen)
            _require(sum(counts.values()) == BUDGET)
            changes[key] = {
                "denominator": BUDGET,
                **{kind: counts[kind] for kind in PAIRED},
                "net_correct_change_on_covered":
                    counts["CORRECTED_BASELINE_ERROR"] -
                    counts["DAMAGED_CORRECT_BASELINE"],
            }
    first_veto_strata = {}
    for name in ("COUNTER_EVIDENCE_UNRESOLVED",
                 "THIRD_CLASS_DIAGNOSTIC_ONLY", "OTHER"):
        group = [x for x in chosen if
                 (x["decision_reason"] == name if name != "OTHER"
                  else x["decision_reason"] not in (
                      "COUNTER_EVIDENCE_UNRESOLVED",
                      "THIRD_CLASS_DIAGNOSTIC_ONLY"))]
        first_veto_strata[name] = _bucket(group)
    _require(sum(x["n"] for x in first_veto_strata.values()) == BUDGET)
    agreeing_third = [x for x in chosen
                      if x["decision_reason"] == "THIRD_CLASS_DIAGNOSTIC_ONLY"
                      and x["blind_class_index"] is not None
                      and x["blind_class_index"] == x["comparison_class_index"]]
    baseline_narrative_correct = sum(row["narrative_class_index"] ==
                                      row["gt_class_index"] for row in rows)
    fallback = {}
    for phase in ("blind", "comparison"):
        count = sum(
            (row[f"{phase}_class_index"]
             if row["r1_selected"] and row[f"{phase}_class_index"] is not None
             else row["narrative_class_index"]) == row["gt_class_index"]
            for row in rows)
        _require(count - baseline_narrative_correct ==
                 changes[f"narrative_vs_{phase}"]["net_correct_change_on_covered"])
        fallback[phase] = {
            "narrative_baseline_correct_140": baseline_narrative_correct,
            "hypothetical_replace_available_correct_140": count,
            "net_difference_140": count - baseline_narrative_correct,
            "NOT_AN_ADMITTED_POLICY_OR_GCN_RESULT": True}
    return {
        "aggregate": {
            "schema": VERSION, "router": ROUTER, "status_of_real_run": status,
            "cohort_size": COHORT, "routed_size": BUDGET,
            "oracle_router_detection": discovery,
            "r1_review_coverage_and_accuracy": arms,
            "paired_correction_vs_baselines": changes,
            "first_veto_strata": first_veto_strata,
            "third_class_phase_agree": _bucket(agreeing_third),
            "selected_baseline_disagreements": discovery["baseline_disagreement"]["true_positive"],
            "selected_high_confidence_agreements": sum(
                row["b1_class_index"] == row["narrative_class_index"]
                and min(row["b1_confidence"], row["narrative_confidence"]) >= 80
                for row in chosen),
            "all_140_b1_correct": sum(
                row["b1_class_index"] == row["gt_class_index"] for row in rows),
            "all_140_narrative_correct": baseline_narrative_correct,
            "hypothetical_narrative_fallback": fallback,
            "decision_reason_counts": dict(sorted(Counter(
                row["decision_reason"] for row in chosen).items())),
            "reviewed_training_admissions": sum(
                row["frozen_training_class_index"] is not None for row in chosen),
            "total_frozen_training_admissions": sum(
                row["frozen_training_class_index"] is not None for row in rows),
            "post_hoc_exploratory": True,
            "no_new_provider_calls_in_evaluation": True,
            "GCN_training_runs": 0,
            "limitation": "R1_NEW_LIVE_COHORT_NOT_INDEPENDENT_HELDOUT; NO_GCN_CLAIM",
        },
        "owner_private_node_rows": rows,
    }


def run(frozen_root, authentic_root, r1_root, gateway_config, summary_sha,
        graph_file, audit_root):
    stage = "SAFE_PATH_PREFLIGHT"
    try:
        r1_root, audit_root, graph_file = map(
            _safe_path, (r1_root, audit_root, graph_file))
        _require(".local_artifacts" in r1_root.parts
                 and ".local_artifacts" in audit_root.parts
                 and audit_root.parent.is_dir()
                 and audit_root != r1_root
                 and audit_root not in r1_root.parents
                 and r1_root not in audit_root.parents)
        for p in (frozen_root, authentic_root, gateway_config, graph_file):
            path = _safe_path(p)
            _require(audit_root != path and audit_root not in path.parents
                     and path not in audit_root.parents)
        stage = "R1_LIVE_REPORT_AND_PROVENANCE"
        summary = _read_content_addressed(r1_root, ("journal",), summary_sha)
        _require(summary.get("schema") == CONTRACT
                 and summary.get("mode") == "LIVE_HTTPS"
                 and summary.get("router") == ROUTER
                 and summary.get("status") in (
                     "COMPLETE_LIVE_UNASSESSED", "BLOCKED_NO_AUTOMATIC_RETRY")
                 and summary.get("GT_accessed") is False
                 and summary.get("training_runs") == 0
                 and summary.get("no_training_label_for_routed_proposals") is True
                 and summary.get("selected_count") == BUDGET
                 and summary.get("denominator") == COHORT
                 and type(summary.get("attempted_calls")) is int
                 and 1 <= summary["attempted_calls"] <= 74
                 and type(summary.get("blind_completed")) is int
                 and 0 <= summary["blind_completed"] <= BUDGET
                 and type(summary.get("comparison_completed")) is int
                 and 0 <= summary["comparison_completed"] <=
                     summary["blind_completed"]
                 and (summary["status"] != "COMPLETE_LIVE_UNASSESSED"
                      or summary["blind_completed"] == BUDGET)
                 and summary.get("prompt_version") == RICH_PROMPT_V2
                 and summary.get("arbitration_version") == ARBITRATION_VERSION)
        report_sha = summary.get("private_report_sha256")
        report = _read_content_addressed(r1_root, ("journal",), report_sha)
        cfg_path = _safe_path(gateway_config)
        _require(cfg_path.is_file() and cfg_path.stat().st_size <= 16384)
        cfg = contract_from_dict(json.loads(cfg_path.read_text(encoding="utf-8")))
        inputs = load_project_inputs(frozen_root, authentic_root)
        selected, context = gateway_context(
            inputs, ROUTER, BUDGET, "sensitivity", cfg, fake=False)
        from ..sara3.experiment import digest
        _require(summary.get("gateway_context_sha256") == digest(context)
                 and summary.get("selected_node_ids") == list(selected)
                 and summary.get("requested_model") == cfg["model"]
                 and report.get("gateway_context_sha256") == digest(context)
                 and report.get("frozen_pairs_sha256") == frozen_pair_digest(inputs.pairs)
                 and report.get("source_hashes") == dict(inputs.provenance)
                 and report.get("router") == ROUTER
                 and report.get("selected_node_ids") == list(selected)
                 and report.get("target_count") == COHORT
                 and report.get("review_budget") == BUDGET
                 and report.get("prompt_version") == RICH_PROMPT_V2
                 and report.get("automated_arbitration_version") == ARBITRATION_VERSION
                 and report.get("gateway_runner_version") == CONTRACT
                 and report.get("data_kind") == "GAPGPT_LIVE_RAW_UNVERIFIED_SEMANTIC_L2"
                 and report.get("GT_accessed") is False
                 and report.get("training_runs") == 0
                 and type(report.get("provider_calls")) is int
                 and report["provider_calls"] == summary["attempted_calls"]
                 and len(report.get("decisions", [])) == COHORT)
        stage = "PINNED_GRAPH_GROUND_TRUTH"
        labels = _labels_from_original_graph(
            graph_file, _expected_graph_names(frozen_root))
        stage = "R1_GT_ONLY_NODE_JOURNEY"
        result = analyze(
            selected, report["decisions"],
            {pair.node_id: pair for pair in inputs.pairs},
            labels, status=summary["status"])
        result["source_graph_sha256"] = GRAPH_SHA256
        result["source_r1_run_sha256"] = report_sha
        result["source_r1_summary_sha256"] = summary_sha
        stage = "PRIVATE_OWNER_AUDIT"
        sha = PrivateAudit(audit_root).write(result)
        _require(PrivateAudit(audit_root).read(sha) == result)
        return {"status": "R1_REAL_GT_NODE_JOURNEY_VERIFIED_OWNER_PRIVATE",
                "artifact_sha256": sha, "relative_path": sha + ".json",
                "source_graph_sha256": GRAPH_SHA256,
                "source_run_sha256": report_sha,
                "aggregate": result["aggregate"]}
    except EvaluationStageError:
        raise
    except Exception:
        raise EvaluationStageError(stage) from None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("frozen-root", "authentic-root", "r1-root", "gateway-config",
                "graph-file", "audit-root"):
        p.add_argument("--" + arg, required=True, type=Path)
    p.add_argument("--summary-sha256", required=True)
    a = p.parse_args(argv)
    try:
        result = run(a.frozen_root, a.authentic_root, a.r1_root,
                     a.gateway_config, a.summary_sha256, a.graph_file,
                     a.audit_root)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True,
                         indent=2, allow_nan=False))
        return 0
    except EvaluationStageError as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "stage": exc.stage}),
              file=sys.stderr)
        return 1
    except Exception:
        print(json.dumps({"status": "FAIL_CLOSED"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
