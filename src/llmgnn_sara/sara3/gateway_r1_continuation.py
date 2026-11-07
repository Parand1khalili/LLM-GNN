"""One-shot, separately approved continuation of the stopped REAL R1-v1 cohort.

Original 51 intents/receipts remain immutable. The invalid Comparison is
preserved as an L1_QUOTE_NOT_FOUND, NOT retried. Only never-attempted Blinds
(and their valid dependent Comparisons) can be dispatched to a private overlay.
All GT access is forbidden; a separate scorer handles post-hoc evaluation.
"""
import argparse
from contextlib import closing
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from ..io.project import load_project_inputs
from ..downstream.prospective import frozen_pair_digest
from .audit import PrivateAudit
from .automated_policy import VERSION as AUTOMATED_VERSION
from .evidence import EvidenceError
from .experiment import digest
from .gapgpt_live import (
    DurableGapGPTVerifier, KEY_VARIABLE, contract_from_dict, wire_for,
    worst_call_cost)
from .gateway_continuation import (
    SyntheticContinuationVerifier, _OverlayAudit, identity, inspect, journal_rows)
from .gateway_run import CONTRACT, gateway_context
from .inputs import canonical_bytes
from .pipeline import run_offline
from .rich_evidence import RICH_PROMPT_V2, RICH_VERSION, rich_verifier_input_v2

VERSION = "sara.gapgpt.r1_v1.continuation.v1"
AMENDMENT_VERSION = "sara.gapgpt.r1_v1.continuation_amendment.v1"
APPROVAL_VERSION = "sara.gapgpt.r1_v1.continuation_owner_approval.v1"
OVERLAY = "r1_v1_continuation_v1"
ROUTER, BUDGET, COHORT = "r1_v1", 37, 140
ORIGINAL_CALLS, ORIGINAL_COMPLETED, MAX_NEW = 51, 50, 14
REJECT_CODE = "L1_QUOTE_NOT_FOUND"
FLAGS = ("data_sharing_approved", "spend_approved",
         "explicit_continuation_dispatch_approved")
_SHA = re.compile(r"[0-9a-f]{64}")


def _root(value):
    supplied = Path(value)
    if supplied.is_symlink() or any(p.is_symlink() for p in supplied.parents):
        raise ValueError("Unsafe private root")
    root = supplied.resolve(strict=False)
    if ".local_artifacts" not in root.parts or root.is_symlink():
        raise ValueError("Owner-only private root required")
    return root


def _read_sha(path, sha):
    if type(sha) is not str or not _SHA.fullmatch(sha):
        raise ValueError("Expected content-addressed artifact")
    target = path / (sha + ".json")
    if target.is_symlink() or not target.is_file():
        raise ValueError("Missing/unsafe content-addressed artifact")
    raw = target.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError("Private artifact digest mismatch")
    data = json.loads(raw)
    if type(data) is not dict:
        raise ValueError("Invalid private artifact")
    return data


def _original_run(root, ctx_sha, selected, cfg, inputs):
    journal = root / "journal"
    found = []
    # Never print original reports, node-level source text or GT.
    for path in journal.glob("*.json"):
        if path.is_symlink() or not _SHA.fullmatch(path.stem):
            raise ValueError("Unsafe journal content")
        candidate = _read_sha(journal, path.stem)
        if (candidate.get("schema") == CONTRACT
                and candidate.get("mode") == "LIVE_HTTPS"
                and candidate.get("router") == ROUTER
                and candidate.get("gateway_context_sha256") == ctx_sha):
            found.append((path.stem, candidate))
    if len(found) != 1:
        raise ValueError("Exactly one frozen real R1 summary expected")
    summary_sha, summary = found[0]
    if (summary.get("status") != "BLOCKED_NO_AUTOMATIC_RETRY"
            or summary.get("selected_node_ids") != list(selected)
            or summary.get("selected_count") != BUDGET
            or summary.get("denominator") != COHORT
            or summary.get("attempted_calls") != ORIGINAL_CALLS
            or summary.get("journal_states") !=
                {"COMPLETED": ORIGINAL_COMPLETED, "REJECTED": 1, "UNCERTAIN": 0}
            or summary.get("rejection_codes") != {REJECT_CODE: 1}
            or summary.get("GT_accessed") is not False
            or summary.get("training_runs") != 0
            or summary.get("prompt_version") != RICH_PROMPT_V2
            or summary.get("arbitration_version") != AUTOMATED_VERSION
            or summary.get("requested_model") != cfg["model"]
            or summary.get("frozen_pairs_sha256") != frozen_pair_digest(inputs.pairs)):
        raise ValueError("Original R1 run provenance differs")
    report_sha = summary.get("private_report_sha256")
    report = _read_sha(journal, report_sha)
    if (report.get("router") != ROUTER or
            report.get("gateway_runner_version") != CONTRACT or
            report.get("gateway_context_sha256") != ctx_sha or
            report.get("frozen_pairs_sha256") != frozen_pair_digest(inputs.pairs) or
            report.get("selected_node_ids") != list(selected) or
            report.get("source_hashes") != dict(inputs.provenance) or
            report.get("prompt_version") != RICH_PROMPT_V2 or
            report.get("automated_arbitration_version") != AUTOMATED_VERSION or
            report.get("data_kind") != "GAPGPT_LIVE_RAW_UNVERIFIED_SEMANTIC_L2" or
            report.get("provider_calls") != ORIGINAL_CALLS or
            report.get("GT_accessed") is not False or
            report.get("training_runs") != 0 or
            len(report.get("decisions", [])) != COHORT):
        raise ValueError("Original R1 live report mismatch")
    return summary_sha, report_sha


