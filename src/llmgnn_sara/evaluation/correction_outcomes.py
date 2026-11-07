"""Separate-process post-hoc evaluator. Never imported by runtime or extraction."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

from ..io.frozen import read_pinned_json
from ..sara3.audit import PrivateAudit
from ..sara3.correction_features import validate
from .cora_gt_shadow import _labels_from_original_graph, _expected_graph_names, GRAPH_SHA256

STATUS = "EXPLORATORY_NOT_INDEPENDENT"
OUTCOMES = ("CORRECTED_BASELINE_ERROR", "DAMAGED_CORRECT_BASELINE", "BOTH_CORRECT",
            "BOTH_INCORRECT", "NO_CLASS_PREDICTION")


def outcome(base, predicted, truth):
    if predicted is None:
        return OUTCOMES[4]
    if base == truth:
        return OUTCOMES[2] if predicted == truth else OUTCOMES[1]
    return OUTCOMES[0] if predicted == truth else OUTCOMES[3]


def analyze(table, truth):
    validate(table)
    if len(truth) != 2708 or any(type(y) is not int or not 0 <= y < 7 for y in truth):
        raise ValueError("Invalid evaluator-only truth")
    counts = defaultdict(Counter); distributions = defaultdict(lambda: defaultdict(Counter))
    private = []
    for row in table["rows"]:
        node, router = row["node_id"], row["router"]
        if not 0 <= node < 2708: raise ValueError("Node alignment failure")
        labels = {}
        for baseline in ("b1", "narrative"):
            for phase in ("blind", "compare"):
                name = baseline + "_to_" + phase
                labels[name] = outcome(row[baseline + "_class"], row[phase]["class_index"], truth[node])
                counts[router + ":" + name][labels[name]] += 1
        category = labels["narrative_to_blind"]
        measured = {k: v for k, v in row.items() if k not in ("node_id", "router", "blind", "compare")}
        for phase in ("blind", "compare"):
            measured.update({phase + "." + k: v for k, v in row[phase].items() if k != "quote_lengths"})
        for feature, value in measured.items():
            distributions[router + ":" + feature]["MISSING" if value is None else str(value)][category] += 1
        private.append({"router": router, "node_id": node, "outcomes": labels})
    aggregate = {"status": STATUS, "observations": 74, "unique_nodes": 57,
                 "paired_outcomes": {k: {o: c[o] for o in OUTCOMES} for k, c in counts.items()},
                 "feature_distributions": {k: {v: {"count": sum(c.values()),
                    "router_denominator": 37, "outcomes": dict(c)} for v, c in values.items()}
                    for k, values in distributions.items()},
                 "independence": "17_SHARED_NODES_NOT_INDEPENDENT_ROUTER_SAMPLES",
                 "training_runs": 0, "training_admissions": 0}
    return {"aggregate": aggregate, "private_events": private}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("feature-file", "graph-file", "frozen-root", "output"):
        p.add_argument("--" + arg, type=Path, required=True)
    p.add_argument("--feature-sha256", required=True)
    args = p.parse_args(argv)
    try:
        table = read_pinned_json(args.feature_file, args.feature_sha256)
        validate(table)  # Feature freeze is admitted BEFORE opening any GT.
        truth = _labels_from_original_graph(args.graph_file, _expected_graph_names(args.frozen_root))
        result = analyze(table, truth)
        result.update(source_feature_sha256=args.feature_sha256, source_graph_sha256=GRAPH_SHA256)
        if ".local_artifacts" not in args.output.absolute().parts: raise ValueError("Private output required")
        audit = PrivateAudit(args.output); sha = audit.write(result)
        if audit.read(sha) != result: raise ValueError("Audit mismatch")
        print(json.dumps({"artifact_sha256": sha, **{k: result["aggregate"][k] for k in
                          ("status", "observations", "unique_nodes", "paired_outcomes")}}, sort_keys=True))
        return 0
    except Exception:
        print('{"status":"FAIL_CLOSED"}', file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
