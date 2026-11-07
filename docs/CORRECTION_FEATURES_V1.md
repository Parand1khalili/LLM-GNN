# Frozen correction features and V1-equivalent shadow replay

Date: 2026-11-07. Status: **EXPLORATORY_NOT_INDEPENDENT**.
Implementation starts from main `8f880075dd6494efbb48912e757957634c93dea3`.

## Boundary and executed slice

`sara3.correction_features` imports no GT evaluator. It loads the nine pinned
GT-free input JSONs and replays every actual original/overlay receipt using the
existing context, effective request identity, wire hash, response hash, usage
binding and strict rich L1 validator. No prediction in a summary is trusted as
the Agent output. One rejected comparison per router remains rejected; no retry.
All journal rows must be accounted for, with 67 R0 and 62 R1 intents and zero
uncertain. Selection is unchanged R0/R1-v1, not a new router.

Schema `sara.correction_features.v1` records 74 `(router,node_id)` observations,
57 unique nodes, baseline classes/confidences and min/max/gap, phase completeness,
L1, abstention/class, support/counter counts, supporting-quote lengths, warnings,
uncertainty, normalized-topic digests, shared exact supporting quotes, candidate
membership and hypothetical class changes. Nested allowlists reject extra fields
including GT/outcome fields. Missing phase features are null, not false/zero.
Topic consistency is **string** equality after trim/casefold, not semantics.
V1 first-veto is a policy-dependent diagnostic, not an independent truth feature.

Feature table was frozen BEFORE invoking the separate GT process:
`e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe`.
The SHA reproduced on a second receipt replay. Private directory:
`.local_artifacts/sara3_correction_features_v1/`.

`evaluation.correction_outcomes` first admits that feature SHA/schema, THEN uses
the existing evaluator-only loader of the exact SHA-pinned trusted Cora graph.
That pre-existing loader uses trusted-graph Torch deserialization; no arbitrary
pickle is admitted. It is not imported/called by extraction or policy.
No GT or outcomes return to selection, features, arbitration or training.
Private outcome artifact:
`1501dac6d417511503cfb8a9a03bf3310beba6b6927ab956d9b1b131c668109c` under
`.local_artifacts/sara3_correction_outcomes_v1/`.
Only aggregate counts print; per-feature distributions and node-linked events
stay private, including potentially identifying topic-digest strata.

## Actual descriptive outcomes

Narrative to Blind; each router denominator is 37:

| Router | Fix | Harm | Both correct | Both incorrect | No class |
|---|---:|---:|---:|---:|---:|
| R0 | 7 | 6 | 12 | 5 | 7 |
| R1-v1 | 3 | 2 | 14 | 6 | 12 |

All B1/Narrative to Blind/Comparison five-category contrasts are in the private
result. Their counts reproduce the supplied thesis ledger. Ten fix and eight
harm events are router observations, not 18 independent nodes: selections share
17 IDs. No thresholds, classifiers, bootstrap or outcome-based tests were fitted.

Examples of feature associations (category count /37, then fix/harm within it):

| Observed feature category | R0: n, fix, harm | R1: n, fix, harm |
|---|---|---|
| Baselines agree | 28, 6, 4 | 30, 2, 1 |
| Blind/Comparison class agrees | 25, 4, 4 | 23, 2, 2 |
| Class-agreement unavailable | 10, 2, 1 | 13, 1, 0 |
| Blind auxiliary warning present | 31, 6, 5 | 26, 3, 2 |
| Blind counter-evidence count=1 | 17, 5, 1 | 6, 1, 1 |
| Primary-topic strings differ | 26, 4, 5 | 23, 2, 2 |
| Topic comparison unavailable | 10, 2, 1 | 13, 1, 0 |

These are descriptive conditional counts, not calibrated risk, causal effects,
independent semantic validation or a reason to remove vetoes. Abstentions remain
in the denominator; a completed Comparison abstention is distinct from missing
or L1-rejected Comparison. The private distribution records count, per-router
denominator, missingness category and all outcomes for each recorded scalar.

