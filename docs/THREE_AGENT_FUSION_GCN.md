# Three-agent fusion and controlled GCN preparation

Date2026-11-07; starts from main afa60e38a62650abb3303fbb139e08ed467dfa76.
There are three functional roles: B1, Narrative-v0, and SARA-3. Blind/Comparison
are dependent phases of Agent3, not two independent agents. B1 and Narrative
historically used the same underlying LLM. Each arm has exactly one final_class
(or null) and one label_source per node. Comparisons against B1/Narrative are
evaluation references for that same vector, never B1+Agent/Narrative+Agent pipelines.

## Phase0: reviewed architecture and unchanged sources

| Component | Role and source |
|---|---|
|sara2/policy.py|Typed B1/Narrative class/confidence; reconstructed agreement80 and R0 risk|
|sara3/selection.py, r1_candidate.py|Existing R0/R1-v1 selection,37 nodes each; unchanged|
|sara3/pipeline.py|Original offline verifier pipeline; old admission/quarantine remains intact|
|sara3/automated_policy.py|V1 consistency screen, not semantic approval; unchanged|
|sara3/rich_evidence.py|Frozen rich JSON, blind-first, exact source quotes and L1; unchanged|
|sara3/consensus_only.py|Frozen diagnostic consensus contract, not rewritten|
|sara3/fusion.py (new)|One GT-free final class/source, conservative P1 and relaxed P2|
|downstream/frozen.py|Original baseline/legacy admission adapter; not weakened|
|downstream/{plan,prospective,model}.py|Historical masks/config/weights, candidate-only legacy admission, training gate; unchanged|
|downstream/fusion.py (new)|Draft grid, exact-fit deduplication, safe graph boundary, new explicitly gated admission|
|evaluation/fusion.py (new)|Separately invoked GT-only label-quality metrics; future paired-seed aggregation|

Frozen input provenance includes the two140-node class/confidence files, FeatProp
manifest, authenticated text/neighborhoods and receipt-replayed R0/R1 feature
freeze. Supplementary private input trace gives B1 class/confidence, Narrative
class/confidence, Router membership and Blind/Comparison state/class/L1/support
for every node, bound to feature/context/journal hashes. Nonrouted phases are
absent, never fabricated. Original receipts/journals/predictions are not modified.

Historical FeatProp: recovered `src/helper/active.py:featprop_query` computes
propagated feature distances and FasterPAM medoids; `helper/data.py` dispatches
it as target selection. Current work reuses its frozen140 targets and five
supplementary exclusions; it does not rerun medoids or treat FeatProp as a loss/PS
toggle. Other target selections would require a separate study and authentic new
responses. Graph features for GCN remain original SBERT x, not FeatProp AAX.

## Frozen policies: no GT, confidence-gap rule or score tuning

Version `sara.three_agent.fusion.v1` contains `sara.fusion.conservative.v1` (P1)
and `sara.fusion.relaxed.v1` (P2). Baseline agreement means same class with both
historical voted confidences >=80. Confidence is not calibrated probability.

| Ordered condition | P1 | P2 |
|---|---|---|
|Unrouted|Baseline agreement, else abstain|Same|
|Both supported, COMPLETED/L1 PASS/non-abstaining, same valid class|Select Agent3 consensus, including third class|Same|
|Both valid, disagree; Comparison chooses B1 or Narrative candidate|Baseline agreement or abstain|Comparison resolver|
|Comparison absent/REJECTED; valid Blind matches a historical candidate|Baseline agreement or abstain|Explicit Blind-candidate fallback|
|Comparison COMPLETED but abstains|Baseline agreement or abstain|Same; no Blind fallback|
|Conflict, invalid response/support/class, other third-class disagreement|Baseline agreement or abstain|Same|

Unknown execution states are rejected. A rejected comparison is never reclassified
as valid. Both-phase consensus permits third classes; single-Blind fallback does
not. Warnings, counters, literal topic differences and missing graph seeds are
not vetoes. Supporting quotes and source/receipt integrity remain mandatory.
P1 reuses the frozen consensus validity conditions even when the class equals
Narrative: retaining/resolving a low-confidence candidate is not a correction.
All final labels are experimental and training_eligible=false until separate
admission; L2 remains NOT_ASSESSED. Prior V1-V3 results remain unchanged.

Freeze occurred before the new GT evaluation. Preflight corrected JSON tuple/list
readback and own-arm confidence for A/B before the final freeze; preliminary
private drafts were retained and never used for scientific outcome evaluation.
A supplemental provenance-only trace was then added without changing the frozen
rule, label vector or outcome hashes. No outcome-based change to P1/P2 occurred.

## Seven unique arms, masks and confidence

A=B1-only, B=Narrative-only, C=agreement80 without Agent3 are shared across
routers. D=P1 and E=P2 each have R0/R1 instances. There are seven unique arms,
not ten separate baseline fits. Natural mask uses each policy's accepted nodes.
The CE/noPS matched mask intersects all seven accepted sets:93 Sensitivity,
89 Primary nodes. Thus class effects on this common accepted subset are separated
from added-label coverage; the matched estimand excludes newly added nodes.
For R0 the matched CE vector equals C; R1 differs at2 C-accepted nodes.

