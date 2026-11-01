# Router robustness decision — review v1

2026-11-01. **GO for drafting a prospective experiment; no production/pilot
freeze, live execution, or scientific winner selection.** No router redesign.
Prespec: `ROUTER_ROBUSTNESS_SCOPE.md`; full diagnostics:
`../reports/router_robustness.json`. No GT, historical correctness, verifier
outcomes or human review records informed routing or recommendations.

## Implementation correctness: PASS

- Independent primary R2 reconstruction matches the unchanged production function
  exactly, including all four stage metadata records, cutoffs and overlap skipping.
- Primary allocation4 unknown/17 observed/16 candidate admits37 distinct IDs.
  Candidate stage skips21 prior admissions; no shortfall/backfill on this cohort.
- All24 prespecified seed/order cases preserve37 unique referrals and reproduce
  under reversed inputs. Exhausted pools/backfill also pass synthetic edge tests.
- Five-router comparison matches the previous report exactly. All use the same
  nine admitted JSONs, canonical class order and frozen140 sensitivity cohort.
  P0 and31+13 pilot seal members remain hash-verified unchanged.

| Router | Disagreement | HH agreement* | Atlas-unknown |
|---|---:|---:|---:|
| Current R0 |9|0|11|
| Semantic-v0 |9|11|6|
| R1-v1 |7|15|30|
| R1-v2 |6|20|0|
| R2-candidate v1 |9|9|10|

*Descriptive reconstructed convention: agreement and both confidence>=80.
These counts are not accuracy, historical equivalence, or winner-selection criteria.

## Selection robustness: seed effects limited here; stage order material

At fixed primary stage order, overlap with primary is34/37 for review-1,
33/37 for review-2 and34/37 for review-3. Thus three/four referrals change with
the arbitrary exploration hash. This does not invalidate budget/determinism,
but node-specific conclusions about the exploration cases are seed-dependent.

At primary seed, keeping each stage's own quotas:

| Order (U=unknown, O=observed, C=candidate) | Primary overlap /37 | Shared nodes changing admission stage |
|---|---:|---:|
| U/O/C (primary) |37|0|
| U/C/O |29|8|
| O/U/C |37|0|
| O/C/U |36|1|
| C/U/O |28|9|
| C/O/U |28|9|

Across the entire4-seed x6-order grid, overlap ranges25..37. The primary observed
boundary has13 exact risk/coverage ties and candidate boundary3 score ties;
candidate-first orders produce22 observed boundary ties. Full scenario admissions,
changed membership/attribution, cutoffs and next eligible IDs are recorded.
Stage order is therefore part of the algorithm, not interchangeable scheduling.
Do not select a favorable order/seed from these outputs. No statistical stability
threshold, generalization claim or performance conclusion was prespecified.

## Verifier/evidence contract: invariant; integration still incomplete

All140 targets have authenticated target text and neighborhood evidence. Legacy
and opt-in rich payload fingerprints, instructions, schemas and target/neighborhood
hashes remain identical per node across selections, evaluated separately by schema.
Blind inputs exclude frozen votes/confidence; comparison retains only its authorized
candidates and blind result. Different nodes naturally have different evidence.

Actual unchanged legacy runtime was exercised for all five selection sets using
test-only selection injection and temporary synthetic verifier/audit fixtures.
Common-node requests match byte-for-byte. Blind abstention suppresses comparison;
valid positive blind responses permit comparison. Failures/missing text remain
covered by the full regression suite. Reviewed fixture responses never become
accepted training labels. Fixture class0/quotes are not semantic observations.

Runtime accepts only `r0`/`semantic`; R1/R2 are standalone selectors. This review
does not integrate them or validate a provider transport. Current runtime iterates
cohort order, not R2 admission order.37 referrals do not guarantee equal calls,
tokens or cost: comparison is conditional. Rich hashes are checked separately;
the five-set actual runtime fixture check uses legacy schema, with rich behavior
covered by existing rich regressions. No schema/prompt substitution is implied.

## Prospective options and unresolved science

Proposed role-based set `sara.routing.experiment.v1-DRAFT` (not frozen):

- Control: `r0_current@dc08852ce918c9ac8ed91f97d6dcded2ed351e11`.
- Primary candidates: `sara.router.r1_candidate.v2` and
  `sara.router.r2_candidate.v1` with unchanged primary seed/order4/17/16.
- Exploratory ablations: Semantic-v0 at that same source checkpoint and
  `sara.router.r1_candidate.v1`. Keep them intact, not declared inferior by counts.

Minimum option: compare the control and two candidates with the same frozen
cohort, class mapping, verifier schema/prompt, conditional call rules and evidence.
Expanded option: include both ablations and report the prespecified seed/order
sensitivity separately. Choose scope/budget before execution, not from errors.
Actual error detection, calibration, class coverage/retention, cost and downstream
effects remain unknown. The Atlas is a lexical proxy; confidence is uncalibrated;
hash exploration is not an inferential random sample. Historical formulas remain
missing. L2 stays NOT_ASSESSED and arbitration is unchanged.

Next smallest slice: a separately reviewed offline experiment manifest and selector
adapter contract with fixed verifier inputs/protocol, request deduplication and
call-budget accounting. No new prompts, automatic L2 gate or live authorization.

## Executed verification

Focused6 PASS. Full Python unittest suite217 tests:216 PASS,1 SKIP in152.281s; skipped real
filesystem symlink creation because the Windows account lacks permission. ZIP
symlink rejection is tested. No failed checks. Nonblocking PyTorch deprecation
warning observed; no real training or untrusted model load executed.
Full-suite file-open/list guards deny the real private human-review session tree;
review-schema regressions use only temporary synthetic records. Network connections
were denied. No genuine human review was accessed. Syntax/import, report readback,
scope and staged credential-pattern/size checks also precede the local commit.
Unrelated GraphScope frontend checks were not run; its files remain unchanged.
