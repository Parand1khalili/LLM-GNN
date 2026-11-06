# Cora140 — isolated post-freeze GT-only accuracy audit

Status: **exploratory / post-hoc**; source labels never enter SARA-3
inference, R0 routing, Blind/Comparison verifier, Arbitration V1, or GCN
training. This tool is separate under \`src/llmgnn_sara/evaluation/\`.

## Why this evaluation

The frozen R0 Cora140 run has 37 routed nodes, 29 L1-completed comparisons,
seven Blind abstentions and zero Arbitration V1 proposals. L1 correctness,
Blind/Comparison agreement and rich evidence do not establish class accuracy.

GT-only scoring addresses an *additional* question: how often each frozen
classification matches the **original seven-class Cora node label**, which
itself is not a semantic L2 adjudication of excerpt interpretation.

## Exact reference, no substitution

The historical independent scorer in
\`recovered_sources/experiments/matched_cora/run_matched.py\` uses the trusted
graph \`cora_random_sbert.pt\`, its \`data.y\` tensor (2708 integer labels)
and \`data.label_names\` class-order identity. The historical runner lowercased the
original class strings for annotation WITHOUT changing class indices:
`Rule_Learning` became `rule_learning`. The isolated evaluator reads
`historical_wrapper.original_ordered_class_names` from the SHA-256-pinned
`preparation_receipt.json` and checks exact equality with the graph's raw
names. It also requires that lowercasing the original names equals the frozen
ordered class vocabulary. No reordering, label remapping or GT alteration is
permitted. This evaluation takes **only**
that original graph with pinned SHA-256
\`9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466\`.
It verifies the **entire graph file hash before any PyTorch deserialization**;
\`torch.load(weights_only=False)\` is used ONLY for the exact verified
historically trusted bytes. **Never use an unverified or internet-downloaded
\`.pt\` file**, or reexport from a new Planetoid class ordering. No caller
override for the known graph SHA is accepted.

Frozen closeout SHA-256 is
\`03625722e672f25acb1001b59a4f4a72dd18ab0286ddb9a58a402b73895a1abb\`.
The evaluator also reuses GT-free pinned input admission, the frozen
context/contract verification, and the final private report's 37 routed
decision reconciliation before reading any GT.

## Windows: run only with the already-present original graph

From repository root on the owner's Windows machine, after updating \`main\`:

\`\`\`powershell
$env:PYTHONPATH = Join-Path $PWD "src"
$env:PYTHONDONTWRITEBYTECODE = "1"
$py = ".\.venv\Scripts\python.exe"
& $py -B -m unittest discover -s tests -p test_cora_gt_shadow.py -v
if ($LASTEXITCODE -ne 0) { throw "GT-only synthetic tests failed" }

# Original, trusted local Cora .pt used for historical raw-accuracy scoring.
# Adjust this exact path ONLY to an already-held copy of the SAME original file.
$graph = "..\LLMGNN_data\cora_random_sbert.pt"
if (-not (Test-Path -LiteralPath $graph -PathType Leaf)) {
    throw "Original graph not found: locate existing cora_random_sbert.pt; DO NOT download or substitute."
}
$graph = (Resolve-Path -LiteralPath $graph).Path
$sha = (Get-FileHash -LiteralPath $graph -Algorithm SHA256).Hash.ToLowerInvariant()
if ($sha -ne "9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466") {
    throw "Original graph SHA256 mismatch — DO NOT score"
}

& $py -B -m llmgnn_sara.evaluation.cora_gt_shadow \`
    --frozen-root .local_artifacts/frozen \`
    --authentic-root .local_artifacts/authentic \`
    --run-root .local_artifacts/sara3_gapgpt_live_cora140_r0_4096_20261105 \`
    --gateway-config configs/gapgpt_rich_v2_output4096_proposed.json \`
    --graph-file $graph \`
    --score-root .local_artifacts/sara3_gt_shadow_score_v1
if ($LASTEXITCODE -ne 0) {
    throw "POST_HOC_GT_EVALUATION_FAIL_CLOSED"
}
\`\`\`

The score runs once locally, with no new API calls. It writes a
content-addressed, private JSON aggregate in
\`.local_artifacts/sara3_gt_shadow_score_v1/\` and prints **only aggregate
performance figures**. Do not place either the original graph or generated
private result in GitHub, Drive public exports, reviewer packs or API
messages. Output is read-only relative to historical journals, Freeze,
Blind Review Pack and decision records. Repeated runs with the same sources
reuse identical content hash, never overwrite existing bytes.

## Metrics and denominators

- The **full 37 routed** nodes are the denominator for coverage and
  correctness over all. B1 and Narrative v0 cover 37.
- Blind class coverage is **30/37** (seven Blind abstentions).
- Comparison class coverage is **27/37**: 29 L1-completed Comparisons
  include **two explicit Comparison abstentions**; another Comparison
  was rejected by L1 and seven were correctly omitted after Blind abstention.
- Selective accuracy is conditional on having a class prediction. Report it
  **alongside coverage** and correct-over-37; do not score abstentions as
  positive or silently exclude abstentions from all-37 results.
- For B1/Narrative vs Blind/Comparison, paired counts on their **shared
  predicted subset** distinguish both correct, only baseline correct
  (false correction), only verifier correct (correct correction), and
  neither correct. Also report changed-class count and net correct
  difference; denominators are explicit and may differ across comparisons.
- Report 11 first-veto Counter-evidence nodes, nine diagnostic Third-class
  nodes, 17 others, and the **seven** Third-class nodes where Blind and
  Comparison assigned the same class. All are exploratory subgroups.
- Per-true-class counts report support, coverage and correct predictions;
  no node ID, true-label vector or per-node correctness is emitted.
- The B1 and Narrative v0 outputs were generated with the same underlying
  LLM and must not be described as two independent votes.

## Scientific boundary

This is **not an independent test-set confirmation**: R0 selected a
nonrandom subset, earlier development investigations already examined
some Cora texts/GT, and post-hoc subgroup identification can bias
interpretation. Do not use these same GT labels to select/tune a new
Arbitration threshold or to support a confirmatory GCN improvement claim.
A new, untouched evaluation partition and predeclared policy are required
for such claims. Original Cora classes are operational reference labels,
not proof of semantic entailment, meaning, or reviewer agreement.

**No change to** the existing V1 Freeze, L1, policy, training admission,
reviewer packets, source journals, or receipts. No GCN or Human L2 is
executed by this scorer. The exact original graph file is not available
to GitHub CI, so CI exercises synthetic labels and fail-closed tests only.

## Safe failure diagnosis (no private payload output)

A failed run remains fail-closed. The CLI now emits a **fixed stage identifier**
along with `FAIL_CLOSED`; no exception text, traceback, node ID or truth label
is printed. Example: `{"status":"FAIL_CLOSED","stage":"GRAPH_CLASS_NAME_ORDER"}`.

- `SAFE_PATH_PREFLIGHT`: output paths or overlap restrictions rejected.
- `FROZEN_CLOSEOUT_READ`, `PRIVATE_FINAL_REPORT_READ`,
  `PINNED_PROJECT_INPUTS`, `FROZEN_CONTEXT_AND_SELECTION`,
  `FIRST_VETO_RECONCILIATION`: a frozen-source/selection/provenance gate failed.
- `GRAPH_PATH_OR_HASH`: graph path/file or SHA-256 rejected.
- `GRAPH_TORCH_DESERIALIZATION`: importing/loading the *hash-verified*
  historical .pt raised an exception. Check the local PyTorch/PyG environment;
  never modify the graph to silence it.
- `GRAPH_CLASS_MAPPING_PROVENANCE`: pinned original class-name metadata is
  missing or inconsistent with the frozen class index order.
- `GRAPH_CLASS_NAME_ORDER`: the raw graph names differ from the original-case,
  historical order (not an index permutation to repair).
- `GRAPH_LABEL_TENSOR_SCHEMA`: the graph lacks 2708 integer node labels
  covering all seven classes.
- `FROZEN_DECISION_SCORING`: decision/proposal/abstention alignment failed.
- `PRIVATE_RESULT_PERSISTENCE`: private audit directory or digest write/read
  failed.

A `torch.jit.script` **FutureWarning** is a library warning, not proof of any
one failing stage. Do not modify scientific pins or silently bypass GT gates.
After a failed run, the command may be re-executed with the same paths:
the scorer never alters frozen source files or existing content-addressed results.

### Owner-local diagnostic and correction (2026-11-06)

The recovered original graph passed its SHA-256 and PyTorch deserialization,
but the initial GT-only evaluator stopped at `GRAPH_CLASS_OR_LABEL_SCHEMA`.
The implementation compared the graph's original-case names directly with
lowercased frozen prediction names. The corrected evaluator verifies the
original-case order against the SHA-pinned historical preparation receipt and
requires the lowercase projection to preserve the exact frozen index order.
Synthetic positive and negative checks exercise this mapping; a real GT score
remains **unverified until the owner completes the Windows run**.
