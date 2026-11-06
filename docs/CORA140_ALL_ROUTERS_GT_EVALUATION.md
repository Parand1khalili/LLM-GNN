# All-router Cora140 — isolated GT-only retrospective comparison

Status: post-hoc exploratory evaluation, fixed 37 referrals from the same
140 frozen Cora papers. Never a live policy change, a prospective test,
a new model call or a GCN result.

## Router inventory

| Router | Implementation | Actual SARA-3 verifier outputs |
| --- | --- | --- |
| r0 | sara3.selection / R0 | YES: 37 frozen real Blind/Comparison reviews |
| semantic | sara3.selection / semantic-v0 | NO |
| r1_v1 | sara3.selection / R1-candidate v1 | NO |
| r1_neutral_v1 | sara3.r1_coverage / rank_policy(NEUTRAL) | NO, offline-only |
| r1_v2 | sara3.selection / R1-candidate v2 | NO |
| r2_v1 | sara3.selection / R2-candidate v1 | NO |

These R1 variants are documented reconstructions, NOT the exact
unrecovered historical R1. R2 is also a prospective reconstruction.

## Scientific questions answered for EACH router

Every route gets the **same original GT** only after completing its GT-free
selection. For 140 source nodes, 37 must be selected deterministically.

- B1 wrong, Narrative v0 wrong, either wrong, both wrong, and both
  agreeing on one wrong label: independently report population total,
  selected true errors, false alarms, missed errors, true negatives,
  selection precision, recall, and error prevalence.
- Number of frozen B1/Narrative disagreements, high-confidence
  agreements and GT class distribution within selected nodes.
- For every pair of the six routers: intersection, exclusives,
  true errors and shared false agreements captured by each.
- Owner-private 140-row table: original node ID, GT, both predictions
  and confidences, and separate selection flag/rank for EACH router.
- Existing real SARA-3 Blind/Comparison classes, validity, correction
  counts and Arbitration V1 outcomes ONLY for the 37 R0 nodes.
  Other routers are explicitly marked NOT_EXECUTED; overlap with R0
  is **not** relabeled as a real R1/R2 evaluation.

The existing single-router GT-only node journey is fully reused and
validated; no fabricated Agent answers or hypothetical admitted labels.

This experiment establishes error-detection power, NOT which alternative
router would yield the best final GCN. Routing criteria must not be
retuned on these observed GT outcomes and then called held-out results.

## Frozen trust and privacy

Source graph: exactly SHA256
9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466.
Source closeout freeze: exactly SHA256
03625722e672f25acb1001b59a4f4a72dd18ab0286ddb9a58a402b73895a1abb.
Private report, authentic inputs, historical class order and frozen
R0 selection must all validate. Graph is hash-verified before PyTorch
deserializes it; source receipts remain unchanged.

Outputs go to
.local_artifacts/sara3_all_routers_gt_v1/
as an owner-private content-addressed report, with SHA readback.
The terminal prints only aggregates plus SHA/relative path.
DO NOT upload the node-level file or put it in reviewer packets.
No API, human L2, routing changes, Arbitration changes, label
admission or GCN execution.

## Windows execution

From existing repository root and existing main branch:

1. Run git fetch origin main, then git merge --ff-only origin/main.
   Never reset; stop if local conflicts exist.
2. Set PYTHONPATH to the absolute src path and use .venv Python.
3. Run: python -B -m unittest discover -s tests -p test_cora_all_routers_gt.py -v
4. Verify original Graph SHA256 exactly equals the pinned digest above.
5. Run the following as one single PowerShell line, using your venv Python:

    & $py -B -m llmgnn_sara.evaluation.cora_all_routers_gt --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --run-root .local_artifacts/sara3_gapgpt_live_cora140_r0_4096_20261105 --gateway-config configs/gapgpt_rich_v2_output4096_proposed.json --graph-file $graph --audit-root .local_artifacts/sara3_all_routers_gt_v1

6. Require exit code 0 and status ALL_ROUTER_GT_AUDIT_VERIFIED_PRIVATE,
   then compare SHA256 of output <audit-root>/<relative_path> to
   <artifact_sha256> in the printed JSON.

The property aggregate.GT_only_routing_accuracy holds all six
comparisons; aggregate.pairwise_selection_and_error_capture holds
15 pairwise comparisons; aggregate.real_R0_verifier_only is the
existing R0 real Agent result; non-R0 Agent results are NOT available.
Review full per-node rows only privately. Do not send the private
file or automatically run the Agent or GCN for other routers.
