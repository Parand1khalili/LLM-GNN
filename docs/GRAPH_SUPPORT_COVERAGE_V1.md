# Graph Support Coverage Audit V1

Audit of fixed Weighted V2 (`f6129ff1`) on the same authenticated R0/R1 inputs.
Its zero-switch result, configuration, source artifacts and Arbitration V1 remain
unchanged. Human review, inference and training are outside this slice.

## Direct seed coverage is the binding limitation

The existing seed pools contain93 R0 and78 R1 unrouted high-confidence baseline
agreements. Every one of37 routed nodes per router has **zero directly adjacent
seed nodes**. Thus all74 fail the >=3-seed gate, even without a density gate.
The140-node cohort has only6 internal undirected edges; none connects a routed
node to its router's admitted seed pool. No pseudo-labels were invented for the
remaining canonical graph neighbors. This is lack of observed support, not
evidence that the Agent is wrong.

Canonical adjacency agrees with every frozen neighborhood ID subset and every
recorded degree across all140 nodes. All2708 existing384-dimensional embeddings
are finite and nonzero. Mapping mismatch or absent embeddings do not explain N.

| Full routed-cohort density | R0 /37 | R1 /37 |
|---|---:|---:|
| Undefined (<2 graph neighbors) |7|6|
| Exactly0 |3|2|
| Greater than0, below0.10 |1|1|
| At least0.10 |26|28|
| Direct seed count0 |37|37|

Gate cross-tab: seed minimum fails for all; density minimum passes26/28 and fails
11/9. Reasons overlap: no Blind class7/12, insufficient seeds37/37, density
undefined7/6, density below minimum4/3. Original V2 skipped support computation
when Blind had no class; its displayed density-unknown group16/18 therefore
included these skipped observations. The new audit computes topology for **all**
74 rows. Neither the earlier16/18 nor the new11/9 should be called "all low
density": undefined/skipped cases are distinct. Original receipts are preserved.

## Class prototype coverage

All seed embeddings are usable. Counts below are pseudo-label counts, not GT
class counts. Sample coverage is6/7 classes per router at the unchanged >=5 gate.

| Frozen class index/name | R0 seeds | R1 seeds | >=5 gate |
|---|---:|---:|---|
|0 rule_learning|7|6|PASS|
|1 neural_networks|24|23|PASS|
|2 case_based|12|10|PASS|
|3 genetic_algorithms|8|8|PASS|
|4 theory|15|8|PASS|
|5 reinforcement_learning|4|4|UNKNOWN: insufficient samples|
|6 probabilistic_methods|23|19|PASS|

All class means are nonzero. No class receives a scarcity bonus. P remains
positive5/4, observed non-support22/21, unknown10/12. Unknown includes missing
Blind classes7/12; the remaining3 R0 cases lack a sufficiently sampled comparison
prototype. Valid embeddings and a defined prototype do not imply support for
the proposed class; relative cosine/margin gates still apply. P is an uncalibrated
compatibility feature, not an error detector with established accuracy.

## Prespecified independent shadow variant

`sara.arbitration.weighted.v2.direct_seed.v1` removes **only** the neighbor-neighbor
density gate. N is UNKNOWN below3 direct admitted seeds. Otherwise N=1 iff at
least2/3 of these seeds have the Agent class and their count exceeds Narrative's
count; observed disagreement gives0. Graph adjacency still defines neighbors.
The rationale is direct pseudo-label consensus: seed neighbors need not cite each
other to supply evidence. This is a prospective definition, not proof of label
reliability or statistical independence of connected seeds.

Seed provenance, P, all weights, Q/T/A/C/U, score thresholds3/4, class restrictions
and phase-validity gates remain unchanged. The contract was written before the
first coverage calculation; no GT or outcome was used to select its parameters.
No multihop propagation, additional labels or lower support minimum was added
after observing zero direct seeds. A synthetic star-graph test demonstrates that
N can become positive without edges between neighbors.

