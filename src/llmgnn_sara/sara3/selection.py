"""Versioned, GT-free router dispatch; no historical parity claim."""
from ..sara2.policy import route_r0, validated_pairs
from .atlas import route_semantic
from .r1_candidate import route_r1_candidate
from .r1_coverage import route_r1_candidate_v2
from .r2_candidate import route_r2_candidate

ROUTERS = ("r0", "semantic", "r1_v1", "r1_v2", "r2_v1")
FIXED_PROSPECTIVE_BUDGET = 37


def select_router(pairs, budget, router):
    rows = validated_pairs(pairs)
    if router not in ROUTERS or type(budget) is not int or budget < 0:
        raise ValueError("Unsupported router or budget")
    if router == "r0":
        return route_r0(rows, budget)
    if router == "semantic":
        return route_semantic(rows, budget)
    if budget != FIXED_PROSPECTIVE_BUDGET:
        raise ValueError("Prospective R1/R2 variants require the predeclared budget 37")
    selected = {"r1_v1": route_r1_candidate, "r1_v2": route_r1_candidate_v2,
                "r2_v1": route_r2_candidate}[router](rows)
    if len(selected) != budget or len(set(selected)) != budget:
        raise ValueError("Prospective router selection invariant failed")
    return selected
