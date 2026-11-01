"""GT-free descriptive coverage diagnostics; never reads human review material."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re

from ..io.project import load_project_inputs
from ..sara3.r1_candidate import route_r1_candidate, BUDGET
from ..sara3.r1_coverage import ORIGINAL, NEUTRAL, VERSION, POLICIES, coverage_terms, policy_score, rank_policy
from .router_comparison import compare_routers, distribution


def settings():
    result = []
    for policy in POLICIES:
        for weight in (Fraction(1, 2), Fraction(1), Fraction(2)):
            result.append((policy, {"disagreement_weight": weight},
                           policy + "/wD=" + str(weight)))
    for missing in (Fraction(1, 4), Fraction(3, 4)):
        result.append((NEUTRAL, {"neutral_missing": missing}, NEUTRAL + "/missing=" + str(missing)))
    for order in ("none", "low"):
        result.append((VERSION, {"coverage_order": order}, VERSION + "/coverage=" + order))
    return result


def compare_coverage(inputs):
    rows = inputs.pairs
    observations = {p.node_id: coverage_terms(p) for p in rows}
    lengths = {p.node_id: len(re.findall(r"[a-z]+", p.text.lower())) for p in rows}
    results = {}
    for policy, options, name in settings():
        ranked = rank_policy(rows, policy, **options)
        selected = ranked[:BUDGET]
        score_options = {k: v for k, v in options.items() if k != "coverage_order"}
        scores = {p.node_id: policy_score(p, policy, **score_options) for p in rows}
        cutoff = scores[selected[-1]]
        chosen = [p for p in rows if p.node_id in selected]
        full_tie = [node for node in ranked if scores[node] == cutoff]
        coverage_at_cutoff = observations[selected[-1]]["coverage"]
        joint_tie = [node for node in full_tie if policy != VERSION
                     or options.get("coverage_order") == "none"
                     or observations[node]["coverage"] == coverage_at_cutoff]
        results[name] = {"policy": policy, "settings": {k: str(v) for k, v in options.items()},
            "selected_node_ids_ranked": list(selected),
            "count": len(selected),
            "zero_match_count": sum(observations[p.node_id]["status"] == "NO_ATLAS_MATCH" for p in chosen),
            "coverage_counts": dict(sorted(Counter(observations[p.node_id]["status"] for p in chosen).items())),
            "disagreement_count": sum(not p.agrees for p in chosen),
            "hh_agreement_at_reconstructed_80": sum(p.agrees and min(p.b1.confidence,
                p.narrative_v0.confidence) >= 80 for p in chosen),
            "score_all": distribution([float(v) for v in scores.values()]),
            "score_selected": distribution([float(scores[node]) for node in selected]),
            "selected_ascii_word_count": distribution([lengths[node] for node in selected]),
            "cutoff_score_exact": str(cutoff), "cutoff_score_tied_ids_ranked": full_tie,
            "cutoff_score_tied_selected": [node for node in full_tie if node in selected],
            "cutoff_joint_tie_ids_ranked": joint_tie,
            "cutoff_joint_tied_selected": [node for node in joint_tie if node in selected],
            "overlap_with_own_primary": len(set(selected) & set(rank_policy(rows, policy)[:BUDGET]))}
    if tuple(results[ORIGINAL + "/wD=1"]["selected_node_ids_ranked"]) != route_r1_candidate(rows):
        raise ValueError("Original v1 equivalence failed")
    names = list(results)
    node_rows = []
    for pair in sorted(rows, key=lambda p: p.node_id):
        terms = observations[pair.node_id]
        length = lengths[pair.node_id]
        node_rows.append({"node_id": pair.node_id,
            **{k: float(v) if type(v) is Fraction else v for k, v in terms.items()},
            "ascii_word_count": length, "distinct_ascii_words": len(set(re.findall(r"[a-z]+", pair.text.lower()))),
            "distinct_atlas_hits_per1000_words": sum(terms["class_keyword_hits"]) * 1000 / length if length else None,
            "primary_scores": {p: str(policy_score(pair, p)) for p in POLICIES}})
    groups = {}
    for status in ("NO_ATLAS_MATCH", "PARTIAL_COVERAGE", "OBSERVED_MULTI_KEYWORD_MATCH"):
        members = [n for n in node_rows if n["status"] == status]
        groups[status] = {"count": len(members), "ascii_word_count": distribution(
            [n["ascii_word_count"] for n in members]) if members else None}
    bins = {}
    for label, low, high in (("0..128", 0, 128), ("129..512", 129, 512), ("513+", 513, float("inf"))):
        members = [n for n in node_rows if low <= n["ascii_word_count"] <= high]
        bins[label] = {"count": len(members), "coverage_counts": dict(sorted(Counter(n["status"] for n in members).items()))}
    previous = compare_routers(inputs)
    return {"schema_version": "sara.r1_coverage_comparison.v1", "cohort_size": len(rows), "budget": BUDGET,
        "prespec_sha256": hashlib.sha256((Path(__file__).resolve().parents[3] / "docs/R1_COVERAGE_POLICY.md").read_bytes()).hexdigest(),
        "source_hashes": dict(inputs.provenance), "atlas_sha256": previous["atlas_sha256"],
        "policies_and_sensitivity": results,
        "pairwise_overlaps": {a + " / " + b: len(set(results[a]["selected_node_ids_ranked"]) &
             set(results[b]["selected_node_ids_ranked"])) for i, a in enumerate(names) for b in names[i+1:]},
        "coverage_groups": groups, "length_bins": bins, "nodes": node_rows,
        "interpretation": "DESCRIPTIVE_ONLY_NOT_ACCURACY_OR_HISTORICAL_RECOVERY",
        "recommendation_basis": "PRESPECIFIED_OBSERVED_RISK_NO_POSITIVE_MISSINGNESS_RISK_NOT_OUTPUT_COUNTS",
        "ground_truth_accessed": False, "human_review_accessed": False,
        "provider_calls": 0, "training_runs": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-root", required=True)
    parser.add_argument("--authentic-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = compare_coverage(load_project_inputs(args.frozen_root, args.authentic_root))
    with Path(args.output).open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
