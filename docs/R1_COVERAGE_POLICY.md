# R1 missing-evidence policy review: prespecified design

Date: 2026-11-01. Design recorded before running the new comparisons.
All policies are prospective reconstructions, not historical R1 recovery.
Existing v1, Atlas, R0, Semantic-v0, frozen artifacts and pilot seals stay unchanged.
No human review files, GT/correctness or verifier outcomes are inputs.

## Interpretation and coverage

Reuse the existing case-insensitive ASCII-word set matcher without new vocabulary.
Let `h[c]` be distinct Atlas keyword hits, `m=max(h)`, `s` the runner-up count,
`D=1[a!=b]`, `M=1-(h[a]+h[b])/(2m)`, and `A=s/m` when `m>0`.
These are lexical proxies, never semantic entailment or probability of error.
Identical candidates and repeated tokens retain v1 behavior.

Coverage is independently observable:

- `NO_ATLAS_MATCH`: `m=0`; M and A are unobserved, represented as null in diagnostics.
- `PARTIAL_COVERAGE`: `m=1`; only one distinct keyword per strongest class.
- `OBSERVED_MULTI_KEYWORD_MATCH`: `m>=2`; multiple distinct lexical cues in at
  least one class. This is more observed vocabulary, NOT meaningful semantic
  approval. Inflections and auxiliary methods can still create spurious matches.
- `C=m/4`, range0..1: fraction of the existing four-keyword class vocabulary
  observed for the strongest class. C is not semantic completeness/confidence.

## Three policies, fixed37 budget

| Version | Ranking score | Secondary order |
|---|---|---|
| `sara.router.r1_candidate.v1` (original) | `(D+M+A)/3`; missing M=A=1 | node ID ascending |
| `sara.router.r1_neutral.v1` | same score; missing M=A=1/2 | node ID ascending |
| `sara.router.r1_candidate.v2` (two dimensions) | observed-risk `(D+I[m>0]*(M+A))/3` | C descending, then node ID ascending |

All scores rank descending using exact fractions. Neutral imputation is the
midpoint of the unobserved0..1 intervals, not an estimated expectation. In v2,
unobserved lexical terms contribute no *observed* risk; this does not assert
zero true risk. Keep M/A null and C separately available. A no-match disagreement
still receives D/3 and can be selected. No-match agreement has observed-risk0.
Coverage only breaks exact risk ties; it never boosts or subtracts risk.

**Prospective choice before outcomes:** recommend and implement v2 as a separate
offline router because missingness must not create positive evidence of mismatch
or ambiguity. Prefer greater observability within equal observed-risk scores,
without a coverage quota or assumed missing-value distribution. This is a design
principle, not a choice of whichever output has more HH/disagreements or stability.
It favors observable cases and can under-route unknown cases. Unknown-case
exploration would need a separately approved sampling objective, not hidden risk.
No runtime default, verifier, pilot or acceptance behavior changes in this slice.

## Prespecified sensitivity, not model selection

Run each policy with disagreement weight `wD in {1/2,1,2}`, holding both lexical
weights at1 and normalizing by `wD+2`. Primary uses wD=1 throughout.
For neutral only, also test missing imputation `{1/4,3/4}` with wD=1.
For v2 only, also test coverage tie order `none` and `low` with wD=1; primary is
`high`. Report all results, cutoff tie sizes and overlaps against each primary.
Do not choose weights, imputations or tie direction from outputs. v1 primary must
match the preserved original function exactly. No historical HH targets used.

## Diagnostics and limitations

For each setting record37 ranked IDs, zero/partial/multi coverage, disagreement,
HH agreements (both frozen confidence>=80: reconstructed descriptive convention),
score range/mean/median, cutoff ties and selected members of the tied block.
Record all pairwise set intersections and per-node coverage, scores, text token
counts, distinct token counts and keyword hits per1000 words. Compare length and
coverage using fixed ASCII-token bins0..128,129..512,513+; report mean/median
length by coverage and selection. These are associations, not causal effects.
Longer text gives more opportunities to hit the fixed28-keyword vocabulary;
set matching limits repetition effects but cannot eliminate length/topic bias.
No opportunistic Atlas expansion or primary-topic interpretation is introduced.

Reproduce (new output path required):

```powershell
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.r1_coverage --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --output .local_artifacts/r1_coverage_new.json
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_r1_coverage.py -v
```

The checked-in descriptive output is `reports/r1_coverage_comparison.json`.