Test is always the2568-node complement of all140 selected IDs. The five Primary
exclusions, abstentions and PS removals never migrate into test. Primary135 and
Sensitivity140 are cohort definitions, not guaranteed training-label counts.
Router cohorts overlap17 nodes; they are not independent experimental samples.

Historical GCN is unchanged: raw384-dimensional features,2708 nodes,7 classes,
2 layers, hidden64, dropout0.5, Adam lr0.01/weight_decay0.0005,30 epochs,
seeds0..9, last epoch/no early stopping/no validation. Safe graph_inputs reads
only hash-admitted tensor storages32(x) and1(edges), no pickle or y decoding;
actual x and original ordered edge bytes match source hashes exactly.
The binary display topology has5278 unique undirected edges; the archive has
10858 ordered edge entries including duplicates. The GCN boundary preserves
those original entries rather than silently coalescing the training graph.
Static opcode inspection of the hash-admitted metadata found no edge_weight
field, consistent with the historical runner's None fallback. No unpickling or
label tensor decoding was used for this check.

- A/B confidence is that arm's own frozen value, preserving historical WCE/PS.
- C/fusion candidate labels use the minimum *matching* baseline confidence,
  explicitly historical candidate confidence, not Agent3 calibration.
- Third-class confidence is unavailable. Natural WCE and PS for these arms are
  BLOCKED; no proxy/constant Agent confidence is invented. CE/noPS needs none.
- The gated legacy CE backend has an unused numeric confidence slot. Only after
  explicit admission, None can be bridged as a100 unit-loss sentinel; the source
  final confidence remains None and sentinel IDs are marked. This is not an
  estimate and is prohibited for WCE/PS. No real admission was performed.
- WCE retains historical min-max confidence weights, constant ->ones, and
  mean(weight*per-node CE), not normalized sum and not class-balancing weights.
  Matched WCE can still differ in confidence weights; only matched CE is the
  clean class-only comparison. No rarity bonus or loss redesign was added.

## Historical PS fidelity and grid

Reuse filtering.ps.derive_ps from the frozen corrected matched-cohort runner,
not generic helper/post_filter_label_free.py's averaged-tie ranks. Recompute
confidence/COE ranks after each deletion, ascending ID tie-breaks, preserve
manifest order, never remove the last member of a class. Drop floor(0.30*N)
accepted eligible labels; insufficient class-guard capacity blocks the plan.

Historical primary runner SHA:
`00f846cc3c53d5f3f42c12142129890bed56d98bb9d0c0d6da6eae3ccdd5b102`;
sensitivity runner SHA:
`491a7ea84280030843294fcd506aae9d944d22087d047421995132eb4ffab5fe`.
Actual A/B PS deletion order, retained IDs/classes/confidences match both pinned
manifests exactly:40/135 removed ->95;42/140 removed ->98. C is a prospective
application of the same filter:89 ->63 and93 ->66, not a claimed historical run.

Grid112 rows =7 arms*2 cohorts*2 losses*2 PS settings*2 mask modes:
56 valid drafts,28 confidence-blocked and28 undefined-common-post-PS-mask rows.
PS is computed independently per arm; a matched PS mask exists only if all
seven natural PS masks are defined, then uses their intersection. Missing
third-class confidence prevents that here. Blocked counts are unknown, not zero
training labels. Exact effective graph/config/mask/label/weight/test identities
deduplicate56 drafts to36 fit specs /360 possible seed fits. This is a plan,
not approval to execute360 fits. Start only with separately approved CE/noPS.
Before any approved fit, recover and verify any existing historical A/B receipts
against the full effective graph/mask/labels/weights/config/test/seed specification.
Historical reports or code-embedded counts alone are insufficient to admit a
cached fit; no previously completed baseline is automatically rerun here.

## Gates and scientific status

No training is authorized in this slice. Every GCN metric, per-seed result,
mean/SD and paired delta is NOT_RUN_BLOCKED/null. Test independence remains
UNVERIFIED_CONTAMINATION_AUDIT_REQUIRED: the140 GT labels are exposed development
data; historical use of the2568 complement needs an independent audit. Do not
call that complement independent merely because masks are disjoint.

New admission adapter requires exact fusion/plan hashes, version, explicit owner
admission approval and hash of a reviewed independent/exploratory test audit.
It rederives labels/masks and never trains. Approval objects express external
authorization; they are not cryptographic proof that a person/audit is genuine.
The original train_gcn allow_training=False gate remains mandatory and unchanged.
PS is already preprocessing when admitted; the unchanged backend applies no
second PS operation. No approval objects were created for real project data.