def preflight(inputs, original_root, *, config, fake=False):
    """Read-only full source verification and exact unapproved scope template."""
    root = _root(original_root)
    cfg = contract_from_dict(config)
    if cfg["max_calls"] != 74 or cfg["max_spend_usd"] != "0.40":
        raise ValueError("Unexpected original gateway contract budget")
    selected, context = gateway_context(
        inputs, ROUTER, BUDGET, "sensitivity", cfg, fake=fake)
    context_sha = digest(context)
    checked = inspect(
        inputs, root, config=cfg, expected_context_sha256=context_sha,
        router=ROUTER, budget=BUDGET, cohort="sensitivity", fake=fake,
        expected_reject_code=REJECT_CODE)
    failed = checked["rejected_phases"]
    missing = checked["never_dispatched_blind_node_ids"]
    if (checked["original_intents"] != ORIGINAL_CALLS
            or checked["completed_replayed_and_l1_verified"] != ORIGINAL_COMPLETED
            or checked["rejected_preserved"] != 1
            or checked["uncertain"] != 0
            or len(failed) != 1 or failed[0]["phase"] != "compare"
            or failed[0]["reason"] != REJECT_CODE
            or checked["missing_comparison_after_completed_blind_node_ids"]
            or len(missing) != 7 or len(set(missing)) != 7
            or checked["maximum_possible_new_calls"] != MAX_NEW
            or checked["remaining_logical_capacity"] != 23):
        raise ValueError("Owner's R1 original journal differs from 51/50/1")
    original_rows, original_phases = journal_rows(
        root, context_sha, cfg["max_calls"])
    original_digest = digest([
        [name, *values] for name, values in sorted(original_rows.items())])
    if not fake:
        summary_sha, report_sha = _original_run(root, context_sha, selected, cfg, inputs)
    else:
        summary_sha = report_sha = None
    amendment = {
        "version": AMENDMENT_VERSION,
        "status": "PROPOSED_NOT_AUTHORIZED",
        "original_context_sha256": context_sha,
        "original_gateway_contract_sha256": digest(cfg),
        "original_journal_rows_sha256": original_digest,
        "original_summary_sha256": summary_sha,
        "original_report_sha256": report_sha,
        "original_intents": ORIGINAL_CALLS,
        "original_completed": ORIGINAL_COMPLETED,
        "original_rejected_node_id": failed[0]["node_id"],
        "original_rejected_phase": "compare",
        "original_reject_code": REJECT_CODE,
        "never_dispatched_blind_ids": list(missing),
        "maximum_new_calls": MAX_NEW,
        "maximum_cumulative_calls": ORIGINAL_CALLS + MAX_NEW,
        "original_contract_call_cap": cfg["max_calls"],
        "owner_dispatch_approval": False,
    }
    approval = {
        "version": APPROVAL_VERSION,
        "amendment_sha256": digest(amendment),
        "execution_context_sha256": context_sha,
        "gateway_contract_sha256": digest(cfg),
        "original_journal_rows_sha256": original_digest,
        "original_intents": ORIGINAL_CALLS,
        "maximum_new_calls": MAX_NEW,
        "maximum_cumulative_calls": ORIGINAL_CALLS + MAX_NEW,
        "max_spend_usd": cfg["max_spend_usd"],
        **{f: False for f in FLAGS}
    }
    return {
        "status": "READ_ONLY_R1_CONTINUATION_PROPOSED_NOT_AUTHORIZED",
        "schema": VERSION,
        "provider_calls": 0,
        "GT_accessed": False,
        "read_only": True,
        "original_completed": ORIGINAL_COMPLETED,
        "original_rejected": 1,
        "original_uncertain": 0,
        "never_attempted_blind_count": len(missing),
        "preserved_rejection_code": REJECT_CODE,
        "maximum_new_calls": MAX_NEW,
        "maximum_total_calls": ORIGINAL_CALLS + MAX_NEW,
        "declared_maximum_reservation_usd": str(
            worst_call_cost(cfg) * (ORIGINAL_CALLS + MAX_NEW)),
        "billing_unverified": True,
        "amendment_template": amendment,
        "approval_template": approval,
    }


