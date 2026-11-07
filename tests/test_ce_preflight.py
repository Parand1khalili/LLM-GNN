"""Synthetic preparation only; no fitting, private data or GT decoding."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from test_three_agent_fusion import synthetic
from llmgnn_sara.downstream import ce_preflight as c
from llmgnn_sara.downstream import fusion as d
from llmgnn_sara.sara3.experiment import digest


class PreflightTests(unittest.TestCase):
    def setUp(self):
        _, _, self.report, _ = synthetic()
        self.grid = d.build_grid(self.report, digest(self.report))

    def test_seven_arms_seeds_dedup_masks_no_mutation_or_training(self):
        before = copy.deepcopy((self.report, self.grid))
        with patch('llmgnn_sara.downstream.model.train_gcn', side_effect=AssertionError('training forbidden')):
            package = c.prepare(self.report, self.grid, cohort='primary')
        self.assertEqual((self.report, self.grid), before)
        self.assertEqual(len(package['natural']), 7)
        self.assertEqual(package['training_runs'], 0)
        self.assertFalse(package['real_training_authorized'])
        self.assertEqual(package, c.prepare(self.report, self.grid, cohort='primary'))
        for fit in package['fits'].values():
            self.assertEqual(fit['seeds'], list(range(10)))
            self.assertEqual(fit['spec']['graph_sha256'], c.GRAPH_SHA256)
            self.assertTrue(set(fit['spec']['train_ids']).isdisjoint(self.grid['test_ids']))
            self.assertTrue(set(fit['spec']['train_ids']).isdisjoint(range(135, 140)))
        flattened = [a for fit in package['fits'].values() for a in fit['arms']]
        self.assertEqual(len(flattened), len(set(flattened)))

    def test_coverage_control_uses_only_baselines_and_same_mask(self):
        package = c.prepare(self.report, self.grid, cohort='sensitivity')
        for control in package['coverage_controls']:
            treatment = next(r for r in package['natural'] if r['arm'] == control['treatment_arm'])
            self.assertEqual(control['train_ids'], treatment['train_ids'])
            self.assertEqual(len(control['class_indices']), len(treatment['class_indices']))
            self.assertIsNone(control['confidence_percent'])
        row = {'train_ids': [0, 1, 2]}
        r = self.report['arms']['C_BASELINE_FUSION']
        r[0].update(b1_class=2, narrative_class=3, b1_confidence=90, narrative_confidence=80)
        r[1].update(b1_class=2, narrative_class=3, b1_confidence=80, narrative_confidence=90)
        r[2].update(b1_class=2, narrative_class=3, b1_confidence=80, narrative_confidence=80)
        labels, sources = c.control_labels(self.report, row)
        self.assertEqual(labels[:2], [2, 3]); self.assertEqual(sources[-1], 'FIXED_HASH_TIE')
        r[2].update(b1_class=3, narrative_class=2)
        self.assertEqual(c.control_labels(self.report, row)[0], labels)
        self.report['arms']['D_P1_r0'][0]['final_class'] = 6
        self.assertEqual(c.control_labels(self.report, row)[0], labels)

    def test_tampered_grid_gt_and_duplicate_ids_rejected(self):
        for change in ('class_indices', 'train_ids', 'test_ids', 'config'):
            bad = copy.deepcopy(self.grid)
            if change in ('class_indices', 'train_ids'): bad['plans'][0][change][0] = 2707
            elif change == 'test_ids': bad['test_ids'][0] = 0
            else: bad['config']['epochs'] = 31
            with self.assertRaises(ValueError): c.prepare(self.report, bad, cohort='primary')
        with self.assertRaises(ValueError): c.prepare({**self.report, 'gt': [0]}, self.grid, cohort='primary')
        with self.assertRaises(ValueError): c.control_labels(self.report, {'train_ids': [0, 0]})
        with self.assertRaises(ValueError): c.prepare(self.report, self.grid, cohort='other')

    def test_default_deny_real_audit_bindings_and_explicit_authorizations(self):
        p = c.prepare(self.report, self.grid, cohort='primary')
        audit = {'schema': 'sara.gcn.source_audit.v1', 'package_sha256': digest(p),
            'graph_sha256': c.GRAPH_SHA256, 'test_ids_sha256': p['test_ids_sha256'],
            'status': 'AUDITED_EXPLORATORY_SPLIT', 'feature_generation_gt_isolation': 'VERIFIED',
            'historical_observed_test_acknowledged': True}
        approval = {'schema': c.VERSION, 'package_sha256': digest(p), 'audit_sha256': digest(audit),
            'owner_authorized': True, 'allow_real_training': True, 'allow_experimental_admission': True}
        with self.assertRaises(PermissionError): c.validate_approval(p, audit, None)
        c.validate_approval(p, audit, approval)  # Synthetic authority only; never dispatches.
        for field, value in (('graph_sha256', 'a'*64), ('test_ids_sha256', 'b'*64),
                             ('feature_generation_gt_isolation', 'UNVERIFIED'),
                             ('historical_observed_test_acknowledged', False)):
            bad = {**audit, field: value}
            with self.assertRaises(ValueError): c.validate_approval(p, bad, {**approval, 'audit_sha256': digest(bad)})
        for field in ('owner_authorized', 'allow_real_training', 'allow_experimental_admission'):
            with self.assertRaises(ValueError): c.validate_approval(p, audit, {**approval, field: False})
        with self.assertRaises(ValueError): c.validate_approval(p, audit, {**approval, 'audit_sha256': 'a'*64})

    def test_public_allowlist_and_no_observed_metrics(self):
        p = c.prepare(self.report, self.grid, cohort='primary'); result = c.summary(p)
        self.assertNotIn('train_ids', str(result)); self.assertNotIn('class_indices', str(result))
        self.assertEqual(p['actual_metrics'], [])
        self.assertEqual(result['training_status'], 'NOT_RUN_BLOCKED')

    def test_historical_source_pins_and_unverified_feature_origin_block(self):
        p = c.prepare(self.report, self.grid, cohort='primary')
        root = Path(__file__).resolve().parents[1]
        audit = c.source_audit(p, root)
        self.assertEqual(audit['status'], 'REVIEW_REQUIRED_NOT_AUTHORIZED')
        self.assertEqual(audit['feature_generation_gt_isolation'], 'UNVERIFIED_ENCODER_EXECUTION_PROVENANCE')
        with patch.dict(c.HISTORICAL_SOURCES, {'recovered_sources/src/models/nn.py': '0'*64}):
            with self.assertRaises(ValueError): c.source_audit(p, root)


if __name__ == '__main__': unittest.main()
