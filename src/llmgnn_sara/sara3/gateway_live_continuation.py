"""Strict, explicitly owner-approved continuation of the stopped Cora140 batch.

Only new intents use the isolated overlay; the 53 original intents and their
receipts are read-only. No GT, GCN training, retry, or fresh experiment.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys

from ..io.project import load_project_inputs
from .audit import PrivateAudit
from .automated_policy import VERSION as AUTOMATED_VERSION
from .experiment import digest
from .gapgpt_live import DurableGapGPTVerifier, KEY_VARIABLE, contract_from_dict, wire_for
from .gateway_continuation import (
    AMENDMENT_VERSION, FROZEN_BLINDS, FROZEN_CONTEXT_SHA256,
    FROZEN_CONTRACT_SHA256, AmendedSyntheticContinuationVerifier,
    SyntheticContinuationVerifier, _OverlayAudit, amendment_preflight,
    identity, journal_rows)
from .gateway_run import gateway_context
from .inputs import canonical_bytes
from .pipeline import run_offline
from .rich_evidence import RICH_PROMPT_V2, RICH_VERSION, rich_verifier_input_v2

VERSION = "sara.gapgpt.cora140.live_continuation.v1"
APPROVAL_VERSION = "sara.gapgpt.cora140.continuation_owner_approval.v1"
OVERLAY = "continuation_amendment_v1"
FROZEN_REJECTED_NODE = 1814
OWNER_FLAGS = ("data_sharing_approved", "spend_approved",
               "explicit_continuation_dispatch_approved")


def require_continuation_approval(approval, amendment, config):
    """Exact separate approval; legacy batch authorization is never inherited."""
    expected = {
        "version": APPROVAL_VERSION,
        "amendment_sha256": digest(amendment),
        "execution_context_sha256": FROZEN_CONTEXT_SHA256,
        "gateway_contract_sha256": FROZEN_CONTRACT_SHA256,
        "original_intents": 53,
        "maximum_new_calls": 16,
        "maximum_cumulative_calls": 69,
        "max_spend_usd": config["max_spend_usd"],
        **{name: True for name in OWNER_FLAGS},
    }
    if type(approval) is not dict or approval != expected or any(
            type(approval.get(name)) is not bool for name in OWNER_FLAGS):
        raise ValueError("Separate exact continuation approval required")
    return expected


class LiveAmendedContinuationVerifier(AmendedSyntheticContinuationVerifier):
    """Reuses the audited Gateway HTTP path; no fake transport permitted."""

    def __init__(self, inputs, config, original_root, overlay_audit,
                 *, amendment, key):
        cfg = contract_from_dict(config)
        checked = amendment_preflight(
            inputs, original_root, config=cfg, amendment=amendment, fake=False)
        _, context = gateway_context(inputs, "r0", 37, "sensitivity", cfg, fake=False)
        if digest(context) != FROZEN_CONTEXT_SHA256:
            raise ValueError("Frozen live context mismatch")
        self._allowed_nodes = frozenset(FROZEN_BLINDS)
        self.base = PrivateAudit(Path(original_root) / "journal")
        self.base_rows, self.base_phases = journal_rows(
            original_root, digest(context), cfg["max_calls"])
        self.base_count = len(self.base_rows)
        if self.base_count != checked["original_intents"]:
            raise ValueError("Frozen original count mismatch")
        # DurableGapGPTVerifier cannot dispatch until the owner-approved
        # invoking runner explicitly calls blind/compare.
        DurableGapGPTVerifier.__init__(
            self, cfg, context, overlay_audit,
            transport=None, key=key, authorized_fake=False)
        self.audit = _OverlayAudit(self.base, overlay_audit)
        self._verify_overlay(inputs)

    def _verify_overlay(self, inputs):
        """Before ANY live call, revalidate every saved overlay response/identity."""
        phases = SyntheticContinuationVerifier.phase_states(self)
        additions = {(n, p): state for (n, p), state in phases.items()
                     if (n, p) not in self.base_phases}
        if (len(additions) > 16 or len(phases) > 69 or
                any(n not in self._allowed_nodes for n, _ in additions) or
                any(state != "COMPLETED" for state in additions.values())):
            raise ValueError("Unsettled or out-of-scope overlay forbids live continuation")
        pairs = {p.node_id: p for p in inputs.pairs}
        for node in FROZEN_BLINDS:
            pair = pairs[node]
            bp = rich_verifier_input_v2(node, pair.text, pair.neighborhood)
            bw = wire_for(bp, self.config)
            bi = identity(self.context_digest, "blind", bp, bw, None)
            blind = None
            if (node, "blind") in additions:
                row = DurableGapGPTVerifier._get(self, bi)
                if row is None:
                    raise ValueError("Overlay blind identity mismatch")
                blind = self._completed(bi, row, bp, bw, None, "blind", pair.text)
            if (node, "compare") not in additions:
                continue
            if blind is None or blind["abstain"]:
                raise ValueError("Overlay comparison missing valid blind")
            candidates = tuple(sorted({pair.b1.class_index,
                                       pair.narrative_v0.class_index}))
            cp = rich_verifier_input_v2(
                node, pair.text, pair.neighborhood, candidates=candidates,
                blind_class=blind["class_index"])
            cw = wire_for(cp, self.config)
            dep = digest(blind)
            ci = identity(self.context_digest, "compare", cp, cw, dep)
            row = DurableGapGPTVerifier._get(self, ci)
            if row is None:
                raise ValueError("Overlay comparison identity mismatch")
            self._completed(ci, row, cp, cw, dep, "compare", pair.text)

    def _reserve(self, identity_sha, payload, dependency, phase, node):
        # Recheck original SQLite binding/identities at the irreversible write
        # boundary, even if another process changed the original after preflight.
        original, phases = journal_rows(
            self.base.root.parent, self.context_digest, self.maximum_calls)
        if original != self.base_rows or phases != self.base_phases:
            raise ValueError("Original historical journal changed during continuation")
        return super()._reserve(identity_sha, payload, dependency, phase, node)


def execute(inputs, original_root, *, config, amendment, approval, key):
    """Single local invocation, zero implicit approval, at most sixteen new calls."""
    cfg = contract_from_dict(config)
    if digest(cfg) != FROZEN_CONTRACT_SHA256:
        raise ValueError("Frozen Gateway contract mismatch")
    require_continuation_approval(approval, amendment, cfg)
    admission = amendment_preflight(
        inputs, original_root, config=cfg, amendment=amendment, fake=False)
    root = Path(original_root)
    if root.is_symlink() or ".local_artifacts" not in root.resolve().parts:
        raise ValueError("Private original root required")
    if type(key) is not str or not key:
        raise ValueError("Missing environment credential")
    overlay = root / OVERLAY
    audit = PrivateAudit(overlay / "journal")
    verifier = LiveAmendedContinuationVerifier(
        inputs, cfg, root, audit, amendment=amendment, key=key)
    # Authorization is durable in the new overlay ONLY, and is verified prior
    # to the first network send. It does not modify original authorizations.
    bound = {"kind": "gapgpt_continuation_authorization_v1",
             "approval": approval, "amendment_sha256": digest(amendment),
             "original_context_sha256": FROZEN_CONTEXT_SHA256,
             "original_intents": 53, "new_call_cap": 16,
             "provider_quotation_verified": False,
             "provider_invoice_verified": False}
    if audit.read(audit.write(bound)) != bound:
        raise ValueError("Continuation authorization audit mismatch")
    run = run_offline(
        inputs.pairs, 37, router="r0", verifier=verifier,
        audit=PrivateAudit(overlay / "phases"),
        response_version=RICH_VERSION, prompt_version=RICH_PROMPT_V2,
        automated_arbitration_version=AUTOMATED_VERSION)
    states = verifier.phase_states()
    original_phases = {(n, p): row[1][3] for (n, p), row in verifier.base_phases.items()}
    if (len(original_phases) != 53
            or any(states.get(key) != val for key, val in original_phases.items())
            or states.get((FROZEN_REJECTED_NODE, "compare")) != "REJECTED"
            or verifier.dispatches > 16 or len(states) > 69):
        raise ValueError("Continuation final scope mismatch")
    new_states = {key: state for key, state in states.items()
                  if key not in original_phases}
    # Private report only; public stdout never emits target text or raw evidence.
    run_sha = audit.write({"kind": "gapgpt_continuation_private_report",
                           "amendment_sha256": digest(amendment), "run": run})
    summary = {
        "schema": VERSION,
        "status": ("HALTED_NO_AUTOMATIC_RETRY"
                   if verifier.halted or any(x != "COMPLETED" for x in new_states.values())
                   else "CONTINUATION_FINISHED_WITH_HISTORICAL_REJECTION"),
        "amendment_sha256": digest(amendment),
        "original_context_sha256": FROZEN_CONTEXT_SHA256,
        "original_completed": 52, "original_rejected": 1,
        "original_uncertain": 0, "original_intents": 53,
        "new_dispatches_this_invocation": verifier.dispatches,
        "new_intents_total": len(new_states),
        "new_states": {x: sum(v == x for v in new_states.values())
                       for x in ("COMPLETED", "REJECTED", "UNCERTAIN")},
        "remaining_new_call_capacity": 16 - len(new_states),
        "cumulative_intents": len(states), "cumulative_cap": 69,
        "historical_rejection_node_id": FROZEN_REJECTED_NODE,
        "historical_rejection_code": "L1_DUPLICATE_EVIDENCE",
        "original_journal_write_operations": 0,
        "training_runs": 0, "GT_accessed": False,
        "provisional_training_eligible": False,
        "provider_invoice_verified": False,
        "private_report_sha256": run_sha,
    }
    audit.read(audit.write(summary))
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-root", type=Path, required=True)
    parser.add_argument("--authentic-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--gateway-config", type=Path, required=True)
    parser.add_argument("--amendment-file", type=Path, required=True)
    parser.add_argument("--owner-approval-file", type=Path, required=True)
    parser.add_argument("--enable-real-dispatch", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        if any(p.is_symlink() for p in (
                args.gateway_config, args.amendment_file, args.owner_approval_file)):
            raise ValueError("Unsafe input file")
        if ".local_artifacts" not in args.owner_approval_file.resolve().parts:
            raise ValueError("Owner approval must remain in private artifacts")
        result = execute(
            load_project_inputs(args.frozen_root, args.authentic_root),
            args.output_root,
            config=json.loads(args.gateway_config.read_text(encoding="utf-8")),
            amendment=json.loads(args.amendment_file.read_text(encoding="utf-8")),
            approval=json.loads(args.owner_approval_file.read_text(encoding="utf-8")),
            key=os.environ.get(KEY_VARIABLE))
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 2 if result["status"] == "HALTED_NO_AUTOMATIC_RETRY" else 0
    except (OSError, TypeError, ValueError, KeyError, sqlite3.DatabaseError):
        print(json.dumps({"status": "FAIL_CLOSED"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
