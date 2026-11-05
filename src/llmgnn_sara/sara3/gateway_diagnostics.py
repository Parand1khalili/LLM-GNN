"""Read-only, content-free diagnosis of rejected private GapGPT receipts.

Does not request a key, call the provider, decode GT, re-score L1 or
modify an existing receipt/SQLite journal. Never prints prompt/response text.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys

from .evidence import EvidenceError, quote_for_matching

VERSION = "sara.gapgpt.rejected_receipt_diagnostic.v1"
_MODELS = frozenset(("gpt-6-luna", "gpt-6-luna-2026-09-22"))
_FINISH = frozenset(("stop", "length", "content_filter", "tool_calls"))


def _private_file(root, name):
    path = root / name
    if path.is_symlink() or not path.is_file():
        raise ValueError("Unsafe or missing private receipt")
    return path


def _receipt(root, receipt):
    if type(receipt) is not str or re.fullmatch(r"[0-9a-f]{64}", receipt) is None:
        raise ValueError("Invalid receipt digest")
    blob = _private_file(root, receipt + ".json").read_bytes()
    if hashlib.sha256(blob).hexdigest() != receipt:
        raise ValueError("Private receipt content hash mismatch")
    value = json.loads(blob)
    if type(value) is not dict:
        raise ValueError("Invalid private receipt")
    return value


def _sanitized_usage(value):
    if type(value) is not dict:
        value = {}
    def number(key):
        item = value.get(key)
        return item if type(item) is int and item >= 0 else None
    details = value.get("completion_tokens_details")
    details = details if type(details) is dict else {}
    rt = details.get("reasoning_tokens")
    return {"prompt_tokens": number("prompt_tokens"),
            "completion_tokens": number("completion_tokens"),
            "reasoning_tokens": rt if type(rt) is int and rt >= 0 else None}


def _content_diagnostic(envelope):
    choices = envelope.get("choices")
    choice = choices[0] if type(choices) is list and len(choices) == 1 and type(choices[0]) is dict else {}
    message = choice.get("message")
    text = message.get("content") if type(message) is dict else None
    result = {"finish_reason": choice.get("finish_reason") if choice.get("finish_reason") in _FINISH
              else "OTHER_OR_MISSING",
              "rich_json_parseable": False,
              "supporting_evidence_count": None,
              "counter_evidence_count": None,
              "duplicate_pair_count": None,
              "duplicate_pair_kinds": {}}
    if type(text) is not str:
        return result
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return result
    if type(data) is not dict:
        return result
    result["rich_json_parseable"] = True
    support, counter = data.get("supporting_evidence"), data.get("counter_evidence")
    if type(support) is not list or type(counter) is not list:
        return result
    result["supporting_evidence_count"] = len(support)
    result["counter_evidence_count"] = len(counter)
    seen = {}
    duplicates = Counter()
    for group, items in (("supporting", support), ("counter", counter)):
        for item in items:
            if type(item) is not dict or type(item.get("source_id")) is not str:
                continue
            try:
                quote = quote_for_matching(item.get("quote"))
            except EvidenceError:
                continue
            key = (item["source_id"], quote)
            if key in seen:
                duplicates[seen[key] + "_then_" + group] += 1
            else:
                seen[key] = group
    result["duplicate_pair_count"] = sum(duplicates.values())
    result["duplicate_pair_kinds"] = dict(sorted(duplicates.items()))
    return result


def diagnose(output_root, *, expected_context_sha256):
    """Return whitelisted metadata only, bound to the caller's frozen run hash."""
    if (type(expected_context_sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}", expected_context_sha256) is None):
        raise ValueError("Expected execution context SHA256 required")
    supplied = Path(output_root)
    if supplied.is_symlink() or any(part.is_symlink() for part in supplied.parents):
        raise ValueError("Private output root cannot contain symlinks")
    root = supplied.resolve(strict=False)
    if ".local_artifacts" not in root.parts or root.is_symlink():
        raise ValueError("Private output root required")
    private = root / "journal"
    if private.is_symlink() or not private.is_dir():
        raise ValueError("Missing or unsafe private journal")
    path = _private_file(private, "fixture_journal.sqlite")
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        rows = db.execute(
            "SELECT version, context_hash, call_limit FROM binding WHERE id=1"
        ).fetchall()
        if (len(rows) != 1 or rows[0][1] != expected_context_sha256
                or rows[0][2] != 74):
            raise ValueError("Private journal binding differs from requested run")
        rejected = db.execute(
            "SELECT node_id,phase,state,receipt FROM intents "
            "WHERE state='REJECTED' ORDER BY node_id,phase"
        ).fetchall()
        counts = dict(db.execute("SELECT state,count(*) FROM intents GROUP BY state"))
    reports = []
    for node, phase, state, receipt_sha in rejected:
        receipt = _receipt(private, receipt_sha)
        raw = bytes.fromhex(receipt.get("raw_hex", ""))
        if (receipt.get("kind") != "gapgpt_gateway_response"
                or receipt.get("context_sha256") != expected_context_sha256
                or hashlib.sha256(raw).hexdigest() != receipt.get("response_sha256")):
            raise ValueError("Rejected response proof differs")
        envelope = json.loads(raw)
        if type(envelope) is not dict:
            raise ValueError("Unexpected response structure")
        model = envelope.get("model")
        provider_id = envelope.get("id")
        reports.append({
            "node_id": node, "phase": phase, "state": state,
            "http_status": receipt.get("http_status"),
            "reject_code": receipt.get("reject_code"),
            "returned_model": model if type(model) is str and model in _MODELS else "OTHER_OR_MISSING",
            "response_id_present": type(provider_id) is str and bool(provider_id),
            **_sanitized_usage(envelope.get("usage")),
            **_content_diagnostic(envelope),
        })
    return {"version": VERSION, "read_only": True,
            "journal_context_verified": True,
            "states": {k: counts.get(k, 0) for k in ("COMPLETED", "REJECTED", "UNCERTAIN")},
            "rejected_receipts": reports, "provider_calls": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--expected-context-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(diagnose(args.output_root,
            expected_context_sha256=args.expected_context_sha256),
            ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, sqlite3.DatabaseError):
        print(json.dumps({"status": "FAIL_CLOSED"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
