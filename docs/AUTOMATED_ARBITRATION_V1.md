# Prospective automated concordance arbitration v1

Version: `sara.arbitration.automated_concordance.v1`. Status: **experimental, opt-in, unvalidated**. Not historical Policy 002, and **not semantic L2**. No human review or second model is required to run this screen. A label provisionally accepted by the screen is **not** a scientifically verified correct label. No GT, correctness flags or E0/E1 outcomes enter routing, prompting or arbitration.

## Execution and strict boundary

Call `run_offline(..., response_version=RICH_VERSION, prompt_version=RICH_PROMPT_V2, automated_arbitration_version=VERSION)` using an explicitly offline fixture. Default ungated behavior is unchanged; `precomparison_l2_gate=True` remains available but cannot be combined with this automatic mode. Historical selection manifests are not accepted with the prospective policy.

1. Frozen B1 and Narrative labels/confidences are read-only and used by the Router. Selected nodes are processed blind before candidates are revealed.
2. The Blind response passes rich-schema L1 and is written to private audit. Abstentions and invalid responses do not dispatch Comparison.
3. The Comparison response sees only the two historical candidate labels and persisted Blind class; it also passes L1 and is saved. Both receipts are reread and L1 is recomputed before arbitration.
4. The automatic screen rejects invalid provenance, third-class proposals and Blind/Comparison class disagreements. It abstains on explicit counter-evidence, auxiliary-method warnings, uncertainty, primary-topic drift or absence of a common exact target-text supporting quote.
5. Otherwise the internal screen suggests **one of the B1/Narrative candidates**. Public per-node output uses `decision=PROPOSE`, `provisional_class_index` and `provisional_confidence_percent`. Crucially, `accepted=false`, `training_class_index=null` and `accepted_label=null` for *all* routed proposals. The historical frozen candidate confidence is retained as provenance, never as a calibrated verifier score.
6. Unrouted baseline behavior remains unchanged: only B1+Narrative agreement with both frozen confidences >=80 is retained; 80 is an explicitly reconstructed, uncalibrated default.
7. Per-node decisions and private audited phase receipts remain separate. The versioned report `sara.automated_arbitration_result.v2` exports `provisional_pseudo_labels` with `training_eligible=false`. `accepted_count`, `coverage` and `class_retention_counts` cover **only baseline training-eligible labels**. `provisional_count`, `provisional_coverage`, `provisional_class_distribution`, `routed_no_proposal_count` and `potential_coverage_if_experimentally_admitted` are separate diagnostics. No GCN training or live provider adapter is enabled.

L2 stays `NOT_ASSESSED` even for an internal screening `ACCEPT` / public `PROPOSE` outcome. `semantic_validation=NOT_PERFORMED`. This is **not** an L2 PASS. The policy is an automatic candidate-selection hypothesis for independent downstream evaluation, not a semantic verifier.

## Explicit controlled GCN-plan admission (opt-in, no training)

The existing `downstream.frozen.plan_from_frozen` continues to reject routed pseudo-label acceptance and never converts a public `PROPOSE`. The only new conversion path is `downstream.prospective.controlled_gcn_plan` using `sara.gcn.experimental_concordance_admission.v1`. The caller must explicitly supply the admission version, a separately pinned SHA-256 of the **complete unchanged offline report**, and a SHA-256 of frozen node IDs, B1/Narrative candidate classes and confidences in manifest order (`offline_report_digest` / `frozen_pair_digest`). These source hashes must be frozen *before* exploratory outcome assessment.

The adapter independently recomputes Router selection and unreferred high-confidence agreement (reconstructed >=80%, not calibrated). It verifies paired Blind/Comparison proposal metadata, unchanged L1 PASS and `L2=NOT_ASSESSED`, no third-class training, class candidate eligibility, report-level counters, missing/forged labels, and forbidden GT fields. It derives training labels itself rather than trusting `accepted=true` or public proposal arrays. It invokes only `gcn_plan` with fixed matched cohort/test complements. The resulting plan explicitly records `EXPERIMENTAL_LABELS_MATCHED_GCN_CONFIG`, source pins, provisional/baseline admitted IDs and `PLAN_ONLY_SEPARATE_APPROVAL_REQUIRED_FOR_GCN_TRAINING`. A Plan is **not** a training run; real GCN training still requires separate approval. The adapter currently requires offline reports (`provider_calls=0`); a live report contract and persistent rich-v2 Resume must be designed separately.

Example of plan creation only, after offline `report` and typed hash-admitted `pairs` exist:

```python
from llmgnn_sara.downstream.prospective import (
    VERSION, controlled_gcn_plan, frozen_pair_digest, offline_report_digest)
plan = controlled_gcn_plan(
    pairs, report, admission_version=VERSION,
    frozen_pairs_sha256=pre_registered_frozen_pair_sha256,
    report_sha256=pre_registered_report_sha256)
# Do not call train_gcn here.
```

The helpers calculate candidate digest values for independent pinning. **Computing a digest inside the same admission call without external review does not prove scientific approval.** This design is for controlled future comparison, not retrospective validation of the inspected Cora140 cohort.

## Research limitation

The Blind and Comparison are produced by the same verifier, and B1 and Narrative v0 also share an underlying LLM. Agreement is not statistically independent. A real but topically irrelevant quote may be repeated unchanged in both phases without any warning. This screen **cannot detect that silent semantic error** and must not be described as doing so. The `counter_evidence`, `auxiliary_method_warning` and `uncertainty_reason` checks only catch explicitly surfaced concerns, not latent ones. A keyword or fixed similarity score would not solve independent semantic entailment.

Before use as training-ready input, pre-register acceptance-risk and coverage limits, evaluate on independently held-out data not previously inspected in E0/E1, and approve the exact training admission adapter. Do not tune thresholds on the final test set.

## Scientific criteria allocation

| Signal | Location | Limitation / ablation |
| --- | --- | --- |
| Frozen candidate disagreement and confidence | R0 and unchanged unrouted baseline | Try routing-vs-baseline, avoid treating high confidence as truth |
| Public Class Atlas lexical proxy | Existing R1 variants | Keyword match is neither semantic validation nor semantic entailment; compare ablations |
| Frozen class frequency and minority retention | Offline evaluation | Compute per-class coverage, compare coverage-matched control; do not use GT frequencies at runtime |
| Graph neighborhood | Verifier request input (target text prioritized) | Compare with/without graph context, verify source IDs |
| Primary topic and auxiliary method | Rich response and automatic veto | Test topics drifting, explicit warning, incidental-method failure; silent errors remain |
| Supporting and counter evidence | L1 plus automatic veto | Exact-quote integrity separately from substantive relevance |
| Coverage loss and cost | Router analysis, reporting | Report accepted count, class distribution and added calls/cost; no cost-optimality inferred |
| Historical similarity matrix / Policy 002 exact thresholds | Not independently recovered | No historical reconstruction claim |

Prospective alternatives, not frozen winners: R1 v1/v2 and R2 candidate. Router choice and budget need a separate prospective freeze and independent evaluation.

## Offline verification

`python -B -m unittest discover -s tests -p 'test_automated_policy.py' -v`

`python -B -m unittest discover -s tests -p 'test_automated_arbitration_pipeline.py' -v`

`python -B -m unittest discover -s tests -p 'test_experimental_gcn_admission.py' -v`

`python -B -m unittest discover -s tests -p 'test_precomparison_l2_gate.py' -v`

`python -B -m unittest discover -s tests -v`

These are fixture tests, not provider calls, valid L2 results or an estimate of correctness. Real GapGPT dispatch and GCN training require separate approval, compatibility checks and a distinct versioned Runner.
