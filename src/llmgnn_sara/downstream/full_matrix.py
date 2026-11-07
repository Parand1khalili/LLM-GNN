"""Frozen full FeatProp/PS/CE/WCE matrix; GT-free experimental labels only."""
from collections import Counter
from dataclasses import asdict
from itertools import combinations
import math
import json

from . import fusion as previous
from .ce_preflight import control_labels, CONTROL
from .plan import GCNConfig, confidence_weights
from ..filtering.ps import derive_ps
from ..io.frozen import reject_gt
from ..io.project import GRAPH_SHA256
from ..sara3.experiment import digest
from ..sara3.correction_features import require

VERSION = "sara.gcn.full_matrix.v1"
HISTORICAL = "historical_confidence.v1"
EXTENSION = "missing_confidence_aware.v1"
CONTRACT = {
    "version": VERSION, "arms": previous.CONTRACT["arms"],
    "selection": "FROZEN_FEATPROP140_NOT_A_TOGGLE", "seeds": list(range(10)),
    "cohorts": ["primary", "sensitivity"], "losses": ["ce", "wce"], "PS": [False, True],
    "protocols": [HISTORICAL, EXTENSION],
    "known_WCE": "MINMAX_FINAL_KNOWN_SUBSET_CONSTANT_TO_ONES",
    "missing_WCE": "EXTENSION_ONLY_UNIT_LOSS_WEIGHT_NOT_MODEL_CONFIDENCE",
    "reduction": "MEAN_OF_WEIGHT_TIMES_PER_NODE_CE_NOT_WEIGHT_NORMALIZED",
    "historical_PS": "FLOOR_0.30_ACCEPTED_CLASS_GUARD_NO_RELAXATION",
    "extension_PS": "FLOOR_0.30_SCORED_CAPPED_BY_SCORED_CLASS_GUARD_CAPACITY",
    "missing_PS": "UNSCORED_PROTECTED_NOT_RANKED",
    "PS_guard": "KEEP_AT_LEAST_ONE_SCORED_SEED_PER_PRESENT_SCORED_CLASS",
    "masks": ["natural", "matched_all", "pairwise", "coverage_matched_no_agent"],
    "matching": "INTERSECT_NATURAL_POST_PS_THEN_RECOMPUTE_WEIGHTS_NO_SECOND_PS",
    "coverage_control": CONTROL,
    "coverage_control_PS": "INHERIT_TREATMENT_POST_PS_IDS_NO_SECOND_PS",
    "test": "FIXED_2568_COMPLEMENT_ALL140_EXPLORATORY_NOT_INDEPENDENT",
    "epochs": 30, "device": "cpu", "torch_threads": 1,
    "reuse": "EXACT_EFFECTIVE_FIT_AND_RUNTIME_HASH_RECEIPT_ONLY",
}


def reject_controls(value):
    reject_gt(value)
    if isinstance(value, dict):
        require(not {"oracle", "debug_gt_label", "filter_all_wrong_labels"}.intersection(value))
        for item in value.values(): reject_controls(item)
    elif isinstance(value, (list, tuple)):
        for item in value: reject_controls(item)


def _weights(conf, loss, protocol):
    if loss == "ce": return [1.0] * len(conf)
    known = [c for c in conf if c is not None]
    require(protocol == EXTENSION or len(known) == len(conf))
    normalized = iter(confidence_weights(known)) if known else iter(())
    return [1.0 if c is None else next(normalized) for c in conf]


