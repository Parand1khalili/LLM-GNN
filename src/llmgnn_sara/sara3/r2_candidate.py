"""Prospective stratified router; no claim of recovered historical R2 behavior."""
import hashlib

from ..sara2.policy import risk, validated_pairs
from .r1_candidate import BUDGET
from .r1_coverage import VERSION as R1_VERSION, coverage_terms, policy_score

VERSION = "sara.router.r2_candidate.v1"
ALLOCATIONS = ((4, 17, 16), (2, 18, 17), (6, 16, 15), (4, 16, 17), (4, 18, 15))


def exploration_key(node_id):
    return hashlib.sha256(f"{VERSION}:explore:{node_id}".encode("utf-8")).hexdigest()


def select_r2(pairs, allocation=ALLOCATIONS[0]):
    """Return37 unique admissions with deterministic stratum/cutoff provenance."""
    if (type(allocation) is not tuple or len(allocation) != 3
            or any(type(n) is not int for n in allocation) or allocation not in ALLOCATIONS):
        raise ValueError("Use a prespecified R2 allocation")
    rows = validated_pairs(pairs)
    if len(rows) < BUDGET:
        raise ValueError("R2-candidate requires at least37 nodes")
    coverage = {p.node_id: coverage_terms(p)["coverage"] for p in rows}
    observed = {p.node_id: policy_score(p, R1_VERSION) for p in rows}
    unknown_key = lambda p: (exploration_key(p.node_id), p.node_id)
    observed_key = lambda p: (-observed[p.node_id], -coverage[p.node_id], p.node_id)
    candidate_key = lambda p: (-risk(p), p.node_id)
    selected, seen, stages = [], set(), []

    def admit(name, pool, quota, key):
        ranked = sorted(pool, key=key)
        eligible = [p for p in ranked if p.node_id not in seen]
        chosen = eligible[:quota]
        ids = [p.node_id for p in chosen]
        cutoff = key(chosen[-1])[:-1] if chosen else None
        stages.append({"stage": name, "requested": quota, "pool_size": len(ranked),
            "overlap_skipped": len(ranked) - len(eligible), "available": len(eligible),
            "admitted_node_ids": ids, "shortfall": quota - len(chosen),
            "cutoff_key_without_node_id": [str(v) for v in cutoff] if cutoff is not None else None,
            "cutoff_tied_ids": [p.node_id for p in eligible if key(p)[:-1] == cutoff] if chosen else [],
            "next_eligible_node_id": eligible[len(chosen)].node_id if len(eligible) > len(chosen) else None})
        selected.extend(ids)
        seen.update(ids)

    admit("unknown_exploration", [p for p in rows if coverage[p.node_id] == 0], allocation[0], unknown_key)
    admit("observed_risk", [p for p in rows if coverage[p.node_id] > 0], allocation[1], observed_key)
    admit("candidate_risk", rows, allocation[2], candidate_key)
    admit("backfill_candidate_risk", rows, BUDGET - len(selected), candidate_key)
    if len(selected) != BUDGET or len(seen) != BUDGET:
        raise ValueError("R2 selection invariant failed")
    return {"router_version": VERSION, "allocation": list(allocation),
            "selected_node_ids_admission_order": selected, "stages": stages}


def route_r2_candidate(pairs):
    return tuple(select_r2(pairs)["selected_node_ids_admission_order"])
