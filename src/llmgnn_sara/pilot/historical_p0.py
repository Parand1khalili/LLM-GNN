"""Validate reconstructed P0 selection only; no prompts, transport or generation."""
import argparse
import json
from pathlib import Path

from ..io.frozen import (PINS, load_frozen, read_pinned_json, reject_gt, require,
                         validate_dataset)

MANIFEST_SHA256 = "7affacee222dbec3ecb5710b038968543c19d252190ee6eab76c5b03a4307410"
GROUPS = {"A": (734, 2379, 2490, 682), "B": (1031, 655, 1013, 1328)}


def _validate_selection(manifest, dataset):
    """Internal checks; only validate_p0 admits original input bytes and pins."""
    reject_gt(manifest)
    validate_dataset(dataset)
    require(dataset.input_evidence == "HASH_VERIFIED", "Pinned frozen inputs required")
    require(manifest.get("schema") == "sara.historical_p0.v1"
            and manifest.get("status") == "RECONSTRUCTED_SELECTION_CONTRACT_NOT_RECOVERED_WIRE",
            "P0 evidence status differs")
    require(manifest.get("frozen_input_sha256") == PINS, "P0 frozen provenance differs")
    require(manifest.get("groups") == {g: list(ids) for g, ids in GROUPS.items()},
            "Historical P0 groups/order differ")
    expected = [{"node_id": n, "group": group, "arm": arm}
                for group, ids in GROUPS.items() for n in ids
                for arm in (("Judge002", "SARA3_V1") if group == "A" else ("SARA3_V1",))]
    records = manifest.get("logical_records")
    require(records == expected, "Historical P0 node/arm records differ")
    require(all(type(r["node_id"]) is int for r in records), "Integer node IDs required")
    ids = {r["node_id"] for r in records}
    require(len(ids) == 8 and len(records) == 12
            and len({(r["node_id"], r["arm"]) for r in records}) == 12,
            "Historical P0 uniqueness/count differs")
    require(ids <= set(dataset.target_ids), "P0 nodes outside frozen cohort")
    contract = manifest.get("group_b_contract", {})
    require(contract == {"agreement_required": True, "hh_min_confidence_percent": 80,
                        "hh_definition_evidence": "SECONDARY_REPORTED_DESCRIPTIVE_BUCKET_NOT_COMPLETE_POLICY_002",
                        "historical_r1_membership": "REPORTED_UNVERIFIED",
                        "historical_outside_r0_membership": "REPORTED_UNVERIFIED"},
            "Group B historical evidence/HH definition differs")
    by_arm = {arm: {r.target_id: r for r in dataset.by_arm(arm)}
              for arm in ("b1", "narrative_v0")}
    require(all(ids <= set(rows) for rows in by_arm.values()), "P0 annotation coverage differs")
    hh = []
    for node in GROUPS["B"]:
        b1, narrative = (by_arm[arm][node] for arm in ("b1", "narrative_v0"))
        require(b1.class_index == narrative.class_index, "Group B agreement failed")
        require(min(b1.confidence_percent, narrative.confidence_percent) >= 80,
                "Group B descriptive HH check failed")
        hh.append({"node_id": node, "agreement": True, "hh": True,
                   "b1_confidence_percent": b1.confidence_percent,
                   "narrative_v0_confidence_percent": narrative.confidence_percent})
    return {"status": "PASS", "scope": "RECONSTRUCTED_P0_SELECTION_ONLY_NOT_P1_WIRE_REPRODUCTION",
            "unique_nodes": 8, "logical_records": 12, "arm_counts": {"Judge002": 4, "SARA3_V1": 8},
            "cohort_size": len(dataset.target_ids), "group_b_checks": hh,
            "historical_r1_membership": "REPORTED_UNVERIFIED",
            "historical_outside_r0_membership": "REPORTED_UNVERIFIED",
            "v1_generation_calls_per_record": "UNKNOWN_DO_NOT_ASSUME_TWO",
            "frozen_input_sha256": dict(dataset.artifact_hashes),
            "missing_evidence": manifest["missing_evidence"],
            "provider_calls": 0, "token_count_requests": 0, "training_runs": 0,
            "ground_truth_accessed": False}


def validate_p0(manifest_path, frozen_root):
    """Read-only, hash-admitted entry point. Never reads raw bodies or graph GT."""
    manifest = read_pinned_json(manifest_path, MANIFEST_SHA256)
    root = Path(frozen_root)
    dataset = load_frozen(root / "b1_final_predictions.json",
                          root / "narrative_v0_final_predictions.json",
                          root / "selection_manifest.json")
    return {**_validate_selection(manifest, dataset), "manifest_sha256": MANIFEST_SHA256}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--frozen-root", required=True)
    args = parser.parse_args()
    print(json.dumps(validate_p0(args.manifest, args.frozen_root), indent=2))


if __name__ == "__main__":
    main()