def values(records, *, loss, ps, protocol):
    """Pure filtering; all label entropy is computed from pseudo-classes."""
    require(loss in CONTRACT["losses"] and type(ps) is bool and protocol in CONTRACT["protocols"])
    require(records and len({r["node_id"] for r in records}) == len(records))
    for r in records:
        require(type(r["node_id"]) is int and 0 <= r["node_id"] < 2708
                and type(r["final_class"]) is int and 0 <= r["final_class"] < 7)
        c = r["confidence_percent"]
        require(c is None or type(c) in (int, float) and math.isfinite(c) and 0 <= c <= 100)
    missing = [r["node_id"] for r in records if r["confidence_percent"] is None]
    row = {"status": "DRAFT_NOT_ADMITTED", "pre_PS_count": len(records),
           "missing_confidence_ids": missing, "protected_ids": missing if ps and protocol == EXTENSION else [],
           "PS_requested": 0, "PS_effective": 0, "PS_shortfall": 0, "PS_removed_ids": [],
           "class_counts_before": dict(Counter(str(r["final_class"]) for r in records))}
    if missing and protocol == HISTORICAL and (ps or loss == "wce"):
        return {**row, "status": "BLOCKED_UNAVAILABLE_FINAL_LABEL_CONFIDENCE"}
    scored = [r for r in records if r["confidence_percent"] is not None]
    if ps and any(r["confidence_percent"] <= 0 for r in scored):
        return {**row, "status": "BLOCKED_NONPOSITIVE_PS_CONFIDENCE"}
    removed = []
    if ps:
        requested = math.floor(.30 * (len(scored) if protocol == EXTENSION else len(records)))
        capacity = len(scored) - len({r["final_class"] for r in scored})
        if protocol == HISTORICAL and requested > capacity:
            return {**row, "status": "BLOCKED_PS_CLASS_GUARD_CAPACITY"}
        effective = min(requested, capacity)
        if effective:
            removed = derive_ps([r["node_id"] for r in scored], [r["final_class"] for r in scored],
                                [r["confidence_percent"] for r in scored], effective)["removed_global_node_ids_in_deletion_order"]
        row.update(PS_requested=requested, PS_effective=effective, PS_shortfall=requested-effective, PS_removed_ids=removed)
    retained = [r for r in records if r["node_id"] not in set(removed)]
    conf = [r["confidence_percent"] for r in retained]
    row.update(train_ids=[r["node_id"] for r in retained], class_indices=[r["final_class"] for r in retained],
               confidence_percent=conf, weights=_weights(conf, loss, protocol),
               weight_status=["UNWEIGHTED_MISSING_CONFIDENCE" if c is None and loss == "wce" else
                              "CE_UNIT_WEIGHT" if loss == "ce" else "FROZEN_BASELINE_CONFIDENCE" for c in conf],
               class_counts_after=dict(Counter(str(r["final_class"]) for r in retained)))
    return row


def subset(row, common):
    if not common: return {**row, "status": "BLOCKED_EMPTY_COMMON_MASK"}
    result = dict(row)
    positions = [j for j, node in enumerate(row["train_ids"]) if node in common]
    for field in ("train_ids", "class_indices", "confidence_percent", "weight_status"):
        result[field] = [row[field][j] for j in positions]
    result["weights"] = _weights(result["confidence_percent"], row["loss"], row["protocol"])
    result["class_counts_after"] = dict(Counter(str(c) for c in result["class_indices"]))
    result["protected_ids"] = [i for i in row["protected_ids"] if i in common]
    return result