def _require_approval(approval, expected):
    if (type(approval) is not dict or set(approval) != set(expected)
            or any(approval.get(k) is not True for k in FLAGS)):
        raise ValueError("Separate owner consent required for R1 continuation")
    for k, v in expected.items():
        if k in FLAGS:
            continue
        if approval[k] != v or type(approval[k]) is not type(v):
            raise ValueError("Owner consent not bound to exact original R1 run")


class R1ContinuationVerifier(SyntheticContinuationVerifier):
    def __init__(self, inputs, cfg, original_root, overlay_audit, *,
                 preflight_result, key, transport=None, fake=False):
        amendment = preflight_result["amendment_template"]
        _, context = gateway_context(inputs, ROUTER, BUDGET, "sensitivity", cfg, fake=fake)
        self.base = PrivateAudit(_root(original_root) / "journal")
        self.base_rows, self.base_phases = journal_rows(
            original_root, digest(context), cfg["max_calls"])
        self.base_count = len(self.base_rows)
        self._original_digest = amendment["original_journal_rows_sha256"]
        self._allowed = frozenset(amendment["never_dispatched_blind_ids"])
        self._rejected = amendment["original_rejected_node_id"]
        # Initialize the real existing Gateway with overlay ONLY.
        DurableGapGPTVerifier.__init__(
            self, cfg, context, overlay_audit, transport=transport,
            key=key, authorized_fake=fake)
        self.audit = _OverlayAudit(self.base, overlay_audit)
        self._verify_overlay(inputs)

    def _completed(self, identity_sha, row, payload, wire, dependency, phase, text):
        rejected = self.base_phases[(self._rejected, "compare")]
        if identity_sha == rejected[0] and row == rejected[1]:
            # Retain the original, L1-rejected answer forever; do NOT resend it.
            raise EvidenceError(REJECT_CODE)
        return super()._completed(
            identity_sha, row, payload, wire, dependency, phase, text)

    def _verify_overlay(self, inputs):
        states = self.phase_states()
        added = {(node, phase): state for (node, phase), state in states.items()
                 if (node, phase) not in self.base_phases}
        if (len(added) > MAX_NEW or
                len(states) > ORIGINAL_CALLS + MAX_NEW or
                any(node not in self._allowed or state != "COMPLETED"
                    for (node, _), state in added.items())):
            raise ValueError("Unsettled/out-of-scope R1 overlay cannot be resumed")
        pairs = {p.node_id: p for p in inputs.pairs}
        for node in self._allowed:
            pair = pairs[node]
            blind = None
            if (node, "blind") in added:
                bp = rich_verifier_input_v2(node, pair.text, pair.neighborhood)
                bi = identity(self.context_digest, "blind", bp, wire_for(bp, self.config), None)
                row = DurableGapGPTVerifier._get(self, bi)
                if row is None:
                    raise ValueError("R1 continuation Blind identity mismatch")
                blind = self._completed(bi, row, bp, wire_for(bp, self.config),
                                        None, "blind", pair.text)
            if (node, "compare") not in added:
                continue
            if blind is None or blind["abstain"]:
                raise ValueError("R1 orphan Comparison")
            cp = rich_verifier_input_v2(
                node, pair.text, pair.neighborhood,
                candidates=tuple(sorted({pair.b1.class_index,
                                         pair.narrative_v0.class_index})),
                blind_class=blind["class_index"])
            ci = identity(self.context_digest, "compare", cp,
                          wire_for(cp, self.config), digest(blind))
            row = DurableGapGPTVerifier._get(self, ci)
            if row is None:
                raise ValueError("R1 continuation Comparison identity mismatch")
            self._completed(ci, row, cp, wire_for(cp, self.config),
                            digest(blind), "compare", pair.text)
        if len(added) > 2 * len(self._allowed):
            raise ValueError("R1 overlay exceeded per-node scope")

    def _reserve(self, identity_sha, payload, dependency, phase, node):
        old, _ = journal_rows(
            self.base.root.parent, self.context_digest, self.maximum_calls)
        if digest([[k, *v] for k, v in sorted(old.items())]) != self._original_digest:
            raise ValueError("Original R1 journal mutated before dispatch")
        if node not in self._allowed or phase not in ("blind", "compare"):
            raise ValueError("Out-of-scope new R1 request")
        if phase == "compare":
            states = self.phase_states()
            if states.get((node, "blind")) != "COMPLETED" or dependency is None:
                raise ValueError("Comparison requires persisted new Blind")
        elif dependency is not None:
            raise ValueError("Blind cannot have a dependency")
        return super()._reserve(identity_sha, payload, dependency, phase, node)

    def _budget_accepts_new_intent(self, existing_count):
        if existing_count + 1 > MAX_NEW or self.base_count + existing_count + 1 > ORIGINAL_CALLS + MAX_NEW:
            raise ValueError("R1 continuation new-call cap exceeded")
        super()._budget_accepts_new_intent(existing_count)


