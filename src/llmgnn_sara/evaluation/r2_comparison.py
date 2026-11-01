"""Offline descriptive hybrid comparisons, no verifier/GT/human review access."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from ..io.project import load_project_inputs
from ..sara2.policy import risk, route_r0
from ..sara3.atlas import route_semantic, semantic_risk
from ..sara3.r1_candidate import VERSION as R1_V1, BUDGET, risk_terms, route_r1_candidate
from ..sara3.r1_coverage import VERSION as R1_V2, coverage_terms, policy_score, route_r1_candidate_v2
from ..sara3.r2_candidate import VERSION, ALLOCATIONS, select_r2, route_r2_candidate
from .router_comparison import compare_routers, distribution


def compare_r2(inputs):
    rows = inputs.pairs
    by_id = {p.node_id: p for p in rows}
    coverage = {p.node_id: coverage_terms(p) for p in rows}
    selectors = {"r0_current": lambda ps: route_r0(ps, BUDGET),
                 "semantic_v0_current": lambda ps: route_semantic(ps, BUDGET),
                 R1_V1: route_r1_candidate, R1_V2: route_r1_candidate_v2,
                 VERSION: route_r2_candidate}
    selections = {name: select(rows) for name, select in selectors.items()}
    stable = {name: selections[name] == select(reversed(rows)) for name, select in selectors.items()}
    if not all(stable.values()):
        raise ValueError("Router input-order stability failed")

    def summary(ids):
        chosen = [by_id[node] for node in ids]
        return {"count": len(ids), "selected_node_ids": list(ids),
            "coverage_counts": dict(sorted(Counter(coverage[p.node_id]["status"] for p in chosen).items())),
            "zero_match_count": sum(coverage[p.node_id]["coverage"] == 0 for p in chosen),
            "disagreement_count": sum(not p.agrees for p in chosen),
            "hh_agreement_at_reconstructed_80": sum(p.agrees and min(p.b1.confidence,
                p.narrative_v0.confidence) >= 80 for p in chosen),
            "r0_score_selected": distribution([risk(p) for p in chosen]),
            "r1_v2_observed_risk_selected": distribution([float(policy_score(p, R1_V2)) for p in chosen])}

    results = {name: summary(ids) for name, ids in selections.items()}
    keys = {"r0_current": lambda p: (-risk(p),),
            "semantic_v0_current": lambda p: (-semantic_risk(p),),
            R1_V1: lambda p: (-risk_terms(p)["score"],),
            R1_V2: lambda p: (-policy_score(p, R1_V2), -coverage[p.node_id]["coverage"])}
    for name, key in keys.items():
        ranked = sorted(rows, key=lambda p: (*key(p), p.node_id))
        cutoff = key(ranked[BUDGET - 1])
        results[name]["cutoff"] = {"key_without_node_id": [str(v) for v in cutoff],
            "tied_node_ids": [p.node_id for p in ranked if key(p) == cutoff],
            "selected_from_tie": [p.node_id for p in ranked[:BUDGET] if key(p) == cutoff],
            "at_budget36_removed_id": ranked[36].node_id,
            "at_budget38_added_id": ranked[37].node_id if len(ranked) > 37 else None}
    scenarios = {}
    primary = set(selections[VERSION])
    for allocation in ALLOCATIONS:
        result = select_r2(rows, allocation)
        if result != select_r2(reversed(rows), allocation):
            raise ValueError("R2 sensitivity input-order stability failed")
        ids = result["selected_node_ids_admission_order"]
        scenarios["/".join(map(str, allocation))] = {**summary(ids), "selection": result,
            "overlap_with_primary": len(primary & set(ids)),
            "added_vs_primary": sorted(set(ids) - primary), "removed_vs_primary": sorted(primary - set(ids)),
            "input_order_stable": True}
    results[VERSION]["selection"] = scenarios["4/17/16"]["selection"]
    names = list(results)
    provenance = compare_routers(inputs)
    return {"schema_version": "sara.r2_comparison.v1", "status": "RECONSTRUCTED_DESCRIPTIVE_ONLY",
        "cohort_size": len(rows), "budget": BUDGET, "source_hashes": dict(inputs.provenance),
        "atlas_sha256": provenance["atlas_sha256"],
        "design_sha256": hashlib.sha256((Path(__file__).resolve().parents[3] / "docs/R2_CANDIDATE.md").read_bytes()).hexdigest(),
        "routers": results, "input_order_stability": stable,
        "pairwise_overlaps": {a + " / " + b: len(set(selections[a]) & set(selections[b]))
                               for i, a in enumerate(names) for b in names[i+1:]},
        "r2_sensitivity": scenarios, "hh_definition": "Agreement and both frozen confidence>=80; reconstructed convention",
        "selection_order": "Baselines: own risk ranking; R2: stage admission order, no global risk score",
        "ground_truth_accessed": False, "human_review_accessed": False,
        "provider_calls": 0, "training_runs": 0, "production_or_pilot_freeze": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-root", required=True)
    parser.add_argument("--authentic-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = compare_r2(load_project_inputs(args.frozen_root, args.authentic_root))
    with Path(args.output).open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
