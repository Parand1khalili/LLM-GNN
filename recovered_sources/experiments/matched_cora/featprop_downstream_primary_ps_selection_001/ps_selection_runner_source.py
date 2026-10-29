#!/usr/bin/env python3
"""Precommitted primary PS-FeatProp + unweighted CE, B1 vs Narrative v0, seeds 0..9.

GT-isolated, frozen pseudo-label confidence + entropy-change filter. This is the
explicit corrected PS analogue precommitted in featprop_downstream_protocol_001,
NOT direct execution of the historical repository's post_process(data.y).

Preflight verifies all 40 prior primary fits and every output hash. Compute and
freeze PS decisions (40 removed/arm) BEFORE loading the graph object or training.
Train paired models on 95 retained pseudo-labels/arm for 30 epochs, only then
read GT for common fixed-test evaluation (2568 nodes). Each seed pair is saved
write-once and independently hash-verified; the final summary is written only
once all ten paired results are verified. DO NOT rerun after partial interruption.
"""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import ast
import hashlib
import io
import json
import math
import os
import random
import re
import statistics
import sys

import numpy as np
import torch
import torch.nn.functional as F
import torch_geometric
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv

ROOT = Path('/content/gdrive/MyDrive/Prnd-project/LLMGNN_reference')
BASE = ROOT / 'experiments/matched_cora'
PROT = BASE / 'featprop_downstream_protocol_001'
PRED = BASE / 'featprop_parser_vote_001'
CE_SUMMARY = BASE / 'featprop_downstream_primary_ce_10seed_summary_001'
W_SUMMARY = BASE / 'featprop_downstream_primary_weighted_ce_10seed_summary_001'
GRAPH = Path('/content/LLMGNN_data/cora_random_sbert.pt')
SCRIPT = Path(__file__)
SCRIPT_NAME = 'featprop_downstream_primary_ps_ce_seed00_09_batch_runner_003.py'
PS_DIR = BASE / 'featprop_downstream_primary_ps_selection_001'
SUMMARY_DIR = BASE / 'featprop_downstream_primary_ps_ce_10seed_summary_001'
ARMS = ('b1', 'narrative_v0')
SEEDS = tuple(range(10))
PINS = {
    'protocol': '4b485aefd9312c2870fba972b59dd35bdd897e2fb3d94e270bcec81ce7752053',
    'predictions': 'cf6a8d2d7f55db826d033360ee7282c46499cfef213a7781c1a9497dcc78bff6',
    'graph': '9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466',
    'model': '5d00c347e5a6aa504de9bf8c5abbd6e084efa1302e004c142567b9dc364b4b9b',
    'ce_summary': '6d55a96ac6d140420ea68ce32dc85e6508d7a4ef8ac581fcc4789c0ee89518f2',
    'ce_summary_json': '66d5adc1ff1fbf7d07583c9ca5b94e0e0d06ccd42a1a759724c42721a2e74534',
    'weighted_summary': 'c5584ca3ddf75fffcbbdf06dd10935d8049aada22ced439d630cbec8bc01f84f',
    'weighted_summary_json': '3621fae4f45e4625a45003fe351c0bb20760d0d9e612c1a7e1d4eb1131c99ff8',
    'weighted_manifest': '7fd49ce028c12b5ec5312542ee10f68ae7d99b2d3f62e994665d8e792e50e02b',
    'weighted_runner': '898e2d2889f1dd3c5a3ef927e7e6b71238d4db33d41e6090de8f2afeaad7cf36',
}
for name, pin in PINS.items():
    assert re.fullmatch(r'[0-9a-f]{64}', pin), 'Malformed pin: ' + name


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def checked(path, expected):
    assert re.fullmatch(r'[0-9a-f]{64}', expected), f'Malformed expected hash: {path}'
    assert path.is_file() and not path.is_symlink(), f'Missing/unsafe file: {path}'
    blob = path.read_bytes()
    assert sha(blob) == expected, f'SHA mismatch: {path}\nExpected: {expected}\nActual:   {sha(blob)}'
    return blob


