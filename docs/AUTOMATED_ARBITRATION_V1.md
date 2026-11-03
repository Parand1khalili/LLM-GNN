# Prospective automated concordance arbitration v1

Version: `sara.arbitration.automated_concordance.v1`. Status: **experimental, opt-in, unvalidated**. Not historical Policy 002, and **not semantic L2**. No human review or second model is required to run this screen. A label provisionally accepted by the screen is **not** a scientifically verified correct label. No GT, correctness flags or E0/E1 outcomes enter routing, prompting or arbitration.

## Execution and strict boundary

Call `run_offline(..., response_version=RICH_VERSION, prompt_version=RICH_PROMPT_V2, automated_arbitration_version=VERSION)` using an explicitly offline fixture. Default ungated behavior is unchanged; `precomparison_l2_gate=True` remains available but cannot be combined with this automatic mode. Historical selection manifests are not accepted with the prospective policy.

1. Frozen B1 and Narrative labels/confidences are read-only and used by the Router. Selected nodes are processed blind before candidates are revealed.
2. The Blind response passes rich-schema L1 and is written to private audit. Abstentions and invalid responses do not dispatch Comparison.
3. The Comparison response sees only the two historical candidate labels and persisted Blind class; it also passes L1 and is saved. Both receipts are reread and L1 is recomputed before arbitration.
4. The automatic screen rejects invalid provenance, third-class proposals and Blind/Comparison class disagreements. It abstains on explicit counter-evidence, auxiliary-method warnings, uncertainty, primary-topic drift or absence of a common exact target-text supporting quote.
5. Otherwise it accepts **one of the B1/Narrative candidates, provisionally**, retaining the confidence supplied by that frozen candidate. It does **not** compute a calibrated new confidence, a semantic entailment score or an L2 grade.
6. Unrouted baseline behavior remains unchanged: only B1+Narrative agreement with both frozen confidences >=80 is retained; 80 is an explicitly reconstructed, uncalibrated default.
7. Per-node decisions and private audited phase receipts remain separate. The `provisional_pseudo_labels` export has `label_status=PROVISIONAL_UNVALIDATED_NOT_GCN_AUTHORIZED`; no GCN training or live provider adapter is enabled.

L2 stays `NOT_ASSESSED` even for an automatic `ACCEPT` outcome. `semantic_validation=NOT_PERFORMED`. This is **not** an L2 PASS. The policy is an automatic candidate-selection hypothesis for independent downstream evaluation, not a semantic verifier.

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

`python -B -m unittest discover -s tests -p 'test_precomparison_l2_gate.py' -v`

`python -B -m unittest discover -s tests -v`

These are fixture tests, not provider calls, valid L2 results or an estimate of correctness. Real GapGPT dispatch and GCN training require separate approval, compatibility checks and a distinct versioned Runner.
