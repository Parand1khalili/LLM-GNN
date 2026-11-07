"""Private CE/noPS preparation only. No GT decoder, admission or training dispatch."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

from . import fusion as downstream
from ..sara3 import fusion
from ..sara3.audit import PrivateAudit
from ..sara3.correction_features import require
from ..sara3.experiment import digest
from ..io.frozen import read_pinned_json, reject_gt
from ..io.project import load_project_inputs, GRAPH_SHA256

VERSION = "sara.gcn.ce_preflight.v1"
CONTROL = {
    "version": "sara.gcn.coverage_matched_no_agent.v1",
    "agreement": "USE_AGREED_CLASS_WITHOUT_CONFIDENCE_THRESHOLD",
    "disagreement": "HIGHER_FROZEN_BASELINE_CONFIDENCE_UNCALIBRATED",
    "equal_confidence": "SORT_CLASSES_THEN_SHA256_VERSION_COLON_NODE_ID_MOD_2",
    "mask": "EXACT_TREATMENT_TRAIN_IDS_NO_RESELECTION",
    "status": "SEPARATE_DRAFT_CONTROL_NOT_A_FUSION_POLICY",
}
HISTORICAL_SOURCES = {
    "recovered_sources/src/models/nn.py": "5d00c347e5a6aa504de9bf8c5abbd6e084efa1302e004c142567b9dc364b4b9b",
    "recovered_sources/experiments/matched_cora/featprop_downstream_primary_ps_selection_001/ps_selection_runner_source.py":
        "00f846cc3c53d5f3f42c12142129890bed56d98bb9d0c0d6da6eae3ccdd5b102",
    "recovered_sources/experiments/matched_cora/featprop_downstream_sensitivity_ps_selection_001/ps_selection_runner_source.py":
        "491a7ea84280030843294fcd506aae9d944d22087d047421995132eb4ffab5fe",
}


def source_audit(package, root):
    evidence = {}
    for name, expected in HISTORICAL_SOURCES.items():
        actual = hashlib.sha256((Path(root) / name).read_bytes()).hexdigest()
        require(actual == expected)
        evidence[name] = actual
    for name in ("src/llmgnn_sara/downstream/model.py", "src/llmgnn_sara/downstream/plan.py",
                 "src/llmgnn_sara/downstream/fusion.py", "src/llmgnn_sara/downstream/ce_preflight.py"):
        evidence[name] = hashlib.sha256((Path(root) / name).read_bytes()).hexdigest()
    environment = {"python": sys.version.split()[0], "device_plan": "CPU_ALL_ARMS_SAME_ENVIRONMENT"}
    for name in ("torch", "torch-geometric", "numpy"):
        try: environment[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: environment[name] = "MISSING"
    return {"schema": "sara.gcn.source_audit.v1", "package_sha256": digest(package),
        "graph_sha256": GRAPH_SHA256, "test_ids_sha256": package["test_ids_sha256"],
        "status": "REVIEW_REQUIRED_NOT_AUTHORIZED", "source_hashes": evidence, "environment": environment,
        "feature_generation_gt_isolation": "UNVERIFIED_ENCODER_EXECUTION_PROVENANCE",
        "feature_storage_integrity": "PASS_HASH_PINNED_RAW_X_AND_EDGE_ONLY",
        "historical_observed_test_acknowledged": False,
        "test_observation_evidence": "RECOVERED_RUNNER_SCORES_FIXED_2568_TEST_AND_CHECKS_PRIOR_RESULTS",
        "gt_origin": "HASH_PINNED_GRAPH_Y_FOR_SEPARATE_EVALUATION_ONLY_NOT_DECODED_HERE",
        "direct_test_leakage_into_current_training": "NO_LABEL_PATH_IN_GRAPHINPUTS_OR_PSEUDOLABEL_PLAN",
        "historical_tuning_contamination": "CANNOT_EXCLUDE_NO_INDEPENDENT_TEST_CLAIM",
        "blocking_items": ["ENCODER_GENERATION_PROVENANCE", "OWNER_REVIEW_OF_EXPLORATORY_TEST",
                           "SEPARATE_EXPERIMENTAL_ADMISSION", "EXPLICIT_REAL_TRAINING_AUTHORIZATION"],
        "training_runs": 0}


def control_labels(report, row):
    """Prespecified GT-free choice; Agent classes never enter this calculation."""
    baseline = {r["node_id"]: r for r in report["arms"]["C_BASELINE_FUSION"]}
    require(len(row["train_ids"]) == len(set(row["train_ids"])))
    labels, provenance = [], []
    for node in row["train_ids"]:
        r = baseline[node]
        b, n = r["b1_class"], r["narrative_class"]
        bc, nc = r["b1_confidence"], r["narrative_confidence"]
        require(type(b) is int and type(n) is int and 0 <= b < 7 and 0 <= n < 7)
        require(type(bc) in (int, float) and type(nc) in (int, float)
                and 0 <= bc <= 100 and 0 <= nc <= 100)
        if b == n:
            label, source = b, "BASELINE_AGREEMENT"
        elif bc != nc:
            label, source = (b, "B1_HIGHER_CONFIDENCE") if bc > nc else (n, "NARRATIVE_HIGHER_CONFIDENCE")
        else:
            bit = int(hashlib.sha256(f"{CONTROL['version']}:{node}".encode("ascii")).hexdigest(), 16) % 2
            label, source = sorted((b, n))[bit], "FIXED_HASH_TIE"
        labels.append(label)
        provenance.append(source)
    return labels, provenance


def fit_spec(grid, row):
    return {"graph_sha256": GRAPH_SHA256, "test_ids_sha256": grid["test_ids_sha256"],
            "config": grid["config"], "train_ids": row["train_ids"],
            "class_indices": row["class_indices"], "weights": row["weights"]}


def prepare(report, grid, *, cohort):
    """Rebuild the grid instead of trusting a supplied draft's labels or masks."""
    reject_gt(report); reject_gt(grid)
    require(cohort in ("primary", "sensitivity"))
    rebuilt = downstream.build_grid(report, digest(report))
    require(all(grid.get(k) == v for k, v in rebuilt.items()))
    natural = [r for r in rebuilt["plans"] if r["cohort"] == cohort and r["loss"] == "ce"
               and not r["PS"] and r["mask_mode"] == "natural"]
    matched = [r for r in rebuilt["plans"] if r["cohort"] == cohort and r["loss"] == "ce"
               and not r["PS"] and r["mask_mode"] == "matched_all_arms"]
    require([r["arm"] for r in natural] == downstream.CONTRACT["arms"]
            and all(r["status"] == "DRAFT_NOT_ADMITTED" for r in natural + matched))
    controls = []
    for row in natural:
        if not row["arm"].startswith(("D_", "E_")): continue
        labels, sources = control_labels(report, row)
        controls.append({"arm": "NO_AGENT_FOR_" + row["arm"], "treatment_arm": row["arm"],
            "train_ids": row["train_ids"].copy(), "class_indices": labels, "weights": row["weights"].copy(),
            "label_sources": sources, "confidence_percent": None,
            "status": "DRAFT_NOT_ADMITTED_SEPARATE_CONTROL_APPROVAL_REQUIRED"})
    fits = {}
    for row in natural + controls:
        spec = fit_spec(rebuilt, row); sha = digest(spec)
        fits.setdefault(sha, {"spec": spec, "arms": [], "seeds": list(range(10))})["arms"].append(row["arm"])
    common = next(r for r in matched if r["arm"] == "C_BASELINE_FUSION")
    return {"schema": VERSION, "fusion_sha256": digest(report), "grid_sha256": digest(grid),
        "cohort": cohort, "control_contract": CONTROL, "control_rule_sha256": digest(CONTROL),
        "natural": natural, "coverage_controls": controls, "fits": fits,
        "natural_seed_fits": 10 * len({r["fit_spec_sha256"] for r in natural}),
        "natural_plus_controls_seed_fits": 10 * len(fits),
        "matched": {"train_count": len(common["train_ids"]),
            "r0_equal_to_no_agent_C": {r["arm"]: r["class_indices"] == common["class_indices"]
                for r in matched if r["arm"] in ("D_P1_r0", "E_P2_r0")},
            "estimand": "CLASS_EFFECT_ON_INTERSECTION_EXCLUDES_ADDED_TRAIN_LABELS"},
        "test_ids_sha256": rebuilt["test_ids_sha256"], "test_count": len(rebuilt["test_ids"]),
        "test_status": "HISTORICALLY_OBSERVED_EXPLORATORY_NOT_INDEPENDENT",
        "historical_fit_reuse": "NONE_ADMITTED_NO_EXACT_FIT_AND_ENVIRONMENT_RECEIPT",
        "training_status": "NOT_RUN_BLOCKED", "training_runs": 0,
        "actual_metrics": [], "admission": "NONE", "real_training_authorized": False}