def execute(inputs, original_root, *, config, amendment, approval, key,
            _testing_transport=None, _testing_fake=False):
    """A single explicit live run; no automatic retry or original writes.

    Test-only injected transport is blocked for the public CLI, which has no
    corresponding args. Only tests pass _testing_fake=True.
    """
    cfg = contract_from_dict(config)
    checked = preflight(inputs, original_root, config=cfg, fake=_testing_fake)
    if amendment != checked["amendment_template"]:
        raise ValueError("Unapproved or stale R1 amendment")
    _require_approval(approval, checked["approval_template"])
    if (type(key) is not str or not key or
            (_testing_fake and not callable(_testing_transport)) or
            (not _testing_fake and _testing_transport is not None)):
        raise ValueError("Private credential or transport invalid")
    root = _root(original_root)
    overlay_root = root / OVERLAY
    # Refuse overwriting any earlier/partial attempt. A settled overlay with
    # prior completion may be independently audited but is never re-dispatched.
    if overlay_root.exists():
        raise ValueError("Existing R1 continuation overlay: do not retry/overwrite")
    audit = PrivateAudit(overlay_root / "journal")
    approval_record = {
        "kind": "gapgpt_r1_v1_continuation_approval_v1",
        "approval": approval, "amendment": amendment,
        "provider_invoice_verified": False,
        "original_journal_immutable": True,
    }
    if audit.read(audit.write(approval_record)) != approval_record:
        raise ValueError("Continuation authorization persistence failed")
    verifier = R1ContinuationVerifier(
        inputs, cfg, root, audit, preflight_result=checked, key=key,
        fake=_testing_fake, transport=_testing_transport)
    run = run_offline(
        inputs.pairs, BUDGET, router=ROUTER, verifier=verifier,
        audit=PrivateAudit(overlay_root / "phases"),
        response_version=RICH_VERSION, prompt_version=RICH_PROMPT_V2,
        automated_arbitration_version=AUTOMATED_VERSION)
    states = verifier.phase_states()
    original, original_phases = journal_rows(root, verifier.context_digest, cfg["max_calls"])
    if (digest([[k, *v] for k, v in sorted(original.items())]) !=
            amendment["original_journal_rows_sha256"]):
        raise ValueError("Original R1 journal changed during continuation")
    added = {(n, p): v for (n, p), v in states.items()
             if (n, p) not in original_phases}
    if (len(added) > MAX_NEW or len(states) > ORIGINAL_CALLS + MAX_NEW or
            any(n not in verifier._allowed for n, _ in added)):
        raise ValueError("R1 continuation scope violated")
    run.update({
        "gateway_runner_version": VERSION,
        "gateway_context_sha256": verifier.context_digest,
        "frozen_pairs_sha256": frozen_pair_digest(inputs.pairs),
        "source_hashes": dict(inputs.provenance),
        "data_kind": ("R1_FAKE_TEST_COMBINED_NOT_REAL" if _testing_fake
                      else "GAPGPT_LIVE_R1_CONTINUED_RETAINING_REJECTED"),
        "GT_accessed": False, "training_runs": 0,
        "provider_calls": 0 if _testing_fake else len(states),
        "original_summary_sha256": amendment["original_summary_sha256"],
        "original_report_sha256": amendment["original_report_sha256"],
        "amendment_sha256": digest(amendment),
        "original_journal_rows_sha256": amendment["original_journal_rows_sha256"],
        "original_response_reused_count": ORIGINAL_COMPLETED,
        "original_rejected_preserved": 1,
    })
    report = {"kind": "gapgpt_r1_v1_continuation_private_report",
              "schema": VERSION, "run": run,
              "amendment_sha256": digest(amendment),
              "original_summary_sha256": amendment["original_summary_sha256"],
              "original_report_sha256": amendment["original_report_sha256"],
              "original_journal_rows_sha256": amendment["original_journal_rows_sha256"]}
    run_sha = audit.write(report)
    summary = {
        "schema": VERSION,
        "status": ("HALTED_NO_AUTOMATIC_RETRY" if verifier.halted or
                   any(v not in ("COMPLETED", "REJECTED") for v in added.values())
                   or any(v == "REJECTED" for v in added.values())
                   else "CONTINUED_PRESERVING_REJECTED_COMPARISON"),
        "source_original_status": "BLOCKED_NO_AUTOMATIC_RETRY",
        "router": ROUTER, "selected_count": BUDGET,
        "original_intents": ORIGINAL_CALLS,
        "original_completed": ORIGINAL_COMPLETED, "original_rejected": 1,
        "new_dispatches": verifier.dispatches, "new_intents": len(added),
        "new_state_counts": {s: sum(v == s for v in added.values())
                             for s in ("COMPLETED", "REJECTED", "UNCERTAIN")},
        "blinds_completed": sum(phase == "blind" and state == "COMPLETED"
                                for (n, phase), state in states.items()),
        "comparisons_completed": sum(phase == "compare" and state == "COMPLETED"
                                     for (n, phase), state in states.items()),
        "total_intents": len(states), "total_cap": ORIGINAL_CALLS + MAX_NEW,
        "source_original_summary_sha256": amendment["original_summary_sha256"],
        "source_original_report_sha256": amendment["original_report_sha256"],
        "source_original_journal_rows_sha256": amendment["original_journal_rows_sha256"],
        "gateway_context_sha256": verifier.context_digest,
        "amendment_sha256": digest(amendment),
        "private_combined_report_sha256": run_sha,
        "GT_accessed": False, "training_runs": 0,
        "training_admission": False, "provider_invoice_verified": False,
        "read_only_original_journal": True,
        "scientific_status": "POST_HOC_R1_NO_SEMANTIC_L2_OR_GCN",
    }
    summary_sha = audit.write(summary)
    summary["private_summary_sha256"] = summary_sha
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "live"), required=True)
    for name in ("frozen-root", "authentic-root", "output-root", "gateway-config"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--amendment-file", type=Path)
    parser.add_argument("--owner-approval-file", type=Path)
    parser.add_argument("--enable-real-dispatch", action="store_true")
    args = parser.parse_args(argv)
    try:
        cfg = json.loads(args.gateway_config.read_text(encoding="utf-8"))
        inputs = load_project_inputs(args.frozen_root, args.authentic_root)
        if args.mode == "preflight":
            if (args.enable_real_dispatch or args.amendment_file is not None or
                    args.owner_approval_file is not None):
                raise ValueError("Read-only preflight forbids dispatch approval")
            result = preflight(inputs, args.output_root, config=cfg)
        else:
            if (not args.enable_real_dispatch or args.amendment_file is None or
                    args.owner_approval_file is None or
                    any(x.is_symlink() for x in (
                        args.amendment_file, args.owner_approval_file)) or
                    ".local_artifacts" not in
                      args.owner_approval_file.resolve(strict=False).parts or
                    ".local_artifacts" not in
                      args.amendment_file.resolve(strict=False).parts):
                raise ValueError("Explicit private owner authorization required")
            result = execute(
                inputs, args.output_root, config=cfg,
                amendment=json.loads(args.amendment_file.read_text(encoding="utf-8")),
                approval=json.loads(args.owner_approval_file.read_text(encoding="utf-8")),
                key=os.environ.get(KEY_VARIABLE))
        print(json.dumps(result, sort_keys=True, ensure_ascii=False,
                         indent=2, allow_nan=False))
        return 2 if result.get("status") == "HALTED_NO_AUTOMATIC_RETRY" else 0
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"status": "FAIL_CLOSED"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
