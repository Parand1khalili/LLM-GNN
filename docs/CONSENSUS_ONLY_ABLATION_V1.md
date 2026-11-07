# Consensus-only shadow ablation and field-origin audit

2026-11-07; starts from main db4fb124810f5df2c499d391fcc6085cdb119c1d.
Version `sara.ablation.consensus_only.v1` is a post-observation diagnostic
ablation, **not V4**, a replacement for V1-V3, or an admission policy.

## Frozen GT-free contract

Switch the experimental output from Narrative only when both phases are
COMPLETED, L1 PASS, non-abstaining, agree on a class0..6, each has authenticated
supporting quotations, and the proposed class differs from Narrative. Third
classes are allowed. Q/A/C/T/P/N/U are diagnostic only, never switch gates;
there is no score or threshold. Training eligibility remains false; L2 remains
NOT_ASSESSED. No inference, human review, admission, GCN or original-label change.

The rule was frozen before calculation and before the separate GT process.
Design followed already observed V1-V3 results: all findings are
`EXPLORATORY_NOT_INDEPENDENT`, not a prospective independent evaluation.

## Private source audit:16 candidates,32 authentic phase responses

Original+continuation journals are opened with SQLite mode=ro/query_only. Their
merged row digests must equal the pinned correction-feature provenance. For each
of the16 candidates, reconstruct the sealed effective blind/comparison request
and actual blind dependency; check context, request identity, wire SHA, receipt
SHA, raw response SHA, original COMPLETED state, usage, parser and rich L1. Replayed
phase features must match the exact frozen source. No failed response is repaired.

Exact decoded warning strings, primary topics, supporting/counter evidence and
claims are preserved in a separate ACL-private diagnostic artifact alongside
source hashes. Raw article text/quotes/claims and node-level outcomes are not in
Git or this public report. No human-review materials were read.

Field origin is the model's versioned rich JSON, not an independent assessor:

The sealed prompt asks for these fields "as applicable"; schema permits null
warning and empty counter arrays. Normalization preserves decoded strings/items;
the feature extractor applies bool(nonempty string) and len(counter array).
It does not synthesize warnings or counter-items. Their comparison-stage
prevalence here is observed model output, not a schema requirement of presence.

- `auxiliary_method_warning` is nullable free text. It has no quotation/source
  binding of its own. A general methodological caution is therefore not proven
  article-specific counter-evidence just because this string is nonempty.
- `counter_evidence[]` has source_id, exact target quotation and claim. L1 checks
  schema/provenance/quotation, **not** that the claim contradicts the primary
  topic or defeats the proposed class. A genuine quotation is not semantic proof.
- `primary_topic` is free text. Frozen T compares strip/casefold strings exactly.
  It neither recognizes paraphrases nor establishes semantic topic drift.

No validated method is available here to classify each warning as generic versus
primary-topic-specific, or each counter-claim as material/resolved. Those semantic
classifications explicitly remain NOT_ASSESSED. The private record supports
traceability, not fabricated semantic ratings. Lexical comparison computes token
edit operations/Jaccard descriptions only; it never authorizes a switch.

| GT-free diagnostic | R0 /10 candidates | R1 /6 candidates |
|---|---:|---:|
| Warning present: Blind / Comparison |8 /10|6 /6|
| Counter items present: Blind / Comparison |4 /10|2 /6|
| Any-phase warning / counter |10 /10|6 /6|
| Shared quote exists |8|3|
| Shared quote count histogram |0:2,1:3,2:4,3:1|0:3,1:3|
| Third-class proposals |7|4|
| Primary-topic normalized strings identical |1|0|
| Token replacement/addition/deletion patterns |9|6|

The15 differing topic strings are not merely punctuation-only or token-reordering
cases under the documented lexical rules. That does **not** determine whether
their meaning changed. Exact private texts and edit operations remain available
locally; no LLM-as-judge or human semantic assessment was performed.

## Separate post-freeze GT-only results

| Measure | R0 | R1-v1 |
|---|---:|---:|
| Routed denominator |37|37|
| Experimental switches |10|6|
| Fix / Harm / Net |4 /4 /0|2 /2 /0|
| Switched but both labels wrong |2|2|
| Switch coverage |10/37 (27.03%)|6/37 (16.22%)|
| Third-class switches |7|4|
| Third-class Fix / Harm / both wrong / Net |3 /2 /2 /+1|1 /1 /2 /0|
| Narrative correct -> ablation correct, selected cohort |21 ->21|17 ->17|
| No valid response / same Narrative / phase disagreement |10 /15 /2|13 /17 /1|

V1, Weighted V2, direct-seed and V3 frozen results remain unchanged:0 switches.
Consensus switches are hypothetical experimental labels, not training admissions.

| Shared-quote stratum | n | Fix | Harm | Both wrong | Net |
|---|---:|---:|---:|---:|---:|
|R0 present|8|4|4|0|0|
|R0 absent|2|0|0|2|0|
|R1 present|3|2|1|0|+1|
|R1 absent|3|0|1|2|-1|

Shared quotations do not guarantee a useful correction. The tiny R1 strata are
descriptive, post-hoc and not grounds for a new filter. Likewise the R0 third-class
subgroup+1 does not override overall net0 or authorize another tuned rule.