def validate_approval(package, audit, approval):
    """Check actual audit content, not merely a syntactically valid audit hash.

    This does not admit labels or set the backend's allow_training flag.
    """
    if approval is None: raise PermissionError("Fresh real-training and independent admission approval required")
    require(type(approval) is dict and set(approval) == {"schema", "package_sha256", "audit_sha256",
            "owner_authorized", "allow_real_training", "allow_experimental_admission"})
    require(approval["schema"] == VERSION and approval["package_sha256"] == digest(package)
            and approval["audit_sha256"] == digest(audit)
            and all(approval[k] is True for k in ("owner_authorized", "allow_real_training", "allow_experimental_admission")))
    require(audit["schema"] == "sara.gcn.source_audit.v1" and audit["package_sha256"] == digest(package)
            and audit["graph_sha256"] == GRAPH_SHA256 and audit["test_ids_sha256"] == package["test_ids_sha256"]
            and audit["status"] == "AUDITED_EXPLORATORY_SPLIT"
            and audit["feature_generation_gt_isolation"] == "VERIFIED"
            and audit["historical_observed_test_acknowledged"] is True)


def summary(package):
    """Explicit public allowlist: no individual node labels, article text or GT."""
    return {"schema": VERSION, "package_sha256": digest(package), "cohort": package["cohort"],
        "natural_counts": {r["arm"]: len(r["train_ids"]) for r in package["natural"]},
        "coverage_controls": {r["treatment_arm"]: {"train_count": len(r["train_ids"]),
            "different_labels": sum(a != b for a, b in zip(r["class_indices"], next(
                p["class_indices"] for p in package["natural"] if p["arm"] == r["treatment_arm"])))}
            for r in package["coverage_controls"]},
        "matched": package["matched"], "natural_seed_fits": package["natural_seed_fits"],
        "natural_plus_controls_seed_fits": package["natural_plus_controls_seed_fits"],
        "test_count": package["test_count"], "test_status": package["test_status"],
        "training_status": package["training_status"], "training_runs": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("fusion", "grid", "features", "frozen-root", "authentic-root", "graph", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--fusion-sha256", required=True)
    parser.add_argument("--grid-sha256", required=True)
    parser.add_argument("--cohort", choices=("primary", "sensitivity"), default="primary")
    args = parser.parse_args(argv)
    try:
        report = read_pinned_json(args.fusion, args.fusion_sha256)
        grid = read_pinned_json(args.grid, args.grid_sha256)
        table = read_pinned_json(args.features, fusion.FEATURE_SHA)
        inputs = load_project_inputs(args.frozen_root, args.authentic_root)
        fusion.validate_report(report, table, inputs)
        downstream.graph_inputs(args.graph)
        downstream.verify_historical_ps(grid, args.frozen_root)
        package = prepare(report, grid, cohort=args.cohort)
        require(".local_artifacts" in args.output.absolute().parts)
        store = PrivateAudit(args.output); sha = store.write(package)
        require(store.read(sha) == package)
        audit = source_audit(package, Path(__file__).resolve().parents[3])
        audit_sha = store.write(audit); require(store.read(audit_sha) == audit)
        print(json.dumps({**summary(package), "source_audit_sha256": audit_sha,
                          "blocking_items": audit["blocking_items"]}, sort_keys=True))
        return 0
    except Exception:
        print('{"status":"FAIL_CLOSED"}', file=sys.stderr)
        return 1


if __name__ == "__main__": raise SystemExit(main())
