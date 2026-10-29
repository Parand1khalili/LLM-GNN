# FEATPROP parser/vote WRITE-ONCE freezer v001. No GT, API, or changes to source runs.
# Reuses the exact verified v002 AST isolation, source selection and regression checks.
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import os
from collections import Counter, defaultdict
from types import SimpleNamespace
import ast, base64, copy, hashlib, json, math, re, warnings

ROOT = Path('/content/gdrive/MyDrive/Prnd-project/LLMGNN_reference')
BASE = ROOT / 'experiments/matched_cora'
SEL = BASE / 'featprop_merged_selection_001'
OLD = BASE / 'matched_infer_003'
REF = ROOT / 'experiments/narrative_v1/run_v1.py'
HIST = BASE / 'run_matched.py'
LLM = ROOT / 'src/llm.py'
UTILS = ROOT / 'src/openail/utils.py'
PINS = {
    'selection_receipt': 'df37a66f2942f56f6c0c38a0696c7a6cf6dcaf1d22d4eb3d2a5caa50056bde2b',
    'historical_runner': 'ff85112696f0db2ece46db37f13609cb3ffbb57c68f7a9bb48f539942a4f7a72',
    'llm': '483e7a1b7d445801edf1ee5e8251187807663e47dac940e4b24efcf06250ecce',
    'utils': 'c6cff1b47d7e8a14aa53077340f9eece2e0affbb2e3d9d177ab170f3b70860c9',
    'historical_freeze': 'd77ee1fee0b8a868263f9a6a1aec365c03bb89aa76512728b737767955cc1853',
}
for key, pin in PINS.items():
    assert re.fullmatch(r'[0-9a-f]{64}', pin), f'Malformed pin: {key}'

def digest(blob):
    return hashlib.sha256(blob).hexdigest()

def verify(path, pin):
    assert path.is_file() and not path.is_symlink(), f'Missing/unsafe: {path}'
    blob = path.read_bytes()
    actual = digest(blob)
    assert actual == pin, f'Integrity failure: {path.name}: {actual}'
    return blob

def parse(blob):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', SyntaxWarning)
        return ast.parse(blob.decode('utf-8-sig'))

def assignment(tree, name):
    values = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    assert len(values) == 1, f'Missing/ambiguous pinned constant: {name}'
    return values[0]

def one(nodes, name, kind=ast.FunctionDef):
    found = [n for n in nodes if isinstance(n, kind) and n.name == name]
    assert len(found) == 1, f'Missing/ambiguous pinned source: {name}'
    return copy.deepcopy(found[0])

def normalize(value):
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))

print('=== FEATPROP 840-RESPONSE PARSER/VOTE WRITE-ONCE FREEZE ===', flush=True)
OUT = BASE / 'featprop_parser_vote_001'
assert not OUT.exists() and not OUT.is_symlink(), 'Output already exists; no overwrite authorized.'
receipt = json.loads(verify(SEL / 'freeze_receipt.json', PINS['selection_receipt']))
assert receipt['selection_count'] == 840 and receipt['target_count'] == 140
artifacts = {filename: verify(SEL / filename, expected)
             for filename, expected in receipt['outputs_sha256'].items()}
