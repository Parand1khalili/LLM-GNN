"""Read-only, privacy-preserving summary of the most recent GapGPT post-130 attempt.

Run from the repository root:
    .venv/Scripts/python.exe -B diagnose_gapgpt_post130.py

This program never reads API credentials, never sends network traffic, never edits
SQLite or receipt files, and prints only allowlisted status/reason codes and counts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3

DIRECTORY = Path('.local_artifacts/gapgpt_post130_v1')
KNOWN_STATES = {'PENDING','UNCERTAIN','COMPLETED','REJECTED','NOT_ATTEMPTED',
 'HALTED_REVIEW_REQUIRED_NO_RETRY','FINISHED','NOT_PERMITTED_BLIND_ABSTENTION',
 'HISTORICAL_REJECTED_DIAGNOSTIC_PASS','HISTORICAL_REJECTED_DIAGNOSTIC_L1_PASS'}
KNOWN_REASONS = {'L1_QUOTE_NOT_FOUND','L1_TRIVIAL_QUOTE','L1_SCHEMA_INVALID',
 'L1_CLAIM_SCHEMA_INVALID','L1_EVIDENCE_MISSING_OR_MALFORMED',
 'L1_ABSTENTION_CONTRADICTION','L1_CLASS_INVALID','L1_DUPLICATE_EVIDENCE',
 'L1_SOURCE_PROVENANCE_INVALID','L1_GT_FIELD_FORBIDDEN',
 'MALFORMED_JSON','MALFORMED_JSON_OR_SCHEMA',
 'HTTP_REJECTION_NO_RETRY','RETURNED_MODEL_MISMATCH',
 'INVALID_ENVELOPE_OR_USAGE','TRUNCATED_OR_NONFINAL',
 'BODY_LIMIT','SECRET_ECHO_REDACTED',
 'UNKNOWN_EXECUTION_OR_AUDIT_FAILURE_NO_RETRY','AUDIT_UNAVAILABLE_NO_RETRY',
 'LOCAL_FAILURE_REVIEW_REQUIRED_NO_RETRY','L1_PASS_L2_NOT_ASSESSED'}


def status(s):
    return s if type(s) is str and s in KNOWN_STATES else 'OTHER_OR_NOT_REPORTED'


def reason(s):
    return s if type(s) is str and s in KNOWN_REASONS else 'OTHER_OR_NOT_REPORTED'


def receipt(digest: str):
    if type(digest) is not str or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('Invalid receipt digest')
    f = DIRECTORY / (digest + '.json')
    if f.is_symlink() or not f.is_file() or f.stat().st_size > 10_000_000:
        raise ValueError('Unsafe or missing receipt')
    data = f.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('Receipt integrity failed')
    return json.loads(data)


def main():
    if DIRECTORY.is_symlink() or not DIRECTORY.is_dir():
        raise ValueError('Missing or unsafe local private directory')
    db_path = DIRECTORY / 'intent.sqlite'
    if db_path.is_symlink() or not db_path.is_file():
        raise ValueError('Missing or unsafe SQLite ledger')
    with sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True) as db:
        entries = db.execute('SELECT id, state, audit_sha FROM intents ORDER BY rowid').fetchall()
        run = db.execute('SELECT state FROM remaining_run WHERE id=1').fetchone()
    items = []
    for identity, state, audit_sha in entries:
        chunks = identity.split(':')
        if len(chunks) < 3 or not chunks[-2].isdigit() or chunks[-1] not in {'blind', 'compare'}:
            raise ValueError('Unrecognized intent identity')
        item = {'node': int(chunks[-2]), 'phase': chunks[-1], 'ledger_state': status(state)}
        if audit_sha:
            saved = receipt(audit_sha)
            if saved.get('kind') != 'readiness_response':
                raise ValueError('Unexpected response-receipt kind')
            item['recorded_reason'] = reason(saved.get('reason'))
        else:
            item['recorded_reason'] = 'NO_READINESS_RECEIPT'
        items.append(item)
    summaries = []
    for f in DIRECTORY.glob('*.json'):
        if f.is_symlink() or len(f.stem) != 64 or any(c not in '0123456789abcdef' for c in f.stem):
            raise ValueError('Unexpected receipt filename')
        # Receipts are limited to 10MB. Never show any raw content.
        obj = receipt(f.stem)
        if obj.get('kind') == 'remaining_summary':
            summary = obj.get('summary', {})
            phases = []
            for row in summary.get('rows', []):
                node = row.get('node')
                if type(node) is not int or node not in {637, 1243, 130, 682, 2396, 653}:
                    continue
                if node not in {130, 682, 2396, 653}:
                    continue
                for p in ('blind','compare'):
                    v = row.get(p, {})
                    if not isinstance(v, dict):
                        continue
                    phases.append({'node':node,'phase':p, 'state':status(v.get('state')),
                                   'reason':reason(v.get('reason')),
                                   'l1_status':v.get('l1_status') if v.get('l1_status') in ('PASS','FAIL','NOT_ASSESSED') else 'NOT_REPORTED'})
            summaries.append({'state':status(summary.get('state')), 'phases':phases})
    output = {'private_directory_found':True,
              'batch_ledger_state':status(run[0]) if run else 'NOT_REPORTED',
              'intents':items,
              'summary_receipts':len(summaries),
              'summary': summaries[0] if len(summaries) == 1 else 'MISSING_OR_MULTIPLE'}
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, sqlite3.Error, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({'diagnostic_error_type':type(exc).__name__,
                          'note':'No secrets or raw response printed; do not rerun the pilot.'}))
        raise SystemExit(1)