Actual variant: N UNKNOWN37/37 for each router; decisions identical to original
V2: R0 KEEP27/NO_VALID10, R1 KEEP24/NO_VALID13. V1, V2 and this variant all have
**zero switches, fixes, harms and net change**. The separate post-freeze GT-only
process reproduced selected-cohort correct counts21/37 and17/37 unchanged.
This is `EXPLORATORY_NOT_INDEPENDENT` (57 unique nodes,17 shared). No accuracy,
generalization, training admission or GCN improvement claim follows.

## Frozen provenance and reproduction

Private output directory: `.local_artifacts/sara3_graph_support_coverage_v1`.
Earlier content-addressed diagnostic reports remain present; no file overwritten.

| Artifact | SHA-256 |
|---|---|
| Unchanged source feature freeze |`e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe`|
| Unchanged V2 report |`56e485e635ac915d07a0bb1b8849f5beb9017bd6f1ca9028192a64de335c0417`|
| Shadow contract (before scoring) |`304eceb336b25ec29b2432b0a9cd1ad8316b6625c8605a2aa385f798f84a830b`|
| Final coverage audit |`4017c86db580769fa54f72841788a318e67259706529628799db2b2666dd6e01`|
| Shadow score freeze |`71c9b21516f18b7bf16d2f6f6e773a7a0168aca6e1c488fb66641c013765a64b`|
| Separate GT-only comparison |`ab00f759fd2f3fb5a48745d2ea2e49050ce8b1e24bd1ca508747bba8f192074e`|

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_graph_support_coverage.py -v
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.graph_support_coverage --features .local_artifacts/sara3_correction_features_v1/e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe.json --base-report .local_artifacts/sara3_weighted_arbitration_v2/56e485e635ac915d07a0bb1b8849f5beb9017bd6f1ca9028192a64de335c0417.json --graph .local_artifacts/gt_reference/cora_random_sbert.pt --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --output .local_artifacts/sara3_graph_support_coverage_v1
# Separate process only after freeze:
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.graph_support_coverage --report .local_artifacts/sara3_graph_support_coverage_v1/71c9b21516f18b7bf16d2f6f6e773a7a0168aca6e1c488fb66641c013765a64b.json --report-sha256 71c9b21516f18b7bf16d2f6f6e773a7a0168aca6e1c488fb66641c013765a64b --base-report .local_artifacts/sara3_weighted_arbitration_v2/56e485e635ac915d07a0bb1b8849f5beb9017bd6f1ca9028192a64de335c0417.json --features .local_artifacts/sara3_correction_features_v1/e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe.json --graph .local_artifacts/gt_reference/cora_random_sbert.pt --frozen-root .local_artifacts/frozen --output .local_artifacts/sara3_graph_support_outcomes_v1
```

Existing V2 source loader reads only exact hash-admitted embedding/edge storages,
without pickle/label decoding. Actual GT is opened only by the separate evaluator
after report binding checks. Private node-level rows never enter Git/public
exports. Output readback verifies hashes and immutable replay. No dependency added.

Verification:7 new focused tests and9 unchanged Weighted V2 tests PASS. Full
guarded discovery ran520 tests in434.140s,0 failures/errors,2 Windows-specific
skips (POSIX permissions and unavailable OS symlink creation; ZIP symlinks tested).
Network dispatch and actual private human-review directories were blocked.
Private test receipt: `d1c12a64321828d6503165ae6b9bf2b0f4ce4d457e351e9ea17980c968977c0f`.
AST3 files, staged scope/secret-pattern checks and4 private hash/ACL/immutable
replay checks PASS. An initial synthetic fixture changed an embedding without
refreshing its baseline binding and correctly failed closed; the fixture was
corrected without weakening production validation. CI status for the final SHA
is reported after push; local tests do not imply remote CI success.

Next scientific question: whether an independently justified, authorized source
of **additional GT-free neighbor pseudo-labels** exists. This slice neither
creates such labels nor replaces absent support with a proxy. Further scoring
complexity cannot restore information that is not available.
