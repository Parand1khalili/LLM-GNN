"""GT-free, read-only preflight for an amended continuation of the SAME batch.

Historical receipts and SQLite are never written. This module intentionally
does NOT authorize or expose any live continuation command.
"""
import argparse
from contextlib import closing
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

from ..io.project import load_project_inputs
from .audit import PrivateAudit
from .evidence import EvidenceError
from .experiment import digest
from .gapgpt_live import (
    VERSION as GATEWAY_VERSION, JOURNAL_VERSION, DurableGapGPTVerifier,
    contract_from_dict, strict_envelope, wire_for, worst_call_cost)
from .gateway_preflight import validate_batch_wire
from .gateway_run import gateway_context
from .inputs import canonical_bytes
from .rich_evidence import rich_verifier_input_v2

VERSION = "sara.gapgpt.continuation_preflight.v1"
_SENTINEL = "read-only-diagnostic-non-credential-sentinel"


def journal_rows(root, context_sha, limit):
    root = Path(root)
    if root.is_symlink() or any(p.is_symlink() for p in root.parents):
        raise ValueError("Unsafe private root")
    path = root / "journal" / "fixture_journal.sqlite"
    if (".local_artifacts" not in root.resolve().parts or
            path.is_symlink() or path.parent.is_symlink() or not path.is_file()):
        raise ValueError("Original private journal missing")
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("SELECT version,context_hash,call_limit FROM binding WHERE id=1").fetchall() != [
                (JOURNAL_VERSION, context_sha, limit)]:
            raise ValueError("Original binding mismatch")
        rows = db.execute("SELECT identity,payload_hash,dependency,phase,state,receipt,node_id FROM intents").fetchall()
    if len(rows) > limit:
        raise ValueError("Original call limit exceeded")
    by_id, by_phase = {}, {}
    for identity, payload_sha, dep, phase, state, receipt, node in rows:
        if (type(node) is not int or type(identity) is not str or
                phase not in ("blind", "compare") or
                state not in ("COMPLETED", "REJECTED", "UNCERTAIN") or
                identity in by_id or (node, phase) in by_phase):
            raise ValueError("Original journal intent collision")
        row = (payload_sha, dep, phase, state, receipt)
        by_id[identity] = row
        by_phase[(node, phase)] = (identity, row)
    return by_id, by_phase


def identity(context_sha, phase, payload, wire, dependency):
    return digest({"version": GATEWAY_VERSION, "phase": phase,
                   "context_sha256": context_sha, "payload_sha256": digest(payload),
                   "wire_sha256": hashlib.sha256(wire).hexdigest(),
                   "blind_response_sha256": dependency})


def replay(audit, row, expected_id, payload, wire, dependency, context_sha, text, cfg):
    record_id, values = row
    payload_sha, saved_dep, phase, state, receipt_id = values
    if (record_id != expected_id or payload_sha != digest(payload)
            or saved_dep != dependency or not receipt_id):
        raise ValueError("Original request identity/dependency mismatch")
    receipt = audit.read(receipt_id)
    if (receipt.get("kind") != "gapgpt_gateway_response"
            or receipt.get("identity") != expected_id
            or receipt.get("context_sha256") != context_sha
            or receipt.get("payload_sha256") != payload_sha
            or receipt.get("dependency") != dependency
            or receipt.get("wire_sha256") != hashlib.sha256(wire).hexdigest()
            or type(receipt.get("raw_hex")) is not str):
        raise ValueError("Original response receipt binding mismatch")
    raw = bytes.fromhex(receipt["raw_hex"])
    if hashlib.sha256(raw).hexdigest() != receipt.get("response_sha256"):
        raise ValueError("Original response hash mismatch")
    if state == "REJECTED":
        if receipt.get("reject_code") != "L1_DUPLICATE_EVIDENCE":
            raise ValueError("Unexpected rejection code")
        try:
            strict_envelope(receipt.get("http_status"), raw, cfg, _SENTINEL, text)
        except EvidenceError as exc:
            if exc.code == "L1_DUPLICATE_EVIDENCE":
                return None
        raise ValueError("Rejected L1 failure not reproducible")
    if state != "COMPLETED":
        raise ValueError("Unsafe original intent")
    result, usage = strict_envelope(receipt.get("http_status"), raw, cfg, _SENTINEL, text)
    if receipt.get("usage_summary") != usage:
        raise ValueError("Original completed usage mismatch")
    return json.loads(canonical_bytes(result))


