"""Read the immutable pre-Codex *parsed* evidence, never graph labels or raw bodies.

Original source paths/IDs and pins are in manifests/recovered_sources.json.
Input JSON hashes are frozen scientific pins, not supplied by the caller.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat

CLASSES = ("rule_learning", "neural_networks", "case_based", "genetic_algorithms",
           "theory", "reinforcement_learning", "probabilistic_methods")
PINS = {
    "b1": "c6bc236ac5f8c1615067a10750cb150ecaf54fbe458afd4df7e750f92ce4b141",
    "narrative_v0": "181806c4622449c8f9cdc9bdabb725232666fdc95394b3a8d7b78067b385ff02",
    "selection": "dc8260974c7c0ca2e828f2d069e2896e9bcf2c363b15ca81d9f09d2803c9b12c",
}
MAX_JSON_BYTES = 16 * 1024 * 1024
RAW_PREFIXES = ("experiments/matched_cora/featprop_infer_001/slots/",
                "experiments/matched_cora/featprop_reannotation_001/slots/",
                "experiments/matched_cora/matched_infer_003/requests/")
FORBIDDEN_KEYS = frozenset({"y", "raw_y", "fixed_y", "gt", "gt_y", "ground_truth",
    "ground_truth_labels", "true_label", "true_labels", "test_labels", "test_outcomes",
    "is_correct", "correctness", "confusion_matrix", "wrong_node_ids", "e0", "e1"})


class InputError(ValueError):
    """Safe error messages contain no input response text or account secrets."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise InputError(message)


def reject_gt(value) -> None:
    """Reject label-bearing/diagnostic fields, while allowing class vocabulary."""
    if isinstance(value, dict):
        for key, item in value.items():
            require(isinstance(key, str), "Non-string object key")
            require(key.casefold() not in FORBIDDEN_KEYS, "GT/diagnostic field rejected")
            if key == "ground_truth_accessed":
                require(item is False, "GT access marker rejected")
            reject_gt(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            reject_gt(item)


def _pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def read_pinned_json(path: str | Path, expected_sha256: str):
    """Hash the same bounded bytes parsed; never follow filesystem symlinks."""
    path = Path(path)
    require(bool(re.fullmatch(r"[0-9a-f]{64}", expected_sha256)), "Invalid SHA-256 pin")
    for component in (path, *path.parents):
        require(not component.is_symlink(), "Symlink input rejected")
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                             | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode), "Input must be a regular file")
            require(info.st_size <= MAX_JSON_BYTES, "Input exceeds size limit")
            blob = stream.read(MAX_JSON_BYTES + 1)
    except OSError:
        raise InputError("Required input missing or inaccessible") from None
    require(len(blob) <= MAX_JSON_BYTES, "Input exceeds size limit")
    require(hashlib.sha256(blob).hexdigest() == expected_sha256, "SHA-256 mismatch")
    try:
        obj = json.loads(blob.decode("utf-8-sig"), object_pairs_hook=_pairs,
                         parse_constant=lambda _: (_ for _ in ()).throw(InputError("Nonfinite JSON")))
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise InputError("Invalid JSON") from None
    reject_gt(obj)
    return obj


def _integer(value, low: int, high: int) -> bool:
    return type(value) is int and low <= value < high


