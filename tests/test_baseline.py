"""Independent offline parsed-sample replay and prompt/graph contract tests."""
from __future__ import annotations

import ast
from collections import Counter
import copy
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from pathlib import Path
import re
import socket
import tempfile
import unittest
from unittest.mock import patch

from llmgnn_sara.annotation.prompts import (
    FrozenPromptTemplate, MATCHED_PREPARATION_SHA256, SENTINEL, build_b1_prompt, build_consensus,
    build_narrative_prompt, disabled_provider,
)
from llmgnn_sara.annotation.replay import replay_dataset, replay_frozen
from llmgnn_sara.annotation.voting import _distance, vote_parsed_samples
from llmgnn_sara.io.frozen import CLASSES, PINS, FrozenDataset, InputError, _validate_objects, read_pinned_json
from llmgnn_sara.selection import build_undirected_neighbors, semantic_topk_1hop

ROOT = Path(__file__).resolve().parents[1]


def frozen_fixture():
    """Expected confidence85 is independently hand-calculated: (80+85+90)/3."""
    selection = {"selected_global_node_ids_sorted": list(range(140))}
    arms = {}
    index = 0
    for arm in ("b1", "narrative_v0"):
        rows = {}
        for node in range(140):
            kind = "historical_reuse" if node < 14 else "supplementary" if node < 19 else "original_fresh"
            ci = node % 7
            samples = []
            for si, confidence in enumerate((80, 90, 100)):
                samples.append({"sample_index": si, "target_id": node, "arm": arm,
                    "original_request_index": index, "source_kind": kind,
                    "source_response_path": f"experiments/matched_cora/featprop_infer_001/slots/synthetic_{index}/provider_response.json",
                    "source_response_sha256": hashlib.sha256(str(index).encode()).hexdigest(),
                    "prompt_sha256": "a"*64,
                    "parsed_answers_for_three_sample_vote": [[CLASSES[ci], confidence]],
                    "first_answer_for_vote": CLASSES[ci], "first_confidence_for_vote": confidence,
                    "first_class_index_for_vote": ci})
                index += 1
            rows[str(node)] = {"target_id": node, "arm": arm, "ground_truth_accessed": False,
                "failure": None, "retries": 0, "repair": {"applied": False, "budget": 0},
                "class_index": ci, "prediction": CLASSES[ci], "confidence_percent_before_tensor_cast": 85,
                "historical_all_invalid_fallback_count": 0, "primary_samples": samples,
                "original_request_indices": [s["original_request_index"] for s in samples],
                "selected_response_sha256_by_sample_index": [s["source_response_sha256"] for s in samples],
                "prompt_sha256": "a"*64, "source_kind": kind}
        arms[arm] = {"schema": "featprop_parser_vote_final_predictions_001", "arm": arm,
            "ground_truth_accessed": False, "ordered_classes": list(CLASSES),
            "target_ids_in_manifest_order": list(range(140)), "predictions_by_target_id": rows}
    return arms["b1"], arms["narrative_v0"], selection


