"""Read-only GT-free co-occurring evidence flags for frozen veto groups.

Uses the authenticated closeout + final-run record and hashes/validates only
the matching phase-audit receipts on the owner's machine. Never emits text,
quotes, per-node predictions, raw evidence, GT or training admission.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys

from .automated_policy import screen_validated, VERSION as POLICY_VERSION
from .gateway_failure_diagnostics import (
    TARGETS, _read_content_addressed, diagnose as first_veto)
from .inputs import canonical_bytes
from .rich_evidence import target_source, validate_rich_result

VERSION = "sara.gapgpt.cora140.secondary_veto_flags.v1"
FLAGS = ("counter_evidence", "auxiliary_method_warning",
         "uncertainty_reason")


def _flag_counts(blind, comparison):
    a, b = (x["rich_evidence"] for x in (blind, comparison))
    both = {field: [bool(a[field]), bool(b[field])] for field in FLAGS}
    first_topic = a["primary_topic"].strip().casefold()
    second_topic = b["primary_topic"].strip().casefold()
    def quotes(evidence):
        return {i["quote"] for i in evidence["supporting_evidence"]
                if i["source_id"] == "target.text"}
    return {
        "blind": {k: int(v[0]) for k, v in both.items()},
        "comparison": {k: int(v[1]) for k, v in both.items()},
        "either": {k: int(any(v)) for k, v in both.items()},
        "both_phases": {k: int(all(v)) for k, v in both.items()},
        "primary_topic_drift": int(first_topic != second_topic),
        "no_common_target_quote": int(not bool(quotes(a) & quotes(b))),
    }


def _matched_phase_receipt(root, sha, name, text, expected_class, request):
    record = _read_content_addressed(
        root, ("continuation_amendment_v1", "phases"), sha)
    if (record.get("kind") != "response" or record.get("l1_status") != "PASS"
            or record.get("request_id") != name
            or record.get("payload_sha256") != request.get("sha256")
            or hashlib.sha256(canonical_bytes(request["payload"])).hexdigest()
                != record["payload_sha256"]):
        raise ValueError("Phase receipt or request binding mismatch")
    validated = validate_rich_result(record["raw_response"], (target_source(text),))
    if (canonical_bytes(validated) != canonical_bytes(record.get("validated"))
            or validated["class_index"] != expected_class
            or validated["abstain"]):
        raise ValueError("Saved L1 and final decision mismatch")
    return validated


def analyze(root, freeze_sha, report_sha):
    root = Path(root)
    if (any(p.is_symlink() for p in (root, *root.parents))
            or ".local_artifacts" not in root.resolve(strict=True).parts):
        raise ValueError("Unsafe private root")
    freeze = _read_content_addressed(root, ("closeout_v1",), freeze_sha)
    if freeze.get("private_report_sha256") != report_sha:
        raise ValueError("Private report digest differs from freeze")
    report = _read_content_addressed(
        root, ("continuation_amendment_v1", "journal"), report_sha)
    validated = first_veto(freeze, report, freeze_sha256=freeze_sha)
    run = report["run"]
    targets = {d["node_id"]: d for d in run["decisions"]
               if d.get("reason") in TARGETS and d.get("routed_for_review") is True}
    if len(targets) != sum(validated["target_diagnostics"][k]["count"] for k in TARGETS):
        raise ValueError("Target count changed")
    inputs = {}
    for req in run.get("verifier_inputs", []):
        if type(req) is not dict or type(req.get("request_id")) is not str:
            raise ValueError("Invalid private verifier input")
        name = req["request_id"]
        if name in inputs:
            raise ValueError("Duplicate verifier request")
        inputs[name] = req

    phase_dir = root / "continuation_amendment_v1" / "phases"
    if phase_dir.is_symlink() or not phase_dir.is_dir():
        raise ValueError("Private phase audit missing")
    arbitrations = {}
    for path in phase_dir.glob("*.json"):
        rec = _read_content_addressed(root,
                ("continuation_amendment_v1", "phases"), path.stem)
        if rec.get("kind") != "arbitration" or rec.get("node_id") not in targets:
            continue
        node = rec["node_id"]
        if node in arbitrations:
            raise ValueError("Duplicate target arbitration audit")
        recorded = rec.get("decision")
        if (rec.get("policy_version") != POLICY_VERSION
                or type(recorded) is not dict
                or any(targets[node].get(key) != value
                       for key, value in recorded.items())):
            # The saved arbitration predates the final run's metadata-only
            # decoration (B1/Narrative and phase class indices).
            raise ValueError("Arbitration audit mismatch")
        arbitrations[node] = rec
    if set(arbitrations) != set(targets):
        raise ValueError("Missing target arbitration audit")

    results = {reason: {"nodes": 0, "blind": Counter(),
                         "comparison": Counter(), "either": Counter(),
                         "both_phases": Counter(),
                         "primary_topic_drift": 0,
                         "no_common_target_quote": 0}
               for reason in TARGETS}
    for node, decision in targets.items():
        records = {}
        for phase in ("blind", "compare"):
            name = f"offline:{node}:{phase}"
            request = inputs.get(name)
            if request is None or type(request.get("payload")) is not dict:
                raise ValueError("Missing sealed verifier request")
            payload = request["payload"]
            source = payload.get("target")
            if (payload.get("node_id") != node or payload.get("phase") != phase
                    or type(source) is not dict
                    or type(source.get("text")) is not str
                    or hashlib.sha256(source["text"].encode()).hexdigest()
                       != source.get("source_sha256")):
                raise ValueError("Verifier target binding mismatch")
            if phase == "compare" and (
                    payload.get("blind_class_index") != decision.get("blind_class_index")
                    or set(payload.get("historical_candidates", ())) !=
                       {decision.get("b1_class_index"), decision.get("narrative_v0_class_index")}):
                raise ValueError("Frozen candidates differ")
            sha = arbitrations[node].get(phase + "_response_sha256")
            records[phase] = _matched_phase_receipt(
                root, sha, name, source["text"],
                decision.get("blind_class_index" if phase == "blind"
                             else "comparison_class_index"), request)
        blind, comparison = records["blind"], records["compare"]
        pair = SimpleNamespace(
            b1=SimpleNamespace(class_index=decision["b1_class_index"]),
            narrative_v0=SimpleNamespace(class_index=decision["narrative_v0_class_index"]),
            agrees=(decision["b1_class_index"] == decision["narrative_v0_class_index"]))
        screen = screen_validated(pair, blind, comparison)
        reason = decision["reason"]
        if (screen["reason"] != reason
                or screen["action"] != decision["automated_screen_status"]):
            raise ValueError("Frozen arbitration re-screen mismatch")
        flags = _flag_counts(blind, comparison)
        bucket = results[reason]
        bucket["nodes"] += 1
        for part, value in flags.items():
            if isinstance(value, dict):
                bucket[part].update(value)
            else:
                bucket[part] += value
    output = {k: {name: dict(sorted(value.items())) if isinstance(value, Counter)
                   else value for name, value in row.items()}
              for k, row in results.items()}
    return {"schema": VERSION, "source_closeout_sha256": freeze_sha,
            "first_veto_policy": POLICY_VERSION,
            "cohort": "FROZEN_R0_ROUTED",
            "post_hoc": True, "provider_calls": 0, "GT_accessed": False,
            "human_review_accessed": False, "GCN_training_runs": 0,
            "training_admission": False, "routed_nodes": validated["routed_nodes"],
            "target_nodes": len(targets), "breakdown": output,
            "interpretation": "DESCRIPTIVE_COOCCURRENCE_NOT_COUNTERFACTUAL_ACCEPTANCE"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--freeze-sha256", required=True)
    parser.add_argument("--private-report-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        result = analyze(args.output_root, args.freeze_sha256,
                         args.private_report_sha256)
        print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"status": "FAIL_CLOSED"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
