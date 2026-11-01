"""Temporary synthetic three-arm integration, never a real annotation experiment."""
import argparse
from collections import Counter
import json
from pathlib import Path
import tempfile

from ..io.project import load_project_inputs
from ..sara3.audit import PrivateAudit
from ..sara3.experiment import FIXTURE_VERSION, MANIFEST_SHA256, build_manifest, load_selection
from ..sara3.experiment_cache import CachedOfflineVerifier
from ..sara3.pipeline import run_offline


class SyntheticExperimentVerifier:
    """Fixed modulo4 cases; outputs are test data, not semantic judgments."""
    offline = True
    fixture_version = FIXTURE_VERSION

    def __init__(self, pairs):
        self.pairs = {p.node_id: p for p in pairs}

    def _response(self, request, compare=False):
        mode = request.node_id % 4
        if mode == 0 or (compare and mode == 2):
            return {"class_index": None, "abstain": True, "evidence": []}
        pair = self.pairs[request.node_id]
        label = next(c for c in range(7) if c not in {pair.b1.class_index, pair.narrative_v0.class_index}) if mode == 1 else pair.b1.class_index
        return {"class_index": label, "abstain": False, "evidence": [request.text.strip()[:120]]}

    def blind(self, request):
        return self._response(request)

    def compare(self, request):
        return self._response(request, True)


def exercise_experiment(inputs, manifest_path):
    manifest = build_manifest(inputs)
    candidates = {p.node_id: {p.b1.class_index, p.narrative_v0.class_index} for p in inputs.pairs}
    selections = {arm: load_selection(manifest_path, MANIFEST_SHA256, arm, inputs)
                  for arm in manifest["primary_arms"]}
    summaries, common = {}, {}
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        cache = CachedOfflineVerifier(SyntheticExperimentVerifier(inputs.pairs),
            manifest["execution_context"], PrivateAudit(root / "cache"))
        for arm, selection in selections.items():
            run = run_offline(inputs.pairs, 37, verifier=cache,
                              audit=PrivateAudit(root / arm), selection=selection)
            decisions = run["decisions"]
            accepted = [d for d in decisions if d["accepted"]]
            if (len({d["node_id"] for d in accepted}) != len(accepted)
                    or any(d["training_class_index"] not in candidates[d["node_id"]] for d in accepted)):
                raise ValueError("Duplicate or third-class training labels")
            if len({d["node_id"] for d in decisions}) != 140:
                raise ValueError("Duplicate/missing experiment decisions")
            reviewed = [d for d in decisions if d["routed_for_review"]]
            if len(reviewed) != 37 or any(d["accepted"] or d["training_class_index"] is not None
                                           or d["l2_status"] != "NOT_ASSESSED" for d in reviewed):
                raise ValueError("Conservative reviewed-label boundary failed")
            for request in run["verifier_inputs"]:
                key = request["payload"]["node_id"], request["payload"]["phase"]
                if common.setdefault(key, request["sha256"]) != request["sha256"]:
                    raise ValueError("Common-node effective requests differ")
            summaries[arm] = {"selected_ids": run["selected_node_ids"],
                "selected_count": len(reviewed), "logical_fixture_requests": run["mock_verifier_calls"],
                "reason_counts": dict(sorted(Counter(d["reason"] for d in reviewed).items())),
                "accepted_reviewed": 0, "unreviewed_baseline_retained": run["accepted_count"],
                "l2_status": "NOT_ASSESSED", "decision_node_ids_unique": True,
                "training_labels_unique": True, "third_class_accepted": 0}
        execution = {"underlying_synthetic_dispatches": cache.dispatches, "cache_hits": cache.hits,
                     "completed_unique_identities": len(cache.cache),
                     "noncompleted_identities": sum(s != "COMPLETED" for s in cache.states.values())}
    return {"schema_version": "sara.routing.experiment.offline_validation.v1",
        "manifest_sha256": MANIFEST_SHA256, "evidence_level": "SYNTHETIC_FIXTURES_NOT_SCIENTIFIC_FINDINGS",
        "arms": summaries, "synthetic_execution": execution, "accounting_bounds": manifest["accounting"],
        "common_node_request_invariance": "PASS", "raw_audit": "PRIVATE_TEMPORARY_REMOVED_AFTER_RUN",
        "live_execution": "NOT_AUTHORIZED_FOR_LIVE_EXECUTION", "ground_truth_accessed": False,
        "human_review_accessed": False, "provider_calls": 0, "training_runs": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-root", required=True)
    parser.add_argument("--authentic-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = exercise_experiment(load_project_inputs(args.frozen_root, args.authentic_root), args.manifest)
    with Path(args.output).open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
