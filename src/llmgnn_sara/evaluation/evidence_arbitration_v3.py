"""Separate post-freeze GT-only evaluation of V3 and unchanged controls."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from ..io.frozen import read_pinned_json
from ..sara3.audit import PrivateAudit
from ..sara3.correction_features import require
from ..sara3 import evidence_arbitration_v3 as policy
from . import weighted_arbitration_v2 as base_evaluation
from . import graph_support_coverage as direct_evaluation
from .correction_outcomes import outcome

DIRECT_SHA = "71c9b21516f18b7bf16d2f6f6e773a7a0168aca6e1c488fb66641c013765a64b"


def summarize(rows, truth):
    result, events = {}, []
    require(len(truth) == 2708 and all(type(v) is int and 0 <= v < 7 for v in truth))
    for router in ("r0", "r1_v1"):
        actions, reasons, outcomes, switched, third = (Counter() for _ in range(5))
        for row in (r for r in rows if r["router"] == router):
            kind = outcome(row["narrative_class"], row["label"], truth[row["node_id"]])
            actions[row["decision"]] += 1; outcomes[kind] += 1
            if row["decision"] == "SWITCH_TO_AGENT":
                switched[kind] += 1
                if row.get("third_class"): third[kind] += 1
            else: reasons[row["reason"]] += 1
            events.append({"router": router, "node_id": row["node_id"], "outcome": kind,
                           "decision": row["decision"]})
        require(sum(actions.values()) == 37)
        fixes, harms = switched["CORRECTED_BASELINE_ERROR"], switched["DAMAGED_CORRECT_BASELINE"]
        result[router] = {"denominator": 37, "switches": actions["SWITCH_TO_AGENT"],
                          "fixes": fixes, "harms": harms, "net": fixes-harms,
                          "third_class_switches": sum(third.values()), "third_class_outcomes": dict(third),
                          "switch_coverage": actions["SWITCH_TO_AGENT"]/37,
                          "decisions": dict(actions), "keep_or_invalid_reasons": dict(reasons),
                          "outcomes": dict(outcomes), "switch_outcomes": dict(switched)}
    return {"routers": result, "private_events": events}


def evaluate(report, table, baseline, direct, truth):
    policy.validate_report(report, table, baseline)
    base_evaluation.validate_report(baseline, table)
    direct_evaluation.project(direct, table, baseline)
    v1 = [{"router": r["router"], "node_id": r["node_id"], "narrative_class": r["narrative_class"],
           "label": r["blind"]["class_index"] if r["shadow_decision"] == "SHADOW_PROPOSE" else r["narrative_class"],
           "decision": "SWITCH_TO_AGENT" if r["shadow_decision"] == "SHADOW_PROPOSE" else "KEEP_NARRATIVE",
           "reason": r["v1_reason"], "third_class": False} for r in table["rows"]]
    return {"schema": "sara.evaluation.evidence_v3.v1", "status": "EXPLORATORY_NOT_INDEPENDENT",
            "source_rule_sha256": report["rule_sha256"], "unique_nodes": 57, "shared_nodes": 17,
            "v3": summarize(report["rows"], truth), "v1": summarize(v1, truth),
            "weighted_v2": summarize(baseline["rows"], truth), "direct_seed": summarize(direct["rows"], truth),
            "training_admissions": 0, "training_runs": 0}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("report", "features", "base-report", "direct-report", "graph", "frozen-root", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--report-sha256", required=True)
    args = p.parse_args(argv)
    try:
        report = read_pinned_json(args.report, args.report_sha256)
        table = read_pinned_json(args.features, policy.base.FEATURE_SHA)
        baseline = read_pinned_json(args.base_report, policy.BASE_REPORT_SHA)
        direct = read_pinned_json(args.direct_report, DIRECT_SHA)
        policy.validate_report(report, table, baseline)
        base_evaluation.validate_report(baseline, table)
        direct_evaluation.project(direct, table, baseline)  # All bindings BEFORE GT.
        truth = base_evaluation._labels_from_original_graph(args.graph, base_evaluation._expected_graph_names(args.frozen_root))
        result = evaluate(report, table, baseline, direct, truth)
        result.update(source_report_sha256=args.report_sha256, source_direct_report_sha256=DIRECT_SHA,
                      source_baseline_sha256=policy.BASE_REPORT_SHA, source_feature_sha256=policy.base.FEATURE_SHA)
        require(".local_artifacts" in args.output.absolute().parts)
        store = PrivateAudit(args.output); sha = store.write(result); require(store.read(sha) == result)
        print(json.dumps({"outcome_sha256": sha, "status": result["status"],
                          "policies": {p: result[p]["routers"] for p in ("v3", "v1", "weighted_v2", "direct_seed")}}))
        return 0
    except Exception:
        print('{"status":"FAIL_CLOSED"}', file=sys.stderr); return 1


if __name__ == "__main__": raise SystemExit(main())
