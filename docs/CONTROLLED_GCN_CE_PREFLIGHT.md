# Controlled GCN CE/noPS preflight v1

2026-11-07; base main `77318de944505f50205fc034c6927166c2cc4334`.
P1/P2, all older arbitration rules, routes, labels and scientific receipts remain
unchanged. This slice prepares data and schedules; it never admits or fits labels.

## Source and leakage audit

| Boundary | Finding | Limit |
|---|---|---|
|GT origin|Historical evaluation reads `y` from the original Cora graph pinned at `9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466`|No GT tensor was decoded in this slice; source identity does not independently authenticate the original dataset conversion|
|Current graph loader|Only admitted raw x/edge storages, no pickle or y; 2708x384 float32, 2x10858 int64 in original order; finite values and bounds checked|Full-graph feature/topology access is transductive, not access to test labels|
|Feature generation|Recovered `src/models/nn.py:sbert` names `all-MiniLM-L6-v2`; 384 dimensions are consistent|The original encoding execution/text-preprocessing/model-revision receipt is unavailable. Dimensional agreement is not proof of GT-free feature generation. This remains an explicit blocker|
|Frozen labels|B1/Narrative, class order, target IDs and R0/R1 source feature freeze are revalidated; final vectors recomputed|Historical confidence is not calibrated probability; no new pseudo-labels or GT features|
|Train/test|All train IDs are inside fixed140, test is complement2568; Primary exclusions/abstentions never become test|Disjoint masks do not establish statistical independence|
|Test observation|Recovered matched runner explicitly scores the2568 complement, checks prior results, and saves predictions|Test was historically observed. Historical tuning contamination cannot be excluded; no independent or confirmatory claim|
|Current training boundary|`GraphInputs` has x/edges/optional weights only; plan labels outside train are -1; separate evaluator receives GT|This is code/source audit, not a claim that unexecuted training passed|
|Historical fit reuse|No fit admitted for reuse|A historical score, model filename, matching seed, or graph hash alone is insufficient. Require exact train IDs/classes/order, test IDs, feature/edge bytes, loss/weights, architecture, optimizer, epochs, initialization, software/device and checkpoint/prediction receipts|

Pinned recovered source evidence (read as text, never imported/executed):

- `recovered_sources/src/models/nn.py`, SHA
  `5d00c347e5a6aa504de9bf8c5abbd6e084efa1302e004c142567b9dc364b4b9b`:
  GCN lines158-198; SBERT factory lines251-253.
- Primary PS runner
  `recovered_sources/experiments/matched_cora/featprop_downstream_primary_ps_selection_001/ps_selection_runner_source.py`,
  SHA `00f846cc3c53d5f3f42c12142129890bed56d98bb9d0c0d6da6eae3ccdd5b102`:
  lines176-216 prior test-result checks; 392-407 protocol; 509-514 graph without y;
  520-589 seed training then final test scoring.
- Sensitivity PS runner SHA
  `491a7ea84280030843294fcd506aae9d944d22087d047421995132eb4ffab5fe`.

Historical training contract remains two GCNConv layers, hidden64, dropout0.5
before each layer, normalized convolution, no BatchNorm, ReLU hidden, Adam0.01,
weight decay0.0005, 30epochs, last-epoch predictions, no validation/early stopping,
seeds0..9. The proposed new run uses CPU consistently; numerical identity with
historical CUDA fits is not assumed. Original feature order/edge multiplicity
must be preserved. Current backend code and installed environment versions are
hash-recorded in each private audit. Metrics will be test Accuracy and fixed-seven-
class Macro-F1, per seed, mean and population SD; paired deltas use identical
seeds and test IDs. Seed variability is not independent dataset uncertainty.

## Natural-mask schedule: seven arms, shared baselines

|Arm|Primary135 train count|Sensitivity140 train count|
|---|---:|---:|
|A B1|135|140|
|B Narrative|135|140|
|C Fusion without Agent3|89|93|
|D P1 R0|114|118|
|E P2 R0|116|120|
|D P1 R1|103|108|
|E P2 R1|103|108|

