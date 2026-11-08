"""Separately invoked, GT-only Raw outcome analysis for Frozen Expanded Atlas.

Never trains, dispatches model calls, or modifies the GT-free vector freeze.
All node-level truth and predictions remain under local private ACLs.
"""
import argparse
import json
from pathlib import Path
import sys

from ..sara3.audit import PrivateAudit
from ..sara3.expanded_atlas_freeze import ROOT, validate_freeze
from .cora_gt_shadow import _labels_from_original_graph, _expected_graph_names
from .node_diagnostics import metrics, paired

VERSION = "sara.expanded_atlas.gt_only_raw.v1"
OLD_INVENTORY_SHA = "789a6aea4715c1e7537ede75d82f5e552859c392a0e27acd8cbbbc03b568da83"


def analyze(frozen, truth, old=None):
    validate_freeze(frozen)
    if len(truth) != 2708 or any(type(x) is not int or x < 0 or x >= 7 for x in truth):
        raise ValueError("Invalid held-out GT")
    vectors = {name: {r["node_id"]: r["class_index"] for r in rows}
               for name, rows in frozen["vectors"].items()}
    ids = set(vectors["C"])
    if old is not None:
        if type(old) is not dict or set(old) != ids or any(
                x is not None and (type(x) is not int or not 0 <= x < 7)
                for x in old.values()):
            raise ValueError("Historical old-Atlas vector mismatch")
        vectors["Old_V1_R1"] = old
    results = {name: metrics(p, truth) for name, p in vectors.items()}
    comparisons = {}
    for base in ("Narrative", "C", "Old_V1_R1"):
        if base in vectors:
            summary, _ = paired(vectors[base], vectors["Expanded_V1"], truth)
            comparisons[base + "_to_Expanded_V1"] = summary
    private = {
        "status": "GT_ONLY_EXPLORATORY_NOT_INDEPENDENT",
        "node_outcomes": [
            {"node_id": node, "ground_truth": truth[node],
             "predictions": {name: vector[node] for name, vector in vectors.items()}}
            for node in sorted(ids)],
    }
    public = {
        "schema": VERSION, "status": "EXPLORATORY_NOT_INDEPENDENT",
        "source_freeze_sha256": frozen["source_summary_sha256"],
        "raw_metrics": results, "paired_comparisons": comparisons,
        "training_runs": 0, "independent_holdout": False,
    }
    return public, private


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--freeze-sha256", required=True)
    args = p.parse_args(argv)
    try:
        freeze = PrivateAudit(ROOT / "expanded_atlas_freeze_v1").read(args.freeze_sha256)
        validate_freeze(freeze)  # Must validate before opening GT.
        old_package = PrivateAudit(ROOT / "expanded_gcn_inventory_v1").read(
            OLD_INVENTORY_SHA)
        old_rows = old_package["arms"]["V1_r1_v1"]
        old = {r["node_id"]: r["final_class"] for r in old_rows}
        if len(old_rows) != 140 or len(old) != 140:
            raise ValueError("Old Atlas cohort mismatch")
        truth = _labels_from_original_graph(
            ROOT / "gt_reference" / "cora_random_sbert.pt",
            _expected_graph_names(ROOT / "frozen"))
        aggregate, private = analyze(freeze, truth, old)
        aggregate["freeze_sha256"] = args.freeze_sha256
        aggregate["old_inventory_sha256"] = OLD_INVENTORY_SHA
        store = PrivateAudit(ROOT / "expanded_atlas_raw_evaluation_v1")
        private_sha = store.write(private)
        aggregate["private_node_outcomes_sha256"] = private_sha
        aggregate_sha = store.write(aggregate)
        if store.read(private_sha) != private or store.read(aggregate_sha) != aggregate:
            raise ValueError("Raw evaluation audit mismatch")
        output = {
            "status": aggregate["status"], "aggregate_sha256": aggregate_sha,
            "raw": {name: {
                "counts": val["counts"],
                "coverage": val["coverage"],
                "selective_accuracy": val["selective_accuracy"],
            } for name, val in aggregate["raw_metrics"].items()},
            "comparison": {
                name: {
                    "wrong_to_correct": val["states"].get("WRONG__CORRECT", 0),
                    "correct_to_wrong": val["states"].get("CORRECT__WRONG", 0),
                    "correct_to_abstain": val["states"].get("CORRECT__ABSTAINED", 0),
                    "wrong_to_abstain": val["states"].get("WRONG__ABSTAINED", 0),
                } for name, val in aggregate["paired_comparisons"].items()},
            "training_runs": 0,
        }
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception:
        print('{"status":"FAIL_CLOSED_GT_ONLY"}', file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
