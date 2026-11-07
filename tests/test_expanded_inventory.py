"""Synthetic preparation only, no private inputs, admission or training."""
import copy
import unittest
from test_three_agent_fusion import synthetic
from llmgnn_sara.downstream.expanded_inventory import matrix
from llmgnn_sara.downstream import full_matrix as m


class ExpandedInventoryTests(unittest.TestCase):
    def test_extra_alias_controls_and_unique_effective_specs(self):
        _, _, report, _ = synthetic()
        arms = copy.deepcopy(report['arms'])
        arms['ZERO_SWITCH_TEST'] = copy.deepcopy(arms['B_NARRATIVE'])
        rows, fits = matrix(arms, report, {'fixture': 'SYNTHETIC_ONLY'})
        self.assertEqual(len(rows), 1344)
        self.assertEqual(len({r['row_id'] for r in rows}), len(rows))
        self.assertTrue(any(r['arm']=='NO_AGENT_FOR_ZERO_SWITCH_TEST' for r in rows))
        for r in rows:
            if r['status'] != 'DRAFT_NOT_ADMITTED': continue
            self.assertEqual(len(r['train_ids']), len(r['class_indices']))
            self.assertEqual(len(r['train_ids']), len(r['weights']))
        b = next(r for r in rows if r['arm']=='B_NARRATIVE' and r['mask']=='natural')
        alias = next(r for r in rows if r['arm']=='ZERO_SWITCH_TEST' and r['mask']=='natural')
        self.assertEqual(b['fit_sha256'], alias['fit_sha256'])


if __name__ == '__main__': unittest.main()
