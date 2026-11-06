"""Owner-local, isolated GT-only *post-hoc* scoring of frozen Cora140 R0.

Never callable from annotation/arbitration/training; no labels passed to them.
Only the exact historically SHA-pinned original Cora graph is eligible for GT.
Scores frozen terminal decisions; no API, human review or GCN execution.
"""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import sys

from ..io.frozen import CLASSES
from ..io.project import load_project_inputs
from ..sara3.audit import PrivateAudit
from ..sara3.blind_review_pack import (
    FREEZE_SHA256, _material, _safe_path)
from ..sara3.gateway_failure_diagnostics import (
    _read_content_addressed, diagnose as verify_first_veto)
from ..sara3.inputs import canonical_bytes

VERSION = "sara.evaluation.cora140.gt_only_posthoc.v1"
GRAPH_SHA256 = "9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466"
STRATA = ("COUNTER_EVIDENCE_UNRESOLVED", "THIRD_CLASS_DIAGNOSTIC_ONLY", "OTHER")
ARMS = ("b1", "narrative_v0", "blind", "comparison")
TRUE_COUNT = 2708
ROUTED_COUNT = 37
COHORT_COUNT = 140


class EvaluationStageError(ValueError):
    """Fixed, non-sensitive checkpoint; never embed an exception message."""
    def __init__(self, stage):
        super().__init__("GT-only evaluation failed closed")
        self.stage = stage


def _require(condition):
    if not condition:
        raise ValueError("GT shadow evaluation proof or alignment mismatch")


def _labels_from_original_graph(path):
    """Pin bytes BEFORE deserialize; the original graph is a trusted pickle.

    torch.load(weights_only=False) is deliberately restricted to this exact
    historical SHA. Never accept arbitrary user-controlled .pt objects or a
    caller-supplied replacement digest. No download/Planetoid conversion.
    """
    stage = "GRAPH_PATH_OR_HASH"
    try:
        path = _safe_path(path)
        _require(path.is_file() and path.stat().st_size < 512 * 1024 * 1024)
        h = hashlib.sha256()
        chunks = []
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
                chunks.append(chunk)
        _require(h.hexdigest() == GRAPH_SHA256)
        stage = "GRAPH_TORCH_DESERIALIZATION"
        import torch  # Only imported within this separately invoked evaluator.
        graph = torch.load(io.BytesIO(b"".join(chunks)),
                           map_location="cpu", weights_only=False)
        stage = "GRAPH_CLASS_OR_LABEL_SCHEMA"
        _require(list(graph.label_names) == list(CLASSES))
        gt = graph.y.detach().cpu()
        _require(gt.ndim == 1 and len(gt) == TRUE_COUNT)
        _require(not gt.is_floating_point())
        values = gt.tolist()
        _require(type(values) is list and len(values) == TRUE_COUNT
                 and all(type(y) is int and 0 <= y < 7 for y in values)
                 and set(values) == set(range(7)))
        return tuple(values)
    except Exception:
        raise EvaluationStageError(stage) from None


def _choice(value):
    _require(value is None or (type(value) is int and 0 <= value < 7))
    return value


def _rate(numerator, denominator):
    return None if denominator == 0 else round(100 * numerator / denominator, 4)


def _arm_counts(rows, arm):
    total = len(rows)
    covered = [(p[arm], p["truth"]) for p in rows if p[arm] is not None]
    correct = sum(p == y for p, y in covered)
    _require(correct <= len(covered) <= total)
    by_truth = []
    for c in range(7):
        items = [row for row in rows if row["truth"] == c]
        n = sum(row[arm] is not None for row in items)
        k = sum(row[arm] == c for row in items)
        by_truth.append({"class_index": c, "support": len(items), "covered": n, "correct": k})
    return {"denominator": total, "covered": len(covered),
            "abstained_or_unavailable": total - len(covered),
            "correct": correct,
            "coverage_percent": _rate(len(covered), total),
            "selective_accuracy_percent": _rate(correct, len(covered)),
            "correct_over_all_percent": _rate(correct, total),
            "per_true_class": by_truth}


