"""Adapted from pinned primary PS runner SHA256 00f846cc...dd5b102.

Preserves sequential ranks, node-ID ties, original order and last-class guard.
Unlike the legacy generic post-filter, equal scores are NOT averaged.
"""
from __future__ import annotations

from collections import Counter
import math


def _entropy(values):
    counts = Counter(values)
    size = len(values)
    return -sum((count / size) * math.log(count / size) for count in counts.values())


def derive_ps(ids, labels, confidences, deletion_count):
    ids, labels, confidences = tuple(ids), tuple(labels), tuple(confidences)
    if not ids or len(ids) != len(labels) or len(ids) != len(confidences):
        raise ValueError("Aligned nonempty pseudo-label inputs required")
    if len(set(ids)) != len(ids) or any(type(i) is not int or i < 0 for i in ids):
        raise ValueError("Unique nonnegative global node IDs required")
    if any(type(y) is not int or not 0 <= y < 7 for y in labels):
        raise ValueError("Invalid pseudo-class index")
    if any(type(c) not in (int, float) or not math.isfinite(c) or not 0 < c <= 100
           for c in confidences):
        raise ValueError("Confidence must be in (0,100]")
    if type(deletion_count) is not int or not 0 <= deletion_count <= len(ids) - len(set(labels)):
        raise ValueError("Deletion count violates the class guard")
    label_of, conf_of = dict(zip(ids, labels)), dict(zip(ids, confidences))
    alive, removed = set(ids), []
    for _ in range(deletion_count):
        present = sorted(alive)
        counts = Counter(label_of[node] for node in present)
        h0 = _entropy([label_of[node] for node in present])
        candidates = [node for node in present if counts[label_of[node]] > 1]
        m = len(candidates)
        coe = {node: _entropy([label_of[j] for j in present if j != node]) - h0
               for node in candidates}
        ranked_conf = sorted(candidates, key=lambda node: (-conf_of[node], node))
        ranked_coe = sorted(candidates, key=lambda node: (coe[node], node))
        conf_ranks = {node: (m-rank)/m for rank, node in enumerate(ranked_conf)}
        coe_ranks = {node: (m-rank)/m for rank, node in enumerate(ranked_coe)}
        node = min(candidates, key=lambda n: (conf_ranks[n] + coe_ranks[n], n))
        alive.remove(node)
        removed.append(node)
    retained = [node for node in ids if node in alive]
    return {"retained_global_node_ids_in_original_manifest_order": retained,
            "removed_global_node_ids_in_deletion_order": removed,
            "retained_pseudo_class_indices_in_order": [label_of[i] for i in retained],
            "retained_confidence_percent_in_order": [conf_of[i] for i in retained],
            "ground_truth_accessed": False}
