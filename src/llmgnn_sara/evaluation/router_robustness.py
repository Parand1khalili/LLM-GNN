"""Review-only seed/order counterfactuals; never changes production routers."""
import argparse
import hashlib
from itertools import permutations
import json
from pathlib import Path

from ..io.frozen import reject_gt
from ..io.project import load_project_inputs
from ..sara2.policy import CLASSES, risk, route_r0, validated_pairs
from ..sara3.r1_candidate import BUDGET
from ..sara3.r1_coverage import VERSION as R1_VERSION, coverage_terms, policy_score, rank_policy
from ..sara3.r2_candidate import VERSION, exploration_key, select_r2
from ..sara3.inputs import canonical_bytes, pair_inputs
from ..sara3.rich_evidence import rich_verifier_input
from .r2_comparison import compare_r2

SEEDS = ("primary", "review-1", "review-2", "review-3")
STAGES = ("unknown_exploration", "observed_risk", "candidate_risk")
ORDERS = tuple(permutations(STAGES))


def review_selection(pairs, seed="primary", order=STAGES):
    if seed not in SEEDS or order not in ORDERS:
        raise ValueError("Use prespecified review seeds/orders")
    rows = validated_pairs(pairs)
    if len(rows) < BUDGET:
        raise ValueError("Review requires at least37 nodes")
    by_id = {p.node_id: p for p in rows}
    coverage = {p.node_id: coverage_terms(p)["coverage"] for p in rows}
    def hashed(node):
        return exploration_key(node) if seed == "primary" else hashlib.sha256(
            f"{VERSION}:explore:{seed}:{node}".encode("utf-8")).hexdigest()
    keys = {"unknown_exploration": lambda n: (hashed(n),),
            "observed_risk": lambda n: (-policy_score(by_id[n], R1_VERSION), -coverage[n]),
            "candidate_risk": lambda n: (-risk(by_id[n]),)}
    pools = {"unknown_exploration": sorted((n for n in by_id if not coverage[n]), key=lambda n: (hashed(n), n)),
             "observed_risk": [n for n in rank_policy(rows, R1_VERSION) if coverage[n]],
             "candidate_risk": list(route_r0(rows, len(rows)))}
    quotas = dict(zip(STAGES, (4, 17, 16)))
    selected, seen, stages = [], set(), []
    for stage in (*order, "backfill_candidate_risk"):
        origin = "candidate_risk" if stage == "backfill_candidate_risk" else stage
        pool = pools[origin]
        quota = BUDGET - len(selected) if stage == "backfill_candidate_risk" else quotas[stage]
        eligible = [n for n in pool if n not in seen]
        chosen = eligible[:quota]
        cutoff = keys[origin](chosen[-1]) if chosen else None
        stages.append({"stage": stage, "requested": quota, "pool_size": len(pool),
            "overlap_skipped": len(pool) - len(eligible), "available": len(eligible),
            "admitted_node_ids": chosen, "shortfall": quota - len(chosen),
            "cutoff_key_without_node_id": [str(v) for v in cutoff] if cutoff is not None else None,
            "cutoff_tied_ids": [n for n in eligible if keys[origin](n) == cutoff] if chosen else [],
            "next_eligible_node_id": eligible[len(chosen)] if len(eligible) > len(chosen) else None})
        selected.extend(chosen)
        seen.update(chosen)
    if len(selected) != BUDGET or len(seen) != BUDGET:
        raise ValueError("Review selection invariant failed")
    return {"router_version": VERSION, "allocation": [4, 17, 16],
            "selected_node_ids_admission_order": selected, "stages": stages}