def _paired(rows, baseline, verifier):
    shared = [row for row in rows if row[verifier] is not None]
    counts = {"both_correct": 0, "baseline_only_correct": 0,
              "verifier_only_correct": 0, "both_incorrect": 0}
    changed = 0
    for row in shared:
        a = row[baseline] == row["truth"]
        b = row[verifier] == row["truth"]
        key = ("both_correct" if a and b else "baseline_only_correct" if a
               else "verifier_only_correct" if b else "both_incorrect")
        counts[key] += 1
        changed += row[baseline] != row[verifier]
    _require(sum(counts.values()) == len(shared))
    return {"matched_denominator": len(shared), **counts,
            "changed_class_count": changed,
            "net_correct_difference": (counts["verifier_only_correct"]
                                       - counts["baseline_only_correct"]),
            "scope": "MATCHED_COVERED_ONLY_NOT_ALL_37"}


def score(selected, decisions, pairs, labels, *, freeze_sha256, graph_sha256):
    """Pure scoring after full frozen selection/provenance validation by caller."""
    _require(type(labels) in (tuple, list) and len(labels) == TRUE_COUNT
             and all(type(y) is int and 0 <= y < 7 for y in labels))
    _require(type(selected) in (tuple, list) and len(selected) == ROUTED_COUNT
             and len(set(selected)) == ROUTED_COUNT
             and all(type(node) is int and 0 <= node < TRUE_COUNT for node in selected))
    _require(type(decisions) is list and len(decisions) == COHORT_COUNT)
    _require(len(pairs) == COHORT_COUNT and set(selected).issubset(pairs))
    by_node = {}
    for d in decisions:
        _require(type(d) is dict and type(d.get("node_id")) is int
                 and d["node_id"] in pairs and d["node_id"] not in by_node)
        by_node[d["node_id"]] = d
    _require(set(by_node) == set(pairs))
    rows = []
    for node in selected:
        d = by_node[node]
        original = pairs[node]
        _require(d.get("routed_for_review") is True
                 and d.get("accepted") is False
                 and d.get("training_class_index") is None
                 and d.get("l2_status") == "NOT_ASSESSED"
                 and d.get("semantic_validation") == "NOT_PERFORMED")
        _require(d.get("b1_class_index") == original.b1.class_index
                 and d.get("narrative_v0_class_index") == original.narrative_v0.class_index)
        blind = _choice(d.get("blind_class_index"))
        comparison = _choice(d.get("comparison_class_index"))
        _require((blind is None) == (d.get("reason") == "BLIND_ABSTENTION"))
        if blind is None:
            _require(comparison is None)
        elif comparison is None:
            _require(d.get("reason") in ("L1_DUPLICATE_EVIDENCE", "VERIFIER_ABSTAINED"))
        group = d.get("reason")
        _require(type(group) is str and group)
        rows.append({"truth": labels[node],
                     "b1": _choice(d["b1_class_index"]),
                     "narrative_v0": _choice(d["narrative_v0_class_index"]),
                     "blind": blind, "comparison": comparison,
                     "group": group if group in STRATA[:2] else "OTHER"})
    _require(sum(row["blind"] is None for row in rows) == 7
             and sum(row["comparison"] is None for row in rows) == 10
             and Counter(row["group"] for row in rows)
                == {"COUNTER_EVIDENCE_UNRESOLVED": 11,
                    "THIRD_CLASS_DIAGNOSTIC_ONLY": 9, "OTHER": 17})

    def bucket(items):
        return {"n": len(items),
                "arms": {arm: _arm_counts(items, arm) for arm in ARMS},
                "paired": {f"{baseline}_vs_{verifier}": _paired(items, baseline, verifier)
                           for baseline in ("b1", "narrative_v0")
                           for verifier in ("blind", "comparison")}}
    third = [row for row in rows
             if row["group"] == "THIRD_CLASS_DIAGNOSTIC_ONLY"]
    _require(all(row["b1"] == row["narrative_v0"]
                 and row["blind"] not in (row["b1"], row["narrative_v0"]) for row in third))
    third_same = [row for row in third if row["blind"] == row["comparison"]]
    _require(len(third_same) == 7)
    out = {"schema": VERSION, "source_closeout_sha256": freeze_sha256,
           "source_graph_sha256": graph_sha256,
           "ground_truth_accessed": True,
           "evaluation_only": True, "post_hoc_exploratory": True,
           "training_admission": False, "provider_calls": 0,
           "human_reviews": 0, "GCN_training_runs": 0,
           "cohort_size": COHORT_COUNT, "routed_size": ROUTED_COUNT,
           "all_routed": bucket(rows),
           "first_veto_strata": {group: bucket([row for row in rows if row["group"] == group])
                                 for group in STRATA},
           "third_class_phase_agree": bucket(third_same),
           "interpretation": (
               "POST_HOC_ONLY_NOT_INDEPENDENT_HOLDOUT;"
               "MATCHED_COVERAGE_MUST_BE_REPORTED;"
               "GT_MUST_NOT_FEED_ANNOTATION_ARBITRATION_TRAINING")}
    return out


