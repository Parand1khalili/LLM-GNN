"""Recompute final decisions from immutable stored parsed samples, not raw bodies."""
from __future__ import annotations

import math

from ..io.frozen import FrozenDataset, load_frozen, validate_dataset
from .voting import vote_parsed_samples


def replay_dataset(dataset: FrozenDataset) -> dict:
    validate_dataset(dataset)
    mismatches, predictions = [], []
    for row in dataset.predictions:
        result = vote_parsed_samples(tuple(s.parsed_answers for s in row.samples), dataset.classes)
        differences = []
        if result.class_index != row.class_index or result.prediction != row.prediction:
            differences.append("class")
        if not math.isclose(result.confidence_percent, row.confidence_percent, rel_tol=0, abs_tol=1e-12):
            differences.append("confidence_percent")
        if result.fallback_count != row.fallback_count:
            differences.append("fallback_count")
        if differences:
            mismatches.append({"target_id": row.target_id, "arm": row.arm, "fields": differences})
        predictions.append({"target_id": row.target_id, "arm": row.arm,
                            "class_index": result.class_index, "prediction": result.prediction,
                            "confidence_percent": result.confidence_percent,
                            "fallback_count": result.fallback_count})
    return {"schema": "sara.frozen_sample_replay.v1", "status": "PASS" if not mismatches else "FAIL",
            "scope": "STORED_PARSED_SAMPLES_ONLY",
            "evidence": "OFFLINE_REPLAYED" if dataset.input_evidence == "HASH_VERIFIED" else "UNVERIFIED_INPUT_REPLAY",
            "input_evidence": dataset.input_evidence,
            "target_count": len(dataset.target_ids), "predictions_checked": len(predictions),
            "predictions_matched": len(predictions) - len(mismatches), "confidence_abs_tolerance": 1e-12,
            "mismatches": mismatches, "predictions": predictions,
            "artifact_sha256": dict(dataset.artifact_hashes),
            "raw_response_provenance": "RAW_PROVENANCE_PARTIAL",
            "raw_hashes_verified_by_this_replay": 0, "raw_response_parsing": "NOT_RUN",
            "GT_accessed": False, "provider_calls": 0, "training_runs": 0}


def replay_frozen(b1_path, narrative_path, selection_path) -> dict:
    return replay_dataset(load_frozen(b1_path, narrative_path, selection_path))
