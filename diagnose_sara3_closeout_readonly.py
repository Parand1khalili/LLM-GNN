"""Read-only diagnostic for a blocked SARA-3 feasibility closeout.

Place beside closeout_sara3_feasibility.py in the existing llm-gnn checkout.
Does not call closeout.main(), create review packets, open an API connection,
modify historical receipts/ledgers, or print article/model response text.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import traceback

# Exactly these known, static closeout-validator strings may be displayed.
# All other messages are suppressed, since downstream errors can include private data.
SAFE_ERRORS = frozenset({
    'This script must run inside the authenticated project checkout',
    '130 diagnostic provenance mismatch',
    'Unexpected intent counts; manual review required',
    'Unexpected final blind dispatch order',
    'Missing or repeated declared intent',
    'Original ledger state differs',
    'Original request differs from sealed input',
    'Original readiness reason differs',
    'Readiness receipt/ledger binding mismatch',
    'Original readiness raw hash differs',
    'Request context hash differs',
    'Outbound wire digest differs from sealed wire',
    'Response context not uniquely bound',
    'Provider response absent, redacted or hash mismatch',
    'Unexpected provider identity/finish state',
    'Missing text completion',
    'Original readiness content mismatch',
    'Expected blind diagnostic pass missing',
    'Expected genuine L1 rejection changed',
    'Completed ledger incompatible with current L1',
    'Unexpected parsed response',
    'Blind abstention distribution differs',
    'Comparison tally differs',
    '653 exact-evidence diagnostic differs',
    '653 case-only diagnostic differs',
    '130 comparison exact-evidence diagnostic differs',
    '130 comparison case-only diagnostic differs',
    '1243 comparison diagnostics differ',
    'Provider usage missing; cannot publish complete totals',
    'Negative provider token usage',
    'Unsupported completion details',
    'Invalid reasoning tokens',
    'Usage coverage incomplete',
    'Unexpected batch terminal state / digest',
    'Incomplete batch binding',
    'Missing or unsafe ledger',
    'Empty private receipt store',
    'Receipt size limit',
    'Immutable receipt hash mismatch',
    'Missing or ambiguous immutable receipt',
    'Human case not source-exact',
    'Not eligible for L2',
    'Invalid proposed class',
    'Closeout already exists; no regeneration or overwrite',
    'Failed to restrict private file',
})


def classify_error(exc: BaseException) -> dict:
    message = str(exc)
    # Avoid outputting any exception messages not known to be data-free.
    code = message if message in SAFE_ERRORS else 'SUPPRESSED_PRIVATE_OR_UNRECOGNIZED'
    frames = traceback.extract_tb(exc.__traceback__)
    # Keep only the final 4 frames and only code locations; never source lines,
    # local variables, absolute paths, or exception messages from dependencies.
    locations = [
        {'file': Path(frame.filename).name, 'line': frame.lineno, 'function': frame.name}
        for frame in frames[-4:]
    ]
    return {'state': 'VERIFY_FAILED_READ_ONLY', 'error_type': type(exc).__name__,
            'safe_error_code': code, 'code_locations': locations,
            'private_data_printed': False}


def run(root: Path) -> dict:
    target = root / '.local_artifacts' / 'sara3_feasibility_closeout_v1'
    result = {
        'closeout_output_dir_exists': target.exists(),
        'original_closeout_script_exists': (root / 'closeout_sara3_feasibility.py').is_file(),
    }
    if not result['original_closeout_script_exists']:
        return {'state':'MISSING_CLOSEOUT_SCRIPT','details':result}
    if str(root / 'src') not in sys.path:
        sys.path.insert(0, str(root / 'src'))
    script = root / 'closeout_sara3_feasibility.py'
    spec = importlib.util.spec_from_file_location('_sara3_closeout_diagnostic', script)
    if spec is None or spec.loader is None:
        return {'state':'UNABLE_TO_LOAD_SCRIPT','details':result}
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        rows, _private, totals, estimate = module.load_verified(root)
        result.update({'verified_phases':len(rows),
                       'original_blind_count':sum(row['phase']=='blind' for row in rows),
                       'original_comparison_count':sum(row['phase']=='compare' for row in rows),
                       'l1_replay_pass':sum(row['replayed_l1']=='PASS' for row in rows),
                       'usage_totals_present': all(k in totals for k in ('prompt_tokens','completion_tokens'))})
        result['state'] = ('VERIFICATION_PASSED_OUTPUT_DIR_EXISTS'
                           if target.exists() else 'VERIFICATION_PASSED_SAFE_TO_RUN_CLOSEOUT_ONCE')
        return result
    except Exception as exc:
        failure = classify_error(exc)
        failure['closeout_output_dir_exists'] = target.exists()
        return failure


if __name__ == '__main__':
    print(json.dumps(run(Path(__file__).resolve().parent), ensure_ascii=False, indent=2))