def inspect(inputs, output_root, *, config, expected_context_sha256,
            router="r0", budget=37, cohort="sensitivity", fake=False,
            expected_rejection=None):
    """Validate every saved request, including a failed comparison, without writes."""
    cfg = contract_from_dict(config)
    selected, ctx = gateway_context(inputs, router, budget, cohort, cfg, fake=fake)
    validate_batch_wire(inputs, router, budget, cfg)
    sha = digest(ctx)
    if sha != expected_context_sha256:
        raise ValueError("Execution context mismatch")
    original, phases = journal_rows(output_root, sha, cfg["max_calls"])
    if any(node not in selected for node, _ in phases):
        raise ValueError("Original node outside frozen selection")
    if any(row[3] == "UNCERTAIN" for row in original.values()):
        raise ValueError("Original unresolved intent forbids continuation")
    # The directory must already exist; PrivateAudit.read verifies protected
    # file mode, ACL and content-addressed receipt hashes.
    audit = PrivateAudit(Path(output_root) / "journal")
    pairs = {p.node_id: p for p in inputs.pairs}
    seen, completed, rejected = set(), 0, []
    missing_blinds, missing_compares, abstained = [], [], []
    for node in selected:
        pair = pairs[node]
        bp = rich_verifier_input_v2(node, pair.text, pair.neighborhood)
        bw = wire_for(bp, cfg)
        bi = identity(sha, "blind", bp, bw, None)
        br = phases.get((node, "blind"))
        if br is None:
            if (node, "compare") in phases:
                raise ValueError("Comparison lacks original blind")
            missing_blinds.append(node)
            continue
        seen.add(bi)
        if br[1][3] != "COMPLETED":
            raise ValueError("Non-completed blind forbids continuation")
        blind = replay(audit, br, bi, bp, bw, None, sha, pair.text, cfg)
        completed += 1
        if blind["abstain"]:
            if (node, "compare") in phases:
                raise ValueError("Comparison after blind abstention")
            abstained.append(node)
            continue
        candidates = tuple(sorted({pair.b1.class_index, pair.narrative_v0.class_index}))
        cp = rich_verifier_input_v2(node, pair.text, pair.neighborhood,
                                    candidates=candidates, blind_class=blind["class_index"])
        cw = wire_for(cp, cfg)
        dep = digest(blind)
        ci = identity(sha, "compare", cp, cw, dep)
        cr = phases.get((node, "compare"))
        if cr is None:
            missing_compares.append(node)
            continue
        seen.add(ci)
        replay(audit, cr, ci, cp, cw, dep, sha, pair.text, cfg)
        if cr[1][3] == "COMPLETED":
            completed += 1
        else:
            rejected.append((node, "compare"))
    if seen != set(original) or len(original) != completed + len(rejected):
        raise ValueError("Original attempts are not fully verified")
    if expected_rejection is not None and rejected != [expected_rejection]:
        raise ValueError("Frozen L1 rejection mismatch")
    capacity = cfg["max_calls"] - len(original)
    possible = 2 * len(missing_blinds) + len(missing_compares)
    if (possible > capacity or
            worst_call_cost(cfg) * (len(original) + possible) > Decimal(cfg["max_spend_usd"])):
        raise ValueError("Cumulative authorization cap would be exceeded")
    return {"schema": VERSION,
            "status": "FRESH_AMENDMENT_AND_OWNER_APPROVAL_REQUIRED",
            "read_only": True, "provider_calls": 0, "GT_accessed": False,
            "training_runs": 0, "original_context_verified": True,
            "gateway_contract_sha256": digest(cfg),
            "original_intents": len(original),
            "completed_replayed_and_l1_verified": completed,
            "rejected_preserved": len(rejected),
            "rejected_phases": [{"node_id": n, "phase": p,
                                "reason": "L1_DUPLICATE_EVIDENCE"} for n, p in rejected],
            "uncertain": 0, "never_dispatched_blind_node_ids": missing_blinds,
            "missing_comparison_after_completed_blind_node_ids": missing_compares,
            "abstained_blind_node_ids": abstained,
            "conditional_comparison_slots_after_new_blinds": len(missing_blinds),
            "remaining_logical_capacity": capacity,
            "maximum_possible_new_calls": possible,
            "authorization": "NOT_GRANTED_REQUIRES_SEPARATE_OWNER_AMENDMENT"}


