"""Offline-only reconciliation and strict three-sample prediction freeze.

Historical intents, receipts, parser and voting are never changed. No partial
sample vote is introduced: invalid and ambiguous responses remain unavailable.
"""
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from .six_arm_run import PIN, ROOT, parse
from .voting import vote_parsed_samples
from ..sara3.audit import PrivateAudit
from ..sara3.experiment import digest
from ..sara3.inputs import canonical_bytes
from ..io.frozen import CLASSES

OUT = Path('.local_artifacts/six_arm_offline_analysis')
SUMMARY = '6cffe5b1bfdae99ef26eefb70dc3fde5c28fb0b37e3bc8bd713c7c4d6751e5fe'
CONFIG = '0521e6b4f66fa7c1591c059cabab6fcdaa1de03f4ba6986b4c82997ec43ef144'
ARMS = ('B1', 'v0', 'v1-A', 'v1-B', 'v1-C', 'v1-D')
PROTOCOL = {
    'version': 'sara.six_arm.strict_partial_analysis.v1',
    'primary': 'v1-B minus v1-A on common targets with three valid samples each',
    'three_valid': 'unchanged vote_parsed_samples; sample_index ascending',
    'zero_one_two_valid': 'UNAVAILABLE; no vote, no imputation, no partial-sample sensitivity',
    'ties': 'historical first appearance in sample_index order',
    'invalid': 'historical parser rejects malformed output, invalid class or confidence',
    'ambiguous': 'no authentic response; no replay; unavailable',
    'integrity_failure': 'fail closed before prediction freeze or GT',
    'confidence': 'historical vote-derived uncalibrated value; missing stays null',
    'all_target_accuracy': 'correct / all manifest targets; unavailable is not labelled wrong',
    'selective_accuracy': 'correct / valid strict-three predictions',
    'paired': 'common strict-three mask; also report all-target difference and mask sizes',
    'classwise': '7x8 confusion: final column unavailable; unavailable counts as recall FN',
    'strata': 'posthoc h<0.5 heterophilic, h=0.5 mixed, h>0.5 homophilic; isolated separate',
    'limitations': ['LIMITED_PROVENANCE_EXPLORATORY', 'EXPLORATORY_NOT_INDEPENDENT'],
    'new_api_calls': 0, 'training_runs': 0,
}