### Do warning/counter flags discriminate?

Any-phase A and C are1 for **every** candidate, including all fixes, harms and
both-wrong switches. There is no absent comparison group: these binary flags
cannot distinguish outcomes within these16 observations. Comparison-stage
warning/counter presence is also constant. This does not establish that the
underlying texts have no semantic information; a valid analysis method is absent.

Phase-specific Blind flags vary, with these descriptive contrasts:

| Blind stratum | n | Fix | Harm | Both wrong |
|---|---:|---:|---:|---:|
|R0 warning present / absent|8 /2|3 /1|3 /1|2 /0|
|R0 counter present / absent|4 /6|3 /1|0 /4|1 /1|
|R1 warning present / absent|6 /0|2 /0|2 /0|2 /0|
|R1 counter present / absent|2 /4|1 /1|1 /1|0 /2|

R0 Blind-counter association does not replicate as a clear separation in R1;
small cells and retrospective selection prohibit turning it into an acceptance
rule. No thresholds, weights or filters were changed after these observations.

### Research decision

**Consensus alone is not reliable for arbitration on the current evidence.**
Both routers have net0, with real harmful switches. It does not improve the
number of correct labels relative to Narrative; zero net is not a safety or equivalence proof.
No new policy tuning is proposed. Record the current evidence limitation before
considering any independently designed future study. No training authorization.

The37-node router cohorts share17 nodes. The16 switch observations concern13
unique nodes, with3 switched in both runs; do not treat them as16 independent
articles or pool router counts into independent evidence. Same-model phases,
small selected samples, prior GT exposure and post-observation design limit
generalization. No confidence interval, p-value or winner claim is warranted here.

## Provenance and reproduction

| Artifact | SHA-256 |
|---|---|
|Unchanged source features|`e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe`|
|Frozen ablation contract|`7de9f37650239e8feb74ba95c2e7476c35f436bc6670dc6005e78ae115f803c3`|
|Private32-response source diagnostic|`434ea5402334ea086a31c9c49ff2242a965979bb042f1298a83d2b2fb850d867`|
|GT-free decision freeze|`0040fdab2a45340256c5087135ff06ff2fab706c219196278bb81a9278654130`|
|Separate GT-only outcome report|`d05ff62fa0b1b1d6b47b4ed5ba4f9afa3aff4536237f80ad1ee9ac9da2defefc`|

Private directories: `.local_artifacts/sara3_consensus_only_v1` and
`.local_artifacts/sara3_consensus_only_outcomes_v1`. No private artifacts committed.

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_consensus_only.py -v
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.consensus_only --features .local_artifacts/sara3_correction_features_v1/e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe.json --base-report .local_artifacts/sara3_weighted_arbitration_v2/56e485e635ac915d07a0bb1b8849f5beb9017bd6f1ca9028192a64de335c0417.json --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --r0-root .local_artifacts/sara3_gapgpt_live_cora140_r0_4096_20261105 --r1-root .local_artifacts/sara3_gapgpt_live_cora140_r1_v1_4096_20261107 --config configs/gapgpt_rich_v2_output4096_proposed.json --output .local_artifacts/sara3_consensus_only_v1
# Separate GT-only process AFTER freeze:
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.consensus_only --report .local_artifacts/sara3_consensus_only_v1/0040fdab2a45340256c5087135ff06ff2fab706c219196278bb81a9278654130.json --report-sha256 0040fdab2a45340256c5087135ff06ff2fab706c219196278bb81a9278654130 --features .local_artifacts/sara3_correction_features_v1/e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe.json --base-report .local_artifacts/sara3_weighted_arbitration_v2/56e485e635ac915d07a0bb1b8849f5beb9017bd6f1ca9028192a64de335c0417.json --diagnostic .local_artifacts/sara3_consensus_only_v1/434ea5402334ea086a31c9c49ff2242a965979bb042f1298a83d2b2fb850d867.json --graph .local_artifacts/gt_reference/cora_random_sbert.pt --frozen-root .local_artifacts/frozen --output .local_artifacts/sara3_consensus_only_outcomes_v1
```

Guarded actual replay reproduced all three GT-free hashes with GT/review/network
access forbidden. Before/after hashes of4 original SQLite files and32 response
receipts were identical. Seven focused synthetic tests PASS. The first offline
audit exposed an adapter assumption about normalized versus top-level rich JSON;
using the established validator normalization fixed it before the decision freeze
and GT evaluation. Original parsers/L1 and scientific rules were not changed.

Full guarded local suite:535 tests,0 failures/errors,2 Windows-specific skips
(POSIX permissions and OS symlink creation; ZIP symlink rejection tested),424.500s.
Private regression receipt:
`c3bd99b9b1389b99cf8a8cc7070f9b619fb57b41966bad9d6469be5d6330cbc0`.
AST3, prior-rule source immutability, diff/staged secret-pattern checks and4
private hash/ACL/immutable-readback checks PASS. The isolated GT-only evaluator
reproduced the exact outcome hash after diagnostic-pin validation was finalized.
CI for the implementation SHA is checked after push; public-only CI cannot
substitute for the owner-local private-data checks above. No dependency added.