manifest = json.loads(artifacts['selection_manifest.json'])
protocol = json.loads(artifacts['protocol.json'])
assert manifest['schema'] == 'featprop_merged_response_selection_manifest_001'
assert (manifest['request_count'], manifest['unique_target_count'], manifest['target_arm_pair_count']) == (840, 140, 280)
assert manifest['arms'] == ['b1', 'narrative_v0']
assert protocol['no_api'] is True and protocol['no_ground_truth_access'] is True
records = manifest['records']
assert len(records) == 840
assert Counter(r['source_kind'] for r in records) == {'original_fresh': 726, 'historical_reuse': 84, 'supplementary': 30}
assert {r['original_request_index'] for r in records} == set(range(840))
assert len({(r['target_id'], r['arm'], r['sample_index']) for r in records}) == 840
hist_blob = verify(HIST, PINS['historical_runner'])
hist_tree = parse(hist_blob)
reference_pin = assignment(hist_tree, 'REFERENCE_HASH')
assert re.fullmatch(r'[0-9a-f]{64}', reference_pin)
reference_blob = verify(REF, reference_pin)
llm_blob = verify(LLM, PINS['llm'])
utils_blob = verify(UTILS, PINS['utils'])
verify(OLD / 'freeze_receipt.json', PINS['historical_freeze'])
ref_tree = parse(reference_blob)
hist_classes = assignment(hist_tree, 'CLASSES')
classes = assignment(ref_tree, 'CLASSES')
assert hist_classes == classes and len(classes) == len(set(classes)) == 7
# Load ONLY the exact frozen, isolated AST; no project-module imports.
# run_matched.py owns the response decoder (pairs/decode), and run_v1.py
# owns the offline parser builder and diagnostics. Both source hashes are pinned.
historical_helpers = ('require', 'pairs', 'decode')
reference_helpers = ('function', 'historical_parser', 'content', 'grammar', 'individual_parse')
chosen = [one(hist_tree.body, 'RunnerError', ast.ClassDef)]
chosen += [one(hist_tree.body, name) for name in historical_helpers]
chosen += [one(ref_tree.body, name) for name in reference_helpers]
assert [node.name for node in chosen] == [
    'RunnerError', *historical_helpers, *reference_helpers
], 'Offline reference AST inventory mismatch'
module = ast.fix_missing_locations(ast.Module(body=chosen, type_ignores=[]))
namespace = {'ast': ast, 'base64': base64, 'copy': copy, 'hashlib': hashlib,
             'json': json, 'Counter': Counter, 'SimpleNamespace': SimpleNamespace,
             'CLASSES': classes}
exec(compile(module, '<verified offline reference AST>', 'exec'), namespace)
parser = namespace['historical_parser']({'source_bytes': {'llm': llm_blob, 'utils': utils_blob}})
print('HASHES: selection / historical runner / reference / LLM / utils / historical freeze VERIFIED')
print('PARSER/VOTE: extracted from historical AST; no project module imported')
root_real = ROOT.resolve(strict=True)

def source_path(relative):
    assert isinstance(relative, str)
    rel = PurePosixPath(relative)
    assert not rel.is_absolute() and rel.parts and '..' not in rel.parts and '.' not in rel.parts
    p = ROOT.joinpath(*rel.parts)
    assert p.resolve(strict=True).is_relative_to(root_real)
    assert not p.is_symlink()
    return p

by_pair = defaultdict(dict)
texts_by_pair = defaultdict(dict)
legacy_diagnostics = {}
for r in records:
    index, target, arm, sample = (r[k] for k in ('original_request_index', 'target_id', 'arm', 'sample_index'))
    assert type(index) is type(target) is type(sample) is int
    assert type(arm) is str and arm in manifest['arms'] and sample in (0, 1, 2)
    assert type(r['prompt_sha256']) is str and re.fullmatch(r'[0-9a-f]{64}', r['prompt_sha256'])
    key = (target, arm)
    assert sample not in by_pair[key]
    by_pair[key][sample] = r
    raw = verify(source_path(r['source_response_path']), r['source_response_sha256'])
    obj = namespace['decode'](raw)
    if r['source_kind'] == 'historical_reuse':
        assert r['source_response_format'] == 'historical_response.json'
        for fld, value in [('target_id', target), ('arm', arm), ('sample_index', sample),
                           ('prompt_sha256', r['prompt_sha256'])]:
            assert obj[fld] == value, f'Historical identity mismatch: {index} / {fld}'
        assert obj['complete'] is True and obj['credential_redaction_required'] is False
        body = base64.b64decode(obj['raw_body_base64'], validate=True)
        assert digest(body) == obj['persisted_body_sha256']
        text, error = namespace['content'](obj)
        assert error is None and isinstance(text, str) and text.strip(), f'Historical content failure: {index}: {error}'
        old_diag = namespace['decode'](verify(source_path(r['frozen_historical_parsing_path']),
                                             r['frozen_historical_parsing_sha256']))
        assert (old_diag['target_id'], old_diag['arm'], old_diag['sample_index']) == (target, arm, sample)
        assert old_diag['response_file_sha256'] == r['source_response_sha256']
        diagnostic = namespace['individual_parse'](parser, text)
        new_grammar = namespace['grammar'](parser, text)
        for field in ('parsed_answers', 'first_answer', 'first_confidence', 'individual_prediction',
                      'individual_class_index', 'literal_parse_failure'):
            if field in old_diag:
                assert normalize(diagnostic.get(field)) == old_diag[field], f'Historical diagnostic regression: {index}/{field}'
        assert normalize(new_grammar) == old_diag['grammar'], f'Historical grammar regression: {index}'
        legacy_diagnostics[(target, arm, sample)] = True
    else:
        assert r['source_kind'] in ('original_fresh', 'supplementary')
        assert r['source_response_format'] == 'provider_response.json'
        choices = obj['choices']
        assert isinstance(choices, list) and len(choices) == 1
        assert choices[0]['finish_reason'] == 'stop'
        text = choices[0]['message']['content']
        assert isinstance(text, str) and text.strip(), f'Provider content missing: {index}'
    texts_by_pair[key][sample] = text

