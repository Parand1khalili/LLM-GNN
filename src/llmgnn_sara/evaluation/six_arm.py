"""Separately invoked GT-only scoring of a verified offline prediction freeze."""
import argparse
import csv
import hashlib
import json
import struct
import zipfile
from collections import Counter
from pathlib import Path

from ..annotation.six_arm_recovery import (
    ARMS, CONFIG, OUT, PIN, PROTOCOL, ROOT, SUMMARY, predictions, reconcile, snapshot)
from ..io.project import GRAPH_SHA256, load_project_inputs
from ..sara3.audit import PrivateAudit
from ..sara3.experiment import digest
from .cora_gt_shadow import _expected_graph_names, _labels_from_original_graph
from .homophily import measure

RESULT_ROOT = '.local_artifacts/six_arm_gt_evaluation'


def score(items):
    """items=(truth, prediction-or-None); missing is distinct from wrong."""
    matrix = [[0]*8 for _ in range(7)]
    for truth, pred in items:
        if type(truth) is not int or not 0 <= truth < 7 or (pred is not None and
                (type(pred) is not int or not 0 <= pred < 7)):
            raise ValueError('CLASS_DOMAIN')
        matrix[truth][7 if pred is None else pred] += 1
    total = len(items)
    correct = sum(matrix[c][c] for c in range(7))
    missing = sum(row[7] for row in matrix)
    accepted = total-missing
    classes = []
    for c in range(7):
        tp = matrix[c][c]; support = sum(matrix[c]); predicted = sum(row[c] for row in matrix)
        precision = tp/predicted if predicted else 0.0
        recall = tp/support if support else 0.0
        classes.append(dict(class_index=c, support=support, predicted=predicted,
            precision=precision, recall=recall,
            f1=2*precision*recall/(precision+recall) if precision+recall else 0.0))
    return dict(total=total, correct=correct, wrong=accepted-correct, abstained=0,
        unavailable=missing, predicted=accepted, invalid_prediction=0,
        all_target_accuracy=correct/total if total else None,
        coverage=accepted/total if total else None,
        selective_accuracy=correct/accepted if accepted else None,
        macro_f1=sum(c['f1'] for c in classes)/7, classes=classes,
        confusion_matrix_7x8=matrix)


def paired(truth, left, right):
    if set(truth) != set(left) or set(truth) != set(right):
        raise ValueError('PAIRED_ALIGNMENT')
    common = [n for n in truth if left[n] is not None and right[n] is not None]
    gain = sum(left[n] != truth[n] and right[n] == truth[n] for n in common)
    harm = sum(left[n] == truth[n] and right[n] != truth[n] for n in common)
    return dict(total=len(truth), common_complete=len(common),
        missing_left=sum(v is None for v in left.values()),
        missing_right=sum(v is None for v in right.values()),
        missing_either=len(truth)-len(common), improvements=gain, regressions=harm,
        both_correct=sum(left[n] == right[n] == truth[n] for n in common),
        both_wrong=sum(left[n] != truth[n] and right[n] != truth[n] for n in common),
        common_accuracy_delta_pp=100*(gain-harm)/len(common) if common else None,
        all_target_accuracy_delta_pp=100*(sum(right[n] == truth[n] for n in truth)-
            sum(left[n] == truth[n] for n in truth))/len(truth) if truth else None)


