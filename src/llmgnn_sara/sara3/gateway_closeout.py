"""Read-only, GT-free closeout of the exact historical + continuation batch.

Private receipts stay on the owner's machine. Only a metadata-only, immutable,
content-addressed freeze summary is written to a separate private directory.
No provider, credentials, GT, human reviews, label admission or GCN training.
"""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys

from ..io.project import load_project_inputs
from .audit import PrivateAudit
from .automated_policy import VERSION as POLICY_VERSION, screen_validated
from .experiment import digest
from .gapgpt_live import contract_from_dict, wire_for
from .gateway_continuation import (
    FROZEN_BLINDS, FROZEN_CONTEXT_SHA256, FROZEN_CONTRACT_SHA256,
    amendment_preflight, identity, journal_rows, replay)
from .gateway_live_continuation import OVERLAY
from .gateway_run import gateway_context
from .gateway_usage_report import _valid_usage
from .inputs import canonical_bytes
from .rich_evidence import rich_verifier_input_v2

VERSION = "sara.gapgpt.cora140.gt_free_closeout.v1"
STATES = ("COMPLETED", "REJECTED", "UNCERTAIN")
PHASES = ("blind", "compare")


def _usage_bucket():
    return {"attempts": 0, "usage_available": 0, "prompt_tokens": 0,
            "completion_tokens": 0, "reasoning_tokens": 0,
            "reasoning_available": 0}


def _usage_summary(groups, cfg):
    def finish(bucket):
        cost = (Decimal(bucket["prompt_tokens"]) * Decimal(cfg["input_usd_per_million"]) +
                Decimal(bucket["completion_tokens"]) * Decimal(cfg["output_usd_per_million"])) / Decimal(1000000)
        return {**bucket,
                "reasoning_tokens": (bucket["reasoning_tokens"]
                                     if bucket["reasoning_available"] == bucket["usage_available"]
                                     else None),
                "estimated_cost_usd": (str(cost)
                                       if bucket["usage_available"] == bucket["attempts"] else None),
                "known_usage_cost_lower_bound_usd": str(cost)}
    combined = _usage_bucket()
    for value in groups.values():
        for k in combined:
            combined[k] += value[k]
    return {**{state: finish(groups[state]) for state in STATES},
            "all_attempts": finish(combined),
            "unknown_billing_attempts": combined["attempts"] - combined["usage_available"],
            "provider_invoice_verified": False,
            "cost_status": "USER_DECLARED_RATE_ESTIMATE_NOT_PROVIDER_BILLING"}


def _record_usage(groups, state, audit, receipt_sha, cfg):
    bucket = groups[state]
    bucket["attempts"] += 1
    if state == "UNCERTAIN":
        raise ValueError("Uncertain intent forbids closeout")
    rec = audit.read(receipt_sha)
    if rec.get("kind") != "gapgpt_gateway_response" or type(rec.get("raw_hex")) is not str:
        raise ValueError("Unexpected response receipt")
    raw = bytes.fromhex(rec["raw_hex"])
    if hashlib.sha256(raw).hexdigest() != rec.get("response_sha256"):
        raise ValueError("Usage source hash mismatch")
    try:
        envelope = json.loads(raw)
    except (UnicodeError, ValueError):
        envelope = None
    usage = _valid_usage(envelope, cfg)
    if usage is None:
        if state == "COMPLETED":
            raise ValueError("Completed response missing valid usage")
        return
    prompt, completion, reasoning = usage
    bucket["usage_available"] += 1
    bucket["prompt_tokens"] += prompt
    bucket["completion_tokens"] += completion
    if reasoning is not None:
        bucket["reasoning_available"] += 1
        bucket["reasoning_tokens"] += reasoning


