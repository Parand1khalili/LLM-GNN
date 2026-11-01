"""Descriptive GT-free router diagnostics. Never calls a verifier or training."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from statistics import mean

from ..io.project import load_project_inputs
from ..sara2.policy import CLASSES, risk, route_r0
from ..sara3.atlas import ATLAS, route_semantic, semantic_risk
from ..sara3.r1_candidate import VERSION, BUDGET, risk_terms, route_r1_candidate


def distribution(values):
    values = sorted(values)
    return {"min": values[0], "median": (values[(len(values)-1)//2] + values[len(values)//2]) / 2,
            "mean": mean(values), "max": values[-1]}


def compare_routers(inputs):
    rows = inputs.pairs
    selections = {"r0_current": route_r0(rows, BUDGET),
                  "semantic_v0_current": route_semantic(rows, BUDGET),
                  VERSION: route_r1_candidate(rows)}
    terms = {p.node_id: risk_terms(p) for p in rows}
    native = {"r0_current": lambda p: risk(p),
              "semantic_v0_current": lambda p: semantic_risk(p),
              VERSION: lambda p: float(terms[p.node_id]["score"])}
    routers = {}
    for name, selected in selections.items():
        chosen = [p for p in rows if p.node_id in selected]
        routers[name] = {"selected_node_ids_ranked": list(selected), "count": len(selected),
            "disagreement_count": sum(not p.agrees for p in chosen),
            "no_keyword_match_count": sum(terms[p.node_id]["evidence_status"] == "NO_ATLAS_KEYWORD_MATCH"
                                          for p in chosen),
            "hh_agreement_count_at_reconstructed_80": sum(
                p.agrees and min(p.b1.confidence, p.narrative_v0.confidence) >= 80 for p in chosen),
            "native_score_all": distribution([native[name](p) for p in rows]),
            "native_score_selected": distribution([native[name](p) for p in chosen]),
            "r1_score_selected": distribution([float(terms[p.node_id]["score"]) for p in chosen])}
    names = list(selections)
    return {"schema_version": "sara.router_comparison.v1", "provenance": "RECONSTRUCTED",
        "cohort_size": len(rows), "budget": BUDGET, "classes": list(CLASSES),
        "r1_parameters": {"weights": {"disagreement": "1/3", "candidate_mismatch": "1/3",
                                         "lexical_ambiguity": "1/3"},
            "normalization": "mismatch=1-(hits_b1+hits_v0)/(2*top); ambiguity=second/top",
            "no_keyword_match": "mismatch=ambiguity=1; explicitly unknown, not semantic failure",
            "tie_break": "descending exact Fraction score, ascending node ID",
            "confidence_in_score": False, "historical_count_tuning": False},
        "no_keyword_match_count": sum(t["evidence_status"] == "NO_ATLAS_KEYWORD_MATCH"
                                       for t in terms.values()),
        "source_hashes": dict(inputs.provenance),
        "atlas_sha256": hashlib.sha256(json.dumps([asdict(c) for c in ATLAS],
            sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "routers": routers,
        "overlaps": {a + " / " + b: len(set(selections[a]) & set(selections[b]))
                     for i, a in enumerate(names) for b in names[i+1:]},
        "r1_terms_by_node": [{"node_id": node, **{k: float(v) if k != "evidence_status" else v
                              for k, v in terms[node].items()}} for node in sorted(terms)],
        "interpretation": "DESCRIPTIVE_ONLY_NO_ACCURACY_OR_HISTORICAL_EQUIVALENCE",
        "hh_definition": "Agreement and both frozen confidence>=80; reconstructed descriptive convention, not verified historical HH",
        "ground_truth_accessed": False, "provider_calls": 0, "training_runs": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-root", required=True)
    parser.add_argument("--authentic-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = compare_routers(load_project_inputs(args.frozen_root, args.authentic_root))
    # New reports only; never overwrite an existing scientific artifact.
    with Path(args.output).open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
