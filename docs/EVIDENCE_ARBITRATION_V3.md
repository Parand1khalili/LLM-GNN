# Evidence-only Arbitration V3 Shadow

Date2026-11-07; implementation starts from main443eed2ef8f1b2f11a4dfa6f3fe05a961a0dcb1e.
Version `sara.arbitration.evidence.v3` is automatic exploratory infrastructure.
Human review is excluded. V1, Weighted V2, direct-seed variant, frozen predictions,
requests, journals, L1 and training acceptance remain unchanged.

## 1. Bounded existing-label provenance inventory

Read-only local scope: admitted frozen/authentic manifests and their JSONs,
recovered-source manifest, existing parsed replay/PS lineage, and canonical
embedding/edge storages. No new Drive inventory or claim that inaccessible archive
files are missing. No graph-label/checkpoint decoding or human-review access.

The57 unique routed nodes have211 unique actual direct neighbors. Only1 neighbor
has mapped frozen B1/Narrative records;210 have no verified label source within
this local scope. Per router: R0 has138 distinct neighbors with1 mapped record;
R1 has132 with0. The one mapped R0 neighbor is an unrouted agreement below the
existing80-confidence threshold. Neither router has an admitted direct seed.

| Source | Mapping/provenance | Eligibility for additional neighbor labels |
|---|---|---|
| Frozen B1/Narrative |140 canonical IDs each; pinned hashes; explicit GT-free flags; existing approved baseline use|No eligible additional direct seeds|
|840 request references|Same140 targets, fixed prompts/model; references do not prove raw-byte recovery or generation timestamps|No new node mapping|
|Preparation receipt|created2026-10-18T21:02:49.367489+00:00|Preparation time is **not** response-generation time|
|Frozen prediction manifests|No independently established per-response generation times in inspected metadata|Insufficient provenance for new uses requiring those timestamps|
|PS / parsed replay|Derived from the same frozen target records|No additional labels|
|Recovered code|Source provenance, not executed predictions|No label source|
|Canonical y / GT diagnostics|Evaluation-only truth|Forbidden as pseudo-label source|
|Saved weights / unspecified caches|No qualifying additional GT-free prediction receipt established in this bounded audit|Not admitted; not executed/decoded|

Inventory decision: **STOP neighbor-label expansion**. No labels generated,
substituted or promoted. Existing authorized baseline use is unchanged; incomplete
generation metadata is not retroactively invented. In transductive experiments,
test-node features/edges can be allowed, but test GT is prohibited as a feature,
seed or tuning signal. Test-node pseudo-labels would require verified GT-free
generation, timestamps, canonical mapping, permitted payloads and independent
protocol authorization; being called a prediction is not sufficient provenance.

## 2. Prespecified rule and rationale

`Score = 2Q + 2T + P + N - A - 2C - U`.

- Both phases must be COMPLETED, L1 PASS, non-abstaining and agree on a class0..6.
- Each phase must have at least one authenticated L1-valid supporting quote;
  quote-length/count feature consistency is checked. The source is the pinned,
  receipt-replayed correction feature freeze, not unauthenticated summaries.
- Q: shared literal L1-valid target supporting quote exists. T: primary-topic
  strings match after strip/casefold. These existing definitions are unchanged.
- A: either phase's auxiliary warning is nonempty. C: either phase contains
  counter-evidence. U: either phase's uncertainty field is nonempty. Presence is
  conservatively penalized; semantic resolution is not inferred.
- P/N: unchanged optional frozen Weighted V2 features, each weight1. No P/N
  positivity gate. Null stays null and contributes0, including negative-weight
  missing terms; missingness is not observed support or observed absence.
- Initial thresholds:3 for historical candidates,4 for a third class. Equal
  Agent/Narrative class is KEEP, never a correction. A passing changed class is
  `SWITCH_TO_AGENT` in the experimental output only, `training_eligible=false`.

Engineering rationale, fixed before computing V3 outputs or connecting to GT:
shared evidence and consistent topic are the central positive signals (weight2
each); graph/prototype signals provide at most1 each and cannot pass alone.
One minor warning costs1; reported counter-evidence costs2. Candidate threshold3
permits one minor penalty with both textual signals; third-class threshold4
requires a stronger total. These are uncalibrated exploratory defaults, not
probabilities or safety guarantees. Both paths can switch with P=N=UNKNOWN when
Q=T=1 and no penalties. No threshold search, alternative-weight sweep, or
post-outcome adjustment was performed.

L1 proves quotation/provenance consistency, not claim support. T is literal
textual consistency, not semantic equivalence. Nonempty warning strings are not
independently verified warnings, and counter-evidence presence does not prove a
material unresolved contradiction. V3 deliberately reuses these frozen proxies;
it neither invents an L2 judge nor relabels them as validated semantic evidence.
L2 remains NOT_ASSESSED; no automatic training/admission gate is enabled.

## 3. Actual frozen outcomes

| Measure /37 each | R0 | R1-v1 |
|---|---:|---:|
|NO_VALID_AGENT_RESPONSE|10|13|
|KEEP_NARRATIVE|27|24|
|Valid agreed proposed changes below threshold|10|6|
|Same class as Narrative|15|17|
|Phase disagreement|2|1|
|Switch / third-class switch / fix / harm / net|0 /0 /0 /0 /0|0 /0 /0 /0 /0|
|Switch coverage|0/37|0/37|

