"""Render thesis figures from public aggregates only; no GT or private files."""
import csv
from html import escape
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((ROOT/'reports/final_cora_gcn_results.csv').open(encoding='utf8')))
for metric,sd,maximum,name in [('Accuracy','Accuracy_SD',100,'accuracy'),('Macro_F1','Macro_F1_SD',1,'macro_f1')]:
    height=140+36*len(rows);left=310;scale=610/maximum
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1140" height="{height}" viewBox="0 0 1140 {height}">',
         '<rect width="1140" height="100%" fill="white"/>',
         f'<text x="20" y="28" font-size="19">Final Cora GCN: {metric} (10-seed mean +/- population SD)</text>',
         '<text x="20" y="50" font-size="12">CE / noPS / Natural / Sensitivity140; exploratory, historically observed test</text>']
    for tick in range(6):
        value=maximum*tick/5;x=left+value*scale
        svg.append(f'<path d="M{x} 70 V{height-40}" stroke="#ddd"/><text x="{x}" y="{height-20}" font-size="12">{value:.2f}</text>')
    for j,r in enumerate(rows):
        value=float(r[metric]);err=float(r[sd]);y=80+j*36;x=left+value*scale
        color='#246b8e' if r['Arm'].startswith('current') else '#77818a' if r['Arm'].startswith('historical') else '#328468'
        svg.extend([f'<text x="12" y="{y+15}" font-size="12">{escape(r["Arm"])}</text>',
            f'<rect x="{left}" y="{y}" width="{value*scale}" height="22" fill="{color}"/>',
            f'<path d="M{x-err*scale} {y+11} H{x+err*scale} M{x-err*scale} {y+5} V{y+17} M{x+err*scale} {y+5} V{y+17}" stroke="#111" fill="none"/>',
            f'<text x="{left+maximum*scale+18}" y="{y+15}" font-size="12">{value:.4f} +/- {err:.4f}</text>'])
    svg.append('</svg>')
    (ROOT/f'reports/final_cora_gcn_{name}.svg').write_text(''.join(svg),encoding='utf8')
print('Rendered aggregate-only horizontal figures with seed SD error bars.')
