"""Prespecified missing-evidence alternatives, independent of frozen R1 v1."""
from fractions import Fraction

from ..sara2.policy import validated_pairs
from .atlas import semantic_support
from .r1_candidate import VERSION as ORIGINAL, BUDGET, risk_terms

NEUTRAL = "sara.router.r1_neutral.v1"
VERSION = "sara.router.r1_candidate.v2"
POLICIES = (ORIGINAL, NEUTRAL, VERSION)


def coverage_terms(pair):
    original = risk_terms(pair)  # Reuse explicit Pair validation and class-order guard.
    counts = semantic_support(pair.text)
    top = max(counts)
    return {"status": "NO_ATLAS_MATCH" if not top else (
                "PARTIAL_COVERAGE" if top == 1 else "OBSERVED_MULTI_KEYWORD_MATCH"),
            "class_keyword_hits": counts, "coverage": Fraction(top, 4),
            "disagreement": original["disagreement"],
            "observed_mismatch": original["candidate_mismatch"] if top else None,
            "observed_ambiguity": original["lexical_ambiguity"] if top else None}


def policy_score(pair, policy, *, disagreement_weight=Fraction(1), neutral_missing=Fraction(1, 2)):
    if policy not in POLICIES:
        raise ValueError("Unknown coverage policy")
    if type(disagreement_weight) is not Fraction or disagreement_weight not in (
            Fraction(1, 2), Fraction(1), Fraction(2)):
        raise ValueError("Use prespecified exact disagreement weights")
    if type(neutral_missing) is not Fraction or neutral_missing not in (
            Fraction(1, 4), Fraction(1, 2), Fraction(3, 4)):
        raise ValueError("Use prespecified exact neutral imputations")
    if policy != NEUTRAL and neutral_missing != Fraction(1, 2):
        raise ValueError("Neutral imputation applies only to neutral policy")
    terms = coverage_terms(pair)
    missing = {ORIGINAL: Fraction(1), NEUTRAL: neutral_missing, VERSION: Fraction(0)}[policy]
    mismatch = terms["observed_mismatch"]
    ambiguity = terms["observed_ambiguity"]
    return (disagreement_weight * terms["disagreement"]
            + (mismatch if mismatch is not None else missing)
            + (ambiguity if ambiguity is not None else missing)) / (disagreement_weight + 2)


def rank_policy(pairs, policy, *, disagreement_weight=Fraction(1),
                neutral_missing=Fraction(1, 2), coverage_order="high"):
    rows = validated_pairs(pairs)
    if len(rows) < BUDGET:
        raise ValueError("Coverage policies require at least37 nodes")
    if coverage_order not in ("high", "low", "none") or (policy != VERSION and coverage_order != "high"):
        raise ValueError("Coverage tie sensitivity applies only to v2")
    def key(pair):
        coverage = coverage_terms(pair)["coverage"] if policy == VERSION else Fraction(0)
        secondary = -coverage if coverage_order == "high" else (
            coverage if coverage_order == "low" else Fraction(0))
        return (-policy_score(pair, policy, disagreement_weight=disagreement_weight,
                              neutral_missing=neutral_missing), secondary, pair.node_id)
    return tuple(p.node_id for p in sorted(rows, key=key))


def route_r1_candidate_v2(pairs):
    """Independent prospective router; no change to existing runtime defaults."""
    return rank_policy(pairs, VERSION)[:BUDGET]
