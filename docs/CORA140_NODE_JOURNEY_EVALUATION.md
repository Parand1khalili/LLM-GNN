# Cora140 GT-only node journey: R0 → SARA-3 → frozen decision

Status: owner-private, post-hoc, exploratory. No new API, GT in inference,
Arbitration V2, GCN training, admitted label or human evaluation.

## Scientific questions in the correct order

**Who selected the 37?** R0, not the third Agent. The original GT-free R0
ranks 140 frozen B1 and Narrative-v0 outputs by baseline class disagreement
and minimum confidence, and sends the 37 highest-risk nodes for review.
First assess the router against the original Cora reference labels, using
explicit oracle definitions: B1 wrong; Narrative wrong; either wrong;
both wrong; both agreed on the same wrong class; and baseline disagreement
(which is itself GT-free). Report TP/FP/FN/TN with denominators 37/103/140.
These are POST-HOC error-detection statistics, never a GT-informed router.

**What did the third Agent actually say?** For each selected node, the
owner-private report contains original node ID, R0 rank/score, original
B1 and Narrative classes and confidence, original GT class,
SARA-3 Blind and Comparison classes (or abstentions), first-veto reason,
and the correctness of each answer. For every one of the 140 nodes the
frozen policy's real final training class (or NULL), admission status and
GT correctness are recorded separately; zero reviewed SARA-3 nodes were
admitted. Unselected nodes remain in the 140-node owner-private report
with no invented verifier response.

**Did a proposed correction help?** For B1 and Narrative separately,
each predicted Blind/Comparison class is annotated as
CORRECTED_BASELINE_ERROR, DAMAGED_CORRECT_BASELINE, BOTH_CORRECT,
BOTH_INCORRECT or NO_CLASS_PREDICTION. The 37 reviewed nodes are
always the denominator; selective comparison denominators must be
reported separately. R0 selection and the actual V1 admissions are
distinct; the frozen V1 admitted ZERO of the reviewed nodes.

**What if Narrative were retained as a fallback?** An optional, fixed
descriptive contrast reports total correct classes among all 140
when a valid third-agent Blind or Comparison class replaces Narrative
on selected nodes only. This is NOT an implementable V1 label admission,
a tuned Arbitration V2, or a GCN accuracy claim. No GT is fed back.

## Integrity, storage and privacy

The evaluator verifies the immutable closeout and final private run,
authentic GT-free inputs, and the exact R0 37-of-140 selection BEFORE
loading any labels. The only GT reference is the original SHA-256-pinned
cora_random_sbert.pt; the seven class indices retain their historical
order through the SHA-pinned original-name mapping.

The full node-level report is written as a SHA256-content-addressed JSON
under .local_artifacts/sara3_gt_node_journey_v1/ using PrivateAudit
owner-only ACL/permissions. Its digest is verified on replay. The CLI
prints ONLY aggregate metrics plus the relative private path and SHA.
Never upload this private file, pass it to reviewers or commit it to GitHub.
No LLM/GCN calls, no changes to Journal, Freeze, receipts or decisions.

## Windows run (from the existing repository root)

    $env:PYTHONPATH = Join-Path $PWD "src"
    $env:PYTHONDONTWRITEBYTECODE = "1"
    $py = ".\.venv\Scripts\python.exe"
    & $py -B -m unittest discover -s tests -p test_cora_node_journey.py -v
    if ($LASTEXITCODE -ne 0) { throw "Synthetic node-journey tests failed" }

    $graph = (Resolve-Path -LiteralPath ".local_artifacts\gt_reference\cora_random_sbert.pt").Path
    $expected = "9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466"
    if ((Get-FileHash -LiteralPath $graph -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
        throw "Original graph SHA mismatch"
    }

    $out = ".local_artifacts/sara3_gt_node_journey_v1"
    $raw = & $py -B -m llmgnn_sara.evaluation.cora_node_journey `
      --frozen-root .local_artifacts/frozen `
      --authentic-root .local_artifacts/authentic `
      --run-root .local_artifacts/sara3_gapgpt_live_cora140_r0_4096_20261105 `
      --gateway-config configs/gapgpt_rich_v2_output4096_proposed.json `
      --graph-file $graph `
      --audit-root $out
    if ($LASTEXITCODE -ne 0) { throw "Node journey FAIL_CLOSED" }
    $summary = ConvertFrom-Json ($raw -join "`n")
    if ($summary.status -ne "OWNER_PRIVATE_NODE_JOURNEY_VERIFIED") {
        throw "Unexpected status"
    }
    $privateFile = Join-Path $out $summary.relative_path
    if ((Get-FileHash -LiteralPath $privateFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $summary.artifact_sha256) {
        throw "Private report hash mismatch"
    }
    $summary.summary | ConvertTo-Json -Depth 12

To see the 37 per-node rows locally, without sharing GT/private data:

    $owner = Get-Content -LiteralPath $privateFile -Raw | ConvertFrom-Json
    $owner.node_rows_owner_private |
      Where-Object r0_selected_for_review |
      Select-Object node_id,r0_rank,ground_truth_class_index,b1_class_index,narrative_v0_class_index,blind_class_index,comparison_class_index,narrative_to_blind,narrative_to_comparison,frozen_arbitration_reason |
      Format-Table -AutoSize

For GCN impact, a new predeclared GT-free admission policy and untouched
test partition are essential. Improvements in a few GT-matched labels do
not establish better GCN generalization.