def snapshot(root):
    """Hash all original files, including unresolved intents, without writing."""
    root = Path(root)
    result = {}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():
            raise ValueError('UNSAFE_SOURCE')
        if p.is_file():
            result[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def binding_for(entry, config):
    if hashlib.sha256(entry['prompt'].encode()).hexdigest() != entry['prompt_sha256']:
        raise ValueError('PROMPT_HASH')
    wire = canonical_bytes(dict(model=config['model'], temperature=1, n=1, max_tokens=4096,
                                messages=[dict(role='user', content=entry['prompt'])]))
    return dict(entry_sha256=digest(entry), wire_sha256=hashlib.sha256(wire).hexdigest(),
                config_sha256=digest(config))


def inspect_request(root, entry, config):
    binding = binding_for(entry, config)
    identity = digest(binding)
    directory = Path(root) / 'calls' / identity
    row = dict(identity=identity, arm=entry['arm'], node_id=entry['node_id'],
               sample_index=entry['sample_index'], prompt_sha256=entry['prompt_sha256'],
               prompt_tokens=entry['tokens'], binding=binding, receipt_sha256=None)
    if not directory.exists():
        return dict(row, status='MISSING_NEVER_DISPATCHED')
    if directory.is_symlink() or not (directory / 'intent.json').is_file():
        raise ValueError('ORPHAN_OR_UNSAFE_REQUEST')
    audit = PrivateAudit(directory)
    if json.loads((directory / 'intent.json').read_bytes()) != binding:
        raise ValueError('INTENT_BINDING')
    receipts = []
    for p in sorted(directory.glob('*.json')):
        if p.name in ('intent.json', 'complete.json'):
            continue
        record = audit.read(p.stem)
        if 'raw_hex' not in record or record.get('binding') != binding:
            raise ValueError('RECEIPT_BINDING')
        raw = bytes.fromhex(record['raw_hex'])
        if hashlib.sha256(raw).hexdigest() != record['raw_sha256']:
            raise ValueError('RESPONSE_HASH')
        receipts.append((p.stem, record, raw))
    complete = directory / 'complete.json'
    if not receipts:
        if complete.exists():
            raise ValueError('COMPLETION_WITHOUT_RESPONSE')
        return dict(row, status='AMBIGUOUS_DISPATCH')
    if len(receipts) != 1:
        raise ValueError('MULTIPLE_RESPONSE_RECEIPTS')
    receipt_sha, record, raw = receipts[0]
    row.update(receipt_sha256=receipt_sha, response_sha256=record['raw_sha256'],
               http_status=record['http_status'], original_state=record['state'])
    # Metadata is descriptive even when the prediction parser rejects content.
    try:
        envelope = json.loads(raw)
    except (ValueError, UnicodeError):
        envelope = {}
    row.update(provider_response_id=envelope.get('id'), model=envelope.get('model'),
               usage=envelope.get('usage'))
    try:
        value = parse(record['http_status'], raw)
    except (ValueError, KeyError, TypeError, IndexError):
        if complete.exists() or record['state'] != 'REJECTED':
            raise ValueError('INVALID_COMPLETION_ASSERTION') from None
        row['status'] = ('COMPLETED_OUTPUT_INVALID' if record['http_status'] == 200
                         else 'EXPLICITLY_FAILED')
        try:
            content = json.loads(envelope['choices'][0]['message']['content'])
            row['output_diagnostic'] = dict(
                answer_count=len(content) if isinstance(content, list) else None,
                invalid_class_positions=[i for i, s in enumerate(content)
                    if isinstance(s, dict) and s.get('answer') not in CLASSES]
                    if isinstance(content, list) else [])
        except (ValueError, KeyError, TypeError, IndexError):
            row['output_diagnostic'] = {'malformed_content': True}
        return row
    if record['state'] != 'COMPLETED' or record.get('validated') != value or not complete.exists():
        raise ValueError('PARSEABLE_RESPONSE_WITHOUT_VALID_TERMINAL_RECEIPT')
    if json.loads(complete.read_bytes()) != {'receipt_sha256': receipt_sha}:
        raise ValueError('COMPLETION_POINTER')
    return dict(row, status='COMPLETED_VALID', validated=value)


def predictions(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row['arm'], row['node_id']].append(row)
    result = []
    for (arm, node), samples in sorted(groups.items()):
        samples.sort(key=lambda r: r['sample_index'])
        if [r['sample_index'] for r in samples] != [0, 1, 2]:
            raise ValueError('SAMPLE_MANIFEST')
        valid = [r for r in samples if r['status'] == 'COMPLETED_VALID']
        vote = asdict(vote_parsed_samples([r['validated']['parsed'] for r in valid])) if len(valid) == 3 else None
        result.append(dict(arm=arm, node_id=node, valid_samples=len(valid),
            status='PREDICTED' if vote else 'UNAVAILABLE_INCOMPLETE_SAMPLES',
            class_index=vote['class_index'] if vote else None, vote=vote,
            confidence_provenance='HISTORICAL_UNCALIBRATED_THREE_SAMPLE_VOTE' if vote else 'UNAVAILABLE',
            sample_statuses=[r['status'] for r in samples]))
    return result


def reconcile(entries, config, root):
    keys = [(e['arm'], e['node_id'], e['sample_index']) for e in entries]
    if len(set(keys)) != len(keys) or {k[0] for k in keys} != set(ARMS):
        raise ValueError('DUPLICATE_OR_INCOMPLETE_MANIFEST')
    nodes = {k[1] for k in keys}
    if set(keys) != {(a, n, s) for a in ARMS for n in nodes for s in range(3)}:
        raise ValueError('UNBALANCED_MANIFEST')
    rows = [inspect_request(root, e, config) for e in entries]
    identities = {r['identity'] for r in rows}
    actual = {p.parent.name for p in (Path(root) / 'calls').glob('*/intent.json')}
    if actual - identities:
        raise ValueError('UNMANIFESTED_INTENT')
    response_ids = [r['provider_response_id'] for r in rows if r.get('provider_response_id')]
    if len(set(response_ids)) != len(response_ids):
        raise ValueError('DUPLICATE_PROVIDER_RESPONSE_ID')
    return rows


def main():
    store = PrivateAudit(OUT)
    protocol_sha = store.write(PROTOCOL)  # Must precede any separately invoked GT evaluator.
    source = PrivateAudit('.local_artifacts/narrative_six_arm').read(PIN)
    execution = PrivateAudit(ROOT)
    config, summary = execution.read(CONFIG), execution.read(SUMMARY)
    if summary['source_manifest_sha256'] != PIN or summary['config_sha256'] != CONFIG:
        raise ValueError('SUMMARY_BINDING')
    before = snapshot(ROOT)
    rows = reconcile(source['requests'], config, ROOT)
    valid = [r for r in rows if r['status'] == 'COMPLETED_VALID']
    unresolved = [r for r in rows if r['status'] != 'COMPLETED_VALID']
    expected_unresolved = {e['draft_identity'] for e, r in zip(source['requests'], rows)
                           if r['status'] != 'COMPLETED_VALID'}
    if (len(valid) != summary['completed'] or expected_unresolved != set(summary['unresolved_request_ids'])
        or sum(r['usage']['prompt_tokens'] for r in valid) != summary['input_tokens']
        or sum(r['usage']['completion_tokens'] for r in valid) != summary['output_tokens']):
        raise ValueError('SUMMARY_RECONCILIATION')
    pred = predictions(rows)
    aggregate = dict(expected_requests=len(rows), targets=len({r['node_id'] for r in rows}),
        states=dict(Counter(r['status'] for r in rows)), per_arm={a:dict(
            request_states=dict(Counter(r['status'] for r in rows if r['arm'] == a)),
            predicted=sum(p['status'] == 'PREDICTED' for p in pred if p['arm'] == a),
            unavailable=sum(p['status'] != 'PREDICTED' for p in pred if p['arm'] == a),
            valid_samples_distribution=dict(Counter(str(p['valid_samples']) for p in pred if p['arm'] == a)),
            prompt_tokens=sum(r['prompt_tokens'] for r in rows if r['arm'] == a),
            recorded_input_tokens=sum((r.get('usage') or {}).get('prompt_tokens', 0) for r in rows if r['arm'] == a),
            recorded_output_tokens=sum((r.get('usage') or {}).get('completion_tokens', 0) for r in rows if r['arm'] == a),
            recorded_reasoning_tokens=sum(((r.get('usage') or {}).get('completion_tokens_details') or {}).get('reasoning_tokens', 0) for r in rows if r['arm'] == a)) for a in ARMS},
        recovered_additional_valid=0, billing='NOT_VERIFIED',
        status='PARTIAL_STRICT_THREE_SAMPLE_ANALYSIS', limitations=PROTOCOL['limitations'])
    if snapshot(ROOT) != before:
        raise ValueError('SOURCE_CHANGED_DURING_AUDIT')
    frozen = dict(schema='sara.six_arm.partial_prediction_freeze.v1', protocol=PROTOCOL,
        protocol_sha256=protocol_sha, source_manifest_sha256=PIN, execution_summary_sha256=SUMMARY,
        config_sha256=CONFIG, config=config, source_files=before, source_snapshot_sha256=digest(before),
        request_response_manifest_sha256=digest(rows), records=rows, unresolved=unresolved,
        predictions=pred, prediction_sha256=digest(pred), aggregate=aggregate,
        implementation_sha256={name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                              for name in ('six_arm_recovery.py', 'six_arm_run.py', 'voting.py')})
    sha = store.write(frozen)
    if store.read(sha) != frozen:
        raise ValueError('FREEZE_READBACK')
    public = dict(freeze_sha256=sha, protocol_sha256=protocol_sha, **aggregate)
    Path('reports/six_arm_recovery_aggregate.json').write_text(json.dumps(public, indent=2)+'\n', encoding='utf8')
    print(json.dumps(public))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('OFFLINE_RECOVERY_BLOCKED: integrity or audit failure; no GT opened.') from None
