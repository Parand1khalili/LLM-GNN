# R2-candidate offline results

Executed2026-11-01 on the admitted140-node frozen Cora cohort. All algorithms
use37 slots. The specification/allocations preceded new output comparisons.
No production/pilot router or cohort is frozen by this report.

## Primary comparison

| Router | Disagreement | HH agreement* | Atlas unknown |
|---|---:|---:|---:|
|r0_current|9|0|11|
|semantic_v0_current|9|11|6|
|sara.router.r1_candidate.v1|7|15|30|
|sara.router.r1_candidate.v2|6|20|0|
|sara.router.r2_candidate.v1|9|9|10|

*Agreement with both frozen confidence>=80 is a reconstructed descriptive
convention, not a verified historical HH definition or correctness measure.

R2 overlaps with R0=27, Semantic-v0=26, R1-v1=17 and R1-v2=19.
All ten pairwise overlaps, five primary selections and per-stage cutoff records
are in `../reports/r2_candidate_comparison.json`. All five primary selections
and five R2 allocation scenarios reproduce under input reversal.

## R2 admission and sensitivity

Primary4/17/16 admits exactly4 unknown-exploration,17 observed-risk and16
candidate-risk records, with no shortfall or backfill. Candidate admission skips
21 already selected nodes. Ten total Atlas-unknown records include the four
explicit exploration cases plus six admitted through candidate-risk ordering.
Unknown is a coverage property, not an error classification.

Primary admission order (not a global risk ranking):

`1013, 1958, 1283, 1031, 722, 267, 682, 1120, 2291, 2396, 130, 1243, 653, 2319, 2487, 25, 47, 62, 972, 979, 1240, 637, 734, 351, 1528, 695, 2238, 2317, 2022, 27, 207, 357, 1559, 568, 2379, 1814, 614`

| Allocation U/O/C | Primary overlap /37 | Disagreement | HH* | Unknown |
|---|---:|---:|---:|---:|
|4/17/16|37|9|9|10|
|2/18/17|36|9|9|9|
|6/16/15|36|9|9|11|
|4/16/17|36|9|8|10|
|4/18/15|36|9|10|10|

All four prespecified allocation changes preserve36/37 primary selections.
This local stability does not validate the quotas or imply accuracy. The primary
observed-risk boundary has13 exact risk/coverage ties; candidate-risk boundary
has3 score ties. Node-ID ordering chooses within these blocks. The report records
the tied IDs and next eligible IDs for every scenario. Baselines also expose
budget36/38 boundary IDs; those are diagnostics, not altered router budgets.

## Verification and scientific limits

Eleven new focused tests plus80 relevant regressions PASS:91tests,7.913seconds.
Checks cover overlaps, pool exhaustion, backfill, exact37, hash collisions and
node-ID ties, separate score ordering, all allocations, GT counterfactual unread
fields, pinned authentic read allowlist, determinism and input immutability.
Prior R0/Semantic/R1-v1/R1-v2 selections match existing public reports exactly.
P0 pin and31+13 pilot seal members verified unchanged. Syntax/readback and scoped
credential-pattern/size checks are performed before the local commit.
No private human-review data/tests accessed; no API, GT evaluation or training.
Full repository tests not run; verifier/L2/arbitration/GraphScope are untouched.

The modest10% reserve, balanced remainder, stage priority and exploration hash
are normative prospective choices, not recovered historical R2 formulas.
No alternate hash-seed or stage-order sensitivity was tested in this slice.
Self-reported confidence is uncalibrated; lexical matching can confuse topic and
auxiliary method, and depends on text length/vocabulary. Deterministic exploration
is not a random sample with inferential inclusion probabilities. No performance
or historical-equivalence conclusion follows from matching any aggregate count.
Next: review this explicit exploration/exploitation objective and cutoff rules
before any separately authorized prospective protocol freeze.