class VotingTests(unittest.TestCase):
    def test_historical_arithmetic_and_invalid_denominator(self):
        result = vote_parsed_samples((((CLASSES[0], 80),), ((CLASSES[0], 90),), (("unknown", 100),)))
        self.assertEqual(result.class_index, 0)
        self.assertAlmostEqual(result.confidence_percent, 55)
        self.assertEqual(result.fallback_count, 0)

    def test_tie_uses_first_appearance_not_sorted_class(self):
        result = vote_parsed_samples((((CLASSES[4], 90),), ((CLASSES[0], 80),), ((CLASSES[1], 70),)))
        self.assertEqual(result.class_index, 4)
        self.assertAlmostEqual(result.confidence_percent, 140/3)

    def test_all_invalid_uses_last_first_answer_and_half_confidence(self):
        result = vote_parsed_samples(((("unmapped", 10),), (("unmapped", 20),), (("theori", 60),)))
        self.assertEqual((result.prediction, result.confidence_percent, result.fallback_count), ("theory", 30, 1))
        self.assertEqual(_distance("kitten", "sitting"), 3)

    def test_malformed_samples_fail_closed(self):
        for samples in ([], [[], [], []], [[("a", float("nan"))]]*3, [[("a", True)]]*3,
                        [[("a", -1)]]*3, [[("a", 101)]]*3):
            with self.subTest(samples=samples), self.assertRaises(InputError):
                vote_parsed_samples(samples)

    def test_comparison_with_hash_pinned_original_prediction_loop(self):
        source = ROOT / "recovered_sources/src/llm.py"
        payload = source.read_bytes()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), "483e7a1b7d445801edf1ee5e8251187807663e47dac940e4b24efcf06250ecce")
        with __import__('warnings').catch_warnings():
            __import__('warnings').simplefilter('ignore', SyntaxWarning)
            tree = ast.parse(payload.decode('utf-8-sig'))
        experiment = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Experiment')
        evaluator = next(n for n in experiment.body if isinstance(n, ast.FunctionDef) and n.name == 'eval_result')
        loop = next(n for n in evaluator.body if isinstance(n, ast.For))
        self.assertFalse({n.id for n in ast.walk(loop) if isinstance(n, ast.Name)} & {'gt', 'gt_y', 'torch', 'data_obj'})
        function = ast.parse("def reference(res,label_names,select_ids):\n pred=[]\n conf=[]\n cannot_fix=0\n method='consistency'\n return pred,conf,cannot_fix\n").body[0]
        function.body.insert(-1, copy.deepcopy(loop))
        namespace = {'most_common_number': lambda values: Counter(values).most_common(1)[0][0],
                     'get_closest_label': lambda text, classes: min(classes, key=lambda c: _distance(text, c))}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), '<isolated GT-free historical loop>', 'exec'), namespace)
        for firsts in (((CLASSES[0], 80), (CLASSES[0], 90), (CLASSES[1], 60)),
                       ((CLASSES[4], 90), (CLASSES[0], 80), (CLASSES[1], 70)),
                       ((CLASSES[0], 80), ("unknown", 99), (CLASSES[0], 90)),
                       (("unknown", 10), ("unknown", 20), ("theori", 60))):
            samples = [[pair] for pair in firsts]
            prediction, confidence, fallback = namespace['reference']([samples], list(CLASSES), [0])
            result = vote_parsed_samples(samples)
            self.assertEqual((result.class_index, result.confidence_percent, result.fallback_count),
                             (prediction[0], confidence[0], fallback))


class FrozenIOTests(unittest.TestCase):
    def test_synthetic_full_alignment_replay_and_immutability(self):
        objects = frozen_fixture()
        before = copy.deepcopy(objects)
        dataset = _validate_objects(*objects)
        report = replay_dataset(dataset)
        self.assertEqual((report['status'], report['predictions_matched']), ('PASS', 280))
        self.assertEqual(report['raw_hashes_verified_by_this_replay'], 0)
        self.assertEqual(report['raw_response_parsing'], 'NOT_RUN')
        self.assertEqual(report['input_evidence'], 'UNVERIFIED')
        self.assertEqual(report['artifact_sha256'], {})
        self.assertEqual(report['evidence'], 'UNVERIFIED_INPUT_REPLAY')
        self.assertEqual(objects, before)
        with self.assertRaises(FrozenInstanceError):
            dataset.predictions[0].class_index = 5

    def test_empty_forged_and_false_hash_provenance_fail_closed(self):
        dataset = _validate_objects(*frozen_fixture())
        for forged in (FrozenDataset((), CLASSES, ()),
                       replace(dataset, predictions=dataset.predictions[:-1]),
                       replace(dataset, predictions=(dataset.predictions[0],)*280),
                       replace(dataset, artifact_hashes=tuple(PINS.items())),
                       replace(dataset, input_evidence='HASH_VERIFIED', artifact_hashes=())):
            with self.subTest(forged=forged.input_evidence), self.assertRaises(InputError):
                replay_dataset(forged)

    def test_precise_mismatch_report(self):
        b1, v0, selection = frozen_fixture()
        b1['predictions_by_target_id']['0']['confidence_percent_before_tensor_cast'] = 84
        report = replay_dataset(_validate_objects(b1, v0, selection))
        self.assertEqual(report['predictions_matched'], 279)
        self.assertEqual(report['mismatches'], [{'target_id': 0, 'arm': 'b1', 'fields': ['confidence_percent']}])

    def test_injected_gt_is_rejected_before_decisions(self):
        for key in ('y', 'fixed_y', 'gt', 'true_labels', 'test_labels', 'confusion_matrix', 'E0'):
            with self.subTest(key=key):
                b1, v0, selection = frozen_fixture()
                b1['predictions_by_target_id']['0'][key] = [0]*140
                with self.assertRaisesRegex(InputError, 'GT/diagnostic'):
                    _validate_objects(b1, v0, selection)

    def test_sample_order_class_order_and_identity_rejected(self):
        for mode in ('sample_order', 'class_order', 'request', 'path', 'hash', 'arm_order', 'boolean'):
            with self.subTest(mode=mode):
                b1, v0, selection = frozen_fixture()
                sample = b1['predictions_by_target_id']['0']['primary_samples'][0]
                if mode == 'sample_order': sample['sample_index'] = 2
                if mode == 'class_order': b1['ordered_classes'].reverse()
                if mode == 'request': sample['original_request_index'] = 1
                if mode == 'path': sample['source_response_path'] = '../GT.pt'
                if mode == 'hash': sample['source_response_sha256'] = 'not-a-hash'
                if mode == 'arm_order': v0['target_ids_in_manifest_order'].reverse()
                if mode == 'boolean': selection['selected_global_node_ids_sorted'][0] = False
                with self.assertRaises(InputError):
                    _validate_objects(b1, v0, selection)

    def test_hash_duplicate_nonfinite_and_symlink_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'input.json'
            for blob in (b'{"a":1,"a":2}', b'{"a":NaN}'):
                path.write_bytes(blob)
                with self.assertRaises(InputError):
                    read_pinned_json(path, hashlib.sha256(blob).hexdigest())
            path.write_bytes(b'{}')
            with self.assertRaisesRegex(InputError, 'SHA-256'):
                read_pinned_json(path, '0'*64)

    def test_real_frozen_280_when_external_artifacts_available(self):
        path = ROOT / '.local_artifacts/frozen'
        files = [path/'b1_final_predictions.json', path/'narrative_v0_final_predictions.json', path/'selection_manifest.json']
        if not all(file.is_file() for file in files):
            self.skipTest('External frozen artifacts unavailable; synthetic tests do not replace them')
        before = [hashlib.sha256(file.read_bytes()).hexdigest() for file in files]
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('network forbidden')):
            report = replay_frozen(*files)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['predictions_matched'], 280)
        self.assertEqual(report['input_evidence'], 'HASH_VERIFIED')
        self.assertEqual(before, [hashlib.sha256(file.read_bytes()).hexdigest() for file in files])


