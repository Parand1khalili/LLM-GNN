# Weighted Arbitration V2

Version `sara.arbitration.weighted.v2` is an automatic, exploratory shadow policy,
independent of unchanged Arbitration V1. Human reviews are neither read nor
required. A switch changes the experimental output label only; every decision
still has `training_eligible=false` and L2 `NOT_ASSESSED`.

## Fixed rule and support

`Score = 2P + N + Q + T - A - 2C - U`.
All observed terms are binary. Missing terms remain JSON null, contribute zero
numerically, and are never interpreted as observed negative or positive evidence.
At least one **observed** P=1 or N=1 is mandatory. Initial exploratory thresholds
are 3 for a historical candidate and 4 for a third class. These defaults were
fixed before scoring and were not changed after viewing scores or GT outcomes.

- Both original phases must be COMPLETED, L1 PASS, non-abstaining and agree on
  an integer class 0..6. Otherwise keep Narrative: invalid/missing phases yield
  `NO_VALID_AGENT_RESPONSE`; valid disagreement yields `KEEP_NARRATIVE`.
- Each router's seed pool contains only its unrouted frozen B1/Narrative
  agreements with both confidences >=80 (93 R0 /78 R1 seeds). The target is
  excluded from its own support. No GT, outcome, or Agent-proposed labels enter
  prototypes or neighborhood votes.
- P: unit-normalize existing SBERT embeddings, average class seeds and normalize
  the mean. Both Agent and Narrative prototypes need >=5 nonzero vectors.
  Agent cosine must be >=0.20 and exceed Narrative by >=0.05. Missing/scarce or
  zero-norm prototypes/target give UNKNOWN. No minority-class bonus.
- N: >=3 seed-labeled graph neighbors, induced density among all target neighbors
  >=0.10, Agent fraction >=2/3 and Agent count strictly greater than Narrative.
  Insufficient seeds/density give UNKNOWN. Density is a reliability gate, not
  evidence that a class is correct. This deliberately conservative definition
  has no inferred pseudo-labels outside the admitted seed pool.
- Q: at least one identical stored L1-valid supporting quotation shared by the
  phases. This reuses the frozen feature definition: literal quote identity,
  not semantic similarity. Decorative-equivalent variants may be undercounted.
- T: nonempty primary-topic strings match after strip/casefold. This is textual
  consistency, not semantic truth or an L2 judge.
- A/U: either phase explicitly reports auxiliary-method warning/uncertainty.
  C: either phase supplies counter-evidence, conservatively treated as unresolved;
  there is no invented semantic-resolution heuristic.

An agreed Agent class equal to Narrative is `KEEP_NARRATIVE`, never a correction.
Otherwise the support and score gates can yield `SWITCH_TO_AGENT`, including a
third class. No baseline file, original response, receipt or training mask changes.
Constants and definitions are pinned in `configs/weighted_arbitration_v2.json`.

The initial defaults are prespecified engineering hypotheses, not calibrated
probabilities: five seeds avoid a single-example prototype; cosine0.20 plus
margin0.05 require positive relative compatibility; three neighbors and a2/3
supermajority avoid single-neighbor decisions; density0.10 requires some local
connectivity. None is a proven reliability threshold. Restricting seeds to the
existing high-confidence agreements preserves their admission provenance but
can amplify baseline bias and leave graph support unavailable. Future changes
need a new version and independent evaluation, not optimization on this cohort.

## Input integrity and isolation

Runtime extracts only embedding storage32 and edge storage1 from the exact
SHA-admitted original Cora archive, without pickle, torch deserialization, or
decoding label storage. Hashing the entire archive does not decode GT. Reviewed
storage descriptors are fixed to this one artifact, not a generic .pt loader.
Finite vectors, dimensions, edge bounds, self-edges and symmetry are checked.
The separate evaluation process validates the report and recomputes decisions
before opening private GT with the existing trusted-source evaluator.