def _number(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _sha(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


@dataclass(frozen=True)
class FrozenSample:
    sample_index: int
    parsed_answers: tuple[tuple[str, float], ...]
    original_request_index: int
    source_kind: str
    source_response_path: str
    source_response_sha256: str
    prompt_sha256: str


@dataclass(frozen=True)
class FrozenPrediction:
    target_id: int
    arm: str
    class_index: int
    prediction: str
    confidence_percent: float
    fallback_count: int
    samples: tuple[FrozenSample, ...]


@dataclass(frozen=True)
class FrozenDataset:
    target_ids: tuple[int, ...]
    classes: tuple[str, ...]
    predictions: tuple[FrozenPrediction, ...]
    artifact_hashes: tuple[tuple[str, str], ...] = ()
    input_evidence: str = "UNVERIFIED"

    def by_arm(self, arm: str) -> tuple[FrozenPrediction, ...]:
        require(arm in ("b1", "narrative_v0"), "Unknown annotation arm")
        return tuple(row for row in self.predictions if row.arm == arm)


def _validate_objects(b1: dict, narrative: dict, selection: dict) -> FrozenDataset:
    """Schema validation is independently testable without replacing scientific pins."""
    for obj in (b1, narrative, selection):
        reject_gt(obj)
        require(isinstance(obj, dict), "Input must be an object")
    ids = selection.get("selected_global_node_ids_sorted")
    require(isinstance(ids, list) and len(ids) == 140
            and all(_integer(i, 0, 2708) for i in ids)
            and len(set(ids)) == 140 and ids == sorted(ids), "Invalid FeatProp selection")
    order = b1.get("target_ids_in_manifest_order")
    require(isinstance(order, list) and len(order) == 140 and all(type(i) is int for i in order)
            and len(set(order)) == 140 and set(order) == set(ids), "Target alignment mismatch")
    predictions, seen_indices, seen_paths, source_counts = [], set(), set(), Counter()
    for arm, obj in (("b1", b1), ("narrative_v0", narrative)):
        require(obj.get("schema") == "featprop_parser_vote_final_predictions_001"
                and obj.get("arm") == arm and obj.get("ground_truth_accessed") is False,
                "Frozen output metadata mismatch")
        require(obj.get("ordered_classes") == list(CLASSES), "Class schema/order mismatch")
        require(obj.get("target_ids_in_manifest_order") == order, "Arm target order mismatch")
        rows = obj.get("predictions_by_target_id")
        require(isinstance(rows, dict) and set(rows) == {str(t) for t in order}, "Prediction coverage mismatch")
        for target in order:
            row = rows[str(target)]
            require(isinstance(row, dict) and row.get("target_id") == target and type(row["target_id"]) is int
                    and row.get("arm") == arm and row.get("ground_truth_accessed") is False,
                    "Prediction identity mismatch")
            require(row.get("failure") is None and row.get("retries") == 0
                    and row.get("repair") == {"applied": False, "budget": 0}, "Frozen failure/repair differs")
            ci, cp = row.get("class_index"), row.get("confidence_percent_before_tensor_cast")
            require(_integer(ci, 0, 7) and row.get("prediction") == CLASSES[ci], "Prediction class mismatch")
            require(_number(cp) and 0 <= cp <= 100, "Invalid frozen confidence")
            fallback = row.get("historical_all_invalid_fallback_count")
            require(_integer(fallback, 0, 2), "Invalid fallback count")
            raw_samples = row.get("primary_samples")
            require(isinstance(raw_samples, list) and len(raw_samples) == 3, "Exactly three samples required")
            samples = []
            for si, sample in enumerate(raw_samples):
                require(isinstance(sample, dict) and sample.get("sample_index") == si
                        and type(sample["sample_index"]) is int and sample.get("target_id") == target
                        and type(sample["target_id"]) is int and sample.get("arm") == arm,
                        "Sample identity/order mismatch")
                index = sample.get("original_request_index")
                require(_integer(index, 0, 840) and index not in seen_indices, "Duplicate/invalid request index")
                seen_indices.add(index)
                answers = sample.get("parsed_answers_for_three_sample_vote")
                require(isinstance(answers, list) and bool(answers), "Empty parsed sample")
                parsed = []
                for answer in answers:
                    require(isinstance(answer, (list, tuple)) and len(answer) == 2
                            and isinstance(answer[0], str) and _number(answer[1])
                            and 0 <= answer[1] <= 100, "Invalid parsed answer")
                    parsed.append((answer[0], answer[1]))
                first = parsed[0]
                require(sample.get("first_answer_for_vote") == first[0]
                        and sample.get("first_confidence_for_vote") == first[1]
                        and sample.get("first_class_index_for_vote") == (CLASSES.index(first[0]) if first[0] in CLASSES else None),
                        "Stored parsed answer metadata differs")
                kind, path = sample.get("source_kind"), sample.get("source_response_path")
                pin, prompt = sample.get("source_response_sha256"), sample.get("prompt_sha256")
                require(kind in ("original_fresh", "supplementary", "historical_reuse"), "Invalid source kind")
                require(isinstance(path, str) and path.startswith(RAW_PREFIXES) and path.endswith(".json")
                        and "\\" not in path and ":" not in path
                        and all(part not in ("", ".", "..") for part in path.split("/"))
                        and not any(ord(c) < 32 for c in path) and path not in seen_paths,
                        "Unsafe/duplicate raw reference")
                require(_sha(pin) and _sha(prompt), "Invalid provenance hash")
                seen_paths.add(path)
                source_counts[kind] += 1
                samples.append(FrozenSample(si, tuple(parsed), index, kind, path, pin, prompt))
            require([s.original_request_index for s in samples] == row.get("original_request_indices")
                    and [s.source_response_sha256 for s in samples] == row.get("selected_response_sha256_by_sample_index")
                    and {s.prompt_sha256 for s in samples} == {row.get("prompt_sha256")}
                    and {s.source_kind for s in samples} == {row.get("source_kind")}, "Pair provenance differs")
            predictions.append(FrozenPrediction(target, arm, ci, row["prediction"], float(cp), fallback, tuple(samples)))
    require(seen_indices == set(range(840)), "Incomplete request order")
    require(source_counts == {"original_fresh": 726, "supplementary": 30, "historical_reuse": 84}, "Source counts differ")
    return FrozenDataset(tuple(order), CLASSES, tuple(predictions))


def validate_dataset(dataset: FrozenDataset) -> None:
    """Fail closed on incomplete or manually forged public-API dataset shapes.

Only load_frozen attaches actual hash-verification evidence. Objects validated
without original input bytes remain UNVERIFIED, even when their votes match.
"""
    require(isinstance(dataset, FrozenDataset), "FrozenDataset required")
    require(dataset.classes == CLASSES and isinstance(dataset.target_ids, tuple)
            and len(dataset.target_ids) == 140 and len(set(dataset.target_ids)) == 140
            and all(_integer(t, 0, 2708) for t in dataset.target_ids), "Invalid dataset target/class contract")
    require(isinstance(dataset.predictions, tuple) and len(dataset.predictions) == 280,
            "Full replay requires280 predictions")
    require(dataset.input_evidence in ("UNVERIFIED", "HASH_VERIFIED"), "Invalid input evidence")
    if dataset.input_evidence == "HASH_VERIFIED":
        require(dataset.artifact_hashes == tuple(PINS.items()), "Artifact verification evidence differs")
    else:
        require(dataset.artifact_hashes == (), "Unverified objects cannot claim artifact hashes")
    pairs, indices, paths, counts = set(), set(), set(), Counter()
    for row in dataset.predictions:
        require(isinstance(row, FrozenPrediction) and type(row.target_id) is int
                and row.target_id in dataset.target_ids and row.arm in ("b1", "narrative_v0"),
                "Invalid dataset prediction identity")
        pair = row.target_id, row.arm
        require(pair not in pairs, "Duplicate dataset prediction")
        pairs.add(pair)
        require(_integer(row.class_index, 0, 7) and row.prediction == CLASSES[row.class_index]
                and _number(row.confidence_percent) and 0 <= row.confidence_percent <= 100
                and _integer(row.fallback_count, 0, 2), "Invalid dataset decision")
        require(isinstance(row.samples, tuple) and len(row.samples) == 3, "Three dataset samples required")
        for si, sample in enumerate(row.samples):
            require(isinstance(sample, FrozenSample) and sample.sample_index == si
                    and type(sample.sample_index) is int, "Dataset sample order differs")
            require(_integer(sample.original_request_index, 0, 840)
                    and sample.original_request_index not in indices, "Duplicate dataset request index")
            indices.add(sample.original_request_index)
            require(isinstance(sample.parsed_answers, tuple) and bool(sample.parsed_answers)
                    and all(isinstance(a, tuple) and len(a) == 2 and isinstance(a[0], str)
                            and _number(a[1]) and 0 <= a[1] <= 100 for a in sample.parsed_answers), "Invalid dataset parsed sample")
            require(sample.source_kind in ("original_fresh", "supplementary", "historical_reuse")
                    and _sha(sample.source_response_sha256) and _sha(sample.prompt_sha256),
                    "Invalid dataset provenance")
            path = sample.source_response_path
            require(isinstance(path, str) and path.startswith(RAW_PREFIXES) and path.endswith('.json')
                    and '\\' not in path and ':' not in path and not any(ord(c) < 32 for c in path)
                    and all(p not in ('', '.', '..') for p in path.split('/'))
                    and path not in paths, "Invalid/duplicate dataset raw reference")
            paths.add(path)
            counts[sample.source_kind] += 1
        require(len({s.prompt_sha256 for s in row.samples}) == 1
                and len({s.source_kind for s in row.samples}) == 1, "Dataset pair provenance differs")
    require(pairs == {(t, a) for t in dataset.target_ids for a in ('b1', 'narrative_v0')}
            and indices == set(range(840)), "Dataset coverage differs")
    require(counts == {"original_fresh": 726, "supplementary": 30, "historical_reuse": 84},
            "Dataset source counts differ")
    for arm in ('b1', 'narrative_v0'):
        require(tuple(r.target_id for r in dataset.by_arm(arm)) == dataset.target_ids, "Dataset arm order differs")


def load_frozen(b1_path: str | Path, narrative_path: str | Path, selection_path: str | Path) -> FrozenDataset:
    """Load only frozen parsed samples. No raw file is read or claimed verified."""
    try:
        dataset = _validate_objects(read_pinned_json(b1_path, PINS["b1"]),
                                 read_pinned_json(narrative_path, PINS["narrative_v0"]),
                                 read_pinned_json(selection_path, PINS["selection"]))
        dataset = replace(dataset, artifact_hashes=tuple(PINS.items()), input_evidence="HASH_VERIFIED")
        validate_dataset(dataset)
        return dataset
    except (KeyError, TypeError, IndexError, RecursionError):
        raise InputError("Invalid frozen schema") from None
