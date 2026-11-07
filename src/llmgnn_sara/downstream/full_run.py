"""Prepare or separately authorize full-matrix fits. This module never loads GT."""
import argparse
import csv
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import sys
from collections import Counter

from . import full_matrix as matrix
from . import fusion as downstream
from .ce_preflight import source_audit
from ..sara3 import fusion
from ..sara3.audit import PrivateAudit
from ..sara3.inputs import canonical_bytes
from ..sara3.experiment import digest
from ..sara3.correction_features import require
from ..io.frozen import read_pinned_json, reject_gt
from ..io.project import load_project_inputs, GRAPH_SHA256

APPROVAL = "sara.gcn.full_matrix.admission_training.v1"
AUDIT = "sara.gcn.limited_provenance_audit.v1"


def runtime(root):
    paths = ["downstream/"+n+".py" for n in ("full_run", "full_matrix", "model", "plan", "fusion", "ce_preflight")]
    paths += ["sara3/fusion.py", "filtering/ps.py", "io/project.py", "io/frozen.py"]
    code = {p: hashlib.sha256((Path(root)/"src/llmgnn_sara"/p).read_bytes()).hexdigest() for p in paths}
    versions = {n: importlib.metadata.version(n) for n in ("torch", "torch-geometric", "numpy")}
    return {"code_sha256": code, "versions": versions, "python": sys.version.split()[0],
            "device": "cpu", "threads": 1, "deterministic_algorithms": True}


def audit_record(package, root):
    # Preserve the older audit as evidence; do not relabel unknown origin VERIFIED.
    source = source_audit(package, root)
    return {"schema": AUDIT, "package_sha256": digest(package), "graph_sha256": GRAPH_SHA256,
            "test_ids_sha256": package["test_ids_sha256"], "runtime": package["runtime"],
            "status": "LIMITED_PROVENANCE_EXPLORATORY", "source_evidence": source,
            "encoder_receipt": "UNAVAILABLE_ORIGINAL_EXECUTION_NOT_PROVEN",
            "test_status": "HISTORICALLY_OBSERVED_NOT_INDEPENDENT",
            "training_authorized": False, "admission_authorized": False}


def approval_template(package, audit):
    return {"schema": APPROVAL, "package_sha256": digest(package), "audit_sha256": digest(audit),
            "allow_experimental_admission": False, "allow_real_training": False,
            "accept_limited_feature_provenance": False, "accept_historical_observed_test": False,
            "owner_authorized": False, "maximum_seed_fits": package["unique_seed_fits"]}


def authorize(package, audit, approval):
    if approval is None: raise PermissionError("Independent admission and real-training approval required")
    matrix.reject_controls(package); matrix.reject_controls(audit); matrix.reject_controls(approval)
    require(package["schema"] == matrix.VERSION and package["contract"] == matrix.CONTRACT
            and package["rule_sha256"] == digest(matrix.CONTRACT)
            and package["unique_seed_fits"] == 10*len(package["fits"]))
    require(all(digest(f["spec"]) == key and f["spec"]["runtime"] == package["runtime"]
                for key, f in package["fits"].items()))
    expected = approval_template(package, audit)
    require(type(approval) is dict and set(approval) == set(expected))
    require(all(approval[k] == v for k, v in expected.items() if type(v) is not bool))
    require(all(approval[k] is True for k, v in expected.items() if type(v) is bool))
    require(audit["schema"] == AUDIT and audit["package_sha256"] == digest(package)
            and audit["graph_sha256"] == GRAPH_SHA256 and audit["test_ids_sha256"] == package["test_ids_sha256"]
            and audit["runtime"] == package["runtime"] and audit["status"] == "LIMITED_PROVENANCE_EXPLORATORY"
            and audit["test_status"] == "HISTORICALLY_OBSERVED_NOT_INDEPENDENT")


def exclusive(path, blob):
    """No replacement. A partial write remains an incident, never an overwrite."""
    with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "wb") as stream:
        stream.write(blob); stream.flush(); os.fsync(stream.fileno())


