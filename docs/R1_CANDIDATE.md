# R1-candidate v1: prospective offline risk ranking

Status: `RECONSTRUCTED`, not recovered historical R1, not semantic evaluation.
Implementation: `sara3/r1_candidate.py`; version `sara.router.r1_candidate.v1`.
Standalone diagnostic command only; existing runtime router defaults and callers
remain unchanged. No reviewer files, verifier outputs or correctness data are inputs.

## Evidence and historical boundary

Historical secondary specification: owner-supplied `SARA3_ROUTING_SPEC.md`,
sections1–4; SHA256
`a93f13023a55b934e4a764fc3937e7b80bea4b29d54a395f80a0847f2db7f120`.
See also `HISTORICAL_P0_ARM_CONTRACTS.md` and `manifests/historical_p0.json`.
Reports establish design intent, not recovered executable source.

| Element | Evidence / implementation status |
|---|---|
| Cora seven canonical classes, frozen140 sensitivity cohort, budget37 | Reported historical constraint; current nine hash-pinned inputs independently admitted |
| GT-free class-aware risk, possible referral of confident agreements | Historical intent preserved; no quota or mandatory agreement selection |
| Historical three risk proxies | Names, formulas, weights and normalization MISSING_EVIDENCE; new three-term design below |
| Historical Class Atlas and49-cell Jaccard matrix | Exact vocabulary/tokenizer/matrix MISSING_EVIDENCE; existing reconstructed Atlas reused unchanged; historical matrix not recreated |
| Historical R1 thresholds, quotas, ties, full selected IDs | MISSING_EVIDENCE; no equivalence claim from aggregate counts |
| Current R0 / Semantic-v0 | Preserved unchanged; themselves reconstructed, not exact historical implementations |
| R2 fusion / quota | MISSING_EVIDENCE; NOT_IMPLEMENTED in this slice |
| Historical P0 groups / six-node seals | Preserved; never reselected from this new router |

## Prespecified formula

Use the existing Atlas `semantic_support`: lowercase ASCII word tokens, set
intersection with four keywords per class. Repetition does not increase support.
Let `h[c]` be its hit count, `m=max(h)`, `s` the second-largest count including
ties, and `a,b` the frozen B1/Narrative class indices.

- `D = 1[a != b]`: candidate disagreement, range0..1, higher means more review risk.
- `M = 1 - (h[a]+h[b])/(2*m)`: relative candidate mismatch, range0..1.
  Averaging treats both arms symmetrically; identical candidates count once in effect.
  Zero means both match maximal lexical support; one means neither has a hit.
- `A = s/m`: cross-class lexical ambiguity, range0..1. Zero means a unique
  lexical topic with no runner-up; one means a tie for maximal support.
- If `m=0`, set `M=A=1` with `NO_ATLAS_KEYWORD_MATCH`. Missing text follows this
  same explicit uncertainty policy. This does not mean the candidates are false.
- `risk=(D+M+A)/3`, range0..1. No confidence, neighborhood, similarity-matrix,
  reviewer, verifier, or correctness term is used.

Equal `1/3` weights are prespecified ignorance defaults after bounding each term:
no component is privileged without evidence. They are neither fitted nor optimal.
Normalization uses each article's strongest lexical class, avoiding text-length
and repeated-word scaling. It remains a crude lexical proxy, not entailment,
primary-topic interpretation, calibrated error probability, or L2 support.

Rank by descending exact rational score (`Fraction`), then ascending integer node
ID. Return exactly37 unique nodes; fewer than37 or duplicate IDs fail explicitly.
Input order cannot change selection. Float exports are descriptive, never ranking
inputs. No weights/quotas were adjusted after diagnostics. Historical HH/error
counts, E0/E1, GT and verifier outcomes were not used for design or selection.

## Reproduce without private review material

From an installed clean checkout with the nine documented authenticated JSON inputs:

```powershell
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.router_comparison --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --output .local_artifacts/router_comparison_new.json
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_r1_candidate.py -v
```

Output must be a new path; the command refuses overwrite. No graph pickle, raw
response, private review file, live transport or model is read/executed.
`reports/r1_candidate_comparison.json` records all ranked selections, pairwise
overlaps, all140 risk components, native and common R1-score distributions, nine
input hashes and Atlas hash. Native R0/Semantic scores have different scales;
compare common R1 distributions only as descriptions, not accuracy measures.

## Executed descriptive results

| Router | Selected | Disagreement | HH agreement* | No keyword match |
|---|---:|---:|---:|---:|
| Current R0 |37|9|0|11|
| Current Semantic-v0 |37|9|11|6|
| R1-candidate v1 |37|7|15|30|

*HH here means agreement with both frozen confidence>=80: a reconstructed
descriptive convention, not a verified historical HH definition or accuracy label.
R1's other15 selected records are non-HH agreements.

Overlaps: R0/Semantic25, R0/R1-candidate17, Semantic/R1-candidate13.
R1 all140 score mean0.299603, median0.333333, range0..1; selected37 mean0.695946,
median0.666667, range0.583333..1. All30 zero-match articles are selected: the
maximal uncertainty default dominates much of this budget. This is an explicit
limitation, not evidence of error detection. Topic/method confusion, negation,
class imbalance and limited Atlas coverage remain unresolved. There is no
claim of historical selection equivalence, annotation accuracy or GNN gain.

Verification: focused8 and related60 tests passed (68 total). Initial sandbox run
had13 temporary-file permission errors; identical suite outside sandbox passed.
No human-review tests were run. Full repository regression suite not run because
this slice does not change runtime verification, arbitration, L2 or training.
Next smallest step: review this prespecified lexical/missing-evidence design
before freezing any prospective pilot selection. No live pilot is authorized.