Label-quality evaluation was actually executed separately after freeze. Results
are EXPLORATORY_NOT_INDEPENDENT; selective accuracy/Macro-F1 use accepted labels
only and must be read alongside coverage. Fix/Harm against B1 and Narrative are
two references for one final vector, not separate SARA pipelines. Additional
correct labels from increased coverage are not automatically class corrections.
P2 adds2 R0 labels (one correct, one incorrect), not an observed class-fix gain;
P1/P2 R1 outputs coincide. No GCN improvement or P2 superiority is established.

See THREE_AGENT_FUSION_RESULTS.md for all aggregate tables and
reports/three_agent_fusion_v1.json for the complete112-row allowlisted matrix.

## Frozen artifacts and owner-local reproduction

| Artifact | SHA-256 |
|---|---|
|Unchanged receipt-derived feature freeze|`e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe`|
|Final P1/P2 rule freeze, before GT|`31ac6ae09ccf5d002867b0f3c739b4762c64fff290c93eea2bc6fdf36c4ce6b2`|
|One final vector per arm|`bc16870399416620ed67f8799ed9bd0f17c2b7cf3c5849b2debe93ac14d96c2c`|
|Supplemental per-node input provenance|`ebe9baf2c521d8a7ba791ab689373a1adfabad0cfce9520b24c03b3bdbbcc43e`|
|Draft-grid contract|`c2ecb05548565545a99fa8fa690de75df5422ac1b0f6401ce22449e7a5f65082`|
|112-row grid, before GT|`c7f51377905a7d5a224d86ef9342dfdf0430fa1ce518f22ccac6647bf227ca0e`|
|Separate GT-only label-quality results|`ae731ac5c0ade855088e7a18af57ccbb91e4b874af43576c326655f1e57ecf2a`|

Private roots: `.local_artifacts/sara3_three_agent_fusion_v1`,
`sara3_three_agent_gcn_grid_v1`, `sara3_three_agent_fusion_outcomes_v1`
(all under `.local_artifacts`). None is committed or sent externally.
Public export uses an explicit aggregate allowlist; no node IDs, train masks,
article text, raw responses, model credentials or GT per node are exported.

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_three_agent_fusion.py -v
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.fusion --features .local_artifacts/sara3_correction_features_v1/e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe.json --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --output .local_artifacts/sara3_three_agent_fusion_v1
.venv\Scripts\python.exe -B -m llmgnn_sara.downstream.fusion --fusion .local_artifacts/sara3_three_agent_fusion_v1/bc16870399416620ed67f8799ed9bd0f17c2b7cf3c5849b2debe93ac14d96c2c.json --fusion-sha256 bc16870399416620ed67f8799ed9bd0f17c2b7cf3c5849b2debe93ac14d96c2c --features .local_artifacts/sara3_correction_features_v1/e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe.json --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --graph .local_artifacts/gt_reference/cora_random_sbert.pt --output .local_artifacts/sara3_three_agent_gcn_grid_v1
# Separate process AFTER freeze. This is GT-only evaluation, NOT training:
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.fusion --fusion .local_artifacts/sara3_three_agent_fusion_v1/bc16870399416620ed67f8799ed9bd0f17c2b7cf3c5849b2debe93ac14d96c2c.json --fusion-sha256 bc16870399416620ed67f8799ed9bd0f17c2b7cf3c5849b2debe93ac14d96c2c --features .local_artifacts/sara3_correction_features_v1/e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe.json --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --graph .local_artifacts/gt_reference/cora_random_sbert.pt --output .local_artifacts/sara3_three_agent_fusion_outcomes_v1 --grid .local_artifacts/sara3_three_agent_gcn_grid_v1/c7f51377905a7d5a224d86ef9342dfdf0430fa1ce518f22ccac6647bf227ca0e.json --grid-sha256 c7f51377905a7d5a224d86ef9342dfdf0430fa1ce518f22ccac6647bf227ca0e --public-summary reports/three_agent_fusion_v1.json
```

The public summary replays only if bytes agree; it never silently overwrites a
different completed report. Raw private research artifacts remain hash-addressed.
Matched seeds and deltas have a tested aggregator, but no executed GCN seed metrics
exist for this new fusion grid. Historical fits are not presented as new execution.
Future or recovered fit receipts/predictions must be verified before using that aggregator;
its synthetic tests are not scientific results. GPU bit determinism is not proven.

Verification includes9 focused synthetic tests, complete guarded repository tests,
actual source graph byte/order checks with torch.load forbidden, historical PS
parity, authenticated full-cohort replay and before/after hashes of15 original
JSON/SQLite files. Original rule files, frozen artifacts and GraphScope changes
are preserved. CI is checked on the implementation commit; public-only CI does
not execute private owner-local data. Final counts are recorded in PROJECT_STATE.md.

Final focused9/9 PASS (4.596s). Final guarded full suite544 tests:0 failures/errors,
2 Windows-specific skips (POSIX permission behavior and OS symlink creation;
ZIP symlink rejection tested),414.125s. Private regression receipt:
`40b7758237a67d35015b182d863c1ad6bfd3e7b2b936bee430f378a49ee057d7`.
The earlier complete pass preceded final graph/provenance/export additions and
is retained separately; the full suite was repeated after those additions.