def read_fit(root, package, fit_sha, seed):
    """Read-only reuse verification, no model unpickling or fitting."""
    import numpy as np
    directory = Path(root)/fit_sha/str(seed)
    if not directory.exists(): return None
    store = PrivateAudit(directory)
    complete, intent = directory/"complete.json", directory/"intent.json"
    require(not complete.is_symlink() and not intent.is_symlink())
    if not complete.exists():
        if intent.exists(): raise RuntimeError("UNCERTAIN_FIT_NO_AUTOMATIC_REPLAY")
        require(not list(directory.iterdir()))
        return None
    for path in (complete, intent, directory/"fit.npz"):
        require(not path.is_symlink())
        if os.name == "nt":
            from ..sara3.audit import _private_windows
            _private_windows(path, store.sid)
        else:
            import stat
            require(path.stat().st_uid == os.getuid() and stat.S_IMODE(path.stat().st_mode) == 0o600)
    completion = json.loads(complete.read_bytes()); require(set(completion) == {"receipt_sha256"})
    receipt = store.read(completion["receipt_sha256"])
    expected = {"package_sha256": digest(package), "fit_sha256": fit_sha, "seed": seed}
    require(all(receipt.get(k) == v for k, v in expected.items()) and receipt["state"] == "COMPLETED")
    require(len(receipt["losses"]) == 30 and all(math_finite(v) for v in receipt["losses"]))
    require(json.loads(intent.read_bytes()) == {**expected, "state": "INTENT_DURABLE_BEFORE_FIT"})
    artifact = directory/"fit.npz"
    require(not artifact.is_symlink() and artifact.stat().st_size < 64*1024*1024
            and hashlib.sha256(artifact.read_bytes()).hexdigest() == receipt["artifact_sha256"])
    with np.load(artifact, allow_pickle=False) as archive:
        logits, predictions = archive["logits"], archive["predictions"]
        require(logits.shape == (2708, 7) and predictions.shape == (2708,)
                and np.isfinite(logits).all() and predictions.dtype.kind in "iu"
                and np.array_equal(predictions, logits.argmax(axis=1))
                and any(k.startswith("state__") for k in archive.files))
        checkpoint_hash = hashlib.sha256()
        for key in archive.files:
            if not key.startswith("state__"): continue
            array = archive[key]
            require(array.dtype.kind in "fiu" and np.isfinite(array).all())
            checkpoint_hash.update(key[len("state__"):].encode("utf-8"))
            checkpoint_hash.update(str(array.dtype).encode("ascii"))
            checkpoint_hash.update(str(array.shape).encode("ascii")); checkpoint_hash.update(array.tobytes())
        require(checkpoint_hash.hexdigest() == receipt["final_parameter_sha256"])
    return receipt


def execute(package, audit, approval, graph, output, *, fitter=None):
    authorize(package, audit, approval)  # Must precede directory creation or dispatch.
    from .model import train_matrix_fit, _validate_graph
    _validate_graph(graph, 2708)
    import numpy as np
    import torch
    torch.set_num_threads(1); torch.use_deterministic_algorithms(True)
    fitter = fitter or train_matrix_fit
    completed, reused = 0, 0
    for fit_sha in sorted(package["fits"]):
        for seed in matrix.CONTRACT["seeds"]:
            if read_fit(output, package, fit_sha, seed) is not None:
                reused += 1; continue
            store = PrivateAudit(Path(output)/fit_sha/str(seed))
            binding = {"package_sha256": digest(package), "fit_sha256": fit_sha, "seed": seed}
            exclusive(store.root/"intent.json", canonical_bytes({**binding, "state": "INTENT_DURABLE_BEFORE_FIT"}))
            # Exceptions leave durable intent. Never automatically rerun an uncertain fit.
            result = fitter(graph, package, fit_sha, seed, allow_training=True)
            require(result["GT_accessed"] is False and result["evaluation_performed"] is False
                    and result["seed"] == seed and len(result["losses"]) == 30
                    and all(math_finite(x) for x in result["losses"]))
            logits = result["logits"].detach().cpu().numpy()
            require(logits.shape == (2708, 7) and np.isfinite(logits).all())
            arrays = {"state__"+k: v.detach().cpu().numpy() for k, v in result["model"].state_dict().items()}
            arrays.update(logits=logits, predictions=logits.argmax(axis=1))
            buffer = io.BytesIO(); np.savez_compressed(buffer, **arrays); blob = buffer.getvalue()
            exclusive(store.root/"fit.npz", blob)
            receipt = {**binding, "state": "COMPLETED", "artifact_sha256": hashlib.sha256(blob).hexdigest(),
                       "losses": result["losses"], "initial_parameter_sha256": result["initial_parameter_sha256"],
                       "final_parameter_sha256": result["final_parameter_sha256"], "evaluation_performed": False}
            sha = store.write(receipt)
            exclusive(store.root/"complete.json", canonical_bytes({"receipt_sha256": sha}))
            require(read_fit(output, package, fit_sha, seed) == receipt)
            completed += 1
    return {"completed_seed_fits": completed, "verified_reused_seed_fits": reused, "GT_evaluation": "NOT_PERFORMED"}