def validate_freeze(frozen):
    if (frozen['schema'] != 'sara.six_arm.partial_prediction_freeze.v1'
        or frozen['protocol'] != PROTOCOL or frozen['protocol_sha256'] != digest(PROTOCOL)
        or frozen['source_manifest_sha256'] != PIN or frozen['config_sha256'] != CONFIG
        or frozen['execution_summary_sha256'] != SUMMARY or digest(frozen['config']) != CONFIG
        or digest(frozen['records']) != frozen['request_response_manifest_sha256']
        or predictions(frozen['records']) != frozen['predictions']
        or digest(frozen['predictions']) != frozen['prediction_sha256']
        or snapshot(ROOT) != frozen['source_files']
        or digest(frozen['source_files']) != frozen['source_snapshot_sha256']):
        raise ValueError('FREEZE_VERIFICATION')
    for name, sha in frozen['implementation_sha256'].items():
        if hashlib.sha256(Path(__file__).parents[1].joinpath('annotation', name).read_bytes()).hexdigest() != sha:
            raise ValueError('IMPLEMENTATION_CHANGED')
    source = PrivateAudit('.local_artifacts/narrative_six_arm').read(PIN)
    if reconcile(source['requests'], frozen['config'], ROOT) != frozen['records']:
        raise ValueError('RECEIPT_REPLAY_MISMATCH')


