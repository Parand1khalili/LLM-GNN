"""Read-only, non-sensitive phase-by-phase audit of SARA-3 closeout readiness reasons.

Place beside closeout_sara3_feasibility.py at the llm-gnn repository root.
This tool reads but NEVER creates/writes/updates a database or receipt. No HTTP.
Only known constant status/error identifiers are printed; unknown values redacted.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sqlite3
import sys

SAFE_REASON = frozenset({
    "L1_PASS_L2_NOT_ASSESSED", "L1_QUOTE_NOT_FOUND", "RETURNED_MODEL_MISMATCH",
    "MALFORMED_JSON", "MALFORMED_JSON_OR_SCHEMA", "INVALID_ENVELOPE_OR_USAGE",
    "L1_EVIDENCE_MISSING_OR_MALFORMED", "L1_CLAIM_SCHEMA_INVALID",
    "L1_ABSTENTION_CONTRADICTION", "L1_SCHEMA_INVALID", "L1_CLASS_INVALID",
    "L1_TRIVIAL_QUOTE", "L1_DUPLICATE_EVIDENCE", "TRUNCATED_OR_NONFINAL",
    "BODY_LIMIT", "SECRET_ECHO_REDACTED", "HTTP_REJECTION_NO_RETRY",
    "L1_REFERENCE_MISMATCH", "L1_SOURCE_PROVENANCE_INVALID",
})
SAFE_STATE = frozenset({"PENDING", "UNCERTAIN", "COMPLETED", "REJECTED"})


def safe_code(value, allowed):
    return value if type(value) is str and value in allowed else "OTHER_REDACTED"


def inspect(root: Path):
    path = root / "closeout_sara3_feasibility.py"
    if not path.is_file():
        return {"state":"MISSING_CLOSEOUT_SCRIPT"}
    spec = importlib.util.spec_from_file_location("_sara_closeout_readiness", path)
    if spec is None or spec.loader is None:
        return {"state":"CANNOT_LOAD_CLOSEOUT_SCRIPT"}
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    rows = []
    for (node, phase), (folder, expected_state, expected_reason) in m.ORIGINAL.items():
        entry = {"node":node, "phase":phase,
                 "expected_state":safe_code(expected_state,SAFE_STATE),
                 "expected_reason":safe_code(expected_reason, SAFE_REASON)}
        store = root / ".local_artifacts" / folder
        try:
            records = m.receipt_dir(store)
            entries, _run = m.ro_ledger(store / "intent.sqlite")
            matches = [r for r in entries if r[0] == m.EXPECTED_IDENTITIES[(node,phase)]]
            if len(matches) != 1:
                entry["check"] = "MISSING_OR_AMBIGUOUS_INTENT"
            else:
                record = matches[0]
                ledger_state = record[2]
                audit_digest = record[4]
                receipt = records.get(audit_digest)
                entry["actual_state"] = safe_code(ledger_state, SAFE_STATE)
                entry["audit_receipt_present"] = isinstance(receipt, dict)
                if isinstance(receipt,dict):
                    kind = receipt.get("kind")
                    reason = receipt.get("reason")
                    entry["readiness_kind_correct"] = kind == "readiness_response"
                    entry["actual_reason"] = safe_code(reason, SAFE_REASON)
                    entry["readiness_request_hash_bound"] = receipt.get("request_sha256") == record[1]
                    entry["readiness_raw_hash_bound"] = receipt.get("raw_sha256") == record[3]
                    entry["reason_matches_expectation"] = reason == expected_reason
                    entry["state_matches_expectation"] = ledger_state == expected_state
                    entry["check"] = ("PASS" if all((
                        kind == "readiness_response", reason == expected_reason,
                        ledger_state == expected_state,
                        entry["readiness_request_hash_bound"], entry["readiness_raw_hash_bound"]
                    )) else "MISMATCH_REVIEW_REQUIRED")
                else:
                    entry["check"] = "READINESS_RECEIPT_MISSING"
        except (OSError, ValueError, TypeError, KeyError, IndexError, sqlite3.Error) as exc:
            entry["check"] = "READ_ONLY_INSPECTION_BLOCKED"
            entry["error_type"] = type(exc).__name__
        rows.append(entry)
    mismatches = [{"node":r["node"],"phase":r["phase"],"check":r["check"]}
                  for r in rows if r["check"] != "PASS"]
    return {"state":"ALL_READINESS_REASONS_MATCH" if not mismatches else "READINESS_MISMATCH_IDENTIFIED",
            "phase_count":len(rows), "mismatches":mismatches, "phases":rows,
            "private_contents_printed":False,"files_modified":False}


if __name__ == "__main__":
    print(json.dumps(inspect(Path(__file__).resolve().parent),ensure_ascii=False,indent=2))