def math_finite(value):
    import math
    return type(value) in (int, float) and math.isfinite(value)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "train"))
    for name in ("fusion", "features", "frozen-root", "authentic-root", "graph", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--fusion-sha256", required=True)
    for name in ("package-sha256", "audit-sha256", "approval-sha256"):
        parser.add_argument("--"+name)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--public-table", type=Path)
    args = parser.parse_args(argv)
    try:
        root = Path(__file__).resolve().parents[3]
        report = read_pinned_json(args.fusion, args.fusion_sha256)
        table = read_pinned_json(args.features, fusion.FEATURE_SHA)
        inputs = load_project_inputs(args.frozen_root, args.authentic_root)
        fusion.validate_report(report, table, inputs)
        graph = downstream.graph_inputs(args.graph)
        downstream.verify_historical_ps(downstream.build_grid(report, digest(report)), args.frozen_root)
        package = matrix.build(report, runtime=runtime(root))
        audit = audit_record(package, root)
        require(".local_artifacts" in args.output.absolute().parts)
        store = PrivateAudit(args.output)
        if args.mode == "prepare":
            sha = store.write(package); audit_sha = store.write(audit)
            blank = store.write(approval_template(package, audit))
            require(store.read(sha) == package and store.read(audit_sha) == audit)
            if args.public_table:
                public = matrix.public_rows(package)
                stream = io.StringIO(newline=""); writer = csv.DictWriter(stream, fieldnames=list(public[0]))
                writer.writeheader(); writer.writerows(public); blob = stream.getvalue().encode("utf-8")
                require(args.public_table.parent.resolve() == (root/"reports").resolve() and not args.public_table.is_symlink())
                if args.public_table.exists(): require(args.public_table.read_bytes() == blob)
                else: exclusive(args.public_table, blob)
            print(json.dumps({"package_sha256": sha, "audit_sha256": audit_sha, "blank_approval_sha256": blank,
                "matrix_rows": len(package["rows"]), "status_counts": dict(Counter(r["status"] for r in package["rows"])),
                "unique_seed_fits": package["unique_seed_fits"], "training_runs": 0,
                "status": "NOT_RUN_BLOCKED_INDEPENDENT_ADMISSION_TRAINING_APPROVAL"}))
        else:
            require(args.package_sha256 == digest(package) and args.audit_sha256 == digest(audit))
            approval = read_pinned_json(args.approval, args.approval_sha256) if args.approval else None
            authorize(package, audit, approval)
            require(sys.stdin.isatty())
            require(input("Authorize full matrix admission/training; type APPROVE FULL MATRIX "+digest(package)+": ").strip()
                    == "APPROVE FULL MATRIX "+digest(package))
            print(json.dumps(execute(package, audit, approval, graph, store.root/"fits")))
        return 0
    except Exception:
        print('{"status":"FAIL_CLOSED_NOT_RUN_OR_PARTIAL_INSPECT_PRIVATE_INTENTS"}', file=sys.stderr)
        return 1


if __name__ == "__main__": raise SystemExit(main())