Primary135 is the proposed first run; Sensitivity140 is separately scheduled,
not silently pooled. Each has60 unique seed fits, not70: P1/P2 R1 have identical
effective CE specs and share fits. A/B/C each run once per cohort, never per
router. Exact-fit hashes cover graph/test/config/train order/classes/weights;
the execution package and source audit bind the common environment/source.
No historical checkpoint is reused. No accuracy, F1 or seed result exists yet.

## Separate estimands and coverage-matched no-Agent control

The existing all-arm matched mask has89 Primary /93 Sensitivity IDs. Both R0
class vectors equal C on that intersection. Those fits cannot measure the
effect of added Agent labels. Natural masks combine coverage and label effects.

New auxiliary control `sara.gcn.coverage_matched_no_agent.v1` is prespecified
before computing its outputs and without GT, not a replacement for C or P1/P2:

Rule SHA-256: `1c0be31c19ce9b7baac10a92de4e4677e052dfa0ddf733ce8aaf2a040da4c57f`.

1. Use exactly each Treatment's train IDs and their order.
2. If B1/Narrative agree, choose their class, with no80-confidence filter.
3. Otherwise choose the class with higher genuine frozen baseline confidence.
4. Equal confidence: sort the two class indices, then choose index
   `int(SHA256(version + ':' + decimal_node_id),16) % 2`.
5. No Agent prediction, graph support, GT or outcome enters that choice.

The choice uses uncalibrated confidence and is exploratory, not a claim that
higher confidence is more accurate. Coverage matching forces labels even where
C abstains; it is a separate control with separate admission approval. Same IDs,
features and loss remove label-count differences for each paired comparison.
Masks themselves were selected by Treatment, so this does not estimate an
unselected-population effect or establish an independent holdout.

Actual GT-free preparation: labels differ from Treatment at9 IDs for each R0
arm and6 for each R1 arm, in both cohorts. These are differences, not fixes/harms.
With optional controls, deduplication gives90 seed fits per cohort. Primary and
Sensitivity together would therefore cost120 natural or180 natural-plus-control
fits. Neither expanded scope nor any training is authorized by preparing it.

## Admission and stop conditions

Existing `downstream/fusion.py:admit` and `model.py:allow_training=False` remain
unchanged. The old admission checks an audit hash's syntax, not actual audit
content. The new `ce_preflight.validate_approval` additionally binds an actual
audit object to package/graph/test hashes, requires verified feature provenance,
explicit acknowledgment of the historically observed test, separate admission
and fresh real-training authorization. It does not call either admission or
training. Hashes bind content, not independently prove the truth of declarations.

Generated audits are `REVIEW_REQUIRED_NOT_AUTHORIZED`, feature origin remains
unverified, all training remains `NOT_RUN_BLOCKED`. Never flip these fields to
VERIFIED without supporting evidence. Before real training: obtain the encoder
generation provenance (or explicitly review a separately documented limited-
provenance experimental protocol), review the actual source audit, approve the
exact cohort/arm/seed schedule and experimental label admission, then explicitly
authorize real training. The coverage-control admission/execution path also
needs review; the current legacy adapter only admits the original seven arms.
No training runner or automatic permission bypass was added in this slice.

After those gates are satisfied, the reviewed execution sequence is: verify
package/audit/source/environment hashes; admit the exact natural rows; fit each
unique CE spec once for each seed0..9 without any GT object; privately freeze
initial/final parameter hashes,30 losses and final logits/predictions; only then
invoke a separate GT-only evaluation process on the fixed2568 IDs. Record metrics
for every seed and all arms, including unfavorable results; never select epochs,
seeds or policies by test outcomes. Each paired delta uses the same seed and test
IDs. Optional coverage-control30 fits and the separate Sensitivity60 fits require
their own explicit scope approval. No unfinished fit may be reused on a filename
or partial-output claim. Historical2568 evaluation remains exploratory even after
all implementation gates pass.

## Confidence for later WCE/PS

