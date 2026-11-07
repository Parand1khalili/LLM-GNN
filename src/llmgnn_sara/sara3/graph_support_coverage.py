"""GT-free coverage audit and fixed direct-seed shadow variant; V2 unchanged."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from ..io.frozen import read_pinned_json
from ..io.project import load_project_inputs
from .audit import PrivateAudit
from .correction_features import validate, require
from .experiment import digest
from . import weighted_arbitration_v2 as base

VERSION = "sara.arbitration.weighted.v2.direct_seed.v1"
BASE_REPORT_SHA = "56e485e635ac915d07a0bb1b8849f5beb9017bd6f1ca9028192a64de335c0417"
# Prespecified before coverage/output/GT inspection; only remove the density gate.
CONTRACT = {"version": VERSION, "base_config_sha256": base.CONFIG_SHA,
            "neighbor_min_samples": 3, "neighbor_support_fraction": 2 / 3,
            "strict_agent_count_advantage": True, "density_gate": False,
            "seed_policy": "UNCHANGED_ROUTER_SPECIFIC_BASELINE_ADMISSIONS",
            "other_weights_thresholds_and_gates": "UNCHANGED_V2",
            "mode": "EXPERIMENTAL_SHADOW_NO_TRAINING_AUTHORIZATION"}


def direct_support(agent, narrative, neighbor_ids, seeds):
    require(type(agent) is int and 0 <= agent < 7 and type(narrative) is int and 0 <= narrative < 7)
    require(len(neighbor_ids) == len(set(neighbor_ids)))
    require(all(type(i) is int and i >= 0 for i in neighbor_ids))
    require(all(type(i) is int and i >= 0 and type(k) is int and 0 <= k < 7 for i, k in seeds.items()))
    labels = [seeds[i] for i in neighbor_ids if i in seeds]
    if len(labels) < CONTRACT["neighbor_min_samples"]: return None
    return int(labels.count(agent) / len(labels) >= CONTRACT["neighbor_support_fraction"]
               and labels.count(agent) > labels.count(narrative))


def variant_decision(source, components, cfg):
    return {**base.decide(source, components, cfg), "policy_version": VERSION}


def audit_and_score(table, inputs, x, adjacency, cfg, baseline):
    import numpy as np
    validate(table)
    require(digest(cfg) == base.CONFIG_SHA)
    original = base.run(table, inputs, x, adjacency, cfg)  # Also validates graph/seeds.
    require(original == baseline["rows"])
    require(all(set(p.neighborhood.neighbor_ids) <= adjacency[p.node_id]
                and p.neighborhood.degree == len(adjacency[p.node_id]) for p in inputs.pairs))
    cohort = {p.node_id for p in inputs.pairs}
    norm = np.linalg.norm(x, axis=1)
    summaries, coverage_rows, rows = {}, [], []
    for router in ("r0", "r1_v1"):
        sources = [r for r in table["rows"] if r["router"] == router]
        selected = {r["node_id"] for r in sources}
        seeds = {p.node_id: p.narrative_v0.class_index for p in inputs.pairs
                 if p.node_id not in selected and p.agrees
                 and min(p.b1.confidence, p.narrative_v0.confidence) >= cfg["seed_min_confidence"]}
        prototypes = []
        for k in range(7):
            ids = sorted(i for i, c in seeds.items() if c == k)
            usable = [i for i in ids if norm[i] > 0]
            nonzero_mean = bool(usable) and float(np.linalg.norm(np.mean(x[usable] / norm[usable, None], axis=0))) > 0
            prototypes.append({"class_index": k, "seed_count": len(ids), "nonzero_embedding_seeds": len(usable),
                               "zero_embedding_seeds": len(ids)-len(usable),
                               "sample_minimum_pass": len(usable) >= cfg["prototype_min_samples"],
                               "nonzero_mean": nonzero_mean})
        reasons, joint, seed_hist, density_hist, ns = (Counter() for _ in range(5))
        for source, prior in zip(sources, (r for r in original if r["router"] == router)):
            node = source["node_id"]
            # Compute topology coverage even when the original run skipped an abstention.
            detail = base.support(node, source["narrative_class"], source["narrative_class"], x, adjacency, seeds, cfg)
            count, density = detail["reliable_neighbor_count"], detail["neighborhood_density"]
            has_class = type(source["blind"]["class_index"]) is int
            enough = count >= cfg["neighbor_min_samples"]
            dense = density is not None and density >= cfg["neighbor_density_min"]
            failed = []
            if not has_class: failed.append("NO_BLIND_CLASS_ORIGINAL_SUPPORT_SKIPPED")
            if not enough: failed.append("INSUFFICIENT_DIRECT_SEEDS")
            if density is None: failed.append("DENSITY_UNDEFINED")
            elif not dense: failed.append("DENSITY_BELOW_MINIMUM")
            reasons.update(failed)
            joint[f"seed_minimum={enough},density_minimum={dense}"] += 1
            seed_hist[str(count)] += 1
            density_hist["UNDEFINED" if density is None else "ZERO" if density == 0 else "(0,0.10)" if density < .1 else "[0.10,1]"] += 1
            n = direct_support(source["blind"]["class_index"], source["narrative_class"], sorted(adjacency[node]), seeds) if has_class else None
            support = {**prior["support"], "N": n}
            decision = variant_decision(source, {"P": support["P"], "N": n}, cfg)
            rows.append({"router": router, "node_id": node, "narrative_class": source["narrative_class"],
                         "support": support, **decision})
            ns["UNKNOWN" if n is None else str(n)] += 1
            coverage_rows.append({"router": router, "node_id": node, "direct_seed_count": count,
                                  "density": density, "original_N": prior["support"]["N"],
                                  "original_unknown_reasons": failed,
                                  "target_zero_embedding": bool(norm[node] == 0)})
        summaries[router] = {"denominator": len(sources), "seed_pool_count": len(seeds),
                             "prototype_classes": prototypes, "seed_neighbor_histogram": dict(seed_hist),
                             "density_histogram": dict(density_hist), "gate_cross_tab": dict(joint),
                             "overlapping_unknown_reasons": dict(reasons), "variant_N": dict(ns),
                             "decisions": dict(Counter(r["decision"] for r in rows if r["router"] == router))}
    return {"routers": summaries, "private_coverage_rows": coverage_rows,
            "canonical_frozen_neighborhood_alignment": "PASS",
            "cohort_internal_undirected_edges": sum(len(adjacency[i] & cohort) for i in cohort) // 2,
            "finite_embedding_rows": int(np.isfinite(x).all(axis=1).sum()),
            "zero_norm_embedding_rows": int((norm == 0).sum())}, rows


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("features", "base-report", "graph", "frozen-root", "authentic-root", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args(argv)
    try:
        table = read_pinned_json(args.features, base.FEATURE_SHA)
        baseline = read_pinned_json(args.base_report, BASE_REPORT_SHA)
        inputs = load_project_inputs(args.frozen_root, args.authentic_root)
        cfg = json.loads(base.CONFIG_PATH.read_text(encoding="utf-8"))
        require(".local_artifacts" in args.output.absolute().parts)
        store = PrivateAudit(args.output)
        rule_sha = store.write(CONTRACT)  # Freeze before graph coverage or scores.
        x, adjacent, provenance = base.load_graph(args.graph)
        coverage, rows = audit_and_score(table, inputs, x, adjacent, cfg, baseline)
        coverage_sha = store.write({"schema": "sara.graph_support.coverage.v1", "rule_sha256": rule_sha,
                                    "source_feature_sha256": base.FEATURE_SHA, "graph_provenance": provenance, **coverage})
        report = {"schema": VERSION, "contract": CONTRACT, "rule_sha256": rule_sha,
                  "config": cfg, "source_feature_sha256": base.FEATURE_SHA,
                  "base_report_sha256": BASE_REPORT_SHA, "coverage_sha256": coverage_sha,
                  "graph_provenance": provenance, "rows": rows, "training_admissions": 0}
        sha = store.write(report); require(store.read(sha) == report)
        print(json.dumps({"status": "GT_FREE_SHADOW_FROZEN", "rule_sha256": rule_sha,
                          "coverage_sha256": coverage_sha, "report_sha256": sha,
                          "summary": {k: v for k, v in coverage.items() if k != "private_coverage_rows"}}))
        return 0
    except Exception:
        print('{"status":"FAIL_CLOSED"}', file=sys.stderr); return 1


if __name__ == "__main__": raise SystemExit(main())