assert len(by_pair) == len(texts_by_pair) == 280
assert len(legacy_diagnostics) == 84
assert all(set(samples) == {0, 1, 2} for samples in by_pair.values())
assert len({t for t, a in by_pair}) == 140
assert all({a for t, a in by_pair if t == target} == set(manifest['arms'])
           for target in {t for t, a in by_pair})
assert all(all(by_pair[(t, a)][s]['source_kind'] == 'supplementary' for a in manifest['arms'] for s in (0,1,2))
           for t in {711, 979, 1716, 2270, 2291})
print('840/840 selected source hashes and content envelopes: VERIFIED')
print('84/84 historical sample diagnostic regressions: MATCH')

legacy_final = {}
old_hashes = {}
for target, arm in by_pair:
    rows = [by_pair[(target, arm)][s] for s in range(3)]
    if all(r['source_kind'] == 'historical_reuse' for r in rows):
        hashes = {r['frozen_historical_final_predictions_sha256'] for r in rows}
        assert len(hashes) == 1
        expected = hashes.pop()
        if arm not in legacy_final:
            final = namespace['decode'](verify(OLD / arm / 'final_predictions.json', expected))
            assert final['ordered_classes'] == classes and final['ground_truth_accessed'] is False
            legacy_final[arm] = final['predictions_by_target_id']
            old_hashes[arm] = expected
        else:
            assert old_hashes[arm] == expected


# All source-identity, parser extraction and historical sample checks above are
# intentionally unchanged from the passing read-only dry-run v002.
AFFECTED = {711, 979, 1716, 2270, 2291}
TARGETS = list(dict.fromkeys(r['target_id'] for r in records))
assert len(TARGETS) == 140 and len(set(TARGETS)) == 140
assert all(sum(r['target_id'] == t for r in records) == 6 for t in TARGETS)
assert all({(a, s) for (t, a), rows in by_pair.items() if t == target for s in rows} ==
           {(a, s) for a in manifest['arms'] for s in (0, 1, 2)} for target in TARGETS)
COMPLETE = [t for t in TARGETS if t not in AFFECTED]
assert len(COMPLETE) == 135 and set(TARGETS) - set(COMPLETE) == AFFECTED
assert all(set(row['source_kind'] for row in by_pair[(t,a)].values()) == {'supplementary'}
           for t in AFFECTED for a in manifest['arms'])
assert all('supplementary' not in {r['source_kind'] for r in by_pair[(t,a)].values()}
           for t in COMPLETE for a in manifest['arms'])

sample_records = []
final_by_arm = {a: {} for a in manifest['arms']}
summary = Counter()
regression_count = 0
failures = []