def analyze(inputs, original_root, *, config, amendment, fake=False,
            frozen_context_sha=FROZEN_CONTEXT_SHA256, frozen_contract_sha=FROZEN_CONTRACT_SHA256,
            allowed_blinds=FROZEN_BLINDS, check_amendment=True):
    """Compute verified summary from both actual SQLite journals and receipts."""
    cfg = contract_from_dict(config)
    if digest(cfg) != frozen_contract_sha:
        raise ValueError("Gateway contract mismatch")
    selected, context = gateway_context(
        inputs, "r0", 37, "sensitivity", cfg, fake=fake)
    context_sha = digest(context)
    if context_sha != frozen_context_sha:
        raise ValueError("Execution context mismatch")
    if check_amendment:
        admission = amendment_preflight(
            inputs, original_root, config=cfg, amendment=amendment, fake=fake)
        if admission["original_context_verified"] is not True:
            raise ValueError("Historical admission failed")
    original, original_phases = journal_rows(original_root, context_sha, cfg["max_calls"])
    overlay_root = Path(original_root) / OVERLAY
    continuation, continuation_phases = journal_rows(
        overlay_root, context_sha, cfg["max_calls"])
    if not continuation or set(original).intersection(continuation):
        raise ValueError("Missing continuation or duplicate cross-journal identity")
    if (set(original_phases).intersection(continuation_phases)
            or len(original) + len(continuation) > 69 or len(continuation) > 16
            or any(n not in allowed_blinds for n, phase in continuation_phases)
            or any(state[3] != "COMPLETED" for state in continuation.values())):
        raise ValueError("Continuation scope, duplication, or state mismatch")
    if len(original) != amendment["original_intents"]:
        raise ValueError("Original intent count mismatch")
    if len(set(selected)) != len(selected):
        raise ValueError("Selection collision")
    original_audit = PrivateAudit(Path(original_root) / "journal")
    continuation_audit = PrivateAudit(overlay_root / "journal")
    phases = {**original_phases, **continuation_phases}
    pairs = {p.node_id: p for p in inputs.pairs}
    groups = {state: _usage_bucket() for state in STATES}
    by_origin = {name: {state: _usage_bucket() for state in STATES}
                 for name in ("historical", "continuation")}
    phase_counts = {phase: Counter() for phase in PHASES}
    origin_counts = {"historical": Counter(), "continuation": Counter()}
    blind_abstentions, no_comparison, reasons = [], [], Counter()
    proposals, class_counts, source_counts = 0, Counter(), Counter()
    evaluated, completed_pairs = 0, 0
    seen = set()

    def verified(node, phase, payload, dep, text):
        wire = wire_for(payload, cfg)
        expected = identity(context_sha, phase, payload, wire, dep)
        row = phases.get((node, phase))
        if row is None:
            return None, None
        origin = "historical" if (node, phase) in original_phases else "continuation"
        audit = original_audit if origin == "historical" else continuation_audit
        if row[0] != expected or expected in seen:
            raise ValueError("Request identity mismatch or duplicate")
        seen.add(expected)
        state = row[1][3]
        value = replay(audit, row, expected, payload, wire, dep,
                       context_sha, text, cfg)
        receipt = row[1][4]
        _record_usage(groups, state, audit, receipt, cfg)
        _record_usage(by_origin[origin], state, audit, receipt, cfg)
        phase_counts[phase][state] += 1
        origin_counts[origin][state] += 1
        return value, state

    if any(node not in selected for node, _ in phases):
        raise ValueError("Node outside frozen selection")
    for node in selected:
        pair = pairs[node]
        bp = rich_verifier_input_v2(node, pair.text, pair.neighborhood)
        blind, bs = verified(node, "blind", bp, None, pair.text)
        if bs != "COMPLETED":
            raise ValueError("Selected blind missing or noncompleted")
        evaluated += 1
        if blind["abstain"]:
            blind_abstentions.append(node)
            reasons["BLIND_ABSTENTION"] += 1
            if (node, "compare") in phases:
                raise ValueError("Comparison after abstained Blind")
            continue
        candidates = tuple(sorted({pair.b1.class_index, pair.narrative_v0.class_index}))
        cp = rich_verifier_input_v2(node, pair.text, pair.neighborhood,
                                    candidates=candidates, blind_class=blind["class_index"])
        comparison, cs = verified(node, "compare", cp, digest(blind), pair.text)
        if cs is None:
            no_comparison.append(node)
            raise ValueError("Missing comparison after non-abstaining Blind")
        if cs == "REJECTED":
            reasons["L1_DUPLICATE_EVIDENCE"] += 1
            continue
        completed_pairs += 1
        result = screen_validated(pair, blind, comparison)
        reasons[result["reason"]] += 1
        if result["action"] == "ACCEPT":
            if result["class_index"] not in candidates:
                raise ValueError("Proposal not in frozen candidates")
            proposals += 1
            class_counts[str(result["class_index"])] += 1
            source_counts[result["label_source"]] += 1
    if seen != set(original) | set(continuation):
        raise ValueError("Unverified or unexpected journal intents")
    if (set(n for n, p in continuation_phases if p == "blind") != set(allowed_blinds)
            or any(n not in blind_abstentions for n in allowed_blinds
                   if (n, "compare") not in continuation_phases)):
        raise ValueError("Conditional continuation incomplete")
    for origin, expected_size in (("historical", len(original)),
                                  ("continuation", len(continuation))):
        if sum(origin_counts[origin].values()) != expected_size:
            raise ValueError("Origin counts do not reconcile")
    if (origin_counts["historical"]["COMPLETED"] != amendment["original_completed"]
            or origin_counts["historical"]["REJECTED"] != 1
            or original_phases[(amendment["original_rejected_node_id"],
                                amendment["original_rejected_phase"])][1][3] != "REJECTED"
            or any(origin_counts[o]["UNCERTAIN"] for o in origin_counts)):
        raise ValueError("Historical terminal status mismatch")
    if proposals > completed_pairs:
        raise ValueError("Proposal overflow")
    total = len(original) + len(continuation)
    summary = {
        "schema": VERSION, "read_only_source_journals": True, "provider_calls": 0,
        "GT_accessed": False, "human_review_accessed": False,
        "GCN_training_runs": 0, "training_admission": False,
        "all_proposals_accepted": False, "all_training_class_indices_null": True,
        "scientific_status": "GT_FREE_AUTOMATED_CONCORDANCE_NOT_SEMANTIC_L2",
        "context_sha256": context_sha, "contract_sha256": digest(cfg),
        "amendment_sha256": digest(amendment),
        "arbitration_policy_version": POLICY_VERSION,
        "cohort_size": len(inputs.pairs), "routed_nodes": len(selected),
        "historical_intents": len(original), "continuation_intents": len(continuation),
        "total_intents": total, "original_contract_call_cap": cfg["max_calls"],
        "amendment_cumulative_cap": amendment["maximum_cumulative_calls"],
        "amendment_new_call_cap": amendment["maximum_new_calls"],
        "intent_states": dict(sorted((k, sum(v[k] for v in origin_counts.values())) for k in STATES)),
        "state_by_origin": {o: dict(sorted(c.items())) for o, c in origin_counts.items()},
        "phase_states": {p: {s: phase_counts[p][s] for s in STATES} for p in PHASES},
        "blind_abstain_count": len(blind_abstentions),
        "blind_abstain_node_ids": blind_abstentions,
        "continuation_blind_abstain_node_ids": [n for n in allowed_blinds if n in blind_abstentions],
        "comparison_missing_after_nonabstain": no_comparison,
        "completed_blind_comparison_pairs": completed_pairs,
        "automated_concordance": {
            "screened_pairs": completed_pairs, "proposals": proposals,
            "veto_or_abstain_reasons": dict(sorted((k, v) for k, v in reasons.items()
                                                if k != "PROVISIONAL_CROSS_PHASE_CONCORDANCE")),
            "proposal_reasons": {"PROVISIONAL_CROSS_PHASE_CONCORDANCE": proposals},
            "proposal_class_distribution": dict(sorted(class_counts.items())),
            "proposal_label_sources": dict(sorted(source_counts.items())),
            "proposal_coverage_of_routed": {"numerator": proposals, "denominator": len(selected)},
            "proposal_coverage_of_cohort": {"numerator": proposals, "denominator": len(inputs.pairs)},
            "routed_coverage_of_cohort": {"numerator": len(selected), "denominator": len(inputs.pairs)},
        },
        "usage": _usage_summary(groups, cfg),
        "usage_by_origin": {origin: _usage_summary(values, cfg)
                            for origin, values in by_origin.items()},
        "receipt_identity_integrity_verified": True,
        "no_cross_journal_duplicate": True, "no_historical_retry": True,
        "freeze_version": VERSION,
    }
    if total != sum(summary["intent_states"].values()):
        raise ValueError("Attempt reconciliation failure")
    return summary


