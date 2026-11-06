"""Post-freeze, metadata-only diagnosis of GT-free automated vetoes.

Consumes the already frozen closeout and its SHA-verified private final report.
This intentionally never reads or emits article text, quotes, raw responses,
human reviews, GT, training labels or individual per-node predictions.
No provider, rerouting, policy change, admission or journal write.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

from .automated_policy import VERSION as POLICY_VERSION
from .gateway_closeout import VERSION as CLOSEOUT_VERSION

VERSION = "sara.gapgpt.cora140.postfreeze_veto_diagnostic.v1"
TARGETS = ("COUNTER_EVIDENCE_UNRESOLVED", "THIRD_CLASS_DIAGNOSTIC_ONLY")
_DIGEST = re.compile(r"[0-9a-f]{64}")


def _read_content_addressed(root, parts, sha):
    if type(sha) is not str or _DIGEST.fullmatch(sha) is None:
        raise ValueError("Invalid content digest")
    path = root.joinpath(*parts, sha + ".json")
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
        raise ValueError("Missing or unsafe private artifact")
    blob = path.read_bytes()
    if hashlib.sha256(blob).hexdigest() != sha:
        raise ValueError("Content-address mismatch")
    result = json.loads(blob)
    if type(result) is not dict:
        raise ValueError("Invalid private artifact")
    return result


def _class_index(value):
    if type(value) is not int or not 0 <= value < 7:
        raise ValueError("Invalid class metadata")
    return value


def diagnose(freeze, report, *, freeze_sha256):
    """Compute an aggregate diagnostic ONLY; raw private report never escapes."""
    if (freeze.get("schema") != CLOSEOUT_VERSION
            or freeze.get("freeze_version") != CLOSEOUT_VERSION
            or freeze.get("arbitration_policy_version") != POLICY_VERSION
            or freeze.get("private_report_reconciled") is not True
            or freeze.get("receipt_identity_integrity_verified") is not True
            or freeze.get("no_cross_journal_duplicate") is not True
            or freeze.get("training_admission") is not False
            or freeze.get("GT_accessed") is not False
            or report.get("kind") != "gapgpt_continuation_private_report"
            or report.get("amendment_sha256") != freeze.get("amendment_sha256")):
        raise ValueError("Freeze and report proof mismatch")
    run = report.get("run")
    if type(run) is not dict or type(run.get("decisions")) is not list:
        raise ValueError("Final private run unavailable")
    selected = run.get("selected_node_ids")
    if (type(selected) is not list or len(selected) != freeze.get("routed_nodes")
            or any(type(n) is not int for n in selected)
            or len(set(selected)) != len(selected)):
        raise ValueError("Frozen selection mismatch")
    decisions = run["decisions"]
    if len(decisions) != freeze.get("cohort_size"):
        raise ValueError("Frozen cohort mismatch")
    by_node = {}
    for entry in decisions:
        if type(entry) is not dict:
            raise ValueError("Invalid private decision")
        n = entry.get("node_id")
        if type(n) is not int or n in by_node:
            raise ValueError("Duplicate or invalid private node")
        by_node[n] = entry
    if not set(selected).issubset(by_node):
        raise ValueError("Selected nodes missing")

    reasons, screened = Counter(), 0
    targets = {name: {"count": 0, "frozen_candidates_agree": 0,
                      "cross_phase_class_agreement": 0,
                      "blind_third_class": 0, "comparison_third_class": 0,
                      "both_phases_third_class": 0,
                      "third_class_distribution": Counter()}
               for name in TARGETS}
    for node in selected:
        d = by_node[node]
        if (d.get("routed_for_review") is not True
                or d.get("accepted") is not False
                or d.get("training_class_index") is not None
                or d.get("l2_status") != "NOT_ASSESSED"
                or d.get("semantic_validation") != "NOT_PERFORMED"):
            raise ValueError("Routed decision breaks provenance or admission")
        reason = d.get("reason")
        if type(reason) is not str:
            raise ValueError("Decision reason missing")
        reasons[reason] += 1
        screened_reason = d.get("automated_screen_reason")
        if screened_reason is not None:
            if (d.get("automated_policy_version") != POLICY_VERSION
                    or screened_reason != reason
                    or d.get("automated_screen_status") not in ("ACCEPT", "ABSTAIN", "REJECT")):
                raise ValueError("Automated policy provenance mismatch")
            screened += 1
        if reason not in TARGETS:
            continue
        if screened_reason != reason:
            raise ValueError("Target group was not screened")
        b1, narr = (_class_index(d.get("b1_class_index")),
                    _class_index(d.get("narrative_v0_class_index")))
        blind, comparison = (_class_index(d.get("blind_class_index")),
                             _class_index(d.get("comparison_class_index")))
        candidates = {b1, narr}
        t = targets[reason]
        t["count"] += 1
        t["frozen_candidates_agree"] += b1 == narr
        t["cross_phase_class_agreement"] += blind == comparison
        bt, ct = blind not in candidates, comparison not in candidates
        t["blind_third_class"] += bt
        t["comparison_third_class"] += ct
        t["both_phases_third_class"] += bt and ct
        if reason == "THIRD_CLASS_DIAGNOSTIC_ONLY":
            if not (bt or ct):
                raise ValueError("Third-class diagnostic has no third class")
            # Mirrors the existing screen's diagnostic precedence, not
            # an accepted label or a new scientific inference.
            proposed = blind if bt else comparison
            if d.get("third_class_proposal") != proposed:
                raise ValueError("Recorded third-class diagnostic mismatch")
            t["third_class_distribution"][str(proposed)] += 1
        elif bt or ct or blind != comparison:
            raise ValueError("Counter-evidence case bypassed class gate")

    observed = dict(sorted(reasons.items()))
    frozen = freeze.get("automated_concordance")
    if type(frozen) is not dict:
        raise ValueError("Missing frozen concordance")
    expected = {**frozen.get("veto_or_abstain_reasons", {}),
                **{k: v for k, v in frozen.get("proposal_reasons", {}).items() if v}}
    if (observed != dict(sorted(expected.items()))
            or screened != frozen.get("screened_pairs")
            or sum(reasons.values()) != freeze["routed_nodes"]
            or run.get("provisional_count") != frozen.get("proposals")
            or (freeze.get("persisted_proposals") != frozen.get("proposals"))):
        raise ValueError("Diagnostic does not reconcile with immutable freeze")
    if any(d.get("provisional_status") == "PROPOSED"
           and (d.get("accepted") is not False
                or d.get("training_class_index") is not None)
           for d in decisions):
        raise ValueError("Proposal incorrectly admitted")

    output_targets = {}
    for name in TARGETS:
        row = targets[name]
        output_targets[name] = {
            k: (dict(sorted(v.items())) if isinstance(v, Counter) else v)
            for k, v in row.items()
        }
    return {"schema": VERSION,
            "source_closeout_sha256": freeze_sha256,
            "arbitration_policy_version": POLICY_VERSION,
            "provider_calls": 0, "GT_accessed": False,
            "human_review_accessed": False, "GCN_training_runs": 0,
            "training_admission": False,
            "routed_nodes": len(selected),
            "screened_pairs": screened,
            "all_routed_reasons_reconciled": True,
            "reason_counts": observed,
            "target_diagnostics": output_targets,
            "interpretation": "POST_HOC_GT_FREE_DESCRIPTIVE_NOT_ACCURACY_OR_ADMISSION"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--freeze-sha256", required=True)
    parser.add_argument("--private-report-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        supplied = args.output_root
        if (any(p.is_symlink() for p in (supplied, *supplied.parents))
                or ".local_artifacts" not in supplied.resolve(strict=True).parts):
            raise ValueError("Private output root required")
        root = supplied.resolve(strict=True)
        freeze = _read_content_addressed(root, ("closeout_v1",),
                                         args.freeze_sha256)
        if freeze.get("private_report_sha256") != args.private_report_sha256:
            raise ValueError("Private final report digest mismatch")
        report = _read_content_addressed(
            root, ("continuation_amendment_v1", "journal"),
            args.private_report_sha256)
        result = diagnose(freeze, report, freeze_sha256=args.freeze_sha256)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True,
                         indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"status": "FAIL_CLOSED"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