for target in TARGETS:
    for arm in manifest['arms']:
        key = (target, arm)
        rows = [by_pair[key][s] for s in (0,1,2)]
        texts = [texts_by_pair[key][s] for s in (0,1,2)]
        source_types = {r['source_kind'] for r in rows}
        assert len(source_types) == 1, f'Mixed sources within a three-sample pair: {target}/{arm}'
        source_kind = source_types.pop()
        prompt_hashes = {r['prompt_sha256'] for r in rows}
        assert len(prompt_hashes) == 1
        prompt_sha = next(iter(prompt_hashes))
        group_samples = []
        try:
            # Same frozen extraction, exact three-sample parser, and vote call as v002.
            parsed = parser['retrieve_multiple_answers'](parser['self'], [texts], None, 3)[0]
            assert len(parsed) == 3
            preds, confs, fallback = parser['vote']([parsed], classes, [0])
            assert len(preds) == len(confs) == 1 and type(preds[0]) is int and 0 <= preds[0] < 7
            assert math.isfinite(float(confs[0]))
            assert type(fallback) is int and fallback >= 0
            # Preserve original confidence arithmetic and avoid any tensor cast.
            prediction = classes[preds[0]]
            confidence = normalize(confs[0])
            assert isinstance(confidence, (int,float)) and not isinstance(confidence, bool)
            for sample_index, (r, text, answers) in enumerate(zip(rows, texts, parsed)):
                diagnostic = normalize(namespace['individual_parse'](parser, text))
                grammar = normalize(namespace['grammar'](parser, text))
                parsed_answers = normalize(answers)
                first_answer = parsed_answers[0][0] if parsed_answers else None
                first_confidence = parsed_answers[0][1] if parsed_answers else None
                first_index = classes.index(first_answer) if first_answer in classes else None
                # Regression on ALL historical samples including the vote-level parse.
                if source_kind == 'historical_reuse':
                    historical = namespace['decode'](verify(source_path(r['frozen_historical_parsing_path']),
                                                            r['frozen_historical_parsing_sha256']))
                    assert grammar == historical['grammar']
                    for field in ('parsed_answers','first_answer','first_confidence','individual_prediction',
                                  'individual_class_index','literal_parse_failure'):
                        if field in historical:
                            assert diagnostic.get(field) == historical[field], (target,arm,sample_index,field)
                sample_record = {
                    'original_request_index': r['original_request_index'],
                    'target_id': target, 'arm': arm, 'sample_index': sample_index,
                    'prompt_sha256': r['prompt_sha256'],
                    'source_kind': source_kind,
                    'source_response_path': r['source_response_path'],
                    'source_response_sha256': r['source_response_sha256'],
                    'grammar_valid': grammar[0],
                    'grammar_result_sha256': digest(json.dumps(grammar, sort_keys=True, ensure_ascii=False, allow_nan=False).encode('utf-8')),
                    'individual_diagnostic': diagnostic,
                    'parsed_answers_for_three_sample_vote': parsed_answers,
                    'first_answer_for_vote': first_answer,
                    'first_confidence_for_vote': first_confidence,
                    'first_class_index_for_vote': first_index,
                }
                group_samples.append(sample_record)
            if source_kind == 'historical_reuse':
                previous = legacy_final[arm][str(target)]
                assert previous['class_index'] == preds[0]
                assert previous['prediction'] == prediction
                assert previous['confidence_percent_before_tensor_cast'] == confs[0]
                assert previous['historical_all_invalid_fallback_count'] == fallback
                assert all(normalize(previous['parsed_samples'][i]['parsed_answers']) ==
                           group_samples[i]['parsed_answers_for_three_sample_vote'] for i in range(3))
                regression_count += 1
            final_by_arm[arm][str(target)] = {
                'arm': arm, 'target_id': target, 'prompt_sha256': prompt_sha,
                'source_kind': source_kind,
                'original_request_indices': [r['original_request_index'] for r in rows],
                'selected_response_sha256_by_sample_index': [r['source_response_sha256'] for r in rows],
                'prediction': prediction, 'class_index': preds[0],
                'confidence_percent_before_tensor_cast': confidence,
                'historical_all_invalid_fallback_count': fallback,
                'primary_samples': group_samples,
                'repair': {'applied': False, 'budget': 0}, 'retries': 0,
                'failure': None, 'ground_truth_accessed': False,
            }
            sample_records.extend(group_samples)
            summary['voted_'+arm] += 1
            summary['fallback_'+arm] += fallback
            summary['supplementary_pairs' if target in AFFECTED else 'original_complete_pairs'] += 1
        except Exception as exc:
            failures.append((target,arm,type(exc).__name__))
            if source_kind == 'historical_reuse':
                raise AssertionError(f'Historical vote/sample regression at {target}/{arm}: {type(exc).__name__}') from exc

assert not failures, f'Parser/vote failures; freeze prohibited: {failures[:15]}'
assert regression_count == 28
assert len(sample_records) == 840 and len({(r['target_id'],r['arm'],r['sample_index']) for r in sample_records}) == 840
assert all(len(final_by_arm[a]) == 140 and list(map(int,final_by_arm[a].keys())) == TARGETS for a in manifest['arms'])
assert summary['original_complete_pairs'] == 270 and summary['supplementary_pairs'] == 10
assert summary['voted_b1'] == summary['voted_narrative_v0'] == 140
assert summary['fallback_b1'] == summary['fallback_narrative_v0'] == 0
assert Counter(r['source_kind'] for r in sample_records) == {'original_fresh':726,'historical_reuse':84,'supplementary':30}
assert all(r['ground_truth_accessed'] is False and r['failure'] is None
           for a in manifest['arms'] for r in final_by_arm[a].values())

