"""Draft natural/matched GCN grids and separately gated fusion admission."""
import argparse
from dataclasses import asdict
import hashlib
import io
import json
import math
import re
from pathlib import Path
import sys
import zipfile

from ..io.frozen import read_pinned_json, reject_gt
from ..io.project import load_project_inputs, GRAPH_SHA256
from ..sara3 import fusion
from ..sara3.audit import PrivateAudit
from ..sara3.experiment import digest
from ..sara3.correction_features import require
from ..sara3.weighted_arbitration_v2 import load_graph
from ..filtering.ps import derive_ps
from .plan import GCNConfig, PseudoLabel, gcn_plan, confidence_weights

VERSION = "sara.gcn.three_agent_grid.v1"
ADMISSION = "sara.gcn.three_agent_admission.v1"
CONTRACT = {"version": VERSION, "target_selection": "FIXED_FEATPROP_NOT_A_TOGGLE",
    "arms": ["A_B1", "B_NARRATIVE", "C_BASELINE_FUSION", "D_P1_r0", "E_P2_r0", "D_P1_r1_v1", "E_P2_r1_v1"],
    "losses": ["ce", "wce"], "PS": [False, True], "cohorts": ["sensitivity", "primary"],
    "mask_modes": ["natural", "matched_all_arms"], "seeds": list(range(10)),
    "PS_remove_rule": "floor(0.30*accepted_eligible_count)_NO_GUARD_RELAXATION",
    "matched_noPS": "INTERSECTION_OF_ALL_SEVEN_ACCEPTED_MASKS",
    "matched_PS": "INTERSECTION_OF_ALL_SEVEN_NATURAL_POST_PS_MASKS_IF_ALL_DEFINED",
    "unknown_confidence": "CE_ALLOWED_WCE_OR_PS_BLOCKED_NO_AGENT_CONFIDENCE_IMPUTATION",
    "fit_deduplication": "EXACT_GRAPH_CONFIG_MASK_LABEL_WEIGHT_AND_TEST_SPEC_PER_SEED",
    "training_status": "NOT_RUN_BLOCKED", "test_independence": "UNVERIFIED_CONTAMINATION_AUDIT_REQUIRED"}


def row_plan(report, arm, cohort, loss, ps, mode, forced=None):
    excluded = set(report["primary_excluded_ids"]) if cohort == "primary" else set()
    eligible = [r for r in report["arms"][arm] if r["node_id"] not in excluded and r["final_class"] is not None
                and (forced is None or r["node_id"] in forced)]
    result = {"arm": arm, "cohort": cohort, "loss": loss, "PS": ps, "mask_mode": mode,
              "status": "DRAFT_NOT_ADMITTED", "training_status": "NOT_RUN_BLOCKED",
              "train_ids": [], "class_indices": [], "confidence_percent": [], "weights": [],
              "ps_removed_ids": [], "pre_PS_count": len(eligible), "per_seed_results": []}
    if not eligible: return {**result, "status": "BLOCKED_EMPTY_TRAIN_MASK"}
    if (loss == "wce" or ps) and any(r["confidence_percent"] is None for r in eligible):
        return {**result, "status": "BLOCKED_UNAVAILABLE_FINAL_LABEL_CONFIDENCE"}
    if ps and any(r["confidence_percent"] <= 0 for r in eligible):
        return {**result, "status": "BLOCKED_NONPOSITIVE_PS_CONFIDENCE"}
    removed = []
    if ps:
        count = math.floor(.30 * len(eligible))
        if count > len(eligible)-len({r["final_class"] for r in eligible}):
            return {**result, "status": "BLOCKED_PS_CLASS_GUARD_CAPACITY"}
        selected = derive_ps([r["node_id"] for r in eligible], [r["final_class"] for r in eligible],
                             [r["confidence_percent"] for r in eligible], count)
        removed = selected["removed_global_node_ids_in_deletion_order"]
        eligible = [r for r in eligible if r["node_id"] not in set(removed)]
    confidence = [r["confidence_percent"] for r in eligible]
    result.update(train_ids=[r["node_id"] for r in eligible], class_indices=[r["final_class"] for r in eligible],
                  confidence_percent=confidence, ps_removed_ids=removed,
                  weights=list(confidence_weights(confidence)) if loss == "wce" else [1.0]*len(eligible))
    return result