- CE needs no calibrated confidence and is the first comparison.
- Preserve historical PS ordering, confidence, class guard and tie breaks;
  FeatProp remains target selection, never a toggle.
- Third-class confidence remains unavailable. A baseline's confidence for a
  different class, self-reported confidence, quote overlap, class rarity or graph
  density is not an admissible substitute. Current affected WCE/PS plans stay blocked.
- A candidate-only complete-confidence subset could be a separately frozen
  sensitivity analysis, with changed masks and third-class exclusion disclosed.
  It cannot stand in for full-policy WCE/PS.
- Uniform unit weights are CE, not a successful WCE solution. Any hybrid weighting
  or revised PS missingness rule is a new protocol requiring separate approval;
  no such change is implemented or tuned here.

## Reproduce locally (no key, no training)

From repository root in PowerShell:

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_ce_preflight.py -v
$fusion = 'bc16870399416620ed67f8799ed9bd0f17c2b7cf3c5849b2debe93ac14d96c2c'
$grid = 'c7f51377905a7d5a224d86ef9342dfdf0430fa1ce518f22ccac6647bf227ca0e'
.venv\Scripts\python.exe -B -m llmgnn_sara.downstream.ce_preflight `
  --fusion ".local_artifacts/sara3_three_agent_fusion_v1/$fusion.json" --fusion-sha256 $fusion `
  --grid ".local_artifacts/sara3_three_agent_gcn_grid_v1/$grid.json" --grid-sha256 $grid `
  --features .local_artifacts/sara3_correction_features_v1/e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe.json `
  --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic `
  --graph .local_artifacts/gt_reference/cora_random_sbert.pt `
  --cohort primary --output .local_artifacts/sara3_ce_preflight_v1
```

Run separately with `--cohort sensitivity` for its plan. CLI prints only aggregate
counts/status/hashes. PrivateAudit writes content-addressed ACL-protected JSON;
rerun reuses verified identical content, never overwrites originals. No model
weights, GT arrays or article text are exported. Real owner-local preparation was
executed for both cohorts; all GCN metrics remain NOT_RUN_BLOCKED.

Package hashes: Primary
`303e43ac1c5fca6e13dc8185c9d0997d7f4bf0028c521c269b82c776e3b7bb9a`;
Sensitivity `18931fc9d06c91a8711ba19f4f69e398d0a5ef6741f21b948eebeedc070b9bd9`.
Audit hashes additionally bind code/environment and must be regenerated after
source changes. Private artifacts remain Git-ignored. No Drive backup or new
GitHub backup is claimed; user-managed push remains pending for this slice.

Owner-local source audits: Primary
`d72507082db1984a87a4cd46c579080be7ead3378a02ab2e40ed16362f4c6453`;
Sensitivity `b90219dacc40f8106c3070dda40806a64eaac678cad93c9bbd8f3959f6ba102f`.

## Executed verification

- Focused synthetic tests6/6 PASS (13.098s): seven-arm schedules, exact masks,
  deduplication, deterministic baseline-only controls, hash/GT corruption,
  authorization default-deny, real audit binding and public allowlist.
- Complete guarded Python suite550 tests,0 failures/errors,2 Windows skips,
  433.109s. Skips: POSIX mode behavior on Windows and native symlink creation
  privilege; ZIP symlink rejection remains tested. Private receipt
  `acd6dceef9f77fc16bc42902762b3e54f3ff102e79ca642d4ec394ba663d5d9c`.
- Initial sandbox run did not pass (543 counted tests,499 errors, including
  private ACL/temp-directory access failures); repeated with approved Windows
  filesystem permissions, not weakened tests. Failed run retained privately.
- Actual owner-local preflight and repeat PASS for both cohorts, with network,
  torch.load and train_gcn forbidden;15 input files byte-unchanged, package and
  audit readback verified. Four existing fusion/training source files unchanged.
- AST, scoped secret-pattern scan, registry JSON and diff whitespace PASS.
  Public CI success42393425961 applies to previous77318 only; no new CI result
  exists until this local commit is pushed. No real GCN fit or metric was produced.
