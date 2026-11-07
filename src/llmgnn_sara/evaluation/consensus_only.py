"""Post-freeze GT-only consensus ablation. Descriptive, not a policy optimizer."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from ..io.frozen import read_pinned_json
from ..sara3 import consensus_only as policy
from ..sara3.audit import PrivateAudit
from ..sara3.correction_features import require
from ..sara3.experiment import digest
from . import evidence_arbitration_v3 as previous

DIAGNOSTIC_SHA = "434ea5402334ea086a31c9c49ff2242a965979bb042f1298a83d2b2fb850d867"


def validate_diagnostic(diagnostic, report, table):
    require(diagnostic["schema"] == "sara.consensus_source_audit.v1"
            and diagnostic["source_feature_sha256"] == policy.v3.base.FEATURE_SHA
            and diagnostic["semantic_status"] == "NOT_ASSESSED")
    cases = diagnostic["private_candidates"]
    switched = {(r["router"], r["node_id"]): r for r in report["rows"] if r["decision"] == "SWITCH_TO_AGENT"}
    sources = {(r["router"], r["node_id"]): r for r in table["rows"]}
    require(len(cases) == len(switched) and {(r["router"], r["node_id"]) for r in cases} == set(switched))
    for case in cases:
        key = case["router"], case["node_id"]
        require(case["third_class"] == switched[key]["third_class"]
                and case["shared_quote_count"] == sources[key]["shared_support"]
                and case["semantic_assessment"] == "NOT_ASSESSED")
        for phase in ("blind", "compare"):
            rich, source = case["rich_evidence"][phase], sources[key][phase]
            require(bool(rich["auxiliary_method_warning"]) == source["auxiliary_warning"]
                    and len(rich["counter_evidence"]) == source["counter_count"]
                    and len(rich["supporting_evidence"]) == source["support_count"]
                    and digest(rich["primary_topic"].strip().casefold()) == source["topic_digest"]
                    and case["provenance"][phase]["context_sha256"] == table["sources"][key[0]]["context_sha256"])
        require(case["topic_difference"] == policy.topic_difference(*(case["rich_evidence"][p]["primary_topic"] for p in ("blind", "compare"))))


def stratum(rows, truth):
    counts = Counter(previous.outcome(r["narrative_class"], r["label"], truth[r["node_id"]]) for r in rows)
    fixes, harms = counts["CORRECTED_BASELINE_ERROR"], counts["DAMAGED_CORRECT_BASELINE"]
    return {"denominator": len(rows), "fixes": fixes, "harms": harms, "net": fixes-harms,
            "both_wrong_after_switch": counts["BOTH_INCORRECT"], "outcomes": dict(counts)}


def evaluate(report, table, baseline, diagnostic, truth):
    policy.validate_report(report, table, baseline)
    validate_diagnostic(diagnostic, report, table)
    result = previous.summarize(report["rows"], truth)  # Validates truth dimensions/types.
    source = {(r["router"], r["node_id"]): r for r in table["rows"]}
    for router, summary in result["routers"].items():
        rows = [r for r in report["rows"] if r["router"] == router]
        selected = [r for r in rows if r["decision"] == "SWITCH_TO_AGENT"]
        flags = {"shared_quote": lambda r: (source[router, r["node_id"]]["shared_support"] or 0) > 0,
                 "third_class": lambda r: r["third_class"]}
        for phase in ("blind", "compare"):
            flags[phase+"_warning"] = lambda r, p=phase: source[router, r["node_id"]][p]["auxiliary_warning"]
            flags[phase+"_counter"] = lambda r, p=phase: source[router, r["node_id"]][p]["counter_count"] > 0
        flags["aggregate_warning"] = lambda r: bool(r["components"]["A"])
        flags["aggregate_counter"] = lambda r: bool(r["components"]["C"])
        summary["diagnostic_strata"] = {name: {"present": stratum([r for r in selected if f(r)], truth),
                                              "absent": stratum([r for r in selected if not f(r)], truth)} for name, f in flags.items()}
        summary["narrative_correct_selected"] = sum(r["narrative_class"] == truth[r["node_id"]] for r in rows)
        summary["ablation_correct_selected"] = sum(r["label"] == truth[r["node_id"]] for r in rows)
        summary["conclusion"] = ("POSITIVE_NET_HYPOTHESIS_REQUIRES_INDEPENDENT_DATA_NOT_TRAINING_AUTHORIZATION"
                                 if summary["net"] > 0 else "CONSENSUS_ALONE_NOT_RELIABLE_FOR_ARBITRATION_ON_THIS_EVIDENCE")
    return {"schema": "sara.evaluation.consensus_only.v1", "status": "EXPLORATORY_NOT_INDEPENDENT",
            "unique_nodes": 57, "shared_cohort_nodes": 17, "training_admissions": 0, "training_runs": 0,
            **result}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("report", "features", "base-report", "diagnostic", "graph", "frozen-root", "output"):
        p.add_argument("--"+name, type=Path, required=True)
    p.add_argument("--report-sha256", required=True)
    args = p.parse_args(argv)
    try:
        report = read_pinned_json(args.report, args.report_sha256)
        table = read_pinned_json(args.features, policy.v3.base.FEATURE_SHA)
        baseline = read_pinned_json(args.base_report, policy.v3.BASE_REPORT_SHA)
        require(report["diagnostic_sha256"] == DIAGNOSTIC_SHA)
        diagnostic = read_pinned_json(args.diagnostic, report["diagnostic_sha256"])
        policy.validate_report(report, table, baseline); validate_diagnostic(diagnostic, report, table)
        truth = previous.base_evaluation._labels_from_original_graph(args.graph, previous.base_evaluation._expected_graph_names(args.frozen_root))
        result = evaluate(report, table, baseline, diagnostic, truth)
        result.update(source_report_sha256=args.report_sha256, source_diagnostic_sha256=report["diagnostic_sha256"])
        require(".local_artifacts" in args.output.absolute().parts)
        store = PrivateAudit(args.output); sha = store.write(result); require(store.read(sha) == result)
        print(json.dumps({"outcome_sha256": sha, "status": result["status"], "routers": result["routers"]}))
        return 0
    except Exception:
        print('{"status":"FAIL_CLOSED"}', file=sys.stderr); return 1


if __name__ == "__main__": raise SystemExit(main())