def verify_private_report(summary, root, report_sha, all_node_ids, selected_node_ids):
    """Check the final persisted ledger without releasing private response content."""
    audit = PrivateAudit(Path(root) / OVERLAY / "journal")
    record = audit.read(report_sha)
    if (record.get("kind") != "gapgpt_continuation_private_report"
            or record.get("amendment_sha256") != summary["amendment_sha256"]):
        raise ValueError("Private final report binding mismatch")
    run = record.get("run")
    if type(run) is not dict or type(run.get("decisions")) is not list:
        raise ValueError("Incomplete final run")
    all_decisions = run["decisions"]
    by_node = {d.get("node_id"): d for d in all_decisions if type(d) is dict}
    if len(by_node) != len(all_decisions) or set(by_node) != set(all_node_ids):
        raise ValueError("Final report node coverage mismatch")
    if set(run.get("selected_node_ids", ())) != set(selected_node_ids):
        raise ValueError("Final report selection mismatch")
    proposed = [d for d in all_decisions if d.get("provisional_status") == "PROPOSED"]
    if any(d.get("accepted") is not False or d.get("training_class_index") is not None
           or d.get("l2_status") != "NOT_ASSESSED" for d in proposed):
        raise ValueError("Private proposals were incorrectly admitted")
    if (len(proposed) != summary["automated_concordance"]["proposals"]
            or run.get("provisional_count") != len(proposed)
            or any(d.get("third_class_training_allowed") is not False for d in proposed)):
        raise ValueError("Private provisional proposal count/admission mismatch")
    return {"private_report_sha256": report_sha,
            "private_report_reconciled": True,
            "persisted_proposals": len(proposed),
            "persisted_proposals_accepted": 0,
            "persisted_proposal_training_indices_nonnull": 0}


