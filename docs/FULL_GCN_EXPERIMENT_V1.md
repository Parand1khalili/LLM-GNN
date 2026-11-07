# Full FeatProp / PS / WCE / Three-Agent GCN experiment v1

Date:2026-11-07. Base main `dcfc2fd8b8bb7d2360722ddec7fa724648cf2d60`;
remote main observed at77318. Existing P1/P2, routes, frozen labels, raw responses,
receipts, prior zero-switch findings and GraphScope work are unchanged.

## Primary-source reconciliation

The [ICLR2024 paper](https://proceedings.iclr.cc/paper_files/paper/2024/file/862819c227b16f9af64dd6ad6cfdf275-Paper-Conference.pdf)
was read at sections3.2,3.4,3.5,4.1 and Table2. Section3.2 combines annotation-
difficulty estimates with active selection; FeatProp is distinct from C-Density.
Section3.4 filters confidence/diversity ranks using pseudo-label entropy;3.5
allows confidence-weighted CE. Section4.1 uses GCN, no validation, fixed short
training and three repeats. Table2 separately reports FeatProp, FeatProp-W,
PS-FeatProp and PS-FeatProp-W (Cora72.82,73.56,75.54,76.23 percent). These are
published reference results, not measurements of our different pipeline/cohort.

Exact authors' revision `1f60eedb1452cdd997be18b5dd932a02666ee57e` was fetched
read-only via official GitHub Contents API after browser cache failures. Nothing
was imported or executed. Five file hashes/blob IDs/URLs are preserved in
`manifests/llmgnn_upstream_audit_v1.json`; private source-evidence bundle
`6e4e39628cac9460e121772c091df04e30298896becd8adbfa6e4c261c293e92`.
AST comparison confirms recovered featprop_query and post_process equal the
upstream functions at that revision. Recovered research runners remain separate.

|Component|Authors' exact source evidence|Current implementation and classification|
|---|---|---|
|FeatProp|[active.py lines337-361](https://github.com/CurryTang/LLMGNN/blob/1f60eedb1452cdd997be18b5dd932a02666ee57e/src/helper/active.py#L337): normalized propagated features, Euclidean distances, FasterPAM medoids/cache; no GT in that function|Reuse frozen140-node manifest. Paper component, not difficulty-aware C-Density or a loss toggle; no reselection|
|PS|[data.py lines675-709](https://github.com/CurryTang/LLMGNN/blob/1f60eedb1452cdd997be18b5dd932a02666ee57e/src/helper/data.py#L675): conf+entropy reads data.y[train_mask] at679|Safe existing filtering/ps.py accepts explicit pseudo-classes/confidence only. Historical project reconstruction: sequential recomputation, fixed30 percent, node-ID ties, last-class guard. Not byte-exact upstream or every paper filtering option|
|Correctness filter|[data.py lines373-375](https://github.com/CurryTang/LLMGNN/blob/1f60eedb1452cdd997be18b5dd932a02666ee57e/src/helper/data.py#L373): wrong_mask compares pseudo-labels to data.y|Forbidden. No current selection, PS, admission or loss receives GT|
|WCE|[train_utils.py lines68-100](https://github.com/CurryTang/LLMGNN/blob/1f60eedb1452cdd997be18b5dd932a02666ee57e/src/helper/train_utils.py#L68): masked min-max confidence, mean(weight*CE), confidence mutated in place|Existing fixed confidence_weights retains min-max/mean mechanism, avoids mutation. Constant confidence ->ones is the explicit project convention; upstream constant branch leaves values unchanged. Not a claim of identical upstream behavior in that edge case|
|GCN|[nn.py](https://github.com/CurryTang/LLMGNN/blob/1f60eedb1452cdd997be18b5dd932a02666ee57e/src/models/nn.py), SHA5d00c347...4b9b, matches recovered model source|Reviewed class already reused; same two-layer64/dropout0.5 historical project configuration. Shared optimization loop, not another model rewrite|
|Evaluation|[main.py lines122-174](https://github.com/CurryTang/LLMGNN/blob/1f60eedb1452cdd997be18b5dd932a02666ee57e/src/main.py#L122): saves GT, normally substitutes pseudo-labels, restores GT for test; debug_gt_label can retain GT|Our training GraphInputs contains x/edges only; separate evaluator reads GT after all checkpoints/logits are frozen. Ten project seeds vs three paper repeats; no independent-test claim|

Upstream `oracle` also feeds oracle/noise-aware selection branches such as RIM;
the whole loader/main graph object must not be presumed label-free. Class count
is sometimes derived from GT as well. Current domain is the fixed seven-class
vocabulary. New matrix rejects GT/correctness fields and oracle/debug_gt_label/
filter_all_wrong_labels controls outright. No authors' general loader is called.
B1 is a local paper-inspired baseline, Narrative/SARA/Fusion are our research
extensions, and the LLM/provider differs. This is component-faithful comparison,
not an exact reproduction of Table2 accuracy.

## Two frozen confidence protocols

Both use genuine frozen source confidence only when the final class matches
that source. If both sources match, the frozen Fusion contract uses their minimum.
Third-class confidence remains null. Neither protocol changes P1/P2 labels.

`historical_confidence.v1`: historical project PS/weighting, only complete-
confidence cells. Missing confidence blocks WCE or PS. CE/noPS needs none.
Baselines' original PS parity is checked against both pinned historical selections.
The mechanism follows the paper, with the project-specific choices above.

`missing_confidence_aware.v1`: separate experimental extension, not paper-faithful:

- WCE: min-max over final retained *known* confidences; a constant known subset
  gives ones. Each unknown sample gets loss weight1 and explicit
  `UNWEIGHTED_MISSING_CONFIDENCE`, never a fabricated confidence. Empty known
  subset gives ordinary unit-weight CE. Reduction remains mean(weight*CE), not
  division by sum(weights). Unit1 can give unknown samples greater relative
  influence than normalized known samples; neutrality is not a safety guarantee.
- PS: unknown samples are `UNSCORED_PROTECTED`, never ranked or removed.
  Requested deletions=floor(0.30*number_of_scored_samples). Capacity=scored_count
  minus number_of_present_scored_classes; effective=min(requested,capacity).
  Keep at least one scored representative of each scored class, even if protected
  members also exist. Record requested/effective/shortfall, protected/removed IDs,
  and class distributions before/after. Existing derive_ps is reused unchanged.
  Protection can shift class distribution; it is not evidence of label validity.
- Zero/nonpositive scored PS confidence remains blocked, not relabeled missing.

Full rule SHA `cc7fd6102299c6d7c6dadb6b764906c39e144c7a5f055eba9e054195296442d8`.
Defaults were fixed without new GT access or outcome optimization. Preliminary
offline code-audit packages remain retained; final package was repeated byte-
identically before any new GT evaluation/training. No best-cell selection rule.

## Matrix and estimands

Seven original arms A/B/C/D/E/F/G correspond internally to A_B1, B_NARRATIVE,
C_BASELINE_FUSION, D_P1_r0, E_P2_r0, D_P1_r1_v1, E_P2_r1_v1. One final label
per node, never separate B1+Agent/Narrative+Agent pipelines. All combinations
are prepared together:2 cohorts x2 losses x2 PS x2 confidence protocols.

Per combination:7 Natural +7 all-arm Matched +42 pairwise Matched (21 pairs)
+4 coverage-matched no-Agent controls =60 rows. Total960. The seven-arm core
Natural/all-Matched portion is224 rows. `reports/full_gcn_matrix_v1.csv` contains
every row with requested columns; unexecuted metrics are empty, not zero.

|Confidence protocol|Data-valid drafts|Missing-confidence blocked|Undefined common-mask blocked|
|---|---:|---:|---:|
|Historical|174|48|258|
|Missing-confidence extension|480|0|0|
|Total|654|48|258|

All654 data-valid rows remain **NOT_RUN_BLOCKED_AUTHORIZATION**. Effective
graph/config/test/train IDs/order/classes/weights/runtime dedup gives187 specs,
or1870 seed fits. A/B/C are shared; equal P1/P2 fits and numerically identical
cross-protocol cells are referenced, not trained twice. No historical fit is
admitted from a score/name/seed alone. Runtime/source hashes are part of identity.

Natural noPS counts remain Primary135/135/89/114/116/103/103 and
Sensitivity140/140/93/118/120/108/108. In extension Natural PS:

|Arm|Primary protected /deleted /retained|Sensitivity protected /deleted /retained|
|---|---|---|
|A|0 /40 /95|0 /42 /98|
|B|0 /40 /95|0 /42 /98|
|C|0 /26 /63|0 /27 /66|
|D P1 R0|7 /32 /82|7 /33 /85|
|E P2 R0|7 /32 /84|7 /33 /87|
|F P1 R1|4 /29 /74|4 /31 /77|
|G P2 R1|4 /29 /74|4 /31 /77|

There was no guard-capacity shortfall on these authentic rows. PS counts are
the same for CE/WCE, before losses are evaluated. Per-class distributions and
protected IDs stay in the private package; these aggregates are GT-free.

Matched masks intersect the applicable Natural *post-PS* masks, then recompute
weights; no second filtering. Blocked members block their matching group.
All-arm89/93 noPS masks exclude Agent-added labels; R0 equals C there. Pairwise
masks are additional, not a replacement. Natural contrasts mix class/coverage;
WCE matched contrasts can also change weighting. No causal population claim.

Coverage controls preserve the exact Treatment post-PS IDs and use the prior
baseline-only agreement/higher-confidence/fixed-hash rule. Their own baseline
confidences are real; they do not independently filter again. Inherited Treatment
PS provenance is separate from control's zero deletion budget. This controls
coverage, not selection of the mask or possible weight differences. R0/R1 share17
routed nodes, so router results are dependent.

## Execution and provenance gates

Graph SHA9285c2af...f466 remains pinned; raw x384 and original10858 ordered edge
entries are read without pickle/y. Test is always complement2568 of all140;
excluded5/abstentions/PS removals never enter test. All-node features/graph are
transductive. Historical test was observed; no untouched holdout claim.

Original encoder execution/preprocessing/model-revision receipt remains absent.
New separate audit/approval contract explicitly supports
`LIMITED_PROVENANCE_EXPLORATORY`; it never changes unknown provenance to VERIFIED.
Old CE preflight, V1 admission and allow_training defaults stay restrictive.
The independent full-matrix adapter requires hash-bound owner approval of both
experimental admission and real training, limited feature provenance and the
historically observed test, plus the exact maximum1870 fits. Generated template
has every approval flag false. No owner approval is manufactured by preparation.

The local interactive confirmation additionally names the exact package SHA.
Before any fitting the CLI rebuilds labels/matrix from admitted frozen inputs,
checks source/environment equality, graph/PS hashes and approval. Training has
no evaluator import or GT parameter. Historical optimization loop is shared via
model._fit; explicit loss weights use a separately gated train_matrix_fit, not
a fake confidence slot or altered legacy weight reconstruction.

CPU, one Torch thread, deterministic algorithms, same seeds0..9,2 layers/64,
dropout0.5, Adam0.01/decay0.0005,30 epochs, no validation/early stopping, last
epoch are fixed. Numerical identity with historical GPU fits is not promised.

Each fit/seed writes exclusive fsynced intent before fitting. Final model arrays,
logits and predictions are frozen in private non-pickle NPZ, with SHA-bound
receipt,30 losses and initial/final parameter hashes. Complete receipts are
readback-verified, including ACL and checkpoint hash. A crash/partial artifact/
audit failure leaves an uncertain intent: no automatic retry. Repeated invocation
may reuse only verified completed exact fits; it stops on any unfinished intent.
All valid fits must complete and freeze before the separate GT-only process.
Initial parameter hashes must agree across fits for each seed before evaluation.

The evaluator reports fixed-seven-class Macro-F1 (0..1), Accuracy(percent), all
ten seeds, mean/population SD and explicit-reference paired deltas, including
loss/PS/protocol/mask contrasts and Agent-minus-coverage-control. Seed SD is not
independent annotation/dataset uncertainty. No current GCN measurement exists.

## Reproduce and request authorization

No API key or provider is involved. From repository root in PowerShell:

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_full_gcn.py -v
$common = @(
  '--fusion', '.local_artifacts/sara3_three_agent_fusion_v1/bc16870399416620ed67f8799ed9bd0f17c2b7cf3c5849b2debe93ac14d96c2c.json',
  '--fusion-sha256', 'bc16870399416620ed67f8799ed9bd0f17c2b7cf3c5849b2debe93ac14d96c2c',
  '--features', '.local_artifacts/sara3_correction_features_v1/e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe.json',
  '--frozen-root', '.local_artifacts/frozen', '--authentic-root', '.local_artifacts/authentic',
  '--graph', '.local_artifacts/gt_reference/cora_random_sbert.pt', '--output', '.local_artifacts/full_gcn_v1'
)
.venv\Scripts\python.exe -B -m llmgnn_sara.downstream.full_run prepare @common --public-table reports/full_gcn_matrix_v1.csv
```

Owner-local prepare and exact replay actually passed with network/torch.load/
both trainers forbidden. Final package5,045,245 bytes:
`c78ff16df921bfcd661ce7981c5467f31c243bd812466ce0bbca747be576d413`;
audit `11ff6f593c792dcadf8e955f2fef9da10784044246e94bf34cfda3f7ff62eb26`;
blank approval `aeb3d49b1d7acdc2b3d6b58ff5bf8c925218acf670e39a98fd657544afd719b0`.
CSV SHA `428a7da963cfde99b1086ca4fbeef1917f0db69ca03d6b28f1b968bc9efeef2f`.

Before training, obtain a separate explicit owner decision for that exact package,
limited-provenance use, experimental label admission and all1870 fits. The blank
template is not authorization. Only the owner should create a distinct private
`owner_training_approval.json` from the template and complete the approved flags.
Do not modify the original blank or any prior receipt. After that authorization:

```powershell
$package = 'c78ff16df921bfcd661ce7981c5467f31c243bd812466ce0bbca747be576d413'
$audit = '11ff6f593c792dcadf8e955f2fef9da10784044246e94bf34cfda3f7ff62eb26'
$approval = '.local_artifacts/full_gcn_v1/owner_training_approval.json'
$approvalHash = (Get-FileHash -LiteralPath $approval -Algorithm SHA256).Hash.ToLowerInvariant()
.venv\Scripts\python.exe -B -m llmgnn_sara.downstream.full_run train @common --package-sha256 $package --audit-sha256 $audit --approval $approval --approval-sha256 $approvalHash
# Only after ALL checkpoints/logits are frozen; explicit separate GT-only command:
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.full_gcn `
  --package ".local_artifacts/full_gcn_v1/$package.json" --package-sha256 $package `
  --fits .local_artifacts/full_gcn_v1/fits --graph .local_artifacts/gt_reference/cora_random_sbert.pt `
  --frozen-root .local_artifacts/frozen --output .local_artifacts/full_gcn_results_v1 `
  --allow-gt-evaluation --public-table reports/full_gcn_results_v1.csv
```

Changed code/environment produces different package/audit hashes and needs new
review, not silent approval reuse. Training/GT evaluation commands above were
NOT run. Private NPZ/labels/receipts/approval files stay ignored and ACL-restricted.
No API, human review or Drive modification. Current accuracy/F1/seed results are
NOT_RUN_BLOCKED; pseudo-label quality remains separate. User code and all older
scientific findings are preserved.

## Actual verification and reporting limits

- Focused8/8 synthetic tests PASS29.959s, including missing weights/PS protection,
  budget/guard, all matrix dimensions, matching, GT/oracle rejection, approval
  binding, default-deny training, crash/no-replay, checkpoint corruption, audit
  write failure and verified completed-fit reuse. Mock fitter never optimizes GCN.
- Full guarded suite558 tests,0 failures/errors,2 Windows skips,475.939s. Skips:
  POSIX mode semantics on Windows and native symlink creation permission; ZIP
  symlink rejection is tested. Private receipt
  `226750e5cddaaffe3a0f4ab7e6f680f358263b335b8d9a4ad346b7477a69c19f`.
- Separate synthetic full-results table/paired-comparison self-check passed;
  those illustrative numbers were not exported as real scientific results.
- Authenticated real matrix preparation/repeat passed with network, torch.load
  and both trainers blocked.14 original input artifacts byte-unchanged during
  initial preparation; final source pins and package readback verified. CSV hash
  verified independently; no private fit directory or real approval was created.
- Syntax, staged secret/sensitive-data and diff checks precede scoped main commit.
  Targeted Git attribute/index-byte verification preserves canonical CSV CRLF
  bytes across checkout; full_gcn_*.csv is exempt from text normalization so
  published SHA and owner-local rerun checks remain identical.
  GitHub CI result is reported only after actual remote readback. Private data
  are unavailable in CI; public CI cannot establish real Cora fit correctness.

Current limitation: optimizer execution on the authentic graph remains untested
because separate training permission is absent. Source/structural/mock tests do
not establish numerical GCN accuracy, performance, calibration or safe correction.