def write_csv(path, rows):
    with Path(path).open('w', newline='', encoding='utf8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def figure(path, title, series, maximum, ylabel):
    """Standalone aggregate SVG; no extra plotting dependency is required."""
    from xml.sax.saxutils import escape
    colors = ('#246b8e','#b05b35','#56823a','#8750a0','#ba8520','#337c72')
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="470" viewBox="0 0 1000 470">',
           '<rect width="1000" height="470" fill="white"/>',
           f'<text x="50" y="28" font-size="19">{escape(title)}</text>',
           f'<text x="50" y="52" font-size="13">{escape(ylabel)}</text>']
    for tick in range(6):
        value = maximum*tick/5; y = 355-270*tick/5
        svg.append(f'<path d="M65 {y} H970" stroke="#ddd"/><text x="10" y="{y+4}" font-size="12">{value:.2f}</text>')
    width = 870/len(series)
    for i,(label,value) in enumerate(series):
        height = 270*value/maximum
        x = 75+i*width
        svg.append(f'<rect x="{x}" y="{355-height}" width="{width*.7}" height="{height}" fill="{colors[i%6]}"/>'
                   f'<text x="{x}" y="{345-height}" font-size="12">{value:.3f}</text>'
                   f'<text transform="translate({x},375) rotate(25)" font-size="11">{escape(label)}</text>')
    svg.append('</svg>')
    Path(path).write_text(''.join(svg),encoding='utf8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', required=True)
    args = parser.parse_args()
    frozen = PrivateAudit(OUT).read(args.freeze)
    validate_freeze(frozen)  # Everything above this boundary is GT-free.
    evidence = PrivateAudit('.local_artifacts/narrative_v1').read(
        '916ef67f164202861dfb16e7144ad99d28f82c84a71e9b4d3a110fa3d0a40900')
    pairs = {p.node_id:p for p in load_project_inputs('.local_artifacts/frozen', '.local_artifacts/authentic').pairs}
    byarm = {a:{r['node_id']:r['class_index'] for r in frozen['predictions'] if r['arm'] == a} for a in ARMS}
    ids = set(byarm['B1'])
    if any(set(v) != ids for v in byarm.values()) or ids != set(pairs) or ids != {r['node_id'] for r in evidence['rows']}:
        raise ValueError('TARGET_ALIGNMENT')
    graph = Path('.local_artifacts/gt_reference/cora_random_sbert.pt')
    if hashlib.sha256(graph.read_bytes()).hexdigest() != GRAPH_SHA256:
        raise ValueError('GRAPH_HASH')
    truth_all = _labels_from_original_graph(graph, _expected_graph_names('.local_artifacts/frozen'))
    truth = {i:truth_all[i] for i in ids}
    with zipfile.ZipFile(graph) as archive:
        values = struct.unpack('<21716q', archive.read('cora_random_sbert/data/1'))
    homophily, _, graph_info = measure(zip(values[:10858], values[10858:]), list(truth_all), 2708)
    historical = {'historical_B1':{i:pairs[i].b1.class_index for i in ids},
                  'historical_v0':{i:pairs[i].narrative_v0.class_index for i in ids}}
    groups = {s:[i for i in ids if homophily[i]['stratum'] == s]
              for s in ('homophilic', 'mixed', 'heterophilic', 'isolated')}
    groups['historical_joint_wrong'] = [i for i in ids if all(v[i] != truth[i] for v in historical.values())]
    groups['historical_other'] = sorted(ids-set(groups['historical_joint_wrong']))
    for low, high in ((0,0), (1,2), (3,5), (6,10), (11,2707)):
        groups[f'degree_{low}_{high}'] = [i for i in ids if low <= homophily[i]['degree'] <= high]
    neighbors = {r['node_id']:len(r['evidence']['neighbors']) for r in evidence['rows']}
    for k in range(5):
        groups[f'provided_neighbors_{k}'] = [i for i in ids if neighbors[i] == k]
    metrics = {a:score([(truth[i], v[i]) for i in sorted(ids)]) for a,v in {**byarm, **historical}.items()}
    comparisons = [('v1-A','v1-B'), ('v0','v1-A'), ('v1-A','v1-C'), ('v1-A','v1-D')]
    comparisons += [('B1', a) for a in ARMS if a != 'B1']
    paired_results = {f'{b}_minus_{a}':paired(truth, byarm[a], byarm[b]) for a,b in comparisons}
    strata = {g:{a:score([(truth[i], v[i]) for i in subset]) for a,v in byarm.items()}
              for g,subset in groups.items()}
    sample_metrics = {}
    for a in ARMS:
        sample_metrics[a] = {}
        for s in range(3):
            rows = {r['node_id']:r for r in frozen['records'] if r['arm'] == a and r['sample_index'] == s}
            # First choice per valid response, never a missing-sample substitute.
            from ..io.frozen import CLASSES
            sample_metrics[a][str(s)] = score([(truth[i], CLASSES.index(rows[i]['validated']['parsed'][0][0])
                if rows[i]['status'] == 'COMPLETED_VALID' else None) for i in sorted(ids)])
    costs = {}
    for a in ARMS:
        p = frozen['aggregate']['per_arm'][a]
        estimate = (p['recorded_input_tokens']*.10+p['recorded_output_tokens']*.50)/1e6
        costs[a] = dict(**p, estimated_usd_owner_unverified_rates=estimate,
            estimate_per_valid_prediction_usd=estimate/p['predicted'] if p['predicted'] else None,
            actual_billed_usd=None, limitation='includes recorded invalid response usage; ambiguous dispatch usage unknown')
    store = PrivateAudit(RESULT_ROOT)
    private_sha = store.write(dict(freeze_sha256=args.freeze, rows=[dict(node_id=i, truth=truth[i],
        predictions={a:v[i] for a,v in byarm.items()}, homophily=homophily[i],
        neighbors_provided=neighbors[i]) for i in sorted(ids)]))
    result = dict(schema='sara.six_arm.gt_only_evaluation.v1', freeze_sha256=args.freeze,
        protocol_sha256=frozen['protocol_sha256'], graph_sha256=GRAPH_SHA256, graph=graph_info,
        metrics=metrics, comparisons=paired_results, strata=strata, sample_metrics=sample_metrics,
        costs=costs, private_node_level_sha256=private_sha, historical_model_matched=False,
        evaluator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        limitations=PROTOCOL['limitations'], status='COMPLETED_EVALUATION_OF_PARTIAL_STRICT_FREEZE')
    sha = store.write(result)
    if store.read(sha) != result:
        raise ValueError('RESULT_READBACK')
    public = dict(result_sha256=sha, **result)
    Path('reports/six_arm_evaluation_aggregate.json').write_text(json.dumps(public, indent=2)+'\n', encoding='utf8')
    write_csv('reports/six_arm_metrics.csv', [dict(arm=a, **{k:v for k,v in m.items() if k not in ('classes','confusion_matrix_7x8')}) for a,m in metrics.items()])
    write_csv('reports/six_arm_paired.csv', [dict(comparison=k, **v) for k,v in paired_results.items()])
    # Public figures contain aggregate values only, never node positions or IDs.
    figure('reports/six_arm_accuracy.svg','Strict three-sample prompt ablation',
           [(a,100*metrics[a]['all_target_accuracy']) for a in ARMS],100,'Correct / all targets (%)')
    figure('reports/six_arm_cost.svg','Recorded usage cost estimate',
           [(a,costs[a]['estimated_usd_owner_unverified_rates']) for a in ARMS],
           max(c['estimated_usd_owner_unverified_rates'] for c in costs.values())*1.2,'USD; unverified rates')
    figure('reports/six_arm_homophily.svg','Post-hoc homophily strata',
           [(s+'/'+a,100*(strata[s][a]['all_target_accuracy'] or 0))
            for s in ('homophilic','mixed','heterophilic') for a in ARMS],100,'Correct / stratum targets (%)')
    report = ['# تحلیل آفلاین آزمایش شش Prompt در SARA-3', '',
        'LIMITED_PROVENANCE_EXPLORATORY / EXPLORATORY_NOT_INDEPENDENT', '',
        '## روش و حدود اعتبار', '',
        'هیچ API یا Training جدیدی اجرا نشد. Parser و رأی‌گیری تاریخی بدون تغییر استفاده شدند. فقط سه Sample معتبر امکان رأی دارند؛ یک یا دو Sample معتبر به Prediction تبدیل نشده‌اند. Tie با اولین ظهور در ترتیب Sample حل می‌شود. Confidence رأی‌گیری کالیبره‌شده نیست.',
        'موارد بدون Prediction به‌عنوان Wrong یا Abstention مدل گزارش نشده‌اند. All-target Accuracy برابر Correct/140 و Selective Accuracy برابر Correct/Predicted است. Confusion Matrix هفت ردیف و هشت ستون دارد؛ ستون آخر Unavailable است و در Recall کلاس، False Negative محسوب می‌شود. F1 کلاس بدون پیش‌بینی صفر تعریف شده است.',
        'تحلیل اصلی، اختلاف زوجی B−A روی اشتراک Complete-case است؛ اختلاف روی کل ۱۴۰ نیز جدا ثبت شده است. هیچ رأی‌گیری Partial یا تغییر Prompt پس از GT انجام نشد.', '',
        '## منشأ و Hashها', '', f'Prediction freeze: `{args.freeze}`',
        f'Protocol: `{frozen["protocol_sha256"]}`', f'GT evaluation: `{sha}`',
        f'Execution summary: `{SUMMARY}`', '',
        '## وضعیت درخواست‌ها', '', str(frozen['aggregate']['states']), '',
        'جزئیات هویت، Receipt، دلیل نامعتبر و Nodeها فقط در Freeze خصوصی نگهداری شده‌اند. مورد Ambiguous فاقد پاسخ ثبت‌شده است؛ هیچ پاسخ جدیدی ساخته یا دوباره درخواست نشد.', '',
        '## نتایج', '', '|Arm|Correct|Wrong|Unavailable|Coverage %|All-target Accuracy %|Selective Accuracy %|Macro-F1|',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for a,m in metrics.items():
        report.append(f'|{a}|{m["correct"]}|{m["wrong"]}|{m["unavailable"]}|{100*m["coverage"]:.2f}|{100*m["all_target_accuracy"]:.2f}|{100*m["selective_accuracy"]:.2f}|{m["macro_f1"]:.4f}|')
    report += ['', '## مقایسه‌های زوجی', '', '|مقایسه|Common N|Fix|Harm|Delta pp مشترک|Delta pp کل|', '|---|---:|---:|---:|---:|---:|']
    for k,v in paired_results.items():
        report.append(f'|{k}|{v["common_complete"]}|{v["improvements"]}|{v["regressions"]}|{v["common_accuracy_delta_pp"]:.3f}|{v["all_target_accuracy_delta_pp"]:.3f}|')
    best = max(ARMS, key=lambda a:metrics[a]['all_target_accuracy'])
    report += ['', '## تفسیر توصیفی', '',
        f'بالاترین All-target Accuracy مشاهده‌شده مربوط به {best} است؛ انتخاب پسینی بهترین Arm، شاهد تعمیم یا برتری قطعی نیست.',
        'v0→A هم نمایش و مقدار شواهد را تغییر می‌دهد؛ تغییر آن را نمی‌توان صرفاً به دستورالعمل نسبت داد. A/B/C/D همان شواهد را با دستورهای متفاوت دریافت کردند. مدل با Alias و Revision گزارش‌شدهٔ Provider ثبت شده است؛ مستقل‌بودن مدل زیرین اثبات نشده است. Historical B1/v0 مرجع‌اند و Model-matched با اجرای جدید معرفی نمی‌شوند.', '',
        '## Homophily، Degree و دادهٔ ناقص', '', '|گروه|N|B1 Correct|v0 Correct|A Correct|B Correct|C Correct|D Correct|', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for g,arms in strata.items():
        report.append('|'+g+'|'+str(arms['B1']['total'])+'|'+'|'.join(str(arms[a]['correct']) for a in ARMS)+'|')
    report += ['', 'Strata توصیفی و پسینی هستند؛ h>0.5 هموفیلیک، h=0.5 مختلط و h<0.5 هتروفیلیک است. Degree از همسایه‌های مستقیم یکتا و بدون Self-loop محاسبه شد. نمونه‌ها وابسته‌اند؛ آزمون معنی‌داری یا ادعای علی انجام نشد.', '',
        '## هزینه', '', '|Arm|Input tokens|Output tokens|Reasoning tokens|Estimated USD|USD/valid prediction|', '|---|---:|---:|---:|---:|---:|']
    for a,c in costs.items():
        report.append(f'|{a}|{c["recorded_input_tokens"]}|{c["recorded_output_tokens"]}|{c["recorded_reasoning_tokens"]}|{c["estimated_usd_owner_unverified_rates"]:.6f}|{c["estimate_per_valid_prediction_usd"]:.6f}|')
    report += ['', 'نرخ Input=$0.10/M و Output=$0.50/M موقت و تأییدنشده‌اند. Usage پاسخ‌های نامعتبر موجود نیز حساب شده؛ Usage و هزینهٔ درخواست Ambiguous نامعلوم است. Reasoning بخشی از Output است و دوباره حساب نشده است. Actual billed cost نامعلوم است.', '',
        '## محدودیت و تصمیم بعدی', '',
        'آزمایش کامل اعلام نمی‌شود؛ تحلیل Strict-partial با Missingness روشن برای پایان‌نامه قابل گزارش است. چهار پاسخ نامعتبر و یک Dispatch نامعلوم تاریخی حفظ شده‌اند. GT فقط پس از Freeze در همین Evaluator باز شد. سه Sample تکرار مستقل پژوهشی نیستند؛ Cora و زیرگروه خطاهای تاریخی قبلاً مشاهده شده‌اند. هیچ Prompt یا آستانه با این نتایج تنظیم نشد.',
        'برای تأیید، پروتکل ازپیش‌ثبت‌شده روی Cohort یا Dataset مستقل و مدل هم‌زمان نیاز است. هر API یا GCN آینده نیازمند مجوز مستقل است. این نتایج هیچ بهبود Downstream GCN را اثبات نمی‌کنند.', '',
        'جدول‌های Class-wise، Confusion، سه Sample و Strata در reports/six_arm_evaluation_aggregate.json و جزئیات Node-level فقط در .local_artifacts/six_arm_gt_evaluation هستند.']
    Path('docs/NARRATIVE_SIX_ARM_OFFLINE_RESULTS_FA.md').write_text('\n'.join(report)+'\n', encoding='utf8')
    print(json.dumps(dict(result_sha256=sha, metrics={a:{k:m[k] for k in ('correct','wrong','unavailable','all_target_accuracy')} for a,m in metrics.items()}, primary=paired_results['v1-B_minus_v1-A'])))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('GT_EVALUATION_BLOCKED: frozen proof, graph or alignment failure.') from None