def decode(blob):
    def unique_pairs(pairs):
        out = {}
        for k, v in pairs:
            assert k not in out, 'Duplicate JSON key: ' + k
            out[k] = v
        return out
    return json.loads(blob, object_pairs_hook=unique_pairs,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode('utf-8')


def exclusive(path, blob):
    assert path.parent.is_dir() and not path.parent.is_symlink()
    assert not path.exists() and not path.is_symlink(), 'NO OVERWRITE: ' + str(path)
    with path.open('xb') as f:
        f.write(blob)
        f.flush()
        os.fsync(f.fileno())
    assert checked(path, sha(blob)) == blob


def inventory(directory):
    assert directory.is_dir() and not directory.is_symlink()
    found = set()
    for path in directory.rglob('*'):
        assert not path.is_symlink(), 'Symlink: ' + str(path)
        if path.is_file():
            found.add(path.relative_to(directory).as_posix())
    return found


def prior_folder(pipeline, seed):
    # The published pipeline key is NOT the directory suffix for these runs.
    # Frozen CE: featprop_downstream_primary_ce_seedNN_001
    # Frozen WCE: featprop_downstream_primary_weighted_ce_seedNN_001
    assert pipeline in ('featprop_ce', 'featprop_weighted_ce'), 'Unexpected upstream pipeline'
    assert type(seed) is int and seed in SEEDS
    suffix = {'featprop_ce': 'ce', 'featprop_weighted_ce': 'weighted_ce'}[pipeline]
    return BASE / f'featprop_downstream_primary_{suffix}_seed{seed:02d}_001'


def seed_folder(seed):
    assert type(seed) is int and seed in SEEDS
    return BASE / f'featprop_downstream_primary_ps_ce_seed{seed:02d}_001'


def parameter_sha(model):
    h = hashlib.sha256()
    for name, value in model.named_parameters():
        h.update(name.encode('utf-8') + b'\0')
        h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def verify_completed_pipeline(pipeline, summary_dir, pin, summary_pin, expected_schema, prior_count):
    """Independently verify each upstream receipt, result and both model bytes."""
    receipt = decode(checked(summary_dir / 'freeze_receipt.json', pin))
    assert receipt['schema'] == expected_schema
    assert receipt['write_once'] and receipt['ten_paired_seeds_verified']
    assert receipt['pipeline'] == pipeline and receipt['cohort'] == 'original_complete_case'
    assert receipt['upstream_protocol_receipt_sha256'] == PINS['protocol']
    assert set(receipt['seed_receipts_sha256']) == {str(s) for s in SEEDS}
    expected_outputs = {'summary.json', 'batch_runner_source.py'}
    if pipeline == 'featprop_weighted_ce':
        expected_outputs.add('static_weight_manifest.json')
        assert receipt['batch_runner_source_sha256'] == PINS['weighted_runner']
        assert receipt['outputs_sha256']['static_weight_manifest.json'] == PINS['weighted_manifest']
    assert set(receipt['outputs_sha256']) == expected_outputs
    assert inventory(summary_dir) == expected_outputs | {'freeze_receipt.json'}
    for relative, digest in receipt['outputs_sha256'].items():
        checked(summary_dir / relative, digest)
    assert receipt['outputs_sha256']['summary.json'] == summary_pin
    summary = decode(checked(summary_dir / 'summary.json', summary_pin))
    assert summary['schema'] == f'featprop_downstream_primary_complete_case_{pipeline}_10seed_summary_001'
    assert summary['pipeline'] == pipeline and summary['cohort'] == 'original_complete_case'
    assert summary['seed_order'] == list(SEEDS) and summary['pairs_completed'] == 10
    assert summary['fits_completed_for_this_pipeline'] == 20
    assert summary['overall_protocol_fits_completed_to_date'] == prior_count
    assert summary['upstream_protocol_receipt_sha256'] == PINS['protocol']
    assert summary['upstream_prediction_receipt_sha256'] == PINS['predictions']
    assert summary['graph_sha256'] == PINS['graph'] and summary['GCN_source_sha256'] == PINS['model']
    assert len(summary['per_seed']) == 10
    initial = {}
    for seed, entry in enumerate(summary['per_seed']):
        assert entry['seed'] == seed and entry['test_count'] == 2568
        rpin = receipt['seed_receipts_sha256'][str(seed)]
        assert entry['seed_freeze_receipt_sha256'] == rpin
        folder = prior_folder(pipeline, seed)
        seed_receipt = decode(checked(folder / 'freeze_receipt.json', rpin))
        assert seed_receipt['schema'] == 'featprop_downstream_seed_pair_freeze_receipt_001'
        assert seed_receipt['write_once'] and seed_receipt['cohort'] == 'original_complete_case'
        assert seed_receipt['pipeline'] == pipeline and seed_receipt['seed'] == seed
        assert seed_receipt['num_training_fits'] == 2
        assert seed_receipt['upstream_protocol_receipt_sha256'] == PINS['protocol']
        assert seed_receipt['no_API'] and seed_receipt['no_upstream_overwrite']
        assert seed_receipt['GT_used_only_final_fixed_test'] is True
        outputs = seed_receipt['outputs_sha256']
        assert set(outputs) == {'paired_seed_result.json','runner_source.py',
                                'b1/model_state.pt','narrative_v0/model_state.pt'}
        assert inventory(folder) == set(outputs) | {'freeze_receipt.json'}
        for name, digest in outputs.items(): checked(folder / name, digest)
        assert outputs['paired_seed_result.json'] == entry['paired_seed_result_sha256']
        result = decode(checked(folder/'paired_seed_result.json',outputs['paired_seed_result.json']))
        # The frozen JSON pipeline field ('featprop_ce' / 'featprop_weighted_ce')
        # is distinct from the published result schema's directory suffix ('ce' / 'weighted_ce').
        # Match the exact schema emitted by each hash-pinned original runner.
        schema_suffix = {'featprop_ce': 'ce', 'featprop_weighted_ce': 'weighted_ce'}[pipeline]
        assert result['schema'] == f'featprop_downstream_primary_{schema_suffix}_seed{seed:02d}_pair_001', (pipeline, seed, result['schema'])
        assert result['pipeline'] == pipeline and result['cohort'] == 'original_complete_case'
        assert result['seed'] == seed and result['epochs_per_fit'] == 30
        assert result['paired_same_initial_parameters'] is True
        assert result['upstream_protocol_receipt_sha256'] == PINS['protocol']
        assert result['upstream_prediction_receipt_sha256'] == PINS['predictions']
        assert result['graph_sha256'] == PINS['graph'] and result['GCN_source_sha256'] == PINS['model']
        assert result['shared_initial_parameters_sha256'] == entry['shared_initial_parameters_sha256']
        assert result['by_arm']['b1']['correct_on_common_test'] == entry['b1_correct']
        assert result['by_arm']['narrative_v0']['correct_on_common_test'] == entry['v0_correct']
        assert result['by_arm']['b1']['initial_model_parameters_sha256'] == result['shared_initial_parameters_sha256']
        assert result['by_arm']['narrative_v0']['initial_model_parameters_sha256'] == result['shared_initial_parameters_sha256']
        for arm in ARMS:
            record = result['by_arm'][arm]
            assert len(record['test_global_node_ids']) == len(record['test_predicted_class_indices']) == 2568
            assert type(record['correct_on_common_test']) is int
            assert 0 <= record['correct_on_common_test'] <= 2568
            assert math.isclose(record['accuracy'], record['correct_on_common_test']/2568, abs_tol=1e-14)
        initial[seed] = result['shared_initial_parameters_sha256']
    assert [x['b1_correct'] for x in summary['per_seed']] == (
        [1777,1799,1775,1796,1801,1805,1792,1782,1791,1776] if pipeline == 'featprop_ce' else
        [1803,1817,1805,1821,1802,1819,1805,1812,1820,1797])
    assert [x['v0_correct'] for x in summary['per_seed']] == (
        [1812,1830,1812,1822,1812,1837,1825,1817,1842,1812] if pipeline == 'featprop_ce' else
        [1855,1859,1845,1878,1867,1887,1868,1860,1888,1855])
    return initial


def entropy(label_values):
    assert len(label_values) > 0
    counts = Counter(label_values)
    n = len(label_values)
    return -sum((count/n) * math.log(count/n) for count in counts.values())


def derive_ps(ids, labels, confidences, deletion_count):
    """Exactly frozen confidence + COE protocol; uses NO graph/GT or outcomes."""
    assert len(ids) == len(labels) == len(confidences) == 135
    assert len(set(ids)) == 135 and deletion_count == 40
    assert all(type(node) is int and 0 <= node < 2708 for node in ids)
    assert all(type(y) is int and 0 <= y < 7 for y in labels)
    assert all(type(c) in (int,float) and math.isfinite(c) and 0 < c <= 100 for c in confidences)
    label_of = dict(zip(ids, labels))
    conf_of = dict(zip(ids, confidences))
    alive = set(ids)
    start_classes = set(labels)
    history = []
    for step in range(deletion_count):
        present = sorted(alive)
        counts = Counter(label_of[node] for node in present)
        h0 = entropy([label_of[node] for node in present])
        # Class guard means a candidate is removable only if its class count >= 2.
        candidates = [node for node in present if counts[label_of[node]] > 1]
        assert candidates, 'No removable candidates under class guard; STOP'
        m = len(candidates)
        coe = {}
        for node in candidates:
            remainder = [label_of[j] for j in present if j != node]
            coe[node] = entropy(remainder) - h0
            assert math.isfinite(coe[node])
        ranked_conf = sorted(candidates, key=lambda node:(-conf_of[node], node))
        ranked_coe = sorted(candidates, key=lambda node:(coe[node], node))
        conf_ranks = {node:(m-rank)/m for rank,node in enumerate(ranked_conf)}
        coe_ranks = {node:(m-rank)/m for rank,node in enumerate(ranked_coe)}
        scores = {node:conf_ranks[node]+coe_ranks[node] for node in candidates}
        removed = min(candidates, key=lambda node:(scores[node],node))
        history.append({
            'step':step+1, 'global_node_id':removed,
            'pseudo_class_index':label_of[removed],
            'confidence_percent':conf_of[removed],
            'removable_candidate_count':m,
            'class_count_before':counts[label_of[removed]],
            'entropy_before':h0,'COE_entropy_without_minus_current':coe[removed],
            'confidence_protection_rank':ranked_conf.index(removed)+1,
            'COE_protection_rank':ranked_coe.index(removed)+1,
            'confidence_protection_percentile':conf_ranks[removed],
            'COE_protection_percentile':coe_ranks[removed],
            'combined_protection_score':scores[removed],
        })
        alive.remove(removed)
        assert Counter(label_of[node] for node in alive)[label_of[removed]] >= 1
        assert set(label_of[node] for node in alive) == start_classes
    retained_ids = [node for node in ids if node in alive]
    removed_ids = [item['global_node_id'] for item in history]
    assert len(removed_ids) == len(set(removed_ids)) == deletion_count
    assert len(retained_ids) == len(set(retained_ids)) == 95
    assert set(retained_ids).isdisjoint(removed_ids)
    assert set(retained_ids) | set(removed_ids) == set(ids)
    return {'retained_global_node_ids_in_original_manifest_order':retained_ids,
            'removed_global_node_ids_in_deletion_order':removed_ids,
            'retained_pseudo_class_indices_in_order':[label_of[i] for i in retained_ids],
            'retained_confidence_percent_in_order':[conf_of[i] for i in retained_ids],
            'initial_pseudo_class_histogram':{str(c):Counter(labels)[c] for c in sorted(start_classes)},
            'retained_pseudo_class_histogram':{str(c):Counter(label_of[i] for i in retained_ids)[c] for c in sorted(start_classes)},
            'removal_history':history}


def verify_new_seed(seed, receipt_sha, script_sha, ps_pin, selection, init_expected, test_ids):
    directory = seed_folder(seed)
    receipt = decode(checked(directory/'freeze_receipt.json', receipt_sha))
    assert receipt['schema'] == 'featprop_downstream_seed_pair_freeze_receipt_001'
    assert receipt['write_once'] is True and receipt['seed'] == seed
    assert receipt['cohort'] == 'original_complete_case' and receipt['pipeline'] == 'ps_featprop_ce'
    assert receipt['upstream_protocol_receipt_sha256'] == PINS['protocol']
    assert receipt['PS_selection_receipt_sha256'] == ps_pin
    assert receipt['num_training_fits'] == 2 and receipt['no_API'] is True
    assert receipt['PS'] is True and receipt['weighted_CE'] is False
    assert receipt['no_upstream_overwrite'] is True and receipt['GT_used_only_final_fixed_test'] is True
    assert receipt['runner_source_sha256'] == script_sha
    outs = receipt['outputs_sha256']
    assert set(outs) == {'paired_seed_result.json','runner_source.py','b1/model_state.pt','narrative_v0/model_state.pt'}
    assert inventory(directory) == set(outs) | {'freeze_receipt.json'}
    for name, dig in outs.items(): checked(directory/name,dig)
    assert outs['runner_source.py'] == script_sha
    r = decode(checked(directory/'paired_seed_result.json',outs['paired_seed_result.json']))
    assert r['schema'] == f'featprop_downstream_primary_ps_ce_seed{seed:02d}_pair_001'
    assert r['pipeline'] == 'ps_featprop_ce' and r['cohort'] == 'original_complete_case'
    assert r['seed'] == seed and r['epochs_per_fit'] == 30 and r['num_training_fits_completed'] == 2
    assert r['upstream_protocol_receipt_sha256'] == PINS['protocol']
    assert r['upstream_prediction_receipt_sha256'] == PINS['predictions']
    assert r['PS_selection_receipt_sha256'] == ps_pin
    assert r['graph_sha256'] == PINS['graph'] and r['GCN_source_sha256'] == PINS['model']
    assert r['runner_source_sha256'] == script_sha and r['paired_same_initial_parameters'] is True
    assert r['shared_initial_parameters_sha256'] == init_expected
    assert r['common_test_count'] == 2568 and r['fitted_arms'] == list(ARMS)
    assert r['GT_training_leakage'] is False and r['GT_labels_or_per_node_correctness_serialized'] is False
    assert r['API'] is False and r['PS'] is True and r['weighted_CE'] is False
    for arm in ARMS:
        record = r['by_arm'][arm]
        ids = selection[arm]['retained_global_node_ids_in_original_manifest_order']
        assert record['arm'] == arm and record['seed'] == seed
        assert record['train_count'] == 95 and record['test_count'] == 2568
        assert record['retained_global_node_ids'] == ids
        assert record['raw_GT_labels_serialized'] is False
        assert record['initial_model_parameters_sha256'] == init_expected
        assert record['test_global_node_ids'] == test_ids
        assert len(record['test_predicted_class_indices']) == 2568
        assert all(type(v) is int and 0 <= v < 7 for v in record['test_predicted_class_indices'])
        assert type(record['correct_on_common_test']) is int and 0 <= record['correct_on_common_test'] <= 2568
        assert math.isclose(record['accuracy'], record['correct_on_common_test']/2568,abs_tol=1e-14)
        assert math.isfinite(record['first_epoch_loss']) and math.isfinite(record['last_epoch_loss'])
    assert math.isclose(r['paired_delta_v0_minus_b1_percentage_points'],
                        100*(r['by_arm']['narrative_v0']['accuracy']-r['by_arm']['b1']['accuracy']),abs_tol=1e-11)
    return {'directory':directory.name,'receipt_sha256':receipt_sha,
            'result_sha256':outs['paired_seed_result.json'],'result':r}


print('=== BATCH: PRIMARY COMPLETE-CASE PS-FEATPROP + CE, SEEDS 0..9 ===', flush=True)
assert ROOT.is_dir() and not ROOT.is_symlink()
assert SCRIPT.is_file() and not SCRIPT.is_symlink() and SCRIPT.name == SCRIPT_NAME
script_blob = SCRIPT.read_bytes()
script_sha = sha(script_blob)
assert not PS_DIR.exists() and not PS_DIR.is_symlink(), 'PS selection folder exists; STOP / audit before continuation'
assert not SUMMARY_DIR.exists() and not SUMMARY_DIR.is_symlink(), 'PS CE summary exists; STOP'
for seed in SEEDS:
    destination = seed_folder(seed)
    assert not destination.exists() and not destination.is_symlink(), f'Seed {seed} folder exists; STOP / no duplicate fit'

# Verify the actual published directory paths BEFORE reading receipts or writing anything.
# This explicitly guards against a pipeline-ID / directory-name mismatch.
for prior_key in ('featprop_ce', 'featprop_weighted_ce'):
    for prior_seed in SEEDS:
        prior = prior_folder(prior_key, prior_seed)
        assert prior.is_dir() and not prior.is_symlink(), f'Missing prior frozen pair: {prior}'
        assert (prior / 'freeze_receipt.json').is_file(), f'Missing prior frozen receipt: {prior}'
print('All 20 PREVIOUS PAIR DIRECTORY PATHS: VERIFIED / no new output created', flush=True)

# Verify all 40 upstream fits and 2 published ten-seed summaries, NO re-training.
ce_initial = verify_completed_pipeline('featprop_ce', CE_SUMMARY, PINS['ce_summary'],
    PINS['ce_summary_json'], 'featprop_downstream_primary_ce_ten_seed_summary_freeze_receipt_001', 20)
w_initial = verify_completed_pipeline('featprop_weighted_ce', W_SUMMARY, PINS['weighted_summary'],
    PINS['weighted_summary_json'], 'featprop_downstream_primary_weighted_ce_ten_seed_summary_freeze_receipt_001', 40)
assert ce_initial == w_initial, 'Prior matched initial model hashes differ'
assert decode(checked(W_SUMMARY/'freeze_receipt.json',PINS['weighted_summary']))['outputs_sha256']['batch_runner_source.py'] == PINS['weighted_runner']
print('PRIOR 40 FITS / BOTH TEN-SEED SUMMARIES / ALL MODEL HASHES: VERIFIED; NOT RETRAINED',flush=True)

receipt = decode(checked(PROT/'freeze_receipt.json',PINS['protocol']))
assert receipt['schema'] == 'featprop_downstream_pre_first_gcn_freeze_receipt_001'
assert receipt['write_once'] and receipt['no_GT_tensor_read'] and receipt['no_training']
assert receipt['total_planned_fits'] == 160
assert receipt['upstream_prediction_receipt_sha256'] == PINS['predictions']
assert receipt['graph_sha256_opaque'] == PINS['graph']
assert inventory(PROT) == set(receipt['outputs_sha256']) | {'freeze_receipt.json'}
artifacts = {name:checked(PROT/name,digest) for name,digest in receipt['outputs_sha256'].items()}
protocol = decode(artifacts['protocol.json'])
inputs = decode(artifacts['gt_isolated_training_inputs.json'])
assert protocol['schema'] == 'featprop_downstream_pre_first_gcn_protocol_001'
assert protocol['status'] == 'PRECOMMITTED_BEFORE_FIRST_GCN_FIT'
assert protocol['fixed_conditions']['arms'] == list(ARMS)
assert protocol['fixed_conditions']['seed_values'] == list(SEEDS)
assert protocol['fixed_conditions']['pipelines'] == ['featprop_ce','featprop_weighted_ce','ps_featprop_ce','ps_featprop_weighted_ce']
assert protocol['fixed_conditions']['cohorts'] == ['original_complete_case','all_node_replacement']
assert protocol['fixed_conditions']['total_planned_fits'] == 160
assert protocol['fixed_conditions']['no_validation_no_early_stopping'] is True
assert protocol['upstream_pins']['parser_vote_receipt_sha256'] == PINS['predictions']
assert inputs['schema'] == 'featprop_downstream_gt_isolated_inputs_001'
assert inputs['source_parser_vote_receipt_sha256'] == PINS['predictions']
assert inputs['graph_sha256'] == PINS['graph'] and inputs['num_nodes'] == 2708
assert inputs['no_ground_truth_access'] is True
assert inputs['ground_truth_derived_evaluation_artifacts_used'] is False
assert inputs['arms'] == list(ARMS)
assert inputs['ordered_classes'] == ['rule_learning','neural_networks','case_based','genetic_algorithms','theory','reinforcement_learning','probabilistic_methods']
assert decode(checked(PRED/'freeze_receipt.json',PINS['predictions']))['schema'] == 'featprop_parser_vote_freeze_receipt_001'
assert protocol['GCN']['epochs_exact'] == 30 and protocol['GCN']['num_layers'] == 2
assert protocol['GCN']['hidden_dimension'] == 64 and protocol['GCN']['num_classes'] == 7
assert protocol['GCN']['dropout'] == .5 and protocol['GCN']['learning_rate'] == .01
assert protocol['GCN']['weight_decay'] == .0005 and protocol['GCN']['batch_norm'] is False
assert protocol['GCN']['feature_l2_normalization'] is False
assert protocol['GCN']['validation'] == 'none' and protocol['GCN']['early_stopping'] == 'none'
ps_contract = protocol['pseudo_label_post_filter']
assert ps_contract['applied_for'] == ['ps_featprop_ce','ps_featprop_weighted_ce']
assert ps_contract['remove_ratio'] == .3
assert ps_contract['remove_count_rule'].startswith('floor(0.30*')
assert ps_contract['inputs_only'].startswith('frozen voted first-class pseudo-labels')
assert ps_contract['class_guard'].startswith('Never remove the last')
assert ps_contract['entropy'].startswith('Shannon entropy of current')
assert ps_contract['ranks'].startswith('At each deletion, rank remaining candidates:')
assert ps_contract['deletion_score'].startswith('r_confidence + r_diversity')
assert ps_contract['iteration'].startswith('Delete exactly one node')
assert ps_contract['arm_specific_filtering'].startswith('Compute independently for each arm')
assert ps_contract['no_outcome_tuning'] is True
assert protocol['GT_firewall']['no_accuracy_or_correctness_based_training_selection'] is True
assert protocol['weighted_ce']['CE_control'].startswith('mean_i(cross_entropy')
print('Frozen protocol/PS policy/prediction input anchors: VERIFIED',flush=True)

cohort = inputs['cohorts']['original_complete_case']
full = inputs['cohorts']['all_node_replacement']
train_ids = cohort['target_ids_in_manifest_order']
all_ids = full['target_ids_in_manifest_order']
test_ids = inputs['common_test_global_node_ids']
excluded = cohort['selected_target_ids_neither_train_nor_test']
assert len(train_ids) == len(set(train_ids)) == 135
assert len(all_ids) == len(set(all_ids)) == 140
assert len(excluded) == len(set(excluded)) == 5
assert set(train_ids) | set(excluded) == set(all_ids)
assert len(test_ids) == len(set(test_ids)) == 2568
assert set(all_ids).isdisjoint(test_ids)
assert test_ids == [i for i in range(2708) if i not in set(all_ids)]
assert all(type(i) is int and 0 <= i < 2708 for i in train_ids + test_ids + excluded)
assert math.floor(.3*len(train_ids)) == 40

# No graph load, no GT read: determine PS independently from frozen voted labels/confidence.
selection = {}
for arm in ARMS:
    row = cohort['by_arm'][arm]
    assert len(row['class_index_in_train_target_order']) == 135
    assert len(row['confidence_percent_in_train_target_order']) == 135
    outcome = derive_ps(train_ids, row['class_index_in_train_target_order'],
                        row['confidence_percent_in_train_target_order'], 40)
    assert len(outcome['retained_global_node_ids_in_original_manifest_order']) == 95
    assert len(outcome['removed_global_node_ids_in_deletion_order']) == 40
    assert set(outcome['retained_global_node_ids_in_original_manifest_order']).isdisjoint(test_ids)
    assert set(outcome['retained_global_node_ids_in_original_manifest_order']).isdisjoint(excluded)
    selection[arm] = outcome
    print(f'{arm}: PS removes 40/135, retains 95; retained histogram: {outcome["retained_pseudo_class_histogram"]}',flush=True)

ps_manifest = {
    'schema':'featprop_downstream_primary_corrected_ps_selection_manifest_001',
    'cohort':'original_complete_case', 'pipeline_family':['ps_featprop_ce','ps_featprop_weighted_ce'],
    'arms':list(ARMS), 'num_targets_before_PS':135, 'remove_count_per_arm':40,
    'retained_count_per_arm':95,'test_count_fixed_shared':2568,
    'upstream_protocol_receipt_sha256':PINS['protocol'],
    'upstream_frozen_GT_isolated_inputs_sha256':receipt['outputs_sha256']['gt_isolated_training_inputs.json'],
    'upstream_prediction_receipt_sha256':PINS['predictions'],
    'frozen_protocol_ps_policy':ps_contract,
    'selection_by_arm':selection,
    'GT_or_evaluation_results_used_in_selection':False,
    'graph_loaded_before_selection':False,
    'reused_for_all_ten_seeds_and_both_PS_CE_and_PS_weighted_CE':True,
}
ps_outputs = {'ps_selection_manifest.json':encoded(ps_manifest), 'ps_selection_runner_source.py':script_blob}
ps_hashes = {name:sha(blob) for name,blob in ps_outputs.items()}
ps_receipt = {
    'schema':'featprop_downstream_primary_ps_selection_freeze_receipt_001',
    'created_utc':datetime.now(timezone.utc).isoformat(),
    'write_once':True,'cohort':'original_complete_case',
    'upstream_protocol_receipt_sha256':PINS['protocol'],
    'upstream_prediction_receipt_sha256':PINS['predictions'],
    'runner_source_sha256':script_sha,
    'outputs_sha256':ps_hashes,
    'removed_per_arm':40,'retained_per_arm':95,
    'no_API':True,'no_GT_read':True,'no_training_before_selection_freeze':True,
    'no_outcome_tuning':True,'no_upstream_overwrite':True,
}
assert not PS_DIR.exists() and not PS_DIR.is_symlink()
PS_DIR.mkdir(parents=False, exist_ok=False)
for name,blob in ps_outputs.items():exclusive(PS_DIR/name,blob)
exclusive(PS_DIR/'freeze_receipt.json',encoded(ps_receipt))
ps_pin = sha((PS_DIR/'freeze_receipt.json').read_bytes())
assert inventory(PS_DIR) == set(ps_outputs) | {'freeze_receipt.json'}
assert decode(checked(PS_DIR/'freeze_receipt.json',ps_pin)) == ps_receipt
for name,digest in ps_hashes.items():checked(PS_DIR/name,digest)
assert decode(checked(PS_DIR/'ps_selection_manifest.json',ps_hashes['ps_selection_manifest.json'])) == ps_manifest
print('PS SELECTED/FROZEN BEFORE GRAPH LOAD OR TRAINING | freeze_receipt.json SHA256:',ps_pin,flush=True)

# Compile ONLY the hash-pinned GCN class. Never import repository model/runner modules.
model_source = checked(ROOT/'src/models/nn.py',PINS['model']).decode('utf-8-sig')
model_tree = ast.parse(model_source)
gcn_nodes = [n for n in model_tree.body if isinstance(n, ast.ClassDef) and n.name == 'GCN']
assert len(gcn_nodes) == 1
namespace = {'torch':torch,'F':F,'GCNConv':GCNConv}
exec(compile(ast.fix_missing_locations(ast.Module(body=gcn_nodes,type_ignores=[])),
             '<pinned GCN AST only>','exec'),namespace)
GCN = namespace['GCN']
assert torch_geometric.__version__ == '2.7.0'
graph_blob = checked(GRAPH,PINS['graph'])
raw = torch.load(io.BytesIO(graph_blob),map_location='cpu',weights_only=False)
assert isinstance(raw,Data) and raw.num_nodes == 2708
assert raw.x.ndim == 2 and raw.x.shape[0] == 2708 and raw.x.is_floating_point()
assert raw.edge_index.ndim == 2 and raw.edge_index.shape[0] == 2 and raw.edge_index.dtype == torch.long
edge_weight = getattr(raw,'edge_weight',None)
assert edge_weight is None or (edge_weight.ndim == 1 and edge_weight.numel() == raw.edge_index.shape[1])
model_data = Data(x=raw.x.detach().clone(),edge_index=raw.edge_index.detach().clone(),
    edge_weight=None if edge_weight is None else edge_weight.detach().clone())
del raw,edge_weight
assert 'y' not in model_data.keys() and 'ys' not in model_data.keys()
input_dim = int(model_data.x.shape[1]); assert input_dim > 0
print(f'GT-isolated pinned GCN model input: x=[2708,{input_dim}], '
      f'edges={model_data.edge_index.shape[1]}, NO y',flush=True)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model_data = model_data.to(device)
test_index_cpu = torch.tensor(test_ids,dtype=torch.long)
test_index_device = test_index_cpu.to(device)
removed_global_by_arm = {arm:set(selection[arm]['removed_global_node_ids_in_deletion_order']) for arm in ARMS}
retained_by_arm = {arm:selection[arm]['retained_global_node_ids_in_original_manifest_order'] for arm in ARMS}
results_by_seed = {}
for seed in SEEDS:
    directory = seed_folder(seed)
    assert not directory.exists() and not directory.is_symlink(), f'Seed {seed} exists; STOP'
    print(f'\n=== PS-FEATPROP + CE: SEED {seed}/9, TWO PAIRED FITS ===',flush=True)
    model_outputs = {}
    initials = {}
    for arm in ARMS:
        retained = retained_by_arm[arm]
        train_index = torch.tensor(retained,dtype=torch.long,device=device)
        label_by_id = dict(zip(train_ids,cohort['by_arm'][arm]['class_index_in_train_target_order']))
        pseudo = torch.full((2708,),-1,dtype=torch.long,device=device)
        pseudo[train_index] = torch.tensor([label_by_id[i] for i in retained],dtype=torch.long,device=device)
        assert int((pseudo >= 0).sum().item()) == 95
        assert torch.all(pseudo[test_index_device] == -1).item()
        assert all(int(pseudo[node].item()) == -1 for node in excluded)
        assert all(int(pseudo[node].item()) == -1 for node in removed_global_by_arm[arm])
        seed_everything(seed)
        model = GCN(num_layers=2,input_dim=input_dim,hidden_dimension=64,
                    num_classes=7,dropout=.5,norm=None).to(device)
        initials[arm] = parameter_sha(model)
        assert initials[arm] == ce_initial[seed] == w_initial[seed], 'Initial model differs from prior paired fits'
        optimizer = torch.optim.Adam(model.parameters(),lr=.01,weight_decay=.0005)
        first_loss = last_loss = None
        for epoch in range(1,31):
            model.train()
            optimizer.zero_grad(set_to_none=True)
            logits = model(model_data)
            loss = F.cross_entropy(logits[train_index],pseudo[train_index],
                                   reduction='mean',label_smoothing=0.)
            assert torch.isfinite(loss).item(), f'Nonfinite PS CE seed={seed} arm={arm} epoch={epoch}'
            loss.backward()
            optimizer.step()
            if epoch == 1:first_loss = float(loss.detach().cpu().item())
            if epoch == 30:last_loss = float(loss.detach().cpu().item())
            if epoch in (1,10,20,30):
                print(f'{arm} | seed {seed} | epoch {epoch:02d}/30 | PS-pseudo-CE={loss.item():.8f}',flush=True)
        model.eval()
        with torch.no_grad():
            final_logits = model(model_data)
            assert final_logits.shape == (2708,7) and torch.isfinite(final_logits).all().item()
            test_pred = final_logits.argmax(dim=1).detach().cpu()[test_index_cpu].tolist()
        buffer = io.BytesIO()
        torch.save({name:value.detach().cpu().clone() for name,value in model.state_dict().items()},buffer)
        model_outputs[arm] = {'first_epoch_loss':first_loss,'last_epoch_loss':last_loss,
                              'test_predicted_class_indices':test_pred,'model_state_bytes':buffer.getvalue()}
        del model,optimizer,pseudo,train_index,logits,loss,final_logits
        if torch.cuda.is_available():torch.cuda.empty_cache()
    assert initials['b1'] == initials['narrative_v0'] == ce_initial[seed]
    print(f'Seed {seed}: both paired fits completed; same initial parameter SHA256={initials["b1"]}',flush=True)
    # First access to graph GT is AFTER BOTH fits of the seed, only for final test scoring.
    scoring = torch.load(io.BytesIO(graph_blob),map_location='cpu',weights_only=False)
    gt = scoring.y
    assert isinstance(gt,torch.Tensor) and gt.numel() == 2708
    gt = gt.view(-1).long().cpu()
    assert int(gt.min()) >= 0 and int(gt.max()) <= 6
    truth_test = gt[test_index_cpu]
    assert truth_test.numel() == 2568
    del scoring,gt
    scored = {}
    for arm in ARMS:
        prediction = torch.tensor(model_outputs[arm]['test_predicted_class_indices'],dtype=torch.long)
        assert prediction.shape == truth_test.shape
        correct = int((prediction == truth_test).sum().item())
        scored[arm] = {
            'arm':arm,'cohort':'original_complete_case','pipeline':'ps_featprop_ce','seed':seed,
            'train_count':95,'test_count':2568,'retained_global_node_ids':retained_by_arm[arm],
            'correct_on_common_test':correct,'accuracy':correct/2568,
            'first_epoch_loss':model_outputs[arm]['first_epoch_loss'],
            'last_epoch_loss':model_outputs[arm]['last_epoch_loss'],
            'initial_model_parameters_sha256':initials[arm],
            'test_global_node_ids':test_ids,
            'test_predicted_class_indices':model_outputs[arm]['test_predicted_class_indices'],
            'raw_GT_labels_serialized':False,
        }
        print(f'{arm}: {correct}/2568 = {100*correct/2568:.6f}% (seed={seed})',flush=True)
    del truth_test,prediction
    delta = 100*(scored['narrative_v0']['accuracy']-scored['b1']['accuracy'])
    print(f'Seed {seed}: paired delta v0-B1 = {delta:+.6f} pp',flush=True)
    result = {
        'schema':f'featprop_downstream_primary_ps_ce_seed{seed:02d}_pair_001',
        'upstream_protocol_receipt_sha256':PINS['protocol'],
        'upstream_prediction_receipt_sha256':PINS['predictions'],
        'upstream_prior_ce_summary_receipt_sha256':PINS['ce_summary'],
        'upstream_prior_weighted_ce_summary_receipt_sha256':PINS['weighted_summary'],
        'PS_selection_receipt_sha256':ps_pin,
        'graph_sha256':PINS['graph'],'GCN_source_sha256':PINS['model'],
        'runner_source_sha256':script_sha,
        'cohort':'original_complete_case','pipeline':'ps_featprop_ce','seed':seed,
        'epochs_per_fit':30,'fitted_arms':list(ARMS),
        'paired_same_initial_parameters':True,
        'shared_initial_parameters_sha256':initials['b1'],
        'matched_unfiltered_ce_initial_parameters_sha256':ce_initial[seed],
        'num_training_fits_completed':2,'num_planned_fits_total':160,
        'common_test_count':2568,
        'PS_policy':'frozen corrected confidence+COE, 40 removed independently per arm; same 95 per arm across all seeds and PS-weighted',
        'GT_access':'AFTER both training fits, fixed common test scoring only',
        'GT_training_leakage':False,'GT_labels_or_per_node_correctness_serialized':False,
        'API':False,'PS':True,'weighted_CE':False,
        'training_device':str(device),
        'versions':{'python':sys.version.split()[0],'torch':torch.__version__,
                    'torch_geometric':torch_geometric.__version__,'numpy':np.__version__},
        'by_arm':scored,'paired_delta_v0_minus_b1_percentage_points':delta,
    }
    outputs = {
        'paired_seed_result.json':encoded(result), 'runner_source.py':script_blob,
        'b1/model_state.pt':model_outputs['b1']['model_state_bytes'],
        'narrative_v0/model_state.pt':model_outputs['narrative_v0']['model_state_bytes'],
    }
    hashes = {name:sha(blob) for name,blob in outputs.items()}
    seed_receipt = {
        'schema':'featprop_downstream_seed_pair_freeze_receipt_001',
        'created_utc':datetime.now(timezone.utc).isoformat(),
        'write_once':True,'upstream_protocol_receipt_sha256':PINS['protocol'],
        'upstream_prior_ce_summary_receipt_sha256':PINS['ce_summary'],
        'upstream_prior_weighted_ce_summary_receipt_sha256':PINS['weighted_summary'],
        'PS_selection_receipt_sha256':ps_pin,
        'runner_source_sha256':script_sha,
        'cohort':'original_complete_case','pipeline':'ps_featprop_ce','seed':seed,
        'num_training_fits':2,'outputs_sha256':hashes,
        'no_API':True,'PS':True,'weighted_CE':False,'no_upstream_overwrite':True,
        'GT_used_only_final_fixed_test':True,
    }
    assert not directory.exists() and not directory.is_symlink(), 'Seed destination appeared; STOP'
    directory.mkdir(parents=False,exist_ok=False)
    (directory/'b1').mkdir(exist_ok=False)
    (directory/'narrative_v0').mkdir(exist_ok=False)
    for name,blob in outputs.items():exclusive(directory/name,blob)
    exclusive(directory/'freeze_receipt.json',encoded(seed_receipt))
    verified = verify_new_seed(seed,sha((directory/'freeze_receipt.json').read_bytes()),
                               script_sha,ps_pin,selection,ce_initial[seed],test_ids)
    results_by_seed[seed] = verified
    del outputs,model_outputs
    print(f'PS-CE SEED {seed} WRITE-ONCE VERIFIED | freeze_receipt.json SHA256: {verified["receipt_sha256"]}',flush=True)
    print(f'Progress: {40+2*(seed+1)}/160 planned fits; PS-FeatProp+CE {seed+1}/10 paired seeds',flush=True)

# Verify all ten current seed outputs again and both prior ten-seed summaries.
assert set(results_by_seed) == set(SEEDS)
rechecked = {seed:verify_new_seed(seed,results_by_seed[seed]['receipt_sha256'],
              script_sha,ps_pin,selection,ce_initial[seed],test_ids) for seed in SEEDS}
assert all(results_by_seed[s]['result_sha256'] == rechecked[s]['result_sha256'] for s in SEEDS)
assert verify_completed_pipeline('featprop_ce',CE_SUMMARY,PINS['ce_summary'],PINS['ce_summary_json'],
    'featprop_downstream_primary_ce_ten_seed_summary_freeze_receipt_001',20) == ce_initial
assert verify_completed_pipeline('featprop_weighted_ce',W_SUMMARY,PINS['weighted_summary'],PINS['weighted_summary_json'],
    'featprop_downstream_primary_weighted_ce_ten_seed_summary_freeze_receipt_001',40) == w_initial
assert decode(checked(PS_DIR/'freeze_receipt.json',ps_pin)) == ps_receipt
assert not SUMMARY_DIR.exists() and not SUMMARY_DIR.is_symlink()
per_seed = []
for seed in SEEDS:
    item = rechecked[seed]
    r = item['result']
    b1,v0 = r['by_arm']['b1'],r['by_arm']['narrative_v0']
    per_seed.append({
        'seed':seed,'seed_directory':item['directory'],
        'seed_freeze_receipt_sha256':item['receipt_sha256'],
        'paired_seed_result_sha256':item['result_sha256'],
        'b1_correct':b1['correct_on_common_test'],'v0_correct':v0['correct_on_common_test'],
        'test_count':2568,'b1_accuracy_percent':100*b1['accuracy'],
        'v0_accuracy_percent':100*v0['accuracy'],
        'paired_delta_v0_minus_b1_percentage_points':100*(v0['accuracy']-b1['accuracy']),
        'shared_initial_parameters_sha256':r['shared_initial_parameters_sha256'],
    })
b1_vals = [i['b1_accuracy_percent'] for i in per_seed]
v0_vals = [i['v0_accuracy_percent'] for i in per_seed]
delta_vals = [i['paired_delta_v0_minus_b1_percentage_points'] for i in per_seed]
summary = {
    'schema':'featprop_downstream_primary_complete_case_ps_featprop_ce_10seed_summary_001',
    'cohort':'original_complete_case','pipeline':'ps_featprop_ce',
    'seed_order':list(SEEDS),'arms':list(ARMS),'train_count_before_PS':135,
    'train_count_after_PS_by_arm':{arm:95 for arm in ARMS},
    'common_test_count':2568,'epochs_per_fit':30,
    'pairs_completed':10,'fits_completed_for_this_pipeline':20,
    'overall_protocol_planned_fits':160,'overall_protocol_fits_completed_to_date':60,
    'previous_ce_and_weighted_ce_forty_fits_verified_not_retrained':True,
    'previous_ce_summary_receipt_sha256':PINS['ce_summary'],
    'previous_weighted_ce_summary_receipt_sha256':PINS['weighted_summary'],
    'PS_selection_receipt_sha256':ps_pin,
    'PS_manifest_sha256':ps_hashes['ps_selection_manifest.json'],
    'batch_runner_source_sha256':script_sha,
    'upstream_protocol_receipt_sha256':PINS['protocol'],
    'upstream_prediction_receipt_sha256':PINS['predictions'],
    'graph_sha256':PINS['graph'],'GCN_source_sha256':PINS['model'],
    'per_seed':per_seed,
    'summary_statistics':{
        'B1':{'mean_accuracy_percent':statistics.mean(b1_vals),
              'population_std_accuracy_percentage_points_ddof0':statistics.pstdev(b1_vals)},
        'Narrative_v0':{'mean_accuracy_percent':statistics.mean(v0_vals),
                        'population_std_accuracy_percentage_points_ddof0':statistics.pstdev(v0_vals)},
        'paired_delta_v0_minus_b1':{
            'mean_percentage_points':statistics.mean(delta_vals),
            'population_std_percentage_points_ddof0':statistics.pstdev(delta_vals),
            'definition':'For each SAME seed, 100*(v0_correct/2568-b1_correct/2568)',
        },
    },
    'GT_access':'fixed final common-test scoring after both fits of each seed only',
    'GT_labels_or_per_node_correctness_serialized':False,
    'API':False,'PS':True,'weighted_CE':False,'remaining_protocol_fits':100,
}
summary_outputs = {'summary.json':encoded(summary),'batch_runner_source.py':script_blob}
summary_hashes = {name:sha(blob) for name,blob in summary_outputs.items()}
summary_receipt = {
    'schema':'featprop_downstream_primary_ps_ce_ten_seed_summary_freeze_receipt_001',
    'created_utc':datetime.now(timezone.utc).isoformat(),
    'write_once':True,'cohort':'original_complete_case','pipeline':'ps_featprop_ce',
    'seed_receipts_sha256':{str(i['seed']):i['seed_freeze_receipt_sha256'] for i in per_seed},
    'upstream_protocol_receipt_sha256':PINS['protocol'],
    'upstream_previous_ce_summary_receipt_sha256':PINS['ce_summary'],
    'upstream_previous_weighted_ce_summary_receipt_sha256':PINS['weighted_summary'],
    'PS_selection_receipt_sha256':ps_pin,
    'batch_runner_source_sha256':script_sha,
    'outputs_sha256':summary_hashes,'ten_paired_seeds_verified':True,
    'prior_forty_fits_not_retrained':True,'no_API':True,'PS':True,
    'weighted_CE':False,'no_upstream_overwrite':True,'no_raw_GT_labels_serialized':True,
}
assert not SUMMARY_DIR.exists() and not SUMMARY_DIR.is_symlink()
SUMMARY_DIR.mkdir(parents=False,exist_ok=False)
for name,blob in summary_outputs.items():exclusive(SUMMARY_DIR/name,blob)
exclusive(SUMMARY_DIR/'freeze_receipt.json',encoded(summary_receipt))
assert inventory(SUMMARY_DIR) == set(summary_outputs) | {'freeze_receipt.json'}
for name,pin in summary_hashes.items():checked(SUMMARY_DIR/name,pin)
assert decode(checked(SUMMARY_DIR/'freeze_receipt.json',sha(encoded(summary_receipt)))) == summary_receipt
print('\n=== PRIMARY PS-FEATPROP + CE: ALL 10 PAIRED SEEDS WRITE-ONCE FREEZE COMPLETE ===',flush=True)
for i in per_seed:
    print(f"seed {i['seed']}: B1 {i['b1_correct']}/2568 ({i['b1_accuracy_percent']:.6f}%) | "
          f"v0 {i['v0_correct']}/2568 ({i['v0_accuracy_percent']:.6f}%) | "
          f"delta {i['paired_delta_v0_minus_b1_percentage_points']:+.6f} pp",flush=True)
print('B1 mean ± population std:',f'{statistics.mean(b1_vals):.6f}% ± {statistics.pstdev(b1_vals):.6f} pp',flush=True)
print('v0 mean ± population std:',f'{statistics.mean(v0_vals):.6f}% ± {statistics.pstdev(v0_vals):.6f} pp',flush=True)
print('Paired delta mean ± population std:',f'{statistics.mean(delta_vals):+.6f} ± {statistics.pstdev(delta_vals):.6f} pp',flush=True)
print('PS selection manifest SHA256:',ps_hashes['ps_selection_manifest.json'],flush=True)
print('PS selection freeze_receipt.json SHA256:',ps_pin,flush=True)
print('summary.json SHA256:',summary_hashes['summary.json'],flush=True)
print('batch_runner_source.py SHA256:',script_sha,flush=True)
print('10-seed summary freeze_receipt.json SHA256:',sha((SUMMARY_DIR/'freeze_receipt.json').read_bytes()),flush=True)
print('ALL 10 PS-CE SEED RECEIPTS/MODELS VERIFIED; PRIOR 40 FITS NOT REPEATED; 60/160 FITS COMPLETE',flush=True)
print('NO API / NO GT TRAINING/PS LEAKAGE / NO HISTORICAL OVERWRITE / NO RAW GT SERIALIZATION',flush=True)