def freeze(summary, root):
    """Create a metadata-only immutable SHA256-named file; no journal writes."""
    root = Path(root)
    dest = root / "closeout_v1"
    if root.is_symlink() or dest.is_symlink() or ".local_artifacts" not in root.resolve().parts:
        raise ValueError("Closeout output must be inside private artifacts")
    blob = canonical_bytes(summary)
    sha = hashlib.sha256(blob).hexdigest()
    dest.mkdir(mode=0o700, exist_ok=True)
    path = dest / (sha + ".json")
    if path.is_symlink():
        raise ValueError("Unsafe existing freeze path")
    if path.exists():
        if path.read_bytes() != blob:
            raise ValueError("Freeze collision")
    else:
        try:
            with path.open("xb") as handle:
                handle.write(blob)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            if path.read_bytes() != blob:
                raise ValueError("Concurrent freeze mismatch")
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        raise ValueError("Freeze file hash failed")
    return sha


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-root", type=Path, required=True)
    parser.add_argument("--authentic-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--gateway-config", type=Path, required=True)
    parser.add_argument("--amendment-file", type=Path, required=True)
    parser.add_argument("--private-report-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if args.gateway_config.is_symlink() or args.amendment_file.is_symlink():
            raise ValueError("Unsafe config or amendment")
        result = analyze(
            load_project_inputs(args.frozen_root, args.authentic_root),
            args.output_root,
            config=json.loads(args.gateway_config.read_text(encoding="utf-8")),
            amendment=json.loads(args.amendment_file.read_text(encoding="utf-8")))
        inputs = load_project_inputs(args.frozen_root, args.authentic_root)
        selected, _ = gateway_context(
            inputs, "r0", 37, "sensitivity",
            contract_from_dict(json.loads(args.gateway_config.read_text(encoding="utf-8"))),
            fake=False)
        result.update(verify_private_report(
            result, args.output_root, args.private_report_sha256,
            {p.node_id for p in inputs.pairs}, selected))
        sha = freeze(result, args.output_root)
        print(json.dumps({"freeze_sha256": sha, **result}, ensure_ascii=False,
                         sort_keys=True, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, sqlite3.DatabaseError):
        print(json.dumps({"status": "FAIL_CLOSED"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
