"""Separate, explicit GT-only scoring AFTER every full-matrix fit is frozen."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import statistics
import math
import sys

from ..downstream import full_matrix as matrix
from ..downstream.full_run import read_fit, runtime, exclusive
from ..sara3.audit import PrivateAudit
from ..sara3.correction_features import require
from ..sara3.experiment import digest
from ..io.frozen import read_pinned_json
from .cora_gt_shadow import _labels_from_original_graph, _expected_graph_names


def metrics(predictions, truth):
    require(len(predictions) == len(truth) > 0 and all(type(c) is int and 0 <= c < 7 for c in predictions + truth))
    f1 = []
    for k in range(7):
        tp = sum(p == y == k for p, y in zip(predictions, truth))
        fp = sum(p == k and y != k for p, y in zip(predictions, truth))
        fn = sum(p != k and y == k for p, y in zip(predictions, truth))
        f1.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.0)
    return {"Accuracy": 100*sum(p == y for p, y in zip(predictions, truth))/len(truth), "Macro-F1": sum(f1)/7}


def paired(left, right):
    require(set(left) == set(right) == set(range(10)))
    require(all(set(v) == {'Accuracy','Macro-F1'} and all(type(v[k]) in (int,float)
        and math.isfinite(v[k]) and 0 <= v[k] <= limit for k, limit in (('Accuracy',100),('Macro-F1',1)))
        for v in list(left.values())+list(right.values())))
    result = {}
    for metric in ("Accuracy", "Macro-F1"):
        delta = [right[s][metric] - left[s][metric] for s in range(10)]
        result[metric] = {"per_seed": delta, "mean": statistics.mean(delta), "population_sd": statistics.pstdev(delta)}
    return result


def tables(package, scored):
    """Public aggregates and seed metrics only; no node-level predictions or GT."""
    aggregate, per_seed = matrix.public_rows(package), []
    for row in aggregate:
        if row['row_id'] not in scored: continue
        result = scored[row['row_id']]
        require(set(result) == set(range(10)))
        for metric in ('Accuracy', 'Macro-F1'):
            vals = [result[s][metric] for s in range(10)]
            row[metric] = statistics.mean(vals)
            row[metric+'_SD'] = statistics.pstdev(vals)
        row.update(Mean=row['Accuracy'], SD=row['Accuracy_SD'], Status='COMPLETED_EXPLORATORY_NOT_INDEPENDENT')
        per_seed.extend({**{k: v for k, v in row.items() if k not in ('Mean','SD','Accuracy_SD','Macro-F1_SD')},
                         'Seed': seed, **result[seed]} for seed in range(10))
    comparisons = []
    dimensions = ('Arm','Cohort','Protocol','Loss','PS','Mask','Pair')
    valid = [r for r in aggregate if r['row_id'] in scored]
    for pos, left in enumerate(valid):
        for right in valid[pos+1:]:
            changes = [k for k in dimensions if left[k] != right[k]]
            coverage_pair = (left['Mask'] == 'natural' and right['Mask'] == 'coverage_matched_no_agent'
                and right['Pair'] == ['NO_AGENT', left['Arm']]
                and all(left[k] == right[k] for k in ('Cohort','Protocol','Loss','PS')))
            mask_pair = (set(changes) == {'Mask','Pair'} and left['Mask'] != 'coverage_matched_no_agent'
                         and right['Mask'] != 'coverage_matched_no_agent')
            if len(changes) != 1 and not coverage_pair and not mask_pair: continue
            a, b = (right, left) if coverage_pair else (left, right)
            comparisons.append({'left_row_id': a['row_id'], 'right_row_id': b['row_id'],
                'estimand': 'AGENT_MINUS_COVERAGE_MATCHED_NO_AGENT_CLASS_AND_WEIGHT_EFFECT' if coverage_pair else
                            'MASK_AND_COVERAGE_EFFECT' if mask_pair else changes[0],
                'right_minus_left': paired(scored[a['row_id']], scored[b['row_id']]),
                'uncertainty': 'TRAINING_SEED_VARIABILITY_NOT_INDEPENDENT_COHORT_REPLICATION'})
    for row in aggregate:
        if row['row_id'] not in scored: continue
        row['Paired Delta'] = [{'reference_row_id': c['left_row_id'],
            'accuracy_pp': c['right_minus_left']['Accuracy']['mean'],
            'macro_f1': c['right_minus_left']['Macro-F1']['mean']}
            for c in comparisons if c['right_row_id'] == row['row_id']]
    return {'schema': 'sara.gcn.full_matrix.results.v1', 'package_sha256': digest(package),
            'scientific_status': 'EXPLORATORY_NOT_INDEPENDENT', 'aggregate': aggregate,
            'per_seed': per_seed, 'paired_comparisons': comparisons}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'fits', 'graph', 'frozen-root', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--package-sha256', required=True)
    parser.add_argument('--allow-gt-evaluation', action='store_true')
    parser.add_argument('--public-table', type=Path)
    args = parser.parse_args(argv)
    try:
        require(args.allow_gt_evaluation is True)
        package = read_pinned_json(args.package, args.package_sha256)
        require(package['schema'] == matrix.VERSION and package['contract'] == matrix.CONTRACT
                and package['rule_sha256'] == digest(matrix.CONTRACT)
                and package['runtime'] == runtime(Path(__file__).resolve().parents[3]))
        import numpy as np
        predictions, initial = {}, {}
        for fit_sha in package['fits']:
            predictions[fit_sha] = {}
            for seed in range(10):
                receipt = read_fit(args.fits, package, fit_sha, seed)
                require(receipt is not None)  # Every checkpoint/logit frozen BEFORE GT.
                initial.setdefault(seed, set()).add(receipt['initial_parameter_sha256'])
                with np.load(args.fits/fit_sha/str(seed)/'fit.npz', allow_pickle=False) as archive:
                    predictions[fit_sha][seed] = archive['predictions'][package['test_ids']].tolist()
        require(all(len(hashes) == 1 for hashes in initial.values()))
        truth = _labels_from_original_graph(args.graph, _expected_graph_names(args.frozen_root))
        truth_test = [int(truth[i]) for i in package['test_ids']]
        scores = {fit: {seed: metrics(pred, truth_test) for seed, pred in seeds.items()}
                  for fit, seeds in predictions.items()}
        rows = {r['row_id']: scores[r['fit_sha256']] for r in package['rows'] if r['status'] == 'DRAFT_NOT_ADMITTED'}
        result = tables(package, rows)
        result['evaluator_source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        require('.local_artifacts' in args.output.absolute().parts)
        store = PrivateAudit(args.output); sha = store.write(result); require(store.read(sha) == result)
        if args.public_table:
            output = result['aggregate']
            fields = list(dict.fromkeys(k for row in output for k in row))
            buffer = io.StringIO(newline=''); writer = csv.DictWriter(buffer, fieldnames=fields)
            writer.writeheader(); writer.writerows(output)
            require(args.public_table.parent.resolve() == (Path(__file__).resolve().parents[3]/'reports').resolve())
            exclusive(args.public_table, buffer.getvalue().encode('utf-8'))
        print(json.dumps({'result_sha256': sha, 'scored_seed_fits': len(scores)*10,
                          'status': 'COMPLETED_EXPLORATORY_NOT_INDEPENDENT'}))
        return 0
    except Exception:
        print('{"status":"FAIL_CLOSED_NO_METRICS_CLAIM"}', file=sys.stderr); return 1


if __name__ == '__main__': raise SystemExit(main())