def request_fingerprints(pair):
    legacy = pair_inputs(pair)
    rich = (rich_verifier_input(pair.node_id, pair.text, pair.neighborhood),
            rich_verifier_input(pair.node_id, pair.text, pair.neighborhood,
                candidates=(pair.b1.class_index, pair.narrative_v0.class_index),
                blind_class="$BLIND_CLASS_INDEX"))
    result = {}
    for version, payloads in (("legacy", legacy), ("rich_v1", rich)):
        blind, comparison = payloads
        reject_gt(blind)
        reject_gt(comparison)
        if any(k in blind for k in ("historical_candidates", "blind_class_index", "confidence", "b1", "narrative_v0")):
            raise ValueError("Blind input boundary failed")
        result[version] = {"blind_sha256": hashlib.sha256(canonical_bytes(blind)).hexdigest(),
            "comparison_template_sha256": hashlib.sha256(canonical_bytes(comparison)).hexdigest(),
            "instructions_sha256": hashlib.sha256(blind["instructions"].encode()).hexdigest(),
            "schema_sha256": hashlib.sha256(canonical_bytes(blind["response_schema"])).hexdigest()}
    result["target_sha256"] = legacy[0]["target"]["source_sha256"]
    result["neighborhood_sha256"] = hashlib.sha256(canonical_bytes(legacy[0]["neighborhood"])).hexdigest()
    result["target_available"] = bool(pair.text.strip())
    result["authentic_neighborhood_available"] = pair.neighborhood is not None
    return result


def robustness_review(inputs):
    rows = inputs.pairs
    primary = select_r2(rows)
    if primary != review_selection(rows):
        raise ValueError("Independent primary/provenance reconstruction differs")
    primary_ids = set(primary["selected_node_ids_admission_order"])
    attribution = {n: s["stage"] for s in primary["stages"] for n in s["admitted_node_ids"]}
    scenarios = {}
    for seed in SEEDS:
        for order in ORDERS:
            result = review_selection(rows, seed, order)
            if result != review_selection(reversed(rows), seed, order):
                raise ValueError("Review input order affected selection")
            selected = set(result["selected_node_ids_admission_order"])
            roles = {n: s["stage"] for s in result["stages"] for n in s["admitted_node_ids"]}
            scenarios[seed + "/" + ",".join(order)] = {"seed": seed, "order": list(order),
                "overlap_with_primary": len(primary_ids & selected),
                "added": sorted(selected - primary_ids), "removed": sorted(primary_ids - selected),
                "shared_nodes_changed_stage": sorted(n for n in selected & primary_ids if roles[n] != attribution[n]),
                "selection": result}
    comparison = compare_r2(inputs)
    by_id = {p.node_id: p for p in rows}
    fingerprints = {str(p.node_id): request_fingerprints(p) for p in sorted(rows, key=lambda p: p.node_id)}
    for result in comparison["routers"].values():
        for node in result["selected_node_ids"]:
            if fingerprints[str(node)] != request_fingerprints(by_id[node]):
                raise ValueError("Router selection changed canonical verifier inputs")
    root = Path(__file__).resolve().parents[3]
    return {"schema_version": "sara.router.robustness.v1", "cohort_size": len(rows), "budget": BUDGET,
        "class_order": list(CLASSES), "source_hashes": dict(inputs.provenance),
        "prespec_sha256": hashlib.sha256((root / "docs/ROUTER_ROBUSTNESS_SCOPE.md").read_bytes()).hexdigest(),
        "primary_r2_exact_metadata_match": True, "scenarios": scenarios,
        "five_router_comparison": comparison, "canonical_requests_by_node": fingerprints,
        "canonical_per_node_input_invariance": "PASS_LEGACY_AND_RICH_SEPARATELY",
        "runtime_support": {"integrated": ["r0", "semantic"], "standalone_not_integrated": ["R1-v1", "R1-v2", "R2-candidate-v1"]},
        "call_protocol": "Blind first; comparison only after valid non-abstaining blind; failures/missing text stop; no fixed two-call guarantee",
        "production_or_pilot_freeze": False, "ground_truth_accessed": False,
        "human_review_accessed": False, "provider_calls": 0, "training_runs": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-root", required=True)
    parser.add_argument("--authentic-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = robustness_review(load_project_inputs(args.frozen_root, args.authentic_root))
    with Path(args.output).open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