def run(frozen_root, authentic_root, output_root, gateway_config, graph_file,
        score_root):
    """Read the verified graph only after frozen GT-free provenance is complete."""
    stage = "SAFE_PATH_PREFLIGHT"
    try:
        output_root = _safe_path(output_root)
        score_root = _safe_path(score_root)
        graph_file = _safe_path(graph_file)
        _require(".local_artifacts" in output_root.parts
                 and ".local_artifacts" in score_root.parts
                 and score_root != output_root
                 and score_root not in output_root.parents
                 and output_root not in score_root.parents
                 and score_root.parent.is_dir())
        for forbidden in (frozen_root, authentic_root, graph_file):
            path = _safe_path(forbidden)
            _require(score_root != path and score_root not in path.parents
                     and path not in score_root.parents)

        stage = "FROZEN_CLOSEOUT_READ"
        freeze = _read_content_addressed(
            output_root, ("closeout_v1",), FREEZE_SHA256)
        report_sha = freeze.get("private_report_sha256")
        _require(type(report_sha) is str and len(report_sha) == 64)

        stage = "PRIVATE_FINAL_REPORT_READ"
        report = _read_content_addressed(
            output_root, ("continuation_amendment_v1", "journal"), report_sha)

        stage = "PINNED_PROJECT_INPUTS"
        config_path = _safe_path(gateway_config)
        _require(config_path.is_file() and config_path.stat().st_size <= 16384)
        config = json.loads(config_path.read_text(encoding="utf-8"))
        inputs = load_project_inputs(frozen_root, authentic_root)

        stage = "FROZEN_CONTEXT_AND_SELECTION"
        material = _material(inputs, freeze, report, config)

        stage = "FIRST_VETO_RECONCILIATION"
        verify_first_veto(freeze, report, freeze_sha256=FREEZE_SHA256)
        selected = [n for n, _ in material["records"]]
        pairs = {p.node_id: p for p in inputs.pairs}

        # No GT until this point; graph bytes are SHA-pinned before torch.load.
        stage = "GRAPH_LOADING"
        labels = _labels_from_original_graph(graph_file)

        stage = "FROZEN_DECISION_SCORING"
        result = score(selected, report["run"]["decisions"], pairs, labels,
                       freeze_sha256=FREEZE_SHA256, graph_sha256=GRAPH_SHA256)

        # Independent owner-only output, never source reports or reviewer packs.
        stage = "PRIVATE_RESULT_PERSISTENCE"
        audit = PrivateAudit(score_root)
        sha = audit.write(result)
        _require(audit.read(sha) == result)
        return {"status": "POST_HOC_GT_EVALUATED_PRIVATE",
                "artifact_sha256": sha,
                "source_graph_sha256": GRAPH_SHA256,
                "source_closeout_sha256": FREEZE_SHA256, **result}
    except EvaluationStageError:
        raise
    except Exception:
        raise EvaluationStageError(stage) from None

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-root", type=Path, required=True)
    parser.add_argument("--authentic-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--gateway-config", type=Path, required=True)
    parser.add_argument("--graph-file", type=Path, required=True)
    parser.add_argument("--score-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.frozen_root, args.authentic_root, args.run_root,
                     args.gateway_config, args.graph_file, args.score_root)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True,
                         indent=2, allow_nan=False))
        return 0
    except EvaluationStageError as failure:
        # Fixed stage name ONLY: no exception, file path, prediction, GT or traceback.
        print(json.dumps({"status": "FAIL_CLOSED", "stage": failure.stage}),
              file=sys.stderr)
        return 1
    except Exception:
        print(json.dumps({"status": "FAIL_CLOSED"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
