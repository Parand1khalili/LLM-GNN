"""Validated standard-library adapter of recovered structure/selector.py.

Real undirected edges, deduplication, no self loops, cosine order and ascending
node-ID ties follow source SHA52be8f75854bf4f7208d82d4fac71954a0002146685c823a77508f2d7471c859.
This adapter uses Python float64; it does NOT claim bit identity to historical
Torch float32 near-tie computations. Replay uses the frozen selected IDs.
No A²X/k-medoids FeatProp selection is recomputed by this module.
"""
from __future__ import annotations

import math

from ..io.frozen import InputError


def _node(value, size):
    if type(value) is not int or not 0 <= value < size:
        raise InputError("Graph node ID outside declared shape")
    return value


def build_undirected_neighbors(edge_index, num_nodes: int) -> tuple[tuple[int, ...], ...]:
    """Accept explicit2xE integer sequences, never a graph carrying hidden labels."""
    if type(num_nodes) is not int or num_nodes < 1:
        raise InputError("Positive graph size required")
    if not isinstance(edge_index, (tuple, list)) or len(edge_index) != 2:
        raise InputError("Expected explicit2xE edge sequences")
    left, right = edge_index
    if not isinstance(left, (tuple, list)) or not isinstance(right, (tuple, list)) or len(left) != len(right):
        raise InputError("Graph edge dimensions differ")
    rows = [set() for _ in range(num_nodes)]
    for a, b in zip(left, right):
        a, b = _node(a, num_nodes), _node(b, num_nodes)
        if a != b:
            rows[a].add(b)
            rows[b].add(a)
    return tuple(tuple(sorted(row)) for row in rows)


def semantic_topk_1hop(features, edge_index, target_ids, k: int = 3) -> dict:
    if (not isinstance(features, (tuple, list)) or not features or type(k) is not int or k < 0):
        raise InputError("Explicit feature rows and nonnegative k required")
    rows = []
    width = None
    for row in features:
        if not isinstance(row, (tuple, list)) or not row:
            raise InputError("Feature matrix must be2D and nonempty")
        if width is None:
            width = len(row)
        if len(row) != width or any(type(x) not in (int, float) or not math.isfinite(x) for x in row):
            raise InputError("Invalid/ragged/nonfinite features")
        norm = max(math.hypot(*row), 1e-12)
        if not math.isfinite(norm):
            raise InputError("Feature norm overflow")
        rows.append(tuple(x/norm for x in row))
    adjacency = build_undirected_neighbors(edge_index, len(rows))
    targets = tuple(target_ids)
    for target in targets:
        _node(target, len(rows))
    if len(set(targets)) != len(targets):
        raise InputError("Duplicate target IDs")
    result = {}
    for target in targets:
        _node(target, len(rows))
        candidates = adjacency[target]
        scored = [(node, sum(a*b for a, b in zip(rows[target], rows[node]))) for node in candidates]
        scored.sort(key=lambda pair: (-pair[1], pair[0]))
        result[target] = {"degree": len(candidates), "neighbors": [
            {"node_id": node, "similarity": score} for node, score in scored[:min(k, len(scored))]]}
    return result
