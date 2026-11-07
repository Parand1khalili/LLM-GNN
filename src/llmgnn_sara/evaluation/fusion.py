"""Separate GT-only label-quality evaluation of ONE vector per fusion arm."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from ..io.frozen import read_pinned_json
from ..io.project import load_project_inputs
from ..sara3 import fusion
from ..sara3.audit import PrivateAudit
from ..sara3.correction_features import require
from .cora_gt_shadow import _labels_from_original_graph, _expected_graph_names
from .correction_outcomes import outcome
from .metrics import matched_summary


def quality(rows, truth):
    accepted = [r for r in rows if r["final_class"] is not None]
    correct = sum(r["final_class"] == truth[r["node_id"]] for r in accepted)
    f1s = []
    for k in range(7):
        tp = sum(r["final_class"] == k and truth[r["node_id"]] == k for r in accepted)
        fp = sum(r["final_class"] == k and truth[r["node_id"]] != k for r in accepted)
        fn = sum(r["final_class"] != k and truth[r["node_id"]] == k for r in accepted)
        f1s.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.0)
    return {**fusion.summarize(rows), "cohort_size": len(rows), "correct_accepted": correct,
            "selective_accuracy_percent": 100*correct/len(accepted) if accepted else None,
            "correct_per_cohort_percent": 100*correct/len(rows),
            "macro_f1_accepted_only_7_classes": sum(f1s)/7 if accepted else None,
            "metric_scope": "PSEUDO_LABEL_QUALITY_NOT_GCN_ACCURACY"}


def reference_outcomes(rows, truth, reference):
    counts = Counter(outcome(r[reference], r["final_class"], truth[r["node_id"]]) for r in rows)
    return {"denominator": len(rows), "outcomes": dict(counts),
            "changed_nonabstaining": sum(r["final_class"] is not None and r["final_class"] != r[reference] for r in rows),
            "fixes": counts["CORRECTED_BASELINE_ERROR"], "harms": counts["DAMAGED_CORRECT_BASELINE"],
            "net": counts["CORRECTED_BASELINE_ERROR"]-counts["DAMAGED_CORRECT_BASELINE"],
            "abstentions_not_counted_as_harm": counts["NO_CLASS_PREDICTION"]}


def evaluate(report, truth):
    require(len(truth) == 2708 and all(type(k) is int and 0 <= k < 7 for k in truth))
    results, events = {}, []
    for cohort in ("sensitivity", "primary"):
        excluded = set(report["primary_excluded_ids"]) if cohort == "primary" else set()
        results[cohort] = {}
        for arm, all_rows in report["arms"].items():
            rows = [r for r in all_rows if r["node_id"] not in excluded]
            agent = [r for r in rows if r["label_source"].startswith("AGENT3")]
            thirds = [r for r in agent if r["third_class"]]
            results[cohort][arm] = {**quality(rows, truth),
                "all_final_vs_references": {k: reference_outcomes(rows, truth, k) for k in ("b1_class", "narrative_class")},
                "agent3_selected_vs_references": {k: reference_outcomes(agent, truth, k) for k in ("b1_class", "narrative_class")},
                "third_class_vs_references": {k: reference_outcomes(thirds, truth, k) for k in ("b1_class", "narrative_class")}}
            for r in rows:
                events.append({"cohort": cohort, "arm": arm, "node_id": r["node_id"],
                               "outcome_vs_narrative": outcome(r["narrative_class"], r["final_class"], truth[r["node_id"]])})
    return {"schema": "sara.evaluation.three_agent_fusion.v1", "status": "EXPLORATORY_NOT_INDEPENDENT",
            "results": results, "private_events": events, "shared_routed_nodes": 17,
            "reference_comparisons_are_not_separate_pipelines": True, "training_runs": 0, "training_admissions": 0}


def paired_seed_summary(control, treatment):
    """Prepared aggregator; actual GCN results must first be receipt-verified."""
    require(set(control) == set(treatment) == set(range(10)))
    result = matched_summary(control, treatment)
    return {"seeds": result["seeds"], "control": result["b1_accuracy_percent"],
            "treatment": result["narrative_accuracy_percent"], "paired_delta_pp": result["paired_delta_pp"],
            "per_seed_delta_pp": result["per_seed_delta_pp"], "uncertainty_scope": result["uncertainty_scope"]}


def public_summary(result, grid, outcome_sha, grid_sha):
    """Explicit aggregate allowlist. No article, node IDs, masks or receipts."""
    fields = ("cohort_size", "accepted", "abstained", "coverage", "correct_accepted", "selective_accuracy_percent",
              "correct_per_cohort_percent", "macro_f1_accepted_only_7_classes", "class_distribution", "label_sources",
              "relative_to_C", "disagreement_resolution", "third_class", "agent3_selected",
              "all_final_vs_references", "agent3_selected_vs_references", "third_class_vs_references")
    return {"schema": "sara.public.three_agent_fusion.v1", "status": result["status"],
            "source_fusion_sha256": result["source_fusion_sha256"], "source_outcome_sha256": outcome_sha,
            "source_grid_sha256": grid_sha, "shared_routed_nodes": 17,
            "label_quality": {c: {a: {k: v[k] for k in fields} for a, v in arms.items()} for c, arms in result["results"].items()},
            "gcn_config": grid["config"], "gcn_status": "NOT_RUN_BLOCKED", "training_runs": 0, "training_admissions": 0,
            "unique_planned_fit_specs": len(grid["unique_fit_specs"]), "unique_planned_seed_fits": grid["unique_planned_seed_fits"],
            "gcn_matrix": [{**{k: row[k] for k in ("arm", "cohort", "loss", "PS", "mask_mode", "status")},
                            "planned_train_count": len(row["train_ids"]) if row["status"] == "DRAFT_NOT_ADMITTED" else None,
                            "accuracy": None, "macro_f1": None, "paired_delta": None, "mean": None, "sd": None,
                            "per_seed_results": []} for row in grid["plans"]]}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("fusion", "features", "frozen-root", "authentic-root", "graph", "output"):
        p.add_argument("--"+name, type=Path, required=True)
    p.add_argument("--fusion-sha256", required=True)
    p.add_argument("--grid", type=Path)
    p.add_argument("--grid-sha256")
    p.add_argument("--public-summary", type=Path)
    a = p.parse_args(argv)
    try:
        report = read_pinned_json(a.fusion, a.fusion_sha256)
        inputs = load_project_inputs(a.frozen_root, a.authentic_root)
        table = read_pinned_json(a.features, fusion.FEATURE_SHA)
        fusion.validate_report(report, table, inputs)  # Before opening GT.
        truth = _labels_from_original_graph(a.graph, _expected_graph_names(a.frozen_root))
        result = evaluate(report, truth); result.update(source_fusion_sha256=a.fusion_sha256, source_rule_sha256=report["rule_sha256"])
        require(".local_artifacts" in a.output.absolute().parts); store = PrivateAudit(a.output)
        sha = store.write(result); require(store.read(sha) == result)
        if a.public_summary is not None:
            grid = read_pinned_json(a.grid, a.grid_sha256)
            require(grid["fusion_sha256"] == a.fusion_sha256)
            target = a.public_summary.absolute()
            require(target.parent == Path(__file__).resolve().parents[3]/"reports" and not target.is_symlink())
            blob = (json.dumps(public_summary(result, grid, sha, a.grid_sha256), sort_keys=True, indent=2, allow_nan=False)+"\n").encode()
            if target.exists(): require(target.read_bytes() == blob)
            else:
                with target.open("xb") as stream: stream.write(blob)
        print(json.dumps({"outcome_sha256": sha, "status": result["status"],
                          "summary": {k: {f: v[f] for f in ("accepted", "abstained", "correct_accepted", "selective_accuracy_percent",
                            "macro_f1_accepted_only_7_classes", "agent3_selected_vs_references")} for k, v in result["results"]["sensitivity"].items()}}))
        return 0
    except Exception:
        print('{"status":"FAIL_CLOSED"}', file=sys.stderr); return 1


if __name__ == "__main__": raise SystemExit(main())
