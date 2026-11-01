"""Prospective lexical risk ranking, NOT recovered historical R1 or L2 support."""
from fractions import Fraction

from ..sara2.policy import CLASSES, Pair, validated_pairs
from .atlas import ATLAS, semantic_support

VERSION = "sara.router.r1_candidate.v1"
BUDGET = 37


def risk_terms(pair: Pair) -> dict:
    """Three bounded risk terms with equal, prespecified weights.

    Missing lexical evidence receives maximal uncertainty, not semantic guilt.
    Fractions preserve exact ranking; floats are descriptive exports only.
    """
    if type(pair) is not Pair:
        raise TypeError("Expected explicit GT-free Pair")
    if tuple(c.name for c in ATLAS) != CLASSES:
        raise ValueError("Atlas class order differs")
    counts = semantic_support(pair.text)
    top, second = sorted(counts, reverse=True)[:2]
    disagreement = Fraction(int(not pair.agrees))
    mismatch = (1 - Fraction(counts[pair.b1.class_index] + counts[pair.narrative_v0.class_index],
                             2 * top)) if top else Fraction(1)
    ambiguity = Fraction(second, top) if top else Fraction(1)
    return {"disagreement": disagreement, "candidate_mismatch": mismatch,
            "lexical_ambiguity": ambiguity,
            "score": (disagreement + mismatch + ambiguity) / 3,
            "evidence_status": "LEXICAL_PROXY_AVAILABLE" if top else "NO_ATLAS_KEYWORD_MATCH"}


def route_r1_candidate(pairs) -> tuple[int, ...]:
    """Exactly37 unique nodes, descending exact score, ascending node-ID ties."""
    rows = validated_pairs(pairs)
    if len(rows) < BUDGET:
        raise ValueError("R1-candidate requires at least37 nodes")
    return tuple(p.node_id for p in sorted(
        rows, key=lambda p: (-risk_terms(p)["score"], p.node_id))[:BUDGET])