## Rule equivalence and no-op GCN plans

The proposed conservative rule has the **same eligibility predicates** as
`sara.arbitration.automated_concordance.v1`: both phases valid/nonabstaining,
same candidate class, shared exact support, matching nonempty topic strings,
no counter-evidence/warning/uncertainty, no third-class admission. Reuse V1;
do not create a duplicate V2. `KEEP_BASELINE` versus `SHADOW_PROPOSE` is a reporting
distinction for a passing candidate, not a relaxed rule. All 74 actual cases
abstain under this screen. L2 remains NOT_ASSESSED; admissions remain zero.

With zero eligible proposals, sanity Control/Treatment plans are byte-identical
per router, built with existing `gcn_plan` from unreviewed frozen agreement
admissions (>=80 reconstructed baseline rule, not a calibrated truth threshold):

| Router | Baseline training count | Same Control/Treatment SHA |
|---|---:|---|
| R0 | 93 | `6d77e475ad618ff020a50496300165ddaff22b23ca6313e75e20eedfea6bd47c` |
| R1-v1 | 78 | `2971e3cef839401d5d0f97f20aa802227479fb9bad0a95c14e7fb39ce39f4686` |

Plans use sensitivity140/test2568, CE/noPS, seeds0..9, historical two-layer64 GCN,
30epochs/dropout.5/lr.01/wd.0005/last checkpoint. They are **not** an approval to
train, a live-label admission adapter, or proof of independent test data. Actual
GCN: **NOT_RUN_BLOCKED_SEPARATE_TRAINING_APPROVAL**. The 140 labels are development;
the historical 2568-label test contamination audit is unresolved. Graph feature
integrity for training has not been newly established. No optimizer ran, no
accuracy/delta was measured, and duplicate no-op training would not demonstrate
the value of the third agent. The existing provider_calls==0 adapter is intact.

## Reproduction (owner-local, separate processes)

```powershell
$env:PYTHONPATH = Join-Path $PWD 'src'
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_correction_features.py -v
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.correction_features --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --r0-root .local_artifacts/sara3_gapgpt_live_cora140_r0_4096_20261105 --r1-root .local_artifacts/sara3_gapgpt_live_cora140_r1_v1_4096_20261107 --config configs/gapgpt_rich_v2_output4096_proposed.json --output .local_artifacts/sara3_correction_features_v1
if ($LASTEXITCODE -ne 0) { throw 'GT-free extraction failed; do not open GT' }
# Check the returned feature SHA independently before the next process.
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.correction_outcomes --feature-file .local_artifacts/sara3_correction_features_v1/e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe.json --feature-sha256 e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe --graph-file .local_artifacts/gt_reference/cora_random_sbert.pt --frozen-root .local_artifacts/frozen --output .local_artifacts/sara3_correction_outcomes_v1
```

Do not send private artifacts, GT events, raw receipts or text to GitHub.
No API key is required. Prior journals are read-only. Human reviews are untouched.

## Limits of this slice

Executed checks: **16/16 synthetic tests PASS** (18.249 seconds): five new
feature/outcome/isolation tests, eight V1 policy tests, and three existing
receipt-corruption/closeout regressions. Syntax and diff-whitespace checks PASS.
No full-suite rerun or GitHub Actions execution for the unpushed local commit;
CI remains pending owner-managed push. Real extraction/evaluation above are
reported separately from synthetic tests.

This is the first extraction/outcome/no-op vertical slice, not completed
confirmatory research. Supporting-quote lengths are recorded; counter-quote
lengths and readable topic strings are not separately materialized. No semantic
topic-equivalence heuristic, confidence intervals or private narrative case-study
report is implemented. No policy tuning follows from the observed associations.
Remaining work: stronger schema/failure-path integration coverage, broader
regressions/CI after owner push, test-contamination audit and any separately
approved admission/training study. Zero proposals is a valid current result.