class _OverlayAudit:
    def __init__(self, base, overlay):
        self.base, self.overlay = base, overlay
        self.root = overlay.root

    def read(self, receipt):
        # Never suppress a malformed continuation receipt by silently falling
        # back to the original for a known overlay identifier.
        if (self.overlay.root / (receipt + ".json")).exists():
            return self.overlay.read(receipt)
        return self.base.read(receipt)

    def write(self, record):
        return self.overlay.write(record)


class SyntheticContinuationVerifier(DurableGapGPTVerifier):
    """Fake transport only; original journal read-only, overlay append-only.

    A separately authorized live adapter can use the same identity accounting
    later; no live dispatch interface is exposed in Slice 2.
    """
    def __init__(self, config, context, original_root, overlay_audit,
                 *, transport, original_count):
        if not callable(transport):
            raise ValueError("Only synthetic transport permitted")
        self.base = PrivateAudit(Path(original_root) / "journal")
        self.base_rows, self.base_phases = journal_rows(
            original_root, digest(context), config["max_calls"])
        if len(self.base_rows) != original_count or any(
                v[3] == "UNCERTAIN" for v in self.base_rows.values()):
            raise ValueError("Original journal differs or contains uncertainty")
        self.base_count = original_count
        super().__init__(config, context, overlay_audit, transport=transport,
                         key="synthetic-local-key-unknown", authorized_fake=True)
        self.audit = _OverlayAudit(self.base, overlay_audit)

    def _get(self, identity_sha):
        saved = super()._get(identity_sha)
        return saved if saved is not None else self.base_rows.get(identity_sha)

    def _reserve(self, identity_sha, payload, dependency, phase, node):
        if identity_sha in self.base_rows or (node, phase) in self.base_phases:
            raise ValueError("Original intent cannot be dispatched again")
        return super()._reserve(identity_sha, payload, dependency, phase, node)

    def _budget_accepts_new_intent(self, overlay_count):
        calls = self.base_count + overlay_count + 1
        if (calls > self.maximum_calls or
                worst_call_cost(self.config) * calls > Decimal(self.config["max_spend_usd"])):
            raise ValueError("Cumulative continuation reservation exceeded")

    def phase_states(self):
        values = {(n, p): row[1][3] for (n, p), row in self.base_phases.items()}
        for key, state in super().phase_states().items():
            if key in values:
                raise ValueError("Overlay duplicated original phase")
            values[key] = state
        return values


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-root", required=True, type=Path)
    parser.add_argument("--authentic-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--gateway-config", required=True, type=Path)
    parser.add_argument("--expected-context-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if args.gateway_config.is_symlink():
            raise ValueError("Unsafe config")
        result = inspect(
            load_project_inputs(args.frozen_root, args.authentic_root),
            args.output_root,
            config=json.loads(args.gateway_config.read_text(encoding="utf-8")),
            expected_context_sha256=args.expected_context_sha256,
            expected_rejection=(1814, "compare"))
        if (result["original_intents"] != 53 or
                result["completed_replayed_and_l1_verified"] != 52 or
                result["rejected_preserved"] != 1):
            raise ValueError("Original owner-reported freeze not matched")
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, sqlite3.DatabaseError):
        print(json.dumps({"status": "FAIL_CLOSED"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
