"""Separate post-freeze GT-only comparison; never used by the shadow runtime."""
import argparse
import copy
import json
from pathlib import Path
import sys

from ..io.frozen import read_pinned_json
from ..sara3.audit import PrivateAudit
from ..sara3.correction_features import require
from ..sara3.experiment import digest
from ..sara3 import graph_support_coverage as shadow
from ..sara3 import weighted_arbitration_v2 as base
from . import weighted_arbitration_v2 as evaluator


def project(report, table, baseline):
    """Reuse V2 scoring/evaluation unchanged, after validating variant bindings."""
    evaluator.validate_report(baseline, table)
    require(report["schema"] == shadow.VERSION and report["contract"] == shadow.CONTRACT
            and report["rule_sha256"] == digest(shadow.CONTRACT)
            and report["base_report_sha256"] == shadow.BASE_REPORT_SHA
            and report["graph_provenance"] == baseline["graph_provenance"]
            and len(report["rows"]) == len(baseline["rows"]))
    prior = {(r["router"], r["node_id"]): r for r in baseline["rows"]}
    for row in report["rows"]:
        require(row["policy_version"] == shadow.VERSION)
        old = prior[row["router"], row["node_id"]]
        require({k: v for k, v in row["support"].items() if k != "N"} ==
                {k: v for k, v in old["support"].items() if k != "N"})
    projected = copy.deepcopy(report)
    projected["schema"] = base.VERSION
    projected["rule_sha256"] = digest({"version": base.VERSION, "config": report["config"]})
    for row in projected["rows"]: row["policy_version"] = base.VERSION
    evaluator.validate_report(projected, table)
    return projected


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("report", "base-report", "features", "graph", "frozen-root", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--report-sha256", required=True)
    args = p.parse_args(argv)
    try:
        report = read_pinned_json(args.report, args.report_sha256)
        baseline = read_pinned_json(args.base_report, shadow.BASE_REPORT_SHA)
        table = read_pinned_json(args.features, base.FEATURE_SHA)
        projected = project(report, table, baseline)  # BEFORE any GT read.
        truth = evaluator._labels_from_original_graph(args.graph, evaluator._expected_graph_names(args.frozen_root))
        result = {"schema": "sara.evaluation.graph_support.v1", "status": "EXPLORATORY_NOT_INDEPENDENT",
                  "source_report_sha256": args.report_sha256,
                  "base_report_sha256": shadow.BASE_REPORT_SHA,
                  "variant": evaluator.evaluate(projected, table, truth),
                  "original_v2": evaluator.evaluate(baseline, table, truth)}
        require(".local_artifacts" in args.output.absolute().parts)
        store = PrivateAudit(args.output); sha = store.write(result); require(store.read(sha) == result)
        print(json.dumps({"artifact_sha256": sha, "status": result["status"],
                          "variant_routers": result["variant"]["routers"],
                          "original_v2_routers": result["original_v2"]["routers"]}))
        return 0
    except Exception:
        print('{"status":"FAIL_CLOSED"}', file=sys.stderr); return 1


if __name__ == "__main__": raise SystemExit(main())