class GraphAndPromptTests(unittest.TestCase):
    def test_real_edges_dedup_self_loops_ties_and_isolated(self):
        features = ((1, 0), (1, 0), (1, 0), (0, 1), (0, 0))
        edges = ((0, 0, 0, 0, 1), (2, 1, 1, 0, 3))
        self.assertEqual(build_undirected_neighbors(edges, 5)[0], (1, 2))
        result = semantic_topk_1hop(features, edges, (0, 4), 3)
        self.assertEqual([r['node_id'] for r in result[0]['neighbors']], [1, 2])
        self.assertEqual(result[4], {'degree': 0, 'neighbors': []})
        self.assertEqual(semantic_topk_1hop(features, edges, (0,), 0)[0]['neighbors'], [])

    def test_bad_graph_invariants_rejected(self):
        for features, edges, targets, k in [(((1, 0), (1,)), ((0,), (1,)), (0,), 3),
                (((1, float('nan')),), ((), ()), (0,), 3), (((1, 0),), ((0,), (1,)), (0,), 3),
                (((1, 0),), ((), ()), (True,), 3), (((1, 0),), ((), ()), (0,), -1)]:
            with self.subTest(features=features), self.assertRaises(InputError):
                semantic_topk_1hop(features, edges, targets, k)

    def test_prompt_semantics_budget_and_original_preservation(self):
        class Tokenizer:
            def encode(self, text): return re.findall(r'\S+|\s+', text)
            def decode(self, tokens): return ''.join(tokens)
        tokenizer = Tokenizer()
        template = FrozenPromptTemplate('Question: '+SENTINEL+'\nTask: public classes')
        self.assertEqual(build_b1_prompt('target  \n', template), 'Question: target  \n\nTask: public classes')
        consensus = build_consensus('verified representative text', 2, 3, tokenizer)
        self.assertIn('1 of the 2 other retrieved', consensus)
        adjacency = ((1, 2, 3), (0, 2), (0, 1), (0,))
        prompt, diagnostics = build_narrative_prompt('target  \n', template, consensus, 0, (1, 2, 3), 1,
            adjacency, lambda text: len(tokenizer.encode(text)))
        self.assertIn('N1 connects directly to N2; N3 has no edge', prompt)
        self.assertEqual(diagnostics['connected_node_pairs'], ((1, 2),))
        offset, inserted = diagnostics['insertion_offset'], diagnostics['inserted_block']
        structural = consensus[:offset] + inserted + consensus[offset:]
        self.assertEqual(structural[:offset] + structural[offset + len(inserted):], consensus)
        self.assertLessEqual(diagnostics['new_structural_tokens'], 320)
        bad_adjacency = ((1, 2, 3), (0,), (0, 1), (0,))
        with self.assertRaisesRegex(ValueError, 'asymmetric'):
            build_narrative_prompt('target', template, consensus, 0, (1, 2, 3), 1, bad_adjacency, lambda _: 1)
        with self.assertRaisesRegex(ValueError, 'historical cap'):
            build_narrative_prompt('target', template, consensus, 0, (1, 2, 3), 1, adjacency, lambda _: 257)

    def test_isolated_b1_fallback_and_disabled_provider(self):
        template = FrozenPromptTemplate('prefix '+SENTINEL+' suffix')
        prompt, diagnostics = build_narrative_prompt('target', template, '', 0, (), None, (), lambda _: 0)
        self.assertEqual(prompt, build_b1_prompt('target', template))
        self.assertEqual(diagnostics['fallback'], 'B1_NO_NEIGHBORS')
        with self.assertRaises(InputError):
            build_narrative_prompt('target', template, 'invented evidence', 0, (), None, (), lambda _: 0)
        with self.assertRaises(PermissionError): disabled_provider()

    def test_prompt_receipt_requires_byte_pin_and_frozen_metadata(self):
        receipt = {'historical_wrapper': {'ordered_class_names': list(CLASSES), 'need_tasks': False,
            'k': 3, 'dataset_name': 'cora', 'exact_complete_template_with_sentinel': 'prefix '+SENTINEL+' suffix'}}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'receipt.json'
            blob = json.dumps(receipt).encode()
            path.write_bytes(blob)
            pin = hashlib.sha256(blob).hexdigest()
            template = FrozenPromptTemplate.from_receipt(path, pin)
            self.assertEqual(template.source_sha256, pin)
            self.assertEqual(build_b1_prompt('target', template), 'prefix target suffix')
            with self.assertRaisesRegex(InputError, 'SHA-256'):
                FrozenPromptTemplate.from_receipt(path, '0'*64)
            for invalid in ([], {'historical_wrapper': []},
                            {'historical_wrapper': {**receipt['historical_wrapper'], 'k': 1}}):
                blob = json.dumps(invalid).encode()
                path.write_bytes(blob)
                with self.assertRaises(InputError):
                    FrozenPromptTemplate.from_receipt(path, hashlib.sha256(blob).hexdigest())

    def test_real_preparation_receipt_wrapper_matches_pinned_historical_source(self):
        path = ROOT/'.local_artifacts/frozen/preparation_receipt.json'
        if not path.is_file():
            self.skipTest('External original preparation receipt unavailable')
        receipt = read_pinned_json(path, MATCHED_PREPARATION_SHA256)
        template = FrozenPromptTemplate.from_receipt(path)
        source = (ROOT/'recovered_sources/src/llm.py').read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(), '483e7a1b7d445801edf1ee5e8251187807663e47dac940e4b24efcf06250ecce')
        text = source.decode('utf-8-sig')
        with __import__('warnings').catch_warnings():
            __import__('warnings').simplefilter('ignore', SyntaxWarning)
            tree = ast.parse(text)
        zero_shot = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'zero_shot_prompt')
        experiment = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Experiment')
        topk = next(n for n in experiment.body if isinstance(n, ast.FunctionDef) and n.name == 'topk_confidence')
        wrapper = receipt['historical_wrapper']
        self.assertEqual(ast.get_source_segment(text, zero_shot), wrapper['zero_shot_function_source'])
        self.assertEqual(ast.get_source_segment(text, topk), wrapper['topk_method_source'])
        namespace = {}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(zero_shot), copy.deepcopy(topk)], type_ignores=[])),
                     '<verified pure historical prompt wrappers>', 'exec'), namespace)
        config = wrapper['configuration']
        # Synthetic text tests actual wrapper assembly without claiming140 real prompt hashes replayed.
        target = 'Synthetic article text with preserved trailing whitespace.  \n'
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('network forbidden')):
            question = namespace['zero_shot_prompt']([target], list(CLASSES), need_tasks=False,
                object_cat=config['object-cat'], question=config['question'], answer_format=config['answer-format'])[0]
            historical = namespace['topk_confidence'](None, question, 3, 'cora')
            actual = build_b1_prompt(target, template)
        self.assertEqual(actual.encode('utf-8'), historical.encode('utf-8'))
        self.assertEqual(template.source_sha256, MATCHED_PREPARATION_SHA256)

    def test_no_graph_object_or_gt_attribute_is_consumed(self):
        class ForbiddenGraph:
            @property
            def y(self): raise AssertionError('GT accessed')
        with self.assertRaises(InputError):
            semantic_topk_1hop(ForbiddenGraph(), ((), ()), (0,))


if __name__ == '__main__':
    unittest.main()