def build(report, *, runtime):
    reject_controls(report); reject_controls(runtime)
    old = previous.build_grid(report, digest(report))  # Domain/cohort/frozen-rule validation.
    rows = []
    for cohort in CONTRACT["cohorts"]:
        excluded = set(report["primary_excluded_ids"]) if cohort == "primary" else set()
        for protocol in CONTRACT["protocols"]:
            for loss in CONTRACT["losses"]:
                for ps in CONTRACT["PS"]:
                    natural = []
                    for arm in CONTRACT["arms"]:
                        records = [r for r in report["arms"][arm] if r["final_class"] is not None and r["node_id"] not in excluded]
                        r = values(records, loss=loss, ps=ps, protocol=protocol)
                        r.update(arm=arm, cohort=cohort, protocol=protocol, loss=loss, PS=ps, mask="natural", pair=None)
                        natural.append(r); rows.append(r)
                    for mode, group in [("matched_all", natural)] + [("pairwise", list(p)) for p in combinations(natural, 2)]:
                        ready = all(r["status"] == "DRAFT_NOT_ADMITTED" for r in group)
                        common = set.intersection(*(set(r["train_ids"]) for r in group)) if ready else set()
                        for r in group:
                            matched = subset(r, common) if ready else {**r, "status": "BLOCKED_UNDEFINED_COMMON_POST_PS_MASK"}
                            matched.update(mask=mode, pair=[p["arm"] for p in group] if mode == "pairwise" else None)
                            rows.append(matched)
                    for treatment in natural[3:]:
                        control = dict(treatment)
                        control.update(arm="NO_AGENT_FOR_"+treatment["arm"], mask="coverage_matched_no_agent", pair=["NO_AGENT", treatment["arm"]])
                        if treatment["status"] == "DRAFT_NOT_ADMITTED":
                            labels, sources = control_labels(report, treatment)
                            originals = {r["node_id"]: r for r in report["arms"]["C_BASELINE_FUSION"]}
                            conf = []
                            for node, label in zip(treatment["train_ids"], labels):
                                base = originals[node]
                                conf.append(min(base[k+"_confidence"] for k in ("b1", "narrative") if base[k+"_class"] == label))
                            control.update(class_indices=labels, confidence_percent=conf, weights=_weights(conf, loss, protocol),
                                label_sources=sources, protected_ids=[], missing_confidence_ids=[],
                                weight_status=["CE_UNIT_WEIGHT" if loss == "ce" else "FROZEN_BASELINE_CONFIDENCE"]*len(labels),
                                class_counts_after=dict(Counter(str(c) for c in labels)),
                                PS_note="INHERITED_TREATMENT_MASK_NOT_INDEPENDENT_CONTROL_FILTER")
                            control.update(inherited_treatment_PS={k: treatment[k] for k in
                                ("PS_requested", "PS_effective", "PS_shortfall", "PS_removed_ids")},
                                pre_PS_count=len(labels), PS_requested=0, PS_effective=0, PS_shortfall=0, PS_removed_ids=[],
                                class_counts_before=dict(Counter(str(c) for c in labels)))
                        rows.append(control)
    fits = {}
    config = json.loads(json.dumps(asdict(GCNConfig())))
    for r in rows:
        r["row_id"] = digest(r)
        if r["status"] != "DRAFT_NOT_ADMITTED": continue
        spec = {"graph_sha256": GRAPH_SHA256, "test_ids_sha256": old["test_ids_sha256"],
                "config": {**config, "loss": r["loss"]}, "train_ids": r["train_ids"],
                "class_indices": r["class_indices"], "weights": r["weights"], "runtime": runtime}
        sha = digest(spec); r["fit_sha256"] = sha
        fits.setdefault(sha, {"spec": spec, "row_ids": []})["row_ids"].append(r["row_id"])
    require(len(rows) == 960 and len({r["row_id"] for r in rows}) == 960)
    return {"schema": VERSION, "contract": CONTRACT, "rule_sha256": digest(CONTRACT),
            "fusion_sha256": digest(report), "selected_ids": report["cohort_ids"],
            "primary_excluded_ids": report["primary_excluded_ids"], "test_ids": old["test_ids"],
            "test_ids_sha256": old["test_ids_sha256"], "rows": rows, "fits": fits,
            "runtime": runtime, "unique_seed_fits": 10*len(fits), "training_runs": 0,
            "training_status": "NOT_RUN_BLOCKED", "scientific_status": "EXPLORATORY_NOT_INDEPENDENT"}


def public_rows(package):
    result = []
    for r in package["rows"]:
        agent = r["arm"].split("_")
        router = "r1_v1" if "r1" in agent else "r0" if "r0" in agent else None
        result.append({"Arm": r["arm"], "Router": router, "Policy": "P1" if "P1" in agent else "P2" if "P2" in agent else "BASELINE",
            "Cohort": r["cohort"], "Protocol": r["protocol"], "Loss": r["loss"], "PS": r["PS"],
            "Mask": r["mask"], "Pair": r["pair"], "Train Count": len(r.get("train_ids", [])) if r["status"] == "DRAFT_NOT_ADMITTED" else None,
            "Test Count": 2568, "Accuracy": None, "Macro-F1": None, "Mean": None, "SD": None, "Paired Delta": None,
            "Status": "NOT_RUN_BLOCKED_AUTHORIZATION" if r["status"] == "DRAFT_NOT_ADMITTED" else r["status"],
            "row_id": r["row_id"]})
    return result