def build_grid(report, fusion_sha):
    require(digest(report) == fusion_sha and report["schema"] == fusion.VERSION
            and report["contract"] == fusion.CONTRACT and report["rule_sha256"] == digest(fusion.CONTRACT))
    reject_gt(report)
    order = report["cohort_ids"]
    require(len(order) == len(set(order)) == 140 and len(set(report["primary_excluded_ids"])) == 5
            and set(report["primary_excluded_ids"]) <= set(order)
            and all(type(i) is int and 0 <= i < 2708 for i in order)
            and set(report["arms"]) == set(CONTRACT["arms"]))
    for rows in report["arms"].values():
        require([r["node_id"] for r in rows] == order and all(r["training_eligible"] is False
                and (r["final_class"] is None or type(r["final_class"]) is int and 0 <= r["final_class"] < 7)
                and (r["confidence_percent"] is None or type(r["confidence_percent"]) in (int, float)
                     and math.isfinite(r["confidence_percent"]) and 0 <= r["confidence_percent"] <= 100) for r in rows))
    plans = []
    for cohort in CONTRACT["cohorts"]:
        for loss in CONTRACT["losses"]:
            for ps in CONTRACT["PS"]:
                natural = [row_plan(report, arm, cohort, loss, ps, "natural") for arm in CONTRACT["arms"]]
                plans.extend(natural)
                if ps:
                    ready = all(r["status"] == "DRAFT_NOT_ADMITTED" for r in natural)
                    common = set.intersection(*(set(r["train_ids"]) for r in natural)) if ready else None
                else:
                    ready = True
                    excluded = set(report["primary_excluded_ids"]) if cohort == "primary" else set()
                    common = set.intersection(*({r["node_id"] for r in report["arms"][a] if r["final_class"] is not None
                                                and r["node_id"] not in excluded} for a in CONTRACT["arms"]))
                for arm in CONTRACT["arms"]:
                    if not ready:
                        plans.append({**row_plan(report, arm, cohort, loss, False, "matched_all_arms", forced=set()),
                                      "PS": ps, "status": "BLOCKED_UNDEFINED_COMMON_POST_PS_MASK"})
                        continue
                    # PS already applied independently before intersection, never filter twice.
                    row = row_plan(report, arm, cohort, loss, False, "matched_all_arms", forced=common)
                    row["PS"] = ps; row["post_PS_intersection"] = ps
                    plans.append(row)
    test = [i for i in range(2708) if i not in set(order)]
    require(len(test) == 2568)
    fits = {}
    for row in plans:
        if row["status"] != "DRAFT_NOT_ADMITTED": continue
        spec = {"graph_sha256": GRAPH_SHA256, "test_ids_sha256": digest(test),
                "config": asdict(GCNConfig(loss=row["loss"])),
                "train_ids": row["train_ids"], "class_indices": row["class_indices"], "weights": row["weights"]}
        row["fit_spec_sha256"] = digest(spec)
        fits.setdefault(row["fit_spec_sha256"], []).append([row[k] for k in ("arm", "cohort", "loss", "PS", "mask_mode")])
    return {"schema": VERSION, "contract": CONTRACT, "fusion_sha256": fusion_sha,
            "selected_ids": order, "test_ids": test, "test_ids_sha256": digest(test),
            "config": json.loads(json.dumps(asdict(GCNConfig()))), "plans": plans,
            "unique_fit_specs": fits, "unique_planned_seed_fits": 10*len(fits),
            "training_runs": 0, "actual_metrics": "NOT_RUN_BLOCKED", "source_rule_sha256": report["rule_sha256"]}


def verify_historical_ps(grid, frozen_root):
    for cohort, pin in (("primary", "fa0a8c79b3c657371dd7cf7417a57174e20ce92b03c50df845873367005eeeed"),
                        ("sensitivity", "8f2d4b026a27f3c01f4bfb021fe1a4b2fd84ab90858da54ec0c4fee0367d9436")):
        expected = read_pinned_json(Path(frozen_root)/f"ps_{cohort}.json", pin)
        for arm, original in (("A_B1", "b1"), ("B_NARRATIVE", "narrative_v0")):
            row = next(r for r in grid["plans"] if r["arm"] == arm and r["cohort"] == cohort and r["loss"] == "ce"
                       and r["PS"] and r["mask_mode"] == "natural")
            legacy = expected["selection_by_arm"][original]
            require(row["status"] == "DRAFT_NOT_ADMITTED"
                    and row["train_ids"] == legacy["retained_global_node_ids_in_original_manifest_order"]
                    and row["ps_removed_ids"] == legacy["removed_global_node_ids_in_deletion_order"]
                    and row["class_indices"] == legacy["retained_pseudo_class_indices_in_order"]
                    and row["confidence_percent"] == legacy["retained_confidence_percent_in_order"])


