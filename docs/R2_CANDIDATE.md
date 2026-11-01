# R2-candidate v1: prespecified prospective hybrid

Date: 2026-11-01. This design and sensitivity grid precede output comparisons.
Version: `sara.router.r2_candidate.v1`. Status: RECONSTRUCTED, not historical R2.

## Evidence boundary

Owner-supplied `SARA3_ROUTING_SPEC.md`, section4, SHA256
`a93f13023a55b934e4a764fc3937e7b80bea4b29d54a395f80a0847f2db7f120`, reports
the intent to combine disagreement/confidence sensitivity with class-aware risk
under37 referrals. Exact fusion, quotas, overlap handling, thresholds, ties and
the historical node set remain MISSING_EVIDENCE. Reported HH/disagreement counts
are not selection objectives, tuning inputs, or evidence of equivalence.
No lost historical source has been recovered by this implementation.

## Objective and primary allocation

Balance observable lexical risk, frozen-candidate disagreement/uncertainty, and
bounded exploration of missing Atlas coverage. Never average incompatible scores.
Use37 unique selections and three sequential strata:

1. **Unknown exploration4:** reserve `ceil(10% * 37)=4` slots for `NO_ATLAS_MATCH`.
   Ten percent is an explicit modest exploration default, not an estimated optimum.
   Rank eligible nodes by ascending SHA256 of the UTF-8 string
   `sara.router.r2_candidate.v1:explore:<decimal node ID>`, then ascending node ID.
   This is deterministic allocation, not a statistically random sample or a risk
   score. It does not use confidence, GT, historical errors or text-body hashes.
2. **Observed-risk17:** split the remaining33 slots as evenly as possible with
   frozen-candidate risk; give the spare slot to the newly investigated observed
   risk objective. Restrict to Atlas-matched nodes (`coverage>0`). Use existing
   R1-v2 order: observed risk descending, coverage descending, node ID ascending.
3. **Candidate-risk16:** among all remaining nodes use unchanged R0 order:
   disagreement/low minimum frozen confidence risk descending, node ID ascending.

Exploration first protects the limited coverage reserve. Observed risk second
protects its distinct contribution; candidate risk then spends its quota on
remaining cases. This priority is a normative prospective choice, not learned
optimal routing. It does not guarantee selection of every disagreement.

All stages skip previously selected IDs and scan the full eligible ranking until
their own quota is filled or their pool is exhausted. No shortfall is transferred
early. After all stages, fill any total shortfall from the remaining global R0
ranking. At least37 unique typed GT-free pairs are required; otherwise fail.
Empty text is unknown coverage, not evidence of an incorrect label. Invalid
annotations, duplicate IDs or mismatched class order fail through existing checks.
Never produce fewer than37 silently. Returned order is stage admission order,
not a globally comparable risk ranking. This is offline only; no runtime defaults
or pilot cohorts change.

## Prespecified sensitivity and diagnostics

Evaluate exactly five allocations `(unknown, observed, candidate)`:

- Primary `(4,17,16)`.
- Exploration sensitivity `(2,18,17)` and `(6,16,15)`; same balanced remainder rule.
- One-slot observed/candidate boundary transfers `(4,16,17)` and `(4,18,15)`.

Keep the exploration hash, all upstream scores and tie rules fixed. Do not choose
the best composition after outputs. Input reversal/repetition must preserve exact
results. Report all five selections, admission provenance, shortages/backfill,
overlap with primary, per-stage cutoff scores/coverage, tied blocks and the next
eligible node. Large ties expose arbitrary deterministic cutoff effects; they do
not establish accuracy. Compare all five existing/new router primaries: R0,
Semantic-v0, R1-v1, R1-v2, R2-candidate. Report37 IDs, pairwise intersections,
disagreement, descriptive HH (agreement/both confidence>=80, reconstructed),
unknown/partial/multi-keyword composition and score distributions separately.
No correctness, verifier outcome, L2 review, GT or training data enters selection.

## Limits and reproduction

The28-keyword Atlas remains a limited lexical proxy, not semantic validation.
Candidate confidence is self-reported, not calibrated error probability. Unknown
exploration is small and cohort/node-ID dependent. Unfilled exploration can be
backfilled from candidate risk;4 is a reserved admission target, not an upper
bound on total unknown cases. Stage order and quotas matter. No performance,
historical R2 equivalence, production freeze or pilot approval follows from
descriptive statistics.

```powershell
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.r2_comparison --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --output .local_artifacts/r2_comparison_new.json
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_r2_candidate.py -v
```

Output paths must be new. See `R2_CANDIDATE_RESULTS.md` and
`../reports/r2_candidate_comparison.json` for executed descriptive results.
