"""Separately invoked GT-only scoring AFTER the weighted score freeze."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from ..io.frozen import read_pinned_json
from ..sara3.audit import PrivateAudit
from ..sara3.experiment import digest
from ..sara3.correction_features import validate, require
from ..sara3.weighted_arbitration_v2 import VERSION, CONFIG_SHA, FEATURE_SHA, decide
from .correction_outcomes import outcome
from .cora_gt_shadow import _labels_from_original_graph, _expected_graph_names, GRAPH_SHA256


def validate_report(report, table):
    validate(table)
    require(report["schema"] == VERSION and digest(report["config"]) == CONFIG_SHA
            and report["source_feature_sha256"] == FEATURE_SHA and report["training_admissions"] == 0
            and report["graph_provenance"]["graph_sha256"] == GRAPH_SHA256
            and report["graph_provenance"]["label_storage_read"] is False
            and report["rule_sha256"] == digest({"version": VERSION, "config": report["config"]}))
    indexed = {(r["router"], r["node_id"]): r for r in table["rows"]}
    require(len(report["rows"]) == 74 and len({(r["router"], r["node_id"]) for r in report["rows"]}) == 74)
    require({(r["router"], r["node_id"]) for r in report["rows"]} == set(indexed))
    for row in report["rows"]:
        source = indexed[row["router"], row["node_id"]]
        expected = decide(source, {k: row["support"][k] for k in ("P", "N")}, report["config"])
        require(all(row.get(k) == v for k, v in expected.items())
                and row["narrative_class"] == source["narrative_class"] and row["training_eligible"] is False)
    return indexed


def evaluate(report, table, truth):
    indexed = validate_report(report, table)
    require(len(truth) == 2708 and all(type(v) is int and 0 <= v < 7 for v in truth))
    aggregate, events = {}, []
    for router in ("r0", "r1_v1"):
        counts, actions = Counter(), Counter()
        third, sparse, density = Counter(), Counter(), Counter()
        baseline_correct, treatment_correct = 0, 0
        for r in (r for r in report["rows"] if r["router"] == router):
            source = indexed[router, r["node_id"]]
            recomputed = decide(source, {k: r["support"][k] for k in ("P", "N")}, report["config"])
            require(all(r.get(k) == v for k, v in recomputed.items()) and r["training_eligible"] is False)
            target = truth[r["node_id"]]
            category = outcome(r["narrative_class"], r["label"], target)
            actions[r["decision"]] += 1; counts[category] += 1
            baseline_correct += r["narrative_class"] == target
            treatment_correct += r["label"] == target
            switched = r["decision"] == "SWITCH_TO_AGENT"
            if r["third_class"]: third["candidate"] += 1; third["switches"] += switched
            if r["support"]["P"] is None: sparse["prototype_unknown"] += 1; sparse["switches"] += switched
            if r["support"].get("neighborhood_density") is None or r["support"].get("neighborhood_density", 0) < report["config"]["neighbor_density_min"]:
                density["low_or_unknown_density"] += 1; density["switches"] += switched
            events.append({"router": router, "node_id": r["node_id"], "outcome": category,
                           "decision": r["decision"]})
        require(sum(actions.values()) == 37)
        aggregate[router] = {"denominator": 37, "decisions": dict(actions), "outcomes": dict(counts),
                             "baseline_correct": baseline_correct, "experimental_correct": treatment_correct,
                             "net_change": treatment_correct-baseline_correct, "third_class": dict(third),
                             "scarce_or_unavailable_prototype": dict(sparse), "density": dict(density),
                             "switch_coverage": actions["SWITCH_TO_AGENT"]/37,
                             "v1_switches": sum(r["shadow_decision"] == "SHADOW_PROPOSE" for r in table["rows"] if r["router"] == router)}
    return {"schema": "sara.evaluation.weighted_v2.v1", "status": "EXPLORATORY_NOT_INDEPENDENT",
            "routers": aggregate, "shared_nodes": 17, "unique_nodes": 57,
            "private_events": events, "training_runs": 0, "training_admissions": 0}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("report", "features", "graph", "frozen-root", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--report-sha256", required=True)
    args = p.parse_args(argv)
    try:
        report = read_pinned_json(args.report, args.report_sha256)
        table = read_pinned_json(args.features, FEATURE_SHA)
        validate_report(report, table)  # Reject corrupted scores/admission BEFORE opening GT.
        truth = _labels_from_original_graph(args.graph, _expected_graph_names(args.frozen_root))
        result = evaluate(report, table, truth)
        result.update(source_report_sha256=args.report_sha256, source_graph_sha256=GRAPH_SHA256)
        require(".local_artifacts" in args.output.absolute().parts)
        audit = PrivateAudit(args.output); sha = audit.write(result); require(audit.read(sha) == result)
        print(json.dumps({"artifact_sha256": sha, "status": result["status"], "routers": result["routers"]}))
        return 0
    except Exception:
        print('{"status":"FAIL_CLOSED"}', file=sys.stderr); return 1


if __name__ == "__main__": raise SystemExit(main())