def graph_inputs(path):
    """Exact original x/edge order only; no pickle or label tensor decoding."""
    import numpy as np
    import torch
    from .model import GraphInputs, _validate_graph
    x, _, provenance = load_graph(path)
    blob = Path(path).read_bytes()
    require(hashlib.sha256(blob).hexdigest() == GRAPH_SHA256)
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        edges = np.frombuffer(archive.read("cora_random_sbert/data/1"), dtype="<i8").reshape(2, 10858).copy()
    graph = GraphInputs(torch.from_numpy(x.astype("float32")), torch.from_numpy(edges))
    require(hashlib.sha256(graph.x.numpy().tobytes()).hexdigest() == provenance["embedding_storage_sha256"]
            and hashlib.sha256(graph.edge_index.numpy().tobytes()).hexdigest() == provenance["edge_storage_sha256"])
    return _validate_graph(graph, 2708)


def admit(report, row, *, table, inputs, approval=None):
    """Explicit hash-bound experimental admission only. Never calls training."""
    if approval is None: raise PermissionError("Separate explicit experimental admission required")
    require(type(approval) is dict and set(approval) == {"version", "fusion_sha256", "plan_sha256", "owner_authorized",
            "allow_experimental_admission", "test_audit_sha256", "test_status"})
    require(approval["version"] == ADMISSION and approval["fusion_sha256"] == digest(report)
            and approval["plan_sha256"] == digest(row) and approval["owner_authorized"] is True
            and approval["allow_experimental_admission"] is True
            and approval["test_status"] in ("AUDITED_INDEPENDENT_TEST", "AUDITED_EXPLORATORY_SPLIT")
            and type(approval["test_audit_sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", approval["test_audit_sha256"]))
    fusion.validate_report(report, table, inputs)
    grid = build_grid(report, digest(report)); require(row in grid["plans"] and row["status"] == "DRAFT_NOT_ADMITTED")
    # The CE backend requires a numeric unused slot. This is a unit-loss sentinel,
    # not a confidence estimate; the fusion report retains genuine None values.
    ce_unknown = [i for i, c in zip(row["train_ids"], row["confidence_percent"]) if c is None]
    labels = [PseudoLabel(i, k, 100.0 if c is None else c) for i, k, c in
              zip(row["train_ids"], row["class_indices"], row["confidence_percent"])]
    require(not ce_unknown or row["loss"] == "ce")
    plan = gcn_plan(report["cohort_ids"], labels, cohort=row["cohort"],
                    excluded_ids=report["primary_excluded_ids"] if row["cohort"] == "primary" else (),
                    config=GCNConfig(loss=row["loss"]), allow_abstention=True)
    require(plan["test_ids"] == grid["test_ids"] and plan["train_ids"] == row["train_ids"] and plan["weights"] == row["weights"])
    plan.update(experimental_admission_version=ADMISSION, source_fusion_sha256=digest(report), source_plan_sha256=digest(row),
                external_PS_already_applied=row["PS"], ce_unit_slot_not_confidence_ids=ce_unknown,
                authorization="ADMISSION_ONLY_TRAINING_STILL_REQUIRES_SEPARATE_ALLOW_TRAINING",
                test_status=approval["test_status"])
    return plan


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("fusion", "features", "frozen-root", "authentic-root", "graph", "output"):
        p.add_argument("--"+name, type=Path, required=True)
    p.add_argument("--fusion-sha256", required=True)
    a = p.parse_args(argv)
    try:
        report = read_pinned_json(a.fusion, a.fusion_sha256)
        inputs = load_project_inputs(a.frozen_root, a.authentic_root)
        table = read_pinned_json(a.features, fusion.FEATURE_SHA); fusion.validate_report(report, table, inputs)
        require(".local_artifacts" in a.output.absolute().parts); store = PrivateAudit(a.output)
        rule_sha = store.write(CONTRACT)
        x, edges, provenance = load_graph(a.graph); require(x.shape == (2708, 384))
        grid = build_grid(report, a.fusion_sha256); verify_historical_ps(grid, a.frozen_root)
        grid.update(graph_provenance=provenance, historical_PS_parity="PASS_BOTH_ARMS_BOTH_COHORTS", grid_rule_sha256=rule_sha)
        sha = store.write(grid); require(store.read(sha) == grid)
        from collections import Counter
        print(json.dumps({"grid_sha256": sha, "grid_rule_sha256": rule_sha, "plan_rows": len(grid["plans"]),
            "status_counts": dict(Counter(r["status"] for r in grid["plans"])), "training_status": "NOT_RUN_BLOCKED"}))
        return 0
    except Exception:
        print('{"status":"FAIL_CLOSED"}', file=sys.stderr); return 1


if __name__ == "__main__": raise SystemExit(main())