print('840/840 selected response hashes/envelopes verified')
print('84/84 historical sample diagnostic regressions matched')
print('28/28 historical vote regressions matched')
print('Successful votes:', {a: summary['voted_'+a] for a in manifest['arms']})
print('Original complete cases: 135 targets / 270 pairs')
print('All-node replacement: 140 targets / 280 pairs; supplementary 5 targets / 10 pairs')
print('No all-invalid fallback; no parser/vote failures')

# Outputs deliberately omit raw response text, ground truth, accuracy and GCN results.
# They keep the common labels/confidence and selected-source provenance intact.
def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')

def exclusive(path, data):
    assert not path.exists() and not path.is_symlink(), f'No overwrite: {path}'
    assert path.parent.is_dir() and not path.parent.is_symlink()
    with path.open('xb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    assert digest(path.read_bytes()) == digest(data)

source_file = Path(__file__)
assert source_file.is_file() and not source_file.is_symlink()
source_bytes = source_file.read_bytes()
source_sha = digest(source_bytes)
assert re.fullmatch(r'[0-9a-f]{64}', source_sha)
assert 'featprop_parser_vote_freezer_001.py' == source_file.name, 'Unexpected freezer filename'

protocol_out = {
    'schema':'featprop_parser_vote_protocol_001',
    'stage':'common_offline_parser_vote_after_response_source_selection',
    'source_selection_freeze_receipt_sha256':PINS['selection_receipt'],
    'source_selection_manifest_sha256':receipt['outputs_sha256']['selection_manifest.json'],
    'historical_runner_source_sha256':PINS['historical_runner'],
    'reference_runner_source_sha256':reference_pin,
    'llm_parser_source_sha256':PINS['llm'],
    'llm_utils_source_sha256':PINS['utils'],
    'historical_inference_freeze_sha256':PINS['historical_freeze'],
    'parser_vote_construction':'Hash-verified AST extraction from exact historical run_v1.py and pinned llm.py, without importing project modules',
    'parser_call':'retrieve_multiple_answers(self,[three_selected_texts],None,3)[0]',
    'vote_call':'vote([parsed],ordered_classes,[0]); historical eval_result loop as extracted by run_v1 historical_parser',
    'sample_diagnostics':'individual_parse and grammar from same historical reference; output stores grammar boolean and result digest, not complete grammar/error text',
    'no_parser_correction':True,'no_grammar_repair':True,'no_api':True,'no_retry':True,
    'no_ground_truth_access':True,'no_training':True,
    'selected_sources_remain_read_only':True,'no_raw_response_text_in_outputs':True,
    'historical_sample_regressions':84,'historical_vote_regressions':28,
    'analysis_cohorts': {
        'original_complete_case': {'target_ids_in_manifest_order':COMPLETE,'target_count':135,
                                   'pair_count':270,'excludes_all_five_originally_incomplete_targets':True},
        'all_node_supplementary_replacement': {'target_ids_in_manifest_order':TARGETS,'target_count':140,
                                               'pair_count':280,'supplementary_replacement_target_ids':sorted(AFFECTED),
                                               'no_mixing_of_original_and_supplementary_samples':True},
    },
}

cohorts = {
    'schema':'featprop_parser_vote_analysis_cohorts_001',
    'ordered_classes':classes,'arms':list(manifest['arms']),
    'complete_case': {'target_ids_in_manifest_order':COMPLETE,
                      'target_count':135,'pair_count':270,
                      'class_index_by_arm': {a:[final_by_arm[a][str(t)]['class_index'] for t in COMPLETE] for a in manifest['arms']},
                      'confidence_percent_by_arm': {a:[final_by_arm[a][str(t)]['confidence_percent_before_tensor_cast'] for t in COMPLETE] for a in manifest['arms']}},
    'all_node_replacement': {'target_ids_in_manifest_order':TARGETS,
                      'target_count':140,'pair_count':280,
                      'supplementary_replacement_target_ids':sorted(AFFECTED),
                      'class_index_by_arm': {a:[final_by_arm[a][str(t)]['class_index'] for t in TARGETS] for a in manifest['arms']},
                      'confidence_percent_by_arm': {a:[final_by_arm[a][str(t)]['confidence_percent_before_tensor_cast'] for t in TARGETS] for a in manifest['arms']}},
    'ground_truth_accessed':False,'accuracy_computed':False,'training_performed':False,
}
outputs = {
    'protocol.json':encoded(protocol_out),
    'sample_diagnostics.json':encoded({'schema':'featprop_selected_sample_diagnostics_001',
                                      'sample_count':840,'source_counts':dict(Counter(r['source_kind'] for r in sample_records)),
                                      'records':sample_records,'ground_truth_accessed':False}),
    'analysis_cohorts.json':encoded(cohorts),
    'b1/final_predictions.json':encoded({'schema':'featprop_parser_vote_final_predictions_001','arm':'b1',
        'target_ids_in_manifest_order':TARGETS,'ordered_classes':classes,'predictions_by_target_id':final_by_arm['b1'],
        'ground_truth_accessed':False}),
    'narrative_v0/final_predictions.json':encoded({'schema':'featprop_parser_vote_final_predictions_001','arm':'narrative_v0',
        'target_ids_in_manifest_order':TARGETS,'ordered_classes':classes,'predictions_by_target_id':final_by_arm['narrative_v0'],
        'ground_truth_accessed':False}),
    'parser_vote_freezer_source.py':source_bytes,
}
receipt_out = {
    'schema':'featprop_parser_vote_freeze_receipt_001',
    'created_utc':datetime.now(timezone.utc).isoformat(),
    'selection_freeze_sha256':PINS['selection_receipt'],
    'selection_manifest_sha256':receipt['outputs_sha256']['selection_manifest.json'],
    'freezer_source_sha256':source_sha,
    'historical_runner_source_sha256':PINS['historical_runner'],
    'reference_runner_source_sha256':reference_pin,
    'llm_parser_source_sha256':PINS['llm'],
    'llm_utils_source_sha256':PINS['utils'],
    'historical_freeze_sha256':PINS['historical_freeze'],
    'selected_sample_count':840,'target_count':140,'target_arm_pair_count':280,
    'original_complete_case_target_count':135,
    'historical_sample_regressions_matched':84,
    'historical_vote_regressions_matched':28,
    'successful_votes_by_arm':{a:summary['voted_'+a] for a in manifest['arms']},
    'historical_all_invalid_fallback_by_arm':{a:summary['fallback_'+a] for a in manifest['arms']},
    'selected_source_counts':dict(Counter(r['source_kind'] for r in sample_records)),
    'outputs_sha256':{key:digest(val) for key,val in sorted(outputs.items())},
    'no_api':True,'no_ground_truth_access':True,'no_training':True,
    'source_responses_not_modified':True,'write_once':True,
}
outputs['freeze_receipt.json'] = encoded(receipt_out)
assert not OUT.exists() and not OUT.is_symlink(), 'Output appeared during checks; no overwrite.'
# Preflight full serializability and file inventory before first write.
assert len(outputs) == 7 and all(isinstance(blob,bytes) and blob for blob in outputs.values())
assert all(not (OUT / rel).exists() for rel in outputs)
print('ALL VALIDATIONS PASSED; creating one NEW output directory:', OUT)
os.mkdir(OUT)
for arm in manifest['arms']:
    os.mkdir(OUT / arm)
for name, blob in sorted(outputs.items(),key=lambda item:item[0]=='freeze_receipt.json'):
    exclusive(OUT / name, blob)
assert all(digest((OUT / name).read_bytes()) == digest(blob) for name,blob in outputs.items())
print('\n=== PARSER/VOTE WRITE-ONCE FREEZE COMPLETE ===')
print('Selected samples:',len(sample_records),'| targets:',len(TARGETS),'| pairs:',280)
print('Historical sample/vote regressions:',len(legacy_diagnostics),'/',regression_count)
print('Successful votes:',{a:summary['voted_'+a] for a in manifest['arms']})
for name in sorted(outputs):
    print(name, 'SHA256:', digest(outputs[name]))
print('NO API / NO GT / NO TRAINING / NO REPAIR / NO RETRY / NO ORIGINAL OVERWRITE')
