# Router final robustness review: prespecified checks

Review version: `sara.router.robustness.v1`, 2026-11-01.
Production router code/defaults and historical artifacts will not change.
This public review specification precedes all new seed/order comparisons.

- Fixed authenticated140-node sensitivity cohort, canonical seven-class order,
 37 unique referrals per router. Recheck original R2 admission metadata against
  an independent review-only reconstruction using the existing ranking functions.
- Exploration seeds: `primary` (unchanged R2 key), `review-1`, `review-2`, `review-3`.
  Alternate keys hash UTF-8 `sara.router.r2_candidate.v1:explore:<seed>:<node ID>`.
  Labels are fixed before comparisons; do not choose a favorable seed afterward.
- Test all six permutations of unknown/observed/candidate stage order, keeping
  their own quotas4/17/16. Cross all four seed choices and all six orders:24
  scenarios. Backfill is always last using unchanged R0. These are review-only
  counterfactuals, not new deployable routers or changes to R2-candidate v1.
- Report primary overlap, membership/attribution changes, admissions, overlap
  skipping, shortfalls, cutoffs, ties and next eligible IDs for each scenario.
  No accuracy or prespecified statistical robustness threshold is claimed.
- Repeat/reverse input order. Compare the five fixed existing router selections,
  shared inputs, class order and budget without selecting a winner by outputs.
- Check canonical legacy and rich blind/comparison payload hashes for common
  nodes across selections; include target/neighborhood evidence hashes and fixed
  instruction/schema hashes. Rich remains opt-in, not a silently substituted
  prompt. Comparison uses the same blind-class placeholder for static comparison.
- Exercise unchanged runtime via test-only selection injection and temporary
  offline fixtures. Fixed node-ID modulo3 cases cover blind abstention, comparison
  abstention and positive-schema comparison; no fixture outcome informs routing.
  This is a wiring test, not integration of the new routers into runtime.
- Runtime currently accepts only `r0` and `semantic`. R1/R2 remain standalone
  selectors; actual future experiment adapters are NOT_IMPLEMENTED. Blind first,
  compare only after valid non-abstaining blind response; missing text/failure
  suppresses later calls.37 referrals does not imply equal calls/tokens/dollars.
- Run focused and full tests where feasible. Genuine private human-review session
  access is prohibited. Temporary synthetic review-schema fixtures may run in
  the regression suite; they are not real reviews or routing evidence. Enforce
  an open-file guard against the actual private human-review session tree.

Recommendations must follow experimental roles, not HH/correctness composition:
R0 is the confidence/agreement control; R1-v2 isolates observed-risk routing;
R2-candidate v1 tests a hybrid/exploration objective. Semantic-v0 and R1-v1 remain
fixed exploratory/ablation comparators. All are reconstructed prospective code,
not exact historical R0/R1/R2. Any future protocol freeze/transport requires its
own review; this robustness report cannot authorize a live pilot or choose a winner.