V1, Weighted V2 and the direct-seed variant also retain0 switches/fixes/harms/net.
The separate GT-only process replayed their validated frozen decisions and V3
after the V3 freeze. Selected-cohort correct labels remain21/37 and17/37; the
140-node label vector remains Narrative (101/140). No GCN accuracy was measured.
For V1 the evaluator compares its proposed-label vector with Narrative fallback
where no proposal exists. Its projected KEEP labels are comparison bookkeeping,
not a reinterpretation of the original V1 ABSTAIN actions or training admissions.

All10/6 agreed changed candidates have both a nonempty A field and C items.
Shared Q is positive8/10 and3/6; literal T is positive1/10 and0/6. Their fixed
score distributions are R0 {-3:2,-2:1,-1:3,0:3,1:1}; R1 {-3:3,-1:1,0:2}.
No graph-support requirement is responsible for these V3 KEEP decisions.
These diagnostics were computed after the score freeze; they did not modify it.

`EXPLORATORY_NOT_INDEPENDENT`:74 router observations,57 unique nodes and17 shared;
do not pool them as74 independent samples. Small, selected, post-hoc data and
same-underlying-model phase dependence preclude independent validation or safety
claims. Zero switches means no correction coverage, not proof that no useful
Agent correction exists. No accuracy confidence interval or superiority test is
claimed. No Admission, GCN plan/training, API or review was performed.

## 4. Private provenance / reproduction

| Artifact | SHA-256 |
|---|---|
|Bounded label inventory|`8cfbbca6c7128588b595c9a5a03f9ad939778c1ca27c169f52e9dc142245970a`|
|Unchanged features|`e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe`|
|Unchanged Weighted V2|`56e485e635ac915d07a0bb1b8849f5beb9017bd6f1ca9028192a64de335c0417`|
|Unchanged direct-seed variant|`71c9b21516f18b7bf16d2f6f6e773a7a0168aca6e1c488fb66641c013765a64b`|
|V3 contract, before scores|`ff13e8719a2abc1e0baa2dedb87c0d7d02de1a3f5bfcd3737b8f125920382e92`|
|V3 GT-free score freeze|`ac1842e6456cbda58379b214977fc5a6a5ea07da04833f47bceb6cfccbf2cbe4`|
|Separate GT-only evaluation|`348a3d49e35dac90c0b6c19ac75bd9cbab78c68df601ec56accb48b399e0e221`|

Private directories: `.local_artifacts/sara3_neighbor_label_provenance_v1`,
`sara3_evidence_arbitration_v3`, `sara3_evidence_v3_outcomes` (the latter two also
under `.local_artifacts`). Content-addressed ACL-restricted records contain no
new annotations; private node/outcome data never enter Git or public exports.

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_evidence_arbitration_v3.py -v
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.evidence_arbitration_v3 --features .local_artifacts/sara3_correction_features_v1/e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe.json --base-report .local_artifacts/sara3_weighted_arbitration_v2/56e485e635ac915d07a0bb1b8849f5beb9017bd6f1ca9028192a64de335c0417.json --output .local_artifacts/sara3_evidence_arbitration_v3
# AFTER score freeze, separate GT-only process:
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.evidence_arbitration_v3 --report .local_artifacts/sara3_evidence_arbitration_v3/ac1842e6456cbda58379b214977fc5a6a5ea07da04833f47bceb6cfccbf2cbe4.json --report-sha256 ac1842e6456cbda58379b214977fc5a6a5ea07da04833f47bceb6cfccbf2cbe4 --features .local_artifacts/sara3_correction_features_v1/e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe.json --base-report .local_artifacts/sara3_weighted_arbitration_v2/56e485e635ac915d07a0bb1b8849f5beb9017bd6f1ca9028192a64de335c0417.json --direct-report .local_artifacts/sara3_graph_support_coverage_v1/71c9b21516f18b7bf16d2f6f6e773a7a0168aca6e1c488fb66641c013765a64b.json --graph .local_artifacts/gt_reference/cora_random_sbert.pt --frozen-root .local_artifacts/frozen --output .local_artifacts/sara3_evidence_v3_outcomes
```

Synthetic positive tests demonstrate candidate and third-class switches with
P/N unavailable, never semantic correctness. Real owner-local scoring under
explicit GT/review/network read guards reproduced the same frozen hash. The
runtime imports no GT evaluator and opens no graph labels or original journal.
The evaluator validates all source and decision bindings before opening GT.

Verification:8/8 new synthetic tests PASS. Complete guarded local suite528 tests,
0 failures/errors,2 Windows platform skips (POSIX permissions and OS symlink
creation; ZIP symlink rejection tested),438.000s. Actual human-review directories
and network dispatch were blocked. Private regression receipt:
`cfac5e84e41b5b7bbb8a2bf872fb1ab713a7c2edc47c7ae96045d8f590c604ab`.
AST checks3/3, unchanged control source check, diff/secret-pattern scan and4
private hash/ACL/immutable-readback checks PASS. Remote CI is checked on the
implementation SHA after push; local results are not a claim that CI ran on
private Windows inputs. No dependency or new infrastructure framework added.