| Artifact | SHA-256 |
|---|---|
| Source feature freeze | `e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe` |
| Canonical config | `42dd9643094e94eb2db14595328f8b757c31dc62b737bede77ce69f53df48863` |
| Rule receipt | `c138d04ca0a6e72709a014ca9f42091c923e69983ffb0fbdf06e09abbaf56870` |
| GT-free scores | `56e485e635ac915d07a0bb1b8849f5beb9017bd6f1ca9028192a64de335c0417` |
| Separate GT-only outcomes | `4f909e83ff9ce6245f62b1ee7a2d4202c200100f9cab79f86d1e8db3d15f5451` |

All row-level data remain private under `.local_artifacts`. No source texts,
quotes, node-level GT, raw responses or human-review records belong in Git.

## Actual frozen results (2026-11-07)

`EXPLORATORY_NOT_INDEPENDENT`: 74 router observations,57 unique nodes,17 shared.
Router observations must not be treated as independent samples.

| Measure | R0 | R1 candidate v1 |
|---|---:|---:|
| Routed denominator |37|37|
| KEEP_NARRATIVE |27|24|
| NO_VALID_AGENT_RESPONSE |10|13|
| V2 switches / fixes / harms / net |0 /0 /0 /0|0 /0 /0 /0|
| V1 switches |0|0|
| Narrative correct -> experimental correct, selected cohort only |21 ->21|17 ->17|
| Agreed third-class candidates / switches |7 /0|4 /0|
| P observed positive / observed zero / unknown |5 /22 /10|4 /21 /12|
| N unknown |37|37|
| Blind abstentions |7|12|
| Low **or unavailable** neighborhood density |16|18|

Reasons R0: invalid10, no positive support7, unchanged15, below threshold3,
phase disagreement2. R1: invalid13, no positive support3, unchanged17,
below threshold3, phase disagreement1. Prototype sample scarcity affects3 R0
observations; other unknowns include unavailable Blind classes. N is unknown
throughout because seed-count/density requirements do not jointly pass; it is
not evidence against the proposed labels. Positive P is not a correctness claim.
Full-cohort experimental labels remain Narrative (101/140); no GCN accuracy was
measured. Synthetic positive tests establish that the rule permits genuine
experimental switches; they establish no scientific benefit.

No new Treatment plan is generated because the requested switch prerequisite
is false. Prior no-op plans remain intact. Training is `NOT_RUN_BLOCKED`:
separate admission/training authorization and split-contamination audit remain
required. No loss/class-balancing or threshold changes were introduced.

## Reproduction (owner-local PowerShell, no API key)

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_weighted_arbitration_v2.py -v
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.weighted_arbitration_v2 --features .local_artifacts/sara3_correction_features_v1/e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe.json --graph .local_artifacts/gt_reference/cora_random_sbert.pt --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --output .local_artifacts/sara3_weighted_arbitration_v2
# Separate process, AFTER the score freeze:
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.weighted_arbitration_v2 --report .local_artifacts/sara3_weighted_arbitration_v2/56e485e635ac915d07a0bb1b8849f5beb9017bd6f1ca9028192a64de335c0417.json --report-sha256 56e485e635ac915d07a0bb1b8849f5beb9017bd6f1ca9028192a64de335c0417 --features .local_artifacts/sara3_correction_features_v1/e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe.json --graph .local_artifacts/gt_reference/cora_random_sbert.pt --frozen-root .local_artifacts/frozen --output .local_artifacts/sara3_weighted_v2_outcomes
```

Existing NumPy is reused; no dependencies installed. Without NumPy the two graph
support tests skip explicitly; rule/evaluator validation tests remain executable.
Actual focused tests9/9 PASS. An initial sandbox temporary-file permission error
was resolved by rerunning with the required local filesystem permission.
Guarded full discovery:511 tests,0 failures/errors,2 platform skips,475.838s.
Skipped: Windows POSIX-permission case and OS symlink creation (ZIP symlink
rejection is tested). Network dispatch and actual private human-review directories
were blocked. Final focused9/9 also covers the two evaluator-integrity tests added
after full discovery began. AST checks3/3 and diff checks PASS. Full-test private
receipt: `364f45af0b1ae758432f992726958c8a7d276ce5cd4876775ce6d0be2432718b`.
GitHub Actions was not run for this unpushed commit; no CI success is claimed.
