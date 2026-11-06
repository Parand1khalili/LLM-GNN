"""Read-only, metadata-only reconciliation of private GapGPT usage.

This never calls the provider, changes a receipt, opens GT, or re-scores L1.
It reports estimated spend at declared rates, NOT verified provider billing.
"""
import argparse
from contextlib import closing
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys

from .gateway_diagnostics import _private_file, _receipt
from .gapgpt_live import contract_from_dict
from .experiment import digest

VERSION = "sara.gapgpt.read_only_usage_reconciliation.v1"


def _valid_usage(envelope, config):
    if type(envelope) is not dict:
        return None
    if envelope.get("model") not in config["allowed_returned_models"]:
        return None
    usage = envelope.get("usage")
    if type(usage) is not dict:
        return None
    p, c, total = (usage.get("prompt_tokens"), usage.get("completion_tokens"),
                   usage.get("total_tokens"))
    if (type(p) is not int or type(c) is not int or p < 0 or c < 0 or
            p > config["max_input_tokens"] or c > config["max_tokens"] or
            (total is not None and (type(total) is not int or total != p + c))):
        return None
    detail = usage.get("completion_tokens_details")
    reasoning = detail.get("reasoning_tokens") if type(detail) is dict else None
    if reasoning is not None and (
            type(reasoning) is not int or reasoning < 0 or reasoning > c):
        return None
    return p, c, reasoning


def reconcile(output_root, *, expected_context_sha256, config, check_node_ids=()):
    cfg = contract_from_dict(config)
    if (type(expected_context_sha256) is not str or
            re.fullmatch(r"[0-9a-f]{64}", expected_context_sha256) is None):
        raise ValueError("Expected context digest required")
    if (type(check_node_ids) not in (list, tuple) or
            any(type(n) is not int or n < 0 for n in check_node_ids) or
            len(set(check_node_ids)) != len(check_node_ids)):
        raise ValueError("Invalid diagnostic node IDs")
    supplied = Path(output_root)
    if supplied.is_symlink() or any(p.is_symlink() for p in supplied.parents):
        raise ValueError("Unsafe private path")
    root = supplied.resolve(strict=False)
    if ".local_artifacts" not in root.parts or root.is_symlink():
        raise ValueError("Private output root required")
    journal = root / "journal"
    if journal.is_symlink() or not journal.is_dir():
        raise ValueError("Missing private journal")
    path = _private_file(journal, "fixture_journal.sqlite")
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        binding = db.execute("SELECT context_hash,call_limit FROM binding WHERE id=1").fetchall()
        if binding != [(expected_context_sha256, cfg["max_calls"])]:
            raise ValueError("Journal binding mismatch")
        rows = list(db.execute("SELECT node_id,phase,state,receipt FROM intents"))
    sums = {state: {"attempts": 0, "usage_available": 0,
                    "prompt_tokens": 0, "completion_tokens": 0,
                    "reasoning_tokens": 0, "reasoning_available": 0}
            for state in ("COMPLETED", "REJECTED", "UNCERTAIN")}
    present = {}
    for node, phase, state, receipt_sha in rows:
        if state not in sums or (node, phase) in present:
            raise ValueError("Unrecognized or duplicate journal intent")
        present[(node, phase)] = state
        bucket = sums[state]
        bucket["attempts"] += 1
        if state == "UNCERTAIN":
            continue
        record = _receipt(journal, receipt_sha)
        if (record.get("kind") != "gapgpt_gateway_response" or
                record.get("context_sha256") != expected_context_sha256 or
                type(record.get("raw_hex")) is not str):
            raise ValueError("Receipt identity/binding mismatch")
        raw = bytes.fromhex(record["raw_hex"])
        if hashlib.sha256(raw).hexdigest() != record.get("response_sha256"):
            raise ValueError("Raw response hash mismatch")
        try:
            envelope = json.loads(raw)
        except (UnicodeError, ValueError):
            envelope = None
        usage = _valid_usage(envelope, cfg)
        if usage is None:
            if state == "COMPLETED":
                raise ValueError("Completed usage receipt invalid")
            continue
        p, c, r = usage
        if state == "COMPLETED":
            summary = record.get("usage_summary")
            if (type(summary) is not dict or
                    summary.get("prompt_tokens") != p or
                    summary.get("completion_tokens") != c or
                    summary.get("returned_model") != envelope["model"]):
                raise ValueError("Completed receipt metadata mismatch")
        bucket["usage_available"] += 1
        bucket["prompt_tokens"] += p
        bucket["completion_tokens"] += c
        if r is not None:
            bucket["reasoning_tokens"] += r
            bucket["reasoning_available"] += 1

    def output(bucket):
        available = bucket["usage_available"]
        cost = ((Decimal(bucket["prompt_tokens"]) * Decimal(cfg["input_usd_per_million"]) +
                 Decimal(bucket["completion_tokens"]) * Decimal(cfg["output_usd_per_million"]))
                / Decimal(1000000))
        return {**bucket, "reasoning_tokens": (
                bucket["reasoning_tokens"] if bucket["reasoning_available"] == available else None),
                "estimated_cost_usd": str(cost) if available == bucket["attempts"] else None}
    completed, rejected, uncertain = (sums[x] for x in ("COMPLETED", "REJECTED", "UNCERTAIN"))
    all_count = sum(x["attempts"] for x in sums.values())
    all_known = sum(x["usage_available"] for x in sums.values())
    combined = {key: sum(x[key] for x in sums.values())
                for key in ("prompt_tokens", "completion_tokens", "reasoning_tokens",
                            "reasoning_available")}
    combined.update(attempts=all_count, usage_available=all_known)
    checked = {}
    for node in check_node_ids:
        phases = {phase: state for (n, phase), state in present.items() if n == node}
        checked[str(node)] = (phases if phases else
                              {"status": "NOT_ATTEMPTED_AFTER_HALT"
                               if rejected["attempts"] or uncertain["attempts"] else
                               "NO_INTENT_NOT_PROVEN_HALTED"})
    return {"schema": VERSION, "read_only": True, "provider_calls": 0,
            "journal_context_verified": True,
            "gateway_contract_sha256": digest(cfg),
            "completed": output(completed), "rejected": output(rejected),
            "uncertain": output(uncertain), "all_attempts": output(combined),
            "unknown_billing_attempts": all_count - all_known,
            "provider_invoice_verified": False,
            "cost_status": "USER_DECLARED_RATE_ESTIMATE_NOT_PROVIDER_BILLING",
            "checked_nodes": checked}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--expected-context-sha256", required=True)
    parser.add_argument("--gateway-config", required=True, type=Path)
    parser.add_argument("--check-node-ids", nargs="*", type=int, default=[])
    args = parser.parse_args(argv)
    try:
        result = reconcile(args.output_root,
                           expected_context_sha256=args.expected_context_sha256,
                           config=json.loads(args.gateway_config.read_text(encoding="utf-8")),
                           check_node_ids=args.check_node_ids)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, sqlite3.DatabaseError):
        print(json.dumps({"status": "FAIL_CLOSED"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
