# Project state

## Single-vector three-agent fusion / GCN preparation — 2026-11-07

- Starts from afa60e38a62650abb3303fbb139e08ed467dfa76 on synchronized main.
  Three functional agents, one final_class/source per node. B1/Narrative are
  comparison references, never separate B1+Agent/Narrative+Agent pipelines.
  All old policies, frozen data, routes and GraphScope/user work preserved.
- Conservative P1 and deterministic relaxed P2 frozen before new GT evaluation:
  rule31ac6ae09ccf5d002867b0f3c739b4762c64fff290c93eea2bc6fdf36c4ce6b2;
  label reportbc16870399416620ed67f8799ed9bd0f17c2b7cf3c5849b2debe93ac14d96c2c;
  supplemental input traceebe9baf2c521d8a7ba791ab689373a1adfabad0cfce9520b24c03b3bdbbcc43e.
  No P2 outcome-based tuning; no scores/confidence-gap rule. Third classes
  permitted experimentally, not admitted. P2 Blind fallback is candidate-only
  and comparison absent/rejected; completed comparison abstention is not bypassed.
- Actual separate GT-only outcomeae731ac5c0ade855088e7a18af57ccbb91e4b874af43576c326655f1e57ecf2a:
  A96/140,B101/140; C72/93 accepted; P1-R0=88/118,P2-R0=89/120;
  P1/P2-R1=82/108. Selective metrics must be read with coverage.
  Agent Fix/Harm vs B1=5/2(R0),3/1(R1); vs Narrative=4/4,2/2.
  These are references for the same final vectors. EXPLORATORY_NOT_INDEPENDENT,
  17 shared routed nodes; no claim of P2/GCN superiority or independent test.
- Gridc7f51377905a7d5a224d86ef9342dfdf0430fa1ce518f22ccac6647bf227ca0e:
  112 natural/matched CE/WCE/PS/cohort rows,56 valid drafts,56 blocked.
  36 effective fit specs/360 possible seed fits after deduplication;0 executed.
  CE/noPS common masks93/89 (Sensitivity/Primary); fixed test complement2568.
  Historical PS deletion/order/class/confidence parity PASS for both baselines
  and cohorts. Missing third-class confidence blocks affected WCE/PS plans.
- New separate hash-bound admission adapter is default-deny; no real approval
  record or admission executed. Existing allow_training gate unchanged.
  Training NOT_RUN_BLOCKED: independent admission/training authorization and
  test-contamination audit absent. No provider calls, human reviews or Drive writes.
- Source graph x2708x384 /edges2x10858 verified without pickle, original byte
  hashes/order match. Guarded authentic replay unchanged15 original JSON/SQLite
  files and frozen hashes. Final focused9/9 PASS; final full544 tests0 failures/errors,
  2 Windows skips,414.125s; private receipt
  40b7758237a67d35015b182d863c1ad6bfd3e7b2b936bee430f378a49ee057d7.
  Final suite repeated after graph/provenance/export completion; earlier pass
  retained. AST4/old-source immutability/public allowlist/diff checks PASS.
  CI/remote readback reported after scoped main commit/push (pending at commit).
  See docs/THREE_AGENT_FUSION_GCN.md, docs/THREE_AGENT_FUSION_RESULTS.md and
  reports/three_agent_fusion_v1.json for all aggregate results and112 plan statuses.

## Consensus-only diagnostic ablation — 2026-11-07

- Starts from db4fb124810f5df2c499d391fcc6085cdb119c1d on synchronized main;
  V1-V3/direct-seed rules/results and unrelated user/GraphScope work unchanged.
  sara.ablation.consensus_only.v1 is NOT V4 or an admission policy. Only valid,
  same-class, non-abstaining two-phase L1-supported changes switch experimentally;
  Q/A/C/T/P/N/U are diagnostic only. Rule frozen before any GT read.
- 32 authentic phase responses for16 candidates replayed against exact original
  context/request/wire/raw hashes and L1; source feature and journal-row hashes
  match. Private source fields retained; no semantic classification fabricated.
  Independent before/after byte hashes:4 SQLite +32 receipts unchanged. Guarded
  real replay with GT/review/network forbidden reproduced identical hashes.
- Rule7de9f37650239e8feb74ba95c2e7476c35f436bc6670dc6005e78ae115f803c3;
  decision0040fdab2a45340256c5087135ff06ff2fab706c219196278bb81a9278654130;
  private diagnostic434ea5402334ea086a31c9c49ff2242a965979bb042f1298a83d2b2fb850d867.
  Separate GT-only outcome d05ff62fa0b1b1d6b47b4ed5ba4f9afa3aff4536237f80ad1ee9ac9da2defefc:
  R0 switches10/fix4/harm4/net0; R1 switches6/fix2/harm2/net0.
- Aggregate A/C and comparison-phase flags constant1: cannot discriminate
  fixes/harms in these candidates. Topic strings differ lexically15/16, semantic
  difference NOT_ASSESSED.16 switch observations concern13 nodes,3 shared;
  full router cohorts share17. EXPLORATORY_NOT_INDEPENDENT, no pooled inference.
- Research decision: consensus alone not reliable on current evidence; record
  limitations instead of more rule tuning. No API/human review/admission/GCN,
  original-label changes or Drive writes. Focused7/7 PASS; full535 tests,
  0 failures/errors,2 Windows platform skips,424.500s. Private test receipt
  c3bd99b9b1389b99cf8a8cc7070f9b619fb57b41966bad9d6469be5d6330cbc0.
  AST3/prior-rule immutability/diff/staged secret-pattern checks and4 private
  hash/ACL/replay checks PASS. Remote CI pending at local commit; readback
  reported after normal main push. Details: docs/CONSENSUS_ONLY_ABLATION_V1.md.

## Evidence-only Arbitration V3 Shadow — 2026-11-07

- Continues from443eed2ef8f1b2f11a4dfa6f3fe05a961a0dcb1e; existing main was
  synchronized. V1/V2/direct-seed sources, all zero-switch history, frozen
  data and unrelated GraphScope/user modifications preserved.
- Bounded local provenance audit:211 distinct actual neighbors of57 selected
  nodes; only1 mapped frozen baseline record, below existing80 confidence.
  No eligible additional source; generation timestamps not established by the
  inspected manifests. No new archive-wide missing-file claim or seed expansion.
  Inventory8cfbbca6c7128588b595c9a5a03f9ad939778c1ca27c169f52e9dc142245970a.
- sara.arbitration.evidence.v3 fixed before scores/GT:2Q+2T+P+N-A-2C-U,
  candidate/third thresholds3/4, valid same-class L1-supported phases mandatory,
  P/N optional. Contractff13e8719a2abc1e0baa2dedb87c0d7d02de1a3f5bfcd3737b8f125920382e92;
  scoreac1842e6456cbda58379b214977fc5a6a5ea07da04833f47bceb6cfccbf2cbe4.
- Separate GT-only evaluation348a3d49e35dac90c0b6c19ac75bd9cbab78c68df601ec56accb48b399e0e221:
  R0/R1 V3 zero switches/third switches/fixes/harms/net, as all three controls.
  All10/6 agreed changed candidates have A/C presence; all fall below fixed
  thresholds. No subsequent tuning. EXPLORATORY_NOT_INDEPENDENT,17 shared nodes.
- Focused8/8 PASS; guarded authentic replay reproduced identical score hash
  with GT/review/network forbidden. Full suite528 tests,0 failures/errors,
  2 Windows platform skips,438.000s; private test receipt
  cfac5e84e41b5b7bbb8a2bf872fb1ab713a7c2edc47c7ae96045d8f590c604ab.
  AST3/source-control immutability/diff/secret checks and4 private hash/ACL
  readback checks PASS. New SHA remote/CI results reported after normal push;
  pending at local commit. No Drive upload.
  No human reviews, new inference, admission, original-label overwrite or GCN.
  Details/reproduction/limitations: docs/EVIDENCE_ARBITRATION_V3.md.

## Graph support coverage / direct-seed shadow — 2026-11-07

- Preserves f6b028f9 and f6129ff1, their zero-switch findings and user GraphScope
  work. Initial fetch: origin/main8f880075,2 local commits pending; approved
  destination verified private Parand1khalili/LLM-GNN. Push/readback status is
  reported separately after scoped commit; no force/history rewrite.
- Every routed observation has0 direct admitted seed neighbors:37/37 per router.
  Density>=0.10 in26/28; it is not the binding limitation. Canonical adjacency
  matches all140 frozen degree/neighbor records;2708 finite nonzero embeddings.
  Prototype class5 has4 seeds in both pools, below5; other classes pass.
- Prespecified sara.arbitration.weighted.v2.direct_seed.v1 removes only density
  gate; unchanged3 seeds,2/3 vote, strict class-count advantage, weights/thresholds.
  Rule304eceb336b25ec29b2432b0a9cd1ad8316b6625c8605a2aa385f798f84a830b;
  score71c9b21516f18b7bf16d2f6f6e773a7a0168aca6e1c488fb66641c013765a64b.
  Separate GT-only evaluation ab00f759fd2f3fb5a48745d2ea2e49050ce8b1e24bd1ca508747bba8f192074e:
  V1/V2/variant all0 switches/fixes/harms/net. EXPLORATORY_NOT_INDEPENDENT.
- No human reviews, inference, GT-derived runtime features, label admission,
  training, original receipt changes or Drive uploads. Documentation/reproduction:
  docs/GRAPH_SUPPORT_COVERAGE_V1.md. Next: assess availability/provenance of
  additional existing GT-free neighbor annotations, without inventing support.
- Verification: new focused7/7 and unchanged V2 tests9/9 PASS. Guarded full
  suite520 tests,0 failures/errors,2 Windows platform skips,434.140s. Private
  test receipt d1c12a64321828d6503165ae6b9bf2b0f4ce4d457e351e9ea17980c968977c0f.
  AST/diff/secret-pattern checks and4 private hash/ACL/replay checks PASS.
  CI for the new SHA is pending at local commit; final remote/CI readback is
  reported after push. No new Treatment plan or GCN execution.

## Automatic Weighted Arbitration V2 — 2026-11-07

- Continues implementation reference f6b028f9a706d64bc47862d19fa671f7ed352cbc.
  V1, routers, source seals and unrelated user work preserved. No human-review
  access, API calls, new embeddings or training. See docs/WEIGHTED_ARBITRATION_V2.md.
- Fixed GT-free rule2P+N+Q+T-A-2C-U permits experimental third-class switches;
  requires observed P/N support, thresholds3/4. Missing evidence stays null.
  Existing embedding/edge storages extracted without unpickling or GT decoding.
- Actual score freeze56e485e635ac915d07a0bb1b8849f5beb9017bd6f1ca9028192a64de335c0417;
  separate GT-only receipt4f909e83ff9ce6245f62b1ee7a2d4202c200100f9cab79f86d1e8db3d15f5451.
  R0/R1: zero switches/fixes/harms/net gain, matching V1 switch count.
  P positive5/4; N unknown37/37. No thresholds changed after observation.
- EXPLORATORY_NOT_INDEPENDENT:74 observations,57 unique nodes,17 shared.
  No new Treatment plan because no switch; GCN NOT_RUN_BLOCKED pending separate
  authorization/admission and contamination audit. All training admissions zero.
- Guarded full discovery511 tests:0 failures/errors,2 platform skips (Windows
  POSIX-permission case and unavailable OS symlink creation),475.838s. Final
  focused9/9 PASS also covers the two evaluator-integrity tests added after full
  discovery began. AST3 files and diff checks PASS. Private full-test receipt
  364f45af0b1ae758432f992726958c8a7d276ce5cd4876775ce6d0be2432718b.
  GitHub Actions NOT_RUN for this unpushed slice; PUSH_PENDING. Drive not updated.

## Correction features / post-hoc outcomes slice — 2026-11-07

- Fast-forwarded existing main to 8f880075dd6494efbb48912e757957634c93dea3;
  both mandatory handoff/ledger documents read, unrelated user work retained.
- Actual R0/R1 original+overlay receipt replay froze74 GT-free observations /57
  unique nodes at e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe.
  Separate evaluator then reproduced Narrative->Blind fix/harm7/6 and3/2,
  all five outcomes retained; private outcome SHA1501dac6d417511503cfb8a9a03bf3310beba6b6927ab956d9b1b131c668109c.
- Conservative eligibility equals V1; no duplicate V2. All74 shadow abstain,
  zero admissions. No-op Control/Treatment plans identical per router (93/78
  existing baseline labels), seeds0..9; actual GCN NOT_RUN_BLOCKED pending
  independent training approval, graph-feature and test-contamination audit.
- No API calls, router/policy changes, historical writes or human-review access.
  Final synthetic checks16/16 PASS (18.249s), syntax/diff checks PASS; full suite
  and GitHub Actions not run in this slice. Local commit remains PUSH_PENDING.
  See docs/CORRECTION_FEATURES_V1.md for scope, hashes and remaining test/report gaps.

## Independent semantic Blind Review Pack V1 — 2026-11-06

- Small offline CLI sara3.blind_review_pack reuses pinned input admission,
  R0/context, frozen closeout/final-report proof and existing PrivateAudit.
  Exact context c41b7a6e..., contract59fd3de6... and freeze03625722... required.
- Two owner-local private packs each contain37 unchanged target texts, seven
  frozen class definitions, neutral primary-topic rubric and blank templates.
  Secret-keyed case IDs and separate deterministic reviewer orderings; node
  mapping/provenance/seed stay in owner_private. No predictions/vetoes exported.
- Synthetic packet + related closeout regressions20/20 PASS. Actual Windows
  pack generation completed separately; no review, GT, provider calls, label
  admission or training. Original frozen journal/receipts and user work preserved.
- Implementation reference before this slice: b73b90a85286f626918c661f5eecf3a44438def3.
  Task explicitly authorizes a scoped main commit/push; remote status reported
  after execution. No Drive upload or permission to share reviewer files.
- Docs: docs/BLIND_REVIEW_PACK_V1.md. Next: owner inspects metadata/hash checks;
  actual independent reviews and later analysis require separate authorization.

## README documentation milestone - 2026-11-06

- Rebuilt the root README with method lineage, historical/SARA flowcharts,
  matched historical result summaries, local startup, architecture and recovery
  boundaries. Preserved the earlier operational README in docs/OFFLINE_OPERATIONS.md
  with an explicit supersession note and repaired relative Markdown links.
- Included two existing, visually inspected local GraphScope screenshots under
  docs/assets with provenance. These depict a local working-tree preview including
  uncommitted frontend work, not a verified deployed or committed frontend.
- Implementation reference: f75d2e4 (prior to this documentation-only commit).
  Eight-node continuation remains PROPOSED_NOT_AUTHORIZED; no live dispatch,
  private journal reconciliation, GT decoding or real training in this task.
- Documentation verification: local Markdown targets/README anchors, JPEG headers (original PNG extensions corrected),
  copy SHA-256 equality, four historical table rows against the website JSON,
  and staged diff/credential-pattern review. No scientific regression rerun.
- GitHub: local documentation commit is PUSH_PENDING; no remote backup verified
  by this task. Google Drive: no upload. Raw response admission remains partial.
- Next approved action: owner review and manual GitHub push; scientific execution
  remains subject to the existing explicit authorization boundaries.

Date: 2026-11-02 (America/Los_Angeles).

- Blind-only post-observation completion prepared, NOT DISPATCHED. Entry:
  python -B -m llmgnn_sara.pilot.blind_only_gapgpt. Exactly682,2396,653 blind only,
  max3 new dispatches; no comparisons even after valid non-abstaining outputs.
  Explicit scientific amendment, not completion of the original paired protocol.
  Reuses existing engine/ledger/audit; source seals and full immutable history of
  637 and both1243/130 phases verified. Prior comparison rejections remain genuine
  FAIL; blind diagnostics remain distinct from original REJECTED terminal states.
  Identity policy, settings, prompts, L1, router and arbitration unchanged.
  Fresh blind-only amendment/privacy/list/limits/USD0.10/dispatch approvals required;
  proposed reservation is not a billing guarantee. Conditional estimate USD0.0056832,
  declared aggregate49152 input/1536 output. No retries or automatic resume.
  New real calls0/3; validity/abstention of new nodes unobserved, not inferred.
  Historical usage excluded from new totals; paired_protocol_complete=false.
  Focused59 PASS (25.722s); full324,323 PASS/1 Windows symlink SKIP (149.381s),
  network and actual human-session access guarded. Protected95 artifacts including
  user untracked diagnose_gapgpt_post130.py unchanged; sealing/no-resume/syntax PASS.
  L2 NOT_ASSESSED; no accepted labels, GT or training. Docs GAPGPT_BLIND_ONLY_COMPLETION.md.
  Parent7ed0ccc12be713c9c509fe0eb9203b3aa9e681f1; PUSH_PENDING; no Drive upload.
  Next: owner runs fixed blind-only CLI with fresh local approvals; never rerun
  started scopes or historical halted commands. User untracked file not committed.

- Exact identity correction/post130 continuation prepared, NOT DISPATCHED.
  Old remaining predicate allowed alias+revision; newer revision-only conjunction
  excluded requested alias. New owner-approved policy sara.gapgpt.identity.
  exact_alias_revision.v1 admits ONLY gpt-6-luna/gpt-6-luna-2026-09-22 under fixed
  GapGPT endpoint/request/wire context. Provider-reported, not upstream proof.
  Old contracts and REJECTED records unchanged. Preserved130 HTTP200 replay passes
  corrected identity, legacy parser and L1, non-abstaining; separate private
  versioned diagnostic in gapgpt_130_identity_reassessment; no accepted label.
  Entry python -B -m llmgnn_sara.pilot.post130_gapgpt:130 comparison only, then
  682,2396,653 blind/conditional comparison; max7 calls. No130 blind or637/1243
  requests. Uses existing engine/ledger/audit; new exact contract and fresh local
  policy/privacy/scope/limits/USD0.10/dispatch approvals required. Estimate
  USD0.0132608 under declared caps/rates, not billing guarantee. New calls0.
  Focused53 PASS (23.643s); final full318,317 PASS/1 Windows symlink SKIP
  (146.334s), network and actual human-session access guarded. Protected86 files
  unchanged; sealed admission, old no-resume guards, syntax/diff checks PASS.
  L2 NOT_ASSESSED; no label promotion, GT or real training. Docs GAPGPT_POST130_IDENTITY.md.
  Parent076a18e1318409ce1869c26ecad72dd1938502df; PUSH_PENDING; no Drive upload.
  Next: owner executes new scoped CLI after fresh terminal approvals; never retry
  a started scope or reset earlier ledgers. Historical usage excluded from new totals.

- Four never-attempted feasibility scope prepared, NOT DISPATCHED. Entry:
  python -B -m llmgnn_sara.pilot.four_gapgpt. Reuses the same continuation engine,
  ledger and private audit; no new verifier. Fixed130,682,2396,653 blind/conditional
  comparison, maximum8 calls. No637/1243 requests of either phase. Prior1243 comparison
  remains genuine REJECTED/L1_QUOTE_NOT_FOUND; raw/request/context/ledger/approval
  and preserved-blind lineage hashes reverified. All prior ledgers remain immutable.
  Exact approved revision/temp1/n1/max_tokens512/L1 wrapper v1 and seals unchanged.
  Fresh local amendment/privacy/scope/limits/USD0.10/dispatch approvals required;
  estimate USD0.0151552 under declared caps/rates, not verified billing or guarantee.
  Private final summary includes six-node history, new phase intent denominators,
  confirmed responses, usage/missingness and costs; historical usage excluded from
  new totals. Any failure/uncertainty halts; no retries or automatic resume.
  Final focused67 PASS (25.956s). Full309:308 PASS/1 Windows symlink SKIP (135.088s)
  before final lineage assertion; that assertion and its negative regression covered
  by final focused run. Initial fixture dependency-key assumption fixed, not a live
  validator defect. Protected77 artifacts unchanged; syntax/sealing/admission PASS.
  New real calls0; no new usage or charge claim. L2 NOT_ASSESSED; no labels promoted.
  Docs GAPGPT_FOUR_NODE_EXECUTION.md; parent5f35bd1a2c05ea0b4f7a6bd6b7b7c305e33dcc3e.
  PUSH_PENDING; no Drive upload. Next: owner confirms and executes new four-only CLI;
  never rerun old halted commands or a started new scope.

- Outstanding-only amended feasibility continuation prepared, NOT DISPATCHED.
  Entry: python -B -m llmgnn_sara.pilot.outstanding_gapgpt. Explicit post-observation
  approval required for preserved1243 non-abstaining blind's comparison. Original
  REJECTED ledger and separate L1 diagnostic remain immutable; never redispatch
  637/1243 blind. Then130,682,2396,653 blind/conditional comparison; maximum9 calls,
  not10. Exact returned revision only; temperature1/n1/max_tokens512, no explicit
  reasoning_effort, L1 decorative matcher v1. Source/seals/context/raw/diagnostic
  hashes and all potential outstanding request identities verified. No old blind
  imported as a fabricated COMPLETED intent. SQLite contract/cursor, immutable
  lineage and private audit bind new requests; no retry/automatic resume.
  Fresh local amendment/privacy/exact-list/limits/USD0.10/dispatch approvals and
  hidden key input required. Estimate USD0.0170496 under declared limits/rates,
  not verified billing or a financial guarantee. New real calls0; no new usage.
  Focused85 PASS (20.429s); full302,301 PASS/1 Windows symlink SKIP (146.657s),
  network and actual human-session access guarded. Protected68 artifacts unchanged;
  old batch restart guard still PASS. L2 NOT_ASSESSED; no labels promoted.
  Docs GAPGPT_OUTSTANDING_CONTINUATION.md; parent27e0bff8616ade0f8742c5f0c41df14d62a6c4a5.
  PUSH_PENDING; no Drive upload. Next: owner runs new scoped command and confirms
  locally; do not rerun a started continuation or old halted commands.

- Post-observation L1 amendment: sara.l1.decorative_quote_match.v1 removes one
  balanced ASCII/curly double-quote wrapper for exact matching only; raw responses
  stay unchanged. Malformed/nested wrappers, edited/fabricated text remain rejected.
  Preserved1243 blind: original HTTP200/JSON PASS/L1_QUOTE_NOT_FOUND/REJECTED;
  separate private diagnostic under revised rule L1 PASS, source-exact, no accepted
  label, L2 NOT_ASSESSED. Original batch remains halted; no comparison/new dispatch.
  Nodes130,682,2396,653 still not attempted. Private versioned receipt in
  .local_artifacts/gapgpt_1243_l1_reassessment; never committed.
  Relevant106 PASS (35.621s); full289,288 PASS/1 Windows symlink SKIP (134.399s).
  Guards blocked network and actual human-review access. Initial full run found
  two synthetic fixtures cutting unmatched boundary quotes; only synthetic exact
  excerpt selection fixed, all router/protocol assertions retained. Synthetic batch
  setup isolated from real intents; production no-resume guard independently PASS.
  Protected67 artifacts including P0, pilot seals, all live receipts/ledgers and
  frozen/authentic inputs byte-unchanged; syntax/diff checks PASS.
  Docs L1_DECORATIVE_QUOTES.md; parent69294627a4b5cfc1de58aae4e220c14d9d5f1069.
  PUSH_PENDING; no Drive upload. Next: separately review continuation, no automatic
  restart, retroactive acceptance or semantic/GCN claims from diagnostic L1 PASS.

- Remaining genuine feasibility batch implemented, NOT DISPATCHED by agent.
  Command: python -B -m llmgnn_sara.pilot.remaining_gapgpt. Fixed remaining order
  1243,130,682,2396,653; excludes637 permanently. Exact owner-approved GapGPT
  alias/revision mapping, provider-reported provenance, temperature1 wire variant;
  original sealed scientific messages unchanged. Max10 calls, fresh aggregate
  USD0.10 local approval, hidden key input, no retries/resume or label promotion.
  Source hashes25/seals/authentic inputs/prior637 admission verified; existing
  operational ledgers show only637 attempts. Private summary is generated only
  on actual owner execution, not from synthetic tests. No batch API calls yet.
  Tests: final relevant65 PASS (18.021s); full281,280 PASS/1 Windows symlink SKIP
  (141.578s), guarded against network and actual human-session access. Source-pin
  binding/summary-only final additions rechecked by final focused suite, including
  missing-cost UNKNOWN handling. Initial
  focused run exposed a test SQLite connection cleanup issue, fixed before passing.
  Protected58 files byte-unchanged; AST checks PASS. Docs GAPGPT_REMAINING_PILOT.md.
  Parent ec471097bef7387ce2fce1504e87d3694b75baae; PUSH_PENDING; no Drive upload.
  Next: owner supplies fresh local privacy/wire/revision/budget/exact-dispatch
  approvals. Actual costs unknown; USD0.018944 estimate is conditional, not a cap.

- Temperature1 owner canary diagnosis: HTTP200, returned dated model revision
  differs from exact requested alias; original REJECTED intent remains immutable.
  Saved content independently passes offline legacy L1, abstains, no label accepted.
  Diagnostic fix preserves usage before model check and reports
  RETURNED_MODEL_MISMATCH; no revision auto-approval, new identity or dispatch.
  Guarded relevant46 tests PASS (24.955s); initial sandbox run failed private-audit
  Windows ACL setup, rerun outside sandbox with socket connections blocked passed.
  Full suite not rerun. Seals/authentic inputs checked by prepare, original private
  artifacts unchanged during read-only reanalysis. See docs/GAPGPT_TEMPERATURE_FIX.md.
  Parent a98233147b92e22a0b6719e1bc1e832b629da168; PUSH_PENDING, no Drive upload.
  Next: explicit exact-revision compatibility decision, not another paid retry.

- Concrete GapGPT compatibility fix (2026-11-01): second endpoint attempt
  actually returned400 invalid_request_error/unsupported_value, param temperature;
  provider says0.7 unsupported, only default1. Not another observed401/key error.
  No claim of zero cost; usage absent. New explicit derivative changes ONLY
  temperature to1, preserves sealed message/body fields and all original files.
  Identity gapgpt-app-t1-blind-637-canary-v1; same api.gapgpt.app; new state
  .local_artifacts/gapgpt_app_t1_canary_637. Command python -B -m
  llmgnn_sara.pilot.canary_gapgpt_t1 requires fresh approvals including APPROVE
  TEMPERATURE 1 and USD0.10. No actual new dispatch/key access during preparation.
  Focused23 PASS; guarded relevant45 PASS (15.761s); both failed intent/receipt
  trees byte-unchanged, seals/nine inputs/P0 PASS. Full suite not rerun.
  Docs: docs/GAPGPT_TEMPERATURE_FIX.md. Parent bbcf9346d8d8607d5c7146d6b508999b3ace4e24;
  PUSH_PENDING; no Drive backup. Next: owner reviews explicit generation delta
  and confirms locally; no retry/fallback/comparison or label promotion.

- Endpoint mismatch diagnosis/fresh canary prepared (2026-11-01): original
  live blind637 attempt observed401 invalid_api_key/authentication_error at
  api.gapapi.com; charges UNKNOWN. Owner confirms correct previously working key.
  Historical source also configures that host/Bearer format; raw successful HTTP
  receipts not independently recovered here. Current panel specifies api.gapgpt.app:
  routing/endpoint policy is leading hypothesis, not proven cause/user error.
  New explicit profile gapgpt-app-blind-637-canary-v1 targets api.gapgpt.app with
  same sealed body, separate .local_artifacts/gapgpt_app_canary_637, fresh local
  approvals/hidden key/USD0.10 reservation. Old profile/REJECTED state retained;
  all original receipt/SQLite byte fingerprints unchanged. No new request sent.
  Command: python -B -m llmgnn_sara.pilot.canary_gapgpt. Docs:
  docs/GAPGPT_ENDPOINT_CANARY.md. Focused21 PASS; guarded relevant43 PASS (15.812s);
 31+13 seals/nine inputs/exact wire/P0 PASS. Full suite not rerun. No real key read.
  Parent383a6ad66cda0e4cc3521a54b650b1e5e2aa8a20; PUSH_PENDING; no Drive backup.
  Next: owner reviews new scope and confirms locally before at most one new blind
  canary; no fallback/retry/comparison, no label or training change.

- GapGPT single blind637 owner-operated canary CLI prepared (2026-11-01), NOT
  EXECUTED. python -B -m llmgnn_sara.pilot.canary verifies31+13 seal members,
  nine inputs and exact wire; fixed endpoint/model; hidden getpass or process env,
  mandatory interactive privacy/wire/declared-limit/USD0.10/final confirmations.
  One fixed private ledger path blocks all repeat intents; full reservation
  retained. UNCERTAIN committed before mocked/owner-authorized dispatch. No retry,
  redirect, comparison or fallback. Raw/usage privately audited with secret-echo
  redaction; strict legacy parser/L1; no accepted labels. General live guard intact.
  Local byte preflight/declarations do not verify vendor tokenization or guarantee
  billing cap. Financial/privacy/compatibility confirmations remain owner actions.
  Focused18 PASS; full guarded256:255 PASS,1 Windows symlink SKIP (173.906s);
  extra positive-quote HTTP smoke PASS. No real credentials/network/human reviews.
  P0/seals/frozen inputs/routers/arbitration/GraphScope untouched. Docs:
  docs/GAPGPT_BLIND_CANARY.md. Parent efc20838696351ffbea27eb660676df0d523470d.
  PUSH_PENDING; no Drive backup. Next: owner reviews/accepts scoped conditions and
  runs command manually in local terminal; never supplies key in chat/Codex.

- GapGPT provider decision fixed by owner (2026-11-01): GapGPT/gpt-6-luna,
  no alternatives/migration. docs/PROVIDER_PREFLIGHT_V1.md updated accordingly.
  Exact historical endpoint remains api.gapapi.com/v1/chat/completions in recovered
  source; temperature0.7/n1/user message, no max_tokens historically. New sealed
 512 cap/legacy JSON task remain canary compatibility questions, not disproven
  by another provider's rules. Provisional owner-reported screenshot rates0.10/M
  input,0.50/M output; screenshot not independently inspected. Conditional full-
  reservation USD0.0227328, not actual billing or approved cap. Current admitted
  inputs contain no provider usage fields; no usage/billing claim.
  Checks:3 recovered source pins,9 inputs,parsed replay,31+13 seals PASS; no live,
  credentials, GT or training. No unit/full rerun for docs-only delta.
  Remaining only wire/endpoint confirmation, privacy approval, actual limits and
  monetary cap, credential availability attestation and explicit live permission.
  Parent dee4978d02a3f4ae21e4d7232351fb6317233a2b; PUSH_PENDING; no Drive backup.

- Minimal provider preflight (2026-11-01): docs/PROVIDER_PREFLIGHT_V1.md.
  Historical GapAPI endpoint/model/settings preserved; official GapAPI documentation
  unavailable through searches/fetch, account availability/prices/privacy UNKNOWN.
  OpenAI official catalog confirms gpt-6-luna only for its own public offering;
  no transfer of compatibility/pricing/privacy to gateway. Omitted reasoning with
  temperature0.7 and deprecated max_tokens require explicit wire review. Prompt
  strings can remain unchanged; any wire derivative needs separate approval/hash.
  Reference-only Standard cost scenarios: USD0.0227328 uncached,0.027648 higher
  cache-write input at declared maxima; not GapAPI prices or approved billing cap.
  Checks PASS:31+13 seals,12 exact message mappings/settings, closed live guard;
  Decimal arithmetic and official-doc review. Docs-only; no unit/full/provider test.
  NO_GO: gateway/model/revision/parameters/privacy/tariff and owner authorization.
  No code/credentials/manifest changes. Parent6b2f828628b80488fa69e3b4d54339e8812a4bc3;
  PUSH_PENDING; no Drive backup. Next: owner supplies official gateway docs URL.

- Third-agent feasibility scientific protocol v1 documented (2026-11-01):
  docs/THIRD_AGENT_FEASIBILITY_V1.md fixes existing six nodes/legacy blind-first
  and conditional comparison, maximum12 calls/16384 declared input/512 output,
  no retries. Execution NO_GO: provider/revision/privacy/prices/financial approval
  and final owner authorization unresolved; no live command/transport enabled.
  Genuine outputs need two separate blinded human reviews per eligible phase
  response; prior consensus cases remain development feedback, not validation.
  L1/L2/arbitration/GCN claims separated; no reviewed-label promotion.
  Checks PASS:31+13 seal members, nine pins,12 current-builder payload matches,
  cohort/classes/blind boundary/placeholders, P0 and live block. Docs-only;
  no unit/full rerun, private review or runtime modification. Parent
  8b30ac51d104a4f3e39d3f31b0b1a21b47db5922; PUSH_PENDING; no Drive upload.
  Next: owner reviews this scope and resolves gates; only minimal bridge/ledger
  and genuine-output packet adapter require later approved engineering.

- L2 Shadow v1 (2026-11-01): evaluation-only private bindings/intake/comparison
  reuse existing human-review/rubric validation and legacy/rich L1. States:
  NOT_ASSESSED, ASSESSED, INVALID, UNAVAILABLE. No semantic judge or label gate.
  Explicit receipt comparison only; no session/form discovery. Synthetic versus
  self-attested external-human provenance separated; genuine identity/independence
  not authenticated, illustrative cases never gold. No genuine assessments ingested.
  Focused6 PASS; guarded full238:237 PASS,1 Windows symlink SKIP (167.383s).
  Before/after synthetic runtime equal; downstream promotion rejected. Existing
  full tests cover routers/replay/experiment; no runtime import of evaluation.
  Nine inputs/P0/31+13 seal members verified intact; real reviews/network guarded.
  Docs: docs/L2_SHADOW_MODE.md. Parent ad25b50af364dbb3038440e18f67799f81f4b127.
  PUSH_PENDING; no Drive backup. Next: coordinator supplies actual completed,
  independently obtained blinded human assessments with truthful provenance;
  preserve L2 runtime NOT_ASSESSED and existing acceptance boundaries.

- Pilot readiness completed offline (2026-11-01): new separate SQLite rehearsal
  binds immutable contract/context and every request; PENDING->UNCERTAIN before
  hypothetical dispatch, then COMPLETED/REJECTED only after parser/L1 and private
  audit readback. Raw-byte SHA and audit-receipt SHA distinct. No automatic retry,
  migration or terminal rewrite. Caps12/16384/512; financial approval UNRESOLVED;
  live unconditionally disabled. Focused3 PASS; guarded full232:231 PASS,1 Windows
  symlink SKIP (339.736s). Nine inputs/P0/31+13 seal members verified unchanged.
  Docs: docs/PILOT_READINESS_DRAFT.md. No real human-review/network/GT/training.
  Parent f61d11f21f8eb4e7d4b7d839741e45a85435d463; PUSH_PENDING, no Drive backup.
  Next: owner reviews legacy recommendation and unresolved provider/model/privacy/
  financial conditions before any separately approved live protocol. No transport.

- Offline routing experiment draft v1 (2026-11-01): pinned manifest connects
  R0 control/R1-v2/R2-v1 candidates to existing legacy pipeline via explicit
  VerifiedSelection; default routing/schema/policy unchanged. Optional Semantic/
  R1-v1 selections retained. All5 selections/budget37, nine sources, cohort/evidence,
  prompts/schema/classes and R2 primary4/17/16 seed/order pinned; live NOT_AUTHORIZED.
  Manifest SHA dd2cd784e58cbb905ffa6c337782ef67073960a11ca32d07e8f9991dcc71387b.
  Exact offline identity binds full effective request/context; comparison requires
  actual blind class and full raw-blind hash. Private readback-verified in-process
  fixture cache shares successful responses only; uncertain/rejected attempts blocked.
  Primary union62: maximum124 calls versus222 standalone; tokens/prices/costs unknown.
  Synthetic3-arm test:203 logical requests,114 dispatches,89 reuse hits; reviewed
  accepted0, third-class accepted0, L2 NOT_ASSESSED, labels unique per arm. Frozen
  unreviewed retention93/73/84 is baseline behavior, not verifier scientific evidence.
  Initial focused11 PASS; full229:228 PASS,1 Windows symlink SKIP (199.481s), no failures;
  all12 new tests included. Real human session/network guarded; only temporary
  synthetic review records in regressions. P0/nine inputs/31+13 pilot members intact.
  Docs: docs/OFFLINE_ROUTING_EXPERIMENT.md; report: reports/routing_experiment_offline.json.
  Parent cbf70ffb32020f0d90cda738e215c20f9ac5991c; PUSH_PENDING; no Drive backup.
  Next: review draft/provider-wire/privacy/replicate/budget/durable recovery gates
  before separately approved live pilot. Cache is not crash-durable or live billing
  protection; no real inference/GT/training/L2 gate, scientific winner or pilot freeze.

- Router robustness review v1 (2026-11-01): no router redesign. Independent
  R2 primary/stage metadata exactly matches; all24 prespecified4-seed x6-order
  scenarios retain37 unique IDs. Seed-only overlaps33..34/37; order-only28..37;
  joint25..37. Stage priority is material, not an interchangeable schedule.
  Five-router comparison unchanged. All140 target/neighborhood inputs available;
  canonical legacy/rich hashes invariant per node. Actual legacy fixture wiring
  confirms conditional blind/comparison behavior for five test-injected selections.
  R1/R2 remain standalone, NOT integrated into runtime; no transport verified.
  Focused6 PASS; full217:216 PASS,1 Windows symlink SKIP (152.281s), no failures.
  Real human-review session/network guarded; review-schema tests use temporary
  synthetic records only. P0/nine inputs/31+13 pilot members unchanged.
  Decision: docs/ROUTER_ROBUSTNESS_DECISION.md; report: reports/router_robustness.json.
  Draft role-based set: R0 control; R1-v2/R2-v1 candidates; Semantic/R1-v1 ablations.
  No scientific winner or protocol freeze. L2/arbitration/defaults/GraphScope intact.
  Parent dc08852ce918c9ac8ed91f97d6dcded2ed351e11; PUSH_PENDING; no Drive backup.
  Next: reviewed offline experiment manifest/adapter contract and matched verifier
  protocol/call-budget accounting; no live execution, GT or training authorization.

- R2-candidate v1 (2026-11-01): prospective stratified hybrid, not historical
  R2 recovery. Prespecified37-slot allocation: unknown4 (version/node hash order),
  observed17 (R1-v2 among covered nodes), candidate16 (remaining R0 rank), then
  global R0 backfill for exhausted pools. No incompatible score averaging.
  Authentic140 selects9 disagreements/9 HH at reconstructed80/10 Atlas-unknown;
  unknown4 from exploration and6 from candidate stage. Overlap with R0/Semantic/
  R1-v1/R1-v2 is27/26/17/19. Four prespecified quota sensitivities retain36/37;
  observed/candidate cutoff ties13/3. These are descriptive, not error detection.
  Eleven focused +80 related regressions PASS (91,7.913s); prior four router
  selections unchanged, nine pins admitted, P0 and31+13 pilot seal members intact.
  No human-review access/tests, GT/provider/training, runtime/default/pilot freeze,
  verifier/L2/arbitration/GraphScope changes. Report: reports/r2_candidate_comparison.json.
  Design/results: docs/R2_CANDIDATE.md and docs/R2_CANDIDATE_RESULTS.md.
  Parent0264f93b750d3d181eb52dc08c22f3405a2e72a2; PUSH_PENDING; no Drive backup.
  Next: review objective/quotas/stage priority and cutoff effects before any
  separately authorized prospective protocol freeze. No accuracy claim.

- R1 coverage review (2026-11-01): three prespecified policies separate lexical
  mismatch from missingness; v2 uses observed-risk=(D+I[match]*(M+A))/3, coverage
  C=max_hits/4 only for descending tie priority, then ascending node ID. Neutral
  imputes1/2; original v1 unchanged. All13 prespecified settings recorded before
  new results; primary choice follows absence-is-not-positive-evidence principle.
  Descriptive140: coverage zero30/partial51/multi59; primary zero-match selections
  v1=30, neutral12, v2=0; disagreements7/9/6; HH at reconstructed80=15/16/20.
  V2 may under-route unknown cases; coverage tie sensitivity retains25..33/37.
  Longer observed-match texts indicate possible vocabulary/length bias, not error.
  Twelve focused +68 related tests PASS (80). Initial descriptor-guard test error
  corrected; syntax/report reproducibility and31+13 seal members verified.
  No human-review access/tests, GT, provider, training, Atlas or runtime changes.
  Docs: docs/R1_COVERAGE_POLICY.md, docs/R1_COVERAGE_RESULTS.md; machine report:
  reports/r1_coverage_comparison.json. Parent e9ffdb6aba110461e2fa3c07348b62d38fdbf8b5.
  PUSH_PENDING; no Drive backup. Next: review observed-risk versus unknown-case
  exploration and tie preference before freezing any prospective pilot selection.

- R1-candidate v1 (2026-11-01): independent fixed37 offline ranking uses equal
  disagreement/candidate lexical mismatch/lexical ambiguity terms; exact rational
  scores and node-ID ties. Historical formulas remain MISSING_EVIDENCE. Existing
  R0/Semantic runtime, P0, both six-node seals and all nine inputs unchanged.
  Descriptive140 comparison: R1 selects7 disagreements/15 HH agreements (>=80
  reconstructed convention), all30 no-keyword-match articles. This exposes sparse
  Atlas coverage, not accuracy. Overlaps R0/Semantic25, R0/R1=17, Semantic/R1=13.
  Focused8 + related60 PASS (68); first sandbox run13 temp-permission errors,
  rerun outside sandbox passed. Syntax and31+13 sealed members PASS. No human
  review material/tests accessed; L2, arbitration, prompts and GraphScope untouched.
  See docs/R1_CANDIDATE.md and reports/r1_candidate_comparison.json.
  Parent f887c2ed5d65c45094da0d39b284e2e00a3b6a2d; PUSH_PENDING, no new Drive backup.
  Next: scientific review of prespecified lexical/missing-evidence defaults before
  any future selection freeze. No R2, live calls, GT evaluation or training.

- Independent L2 review infrastructure: evaluation.l2_reviews prepares blinded
  allowlisted packets and blank forms, imports hash-bound human-self-attested
  records and compares outcomes/dimensions without adjudication or label gates.
  Actual private session .local_artifacts/l2_human_review_session contains12
  packets/12 blank forms for two unassigned slots; completed human reviews0,
  missing12. No reviewer identity or genuine independence is authenticated.
  Only each working/<slot>/ folder may be given to its human; coordinator,
  author benchmark and other review files must remain hidden. No sharing occurred.
  Focused13 plus related27 tests PASS; full suite not rerun for this isolated slice.
  Test completed-record fixtures are temporary syntax data, not human/LLM reviews.
  Benchmark/nine input hashes/P0/six-node seals unchanged; runtime/arbitration,
  routing and GraphScope untouched. Report: reports/l2_human_review_workflow.json;
  instructions: docs/L2_HUMAN_REVIEW_WORKFLOW.md.
  Parentb34ef1f4aa4f54a56e5182e6c37835baa0d83ba1. PUSH_PENDING; no Drive backup.
  Next: coordinator assigns two genuine independent humans and collects their
  completed forms offline. L2 stays NOT_ASSESSED; no gold standard or holdout
  promotion, API/GT evaluation/training/automatic adjudication is introduced.

- L2 evaluation foundation: docs/L2_EVALUATION_RUBRIC.md defines four dimensions
  and SUPPORTED/UNSUPPORTED/AMBIGUOUS/NOT_ASSESSED as reviewer outcomes, not gates.
  Six pinned development cases at nodes90/130/734 contain controlled interpretations
  and author rationales/citations. All illustrative; independently reviewed0, no
  gold standard or holdout. Runtime L2/arbitration remains unchanged NOT_ASSESSED.
  evaluation.l2_benchmark validates structure, source/quote hashes, L1 and reviewer
  provenance only; never scores semantics or imports into runtime. New12 tests and
  related33 regressions PASS; full suite not rerun for this isolated slice.
  Nine input hashes, P0 and six-node seals verified unchanged; GraphScope untouched.
  Report: reports/l2_benchmark_validation.json. Parent84900e9e6933354dc912167e37b3ae671716e6b2.
  Next: independent offline reviews with author opinions initially hidden, followed
  by a reviewed immutable reviewer-record contract. No judge, prompts, thresholds,
  API/GT evaluation/training or Drive writes. PUSH_PENDING.

- Rich evidence: explicit response_version=sara.verifier.rich_evidence.v1 adds
  primary_topic, support/counter source-quote-claim items, auxiliary warning and
  uncertainty diagnostics. All quotes use existing L1 provenance rules; L2 remains
  NOT_ASSESSED and conservative arbitration is unchanged. Legacy is still default;
  rich request/schema is new and unsealed, not an authorized live prompt.
  Eighteen focused tests PASS; full155:154PASS,1Windows symlink SKIP (103.177s).
  Offline wheel build and isolated stdlib-only wheel import PASS; no static type
  checker is configured. Legacy authentic replay matches its report exactly;
  P0, both six-node seals, nine inputs, routing/providers/old prompts and GraphScope
  are unchanged. Report: reports/rich_evidence_validation.json; contract:
  docs/RICH_EVIDENCE_SCHEMA.md. Parent661d80065c3b5c12e01e8e9286c5cd3239ae644a.
  No API/model prompt execution, token-count requests, GT evaluation, real training,
  new Judge, third-class acceptance or Drive writes. PUSH_PENDING.
  Next: review L2 semantics for topic/claim alignment and counter-evidence; schema
  completeness alone must never approve a label.

- Authentic L2-boundary replay: sara3.replay uses nine pinned JSON inputs, real
  target/neighborhood/Atlas data and clearly synthetic fixed verifier responses.
  Eleven cases and both full140 routers each run twice deterministically (330
  mock calls total, zero provider calls). Each router reviews37; reviewed accepted0.
  Baseline unreviewed retention is93/R0 and82/semantic, not verifier approval.
  Genuine non-topic copyright quotation passes L1 but L2 stays NOT_ASSESSED.
  Private audit readback validates fixture bodies/request hashes/blind references;
  injected write failure and timeout explicitly report unavailable raw responses.
  Seven new integration tests PASS; full regressions137:136PASS,1Windows symlink
  SKIP (106.738s). P0, six-node seals, original runtime/routing/prompts/policies and
  GraphScope remain unchanged. Report: reports/authentic_l2_replay.json;
  instructions: docs/L1_EVIDENCE_VALIDATION.md. Parent6f8fe0c45e308cf01dd25d53647bfdf5ba33bcec.
  No semantic judge, API/token-count, GT evaluation, real training or Drive writes.
  Next: review offline L2 semantic-support criteria; no acceptance enabled here.

- L1/V1 slice: strict abstention/schema/source/quote validation now fails closed.
  Private current-user ACL audit stores decoded raw responses and proposals before
  comparison; public decisions contain no raw evidence or third-class suggestions.
  L1 provenance is NOT semantic approval. Reviewed candidate agreement now abstains
  with L2_NOT_ASSESSED; unreviewed baseline policy/routing/prompts/caps are unchanged.
  Full suite129:128PASS,1Windows symlink SKIP; final focused19PASS after small
  source/ACL hardening. Nine frozen inputs, P0 and six-node seals hash-verified
  unchanged. See reports/l1_validation.json and docs/L1_EVIDENCE_VALIDATION.md.
  Initial Windows ACL self-check failed, then native protected-DACL setup and
  unsafe-ACL rejection passed. POSIX permission behavior is not tested here.
  Parent: 803234dc20eee1748bc7c588593958539b8d6cbc on main; PUSH_PENDING.
  No API/token-count/GT evaluation/real training or historical archive writes.
  Next: review an offline L2 support contract with irrelevant-but-genuine quote
  fixtures before enabling any reviewed-label acceptance.

- P0 arm specification: docs/HISTORICAL_P0_ARM_CONTRACTS.md separates reported
  Judge002/V1 intent, current reconstructed fields and missing original contracts.
  Offline adapter decisions and provider gates remain unresolved; no runtime change.
  Parent for this documentation slice: 628aa6484e6a8670de6e394cd7b40ec0f393de26.
  Content/eight local links and P0/six-node seal hashes checked successfully;
  documentation-only slice, no new runtime tests or provider checks executed.

- Historical P0: manifests/historical_p0.json reconstructs eight fixed nodes and
  twelve logical node/arm records, not twelve stage intents or recovered P1 wire.
  Read-only pilot.historical_p0 validator admits three pinned frozen inputs;
  all eight nodes align and all four Group B nodes have agreement/HH >=80.
  R1 membership remains REPORTED_UNVERIFIED; missing prompts/schemas/policies/wire
  remain MISSING_EVIDENCE. Nine focused tests and ten existing pilot regressions
  PASS; syntax checks PASS. Six-node seals are hash-verified unchanged.
  See reports/historical_p0_validation.json for executed checks and initial
  Windows sandbox temporary-directory errors resolved by running outside sandbox.
  Parent before this slice: 573b1e42507d57ddeafc212a165b7f388d965ffe on main.
  No new transport, verifier prompts, provider requests, GT use or training.

- Objective: defensible ground-truth-free annotation and downstream GCN research.
- GraphScope v2: isolated static React/TypeScript atlas in web/graphscope/;
  follows research commit 3e56105d51017bcd19729b417bf3eea3987c0c11.
  Six sections inspect 478 recorded nodes/525 edges, 280 frozen annotations and
  160 saved historical FeatProp GCN fits. Offline routing flags are distinct
  from verifier judgments. No new science execution or public deployment.
  See web/graphscope/VERIFICATION.md for checks, limits and publication steps.
- Authorization: owner-approved V2 Scientific Handoff; offline implementation and
  frozen parsed-sample replay on existing main are approved without all840 raw
  bodies. No live APIs, real training, GT decoding, Drive writes or GitHub actions.
- Implementation: one installable package src/llmgnn_sara with io, selection,
  annotation, frozen PS, reconstructed SARA2/3, downstream, isolated evaluation
  and CLI. No historical startup/module execution or untrusted pickle loading.
- Latest independently executed baseline: all280 frozen target-arm votes matched,
  including class, confidence (abs1e-12) and fallback; four PS cohort-arm checks
  matched retained/deleted order, labels and confidence. This is stored-parsed
  replay, not raw parsing, annotation rerun or GCN result reproduction.
- Verification: full suite92 tests,91PASS,1Windows symlink SKIP; subsequent6CLI
  regressions PASS after Primary routing-boundary adjustment. Actual4-node GCN
  forward and real cached cl100k_base Consensus parity/budget tests PASS.
  See reports/offline_test_results.json and offline_implementation_verification.json.
- Runtime: Python3.12.14, Torch2.15.0+cpu, PyG2.7.0, NumPy2.3.5, tiktoken0.14.0
  installed locally; versions/requirements recorded in configs/. Initial TLS
  issuer error was resolved using already-trusted OS roots, never disabling TLS.
  This differs from the receipt-reported historical successful environment.
- Authentic-input milestone: all140 target texts and recorded neighborhoods admitted
  from nine pinned JSON inputs;280 stored prompts match840 sample references.
  Both GT-free routers run at37 review slots on140 nodes. Deterministic fixture
  outputs are NOT real verifier findings: R0 retains105/abstains35; semantic
  retains90/abstains50; failures0. Exact inputs/hashes are saved outside Git.
- Pilot: six fixed GT-free nodes637,1243,130,682,2396,653; maximum12 future calls,
  no retries, immutable blind inputs and conditional comparison templates. Persistent
  intent ledger enforces12 intents/duplicate rejection across restarts. No client
  dispatch exists. GapAPI/gpt-6-luna historical settings match pinned sources;
  current compatibility, max_tokens support, prices and retention remain unverified.
- Tests for this milestone:102 executed,101PASS,1Windows symlink SKIP. Existing
  class-field test updated; SQLite handles now close explicitly on Windows.
  Clean staged-source checkout also passed both stdlib-only and tokenized runs;
  tokenized pilot/artifact hashes reproduced exactly. See reports/clean_checkout_pilot.json
  and reports/authentic_pilot_tests.json.
- SARA limits: Policy002 exact thresholds remain missing; defaults are unvalidated
  reconstruction choices. Actual neighborhood graph bytes were not decoded or
  recomputed; evidence is hash-anchored historical recorded graph context.
- Downstream: matched CE/WCE-noPS plans for both arms and both cohorts preserve
  Primary135/Sensitivity140/sharedtest2568/seeds0..9/30epochs/loss semantics.
  Third-class proposals cannot enter training. Optimizer/training never executed.
- Source provenance:25 original pre-Codex snapshots preserved; pure Narrative
  module and GCN class reused. Newly reconstructed code is not recovered Codex-era
  source. Stored prompt hash parity now verified; independent full prompt
  regeneration from canonical graph remains NOT_RUN.
- Raw gap:840 references (726fresh/30supplementary/84reused); prior84 raw byte
  readbacks remain prior evidence. This implementation verifies zero raw bodies.
  48reuses remain unresolved-access, not proven missing. Colab ZIP is pending.
- Scientific baseline: historical GCN numbers remain HISTORICAL_REPORTED; neither
  new SARA accuracy nor downstream improvement/generalization is established.
- Git: accepted prior milestone c3a4e00b03ad8260e3f2d3be28bec1a976301b56;
  parent before the authentic-input milestone is user commit
  e8cb5839e891465d9e6c0d459b992b95440e3cda. Resolve current HEAD with
  git rev-parse HEAD; this document cannot name its own commit SHA.
  No tags/remotes or verified remote code backup.
  All local commits are PUSH_PENDING. Owner performs pushes manually.
- User work preserved: user-committed recovery documents and the backup-guide x
  remain untouched. Concurrent .github/, .pnpm-store/ and web/ work is unrelated
  and excluded from this milestone's commits.
- Drive backup: historical archive read-only; dedicated destination unapproved,
  no upload/readback. Updated incremental artifact plan is not a completed backup.
- Next gate: owner reviews both artifact and pilot seal hashes; verify current
  GapAPI account/model parameters, tariff, credentials mechanism and retention
  before separate spending/data-sharing approval. Colab raw ZIP is still pending.
  Real inference, GT evaluation and GCN training remain unauthorized.

## Slice 1 (2026-11-06): reporting-only repair

The owner reports a halted, local-only Cora-140 R0 Rich V2/4096 live run: 53 recorded attempts (52 COMPLETED, one REJECTED for node 1814 compare / L1_DUPLICATE_EVIDENCE; zero UNCERTAIN). The private journal was **not** available to the GitHub editing session. No new dispatch, GT evaluation, L2 approval or GCN training was performed. The batch remains halted; never resume it from these changes.

The corrected run-report layer distinguishes nodes with no persisted intent after halt from genuine UNCERTAIN intents. The new `python -B -m llmgnn_sara.sara3.gateway_usage_report` reconciles only local, content-hash-verified private receipts with declared tariff inputs. COMPLETED/REJECTED/UNCERTAIN and ALL ATTEMPTS are separate, and incomplete provider usage produces a null total estimate rather than a fabricated invoice. Historical summary JSON and terminal states remain immutable. The reported 80760 input / 33192 output / 18619 reasoning tokens and USD 0.0246720 are **owner-provided observations**, pending local read-only reconciliation, not independently verified by this GitHub change. L1/prompt/router/arbitration remain unchanged.

## Slice 2 continuation preparation — 2026-11-06

Historical Cora140/R0 Rich V2/4096 remains halted: owner read-only evidence reports 52 COMPLETED, one L1_DUPLICATE_EVIDENCE REJECTED (node 1814 / compare), zero UNCERTAIN. This is a valid structural L1 rejection; the semantic polarity of its claims is NOT established. No reclassification, retry or training proposal for node 1814.

`python -B -m llmgnn_sara.sara3.gateway_continuation` is a **read-only local preflight** requiring existing frozen/authentic inputs, original private output root, exact gateway config, and context hash. It reconstructs and validates EVERY historical identity, wire/payload digest, saved Blind dependency, receipt SHA and strict L1/usage for completed responses. It refuses uncertainty/tampering. It reports never-dispatched blind IDs, conditional comparisons, cumulative capacity, and fresh amendment/authorization requirement. No API key or HTTP is used.

A minimal **synthetic-only** continuation overlay verifier exists for regression: original SQLite/receipts are read-only, any new fixture intents are appended exclusively under a distinct continuation directory tied to the original run; original REJECTED remains a terminal abstention. This is NOT a new experiment or a fresh 74-call budget. It does not enable live dispatch or create an owner approval. A separate amendment and explicit future authorization are required before extending this adapter to live traffic; do not invoke the old live runner to resume the halted run. No GT, GCN, L1, Prompt, Router or Arbitration modifications were made.

## Slice 3 — frozen, unapproved continuation amendment (2026-11-06)

`configs/sara3_gapgpt_continuation_amendment_v1.json` is a PROPOSAL, never a live authorization. It binds the exact original context/contract SHA, Cora140 R0 Rich V2 4096, 53 historical intents (52 L1-passing COMPLETED, node 1814 comparison terminal REJECTED), and exactly eight no-intent Blind nodes (2487,2396,2238,2317,2022,2379,2490,2534). At most 16 new logical calls (8 Blind plus conditional comparison), cumulative at most 69 of the original 74; the five spare slots cannot be repurposed. The node 1814 rejection is a valid structural L1 failure, not evidence of semantic polarity disagreement; no label promotion/retry.

Read-only local command: `python -B -m llmgnn_sara.sara3.gateway_continuation --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --output-root .local_artifacts/sara3_gapgpt_live_cora140_r0_4096_20261105 --gateway-config configs/gapgpt_rich_v2_output4096_proposed.json --expected-context-sha256 c41b7a6ecec46a2a99c3b570f7e0b093756db4db98d692f4bb956135584599f8 --amendment-file configs/sara3_gapgpt_continuation_amendment_v1.json`. It validates 52 historical full L1/receipt/identity replays and the exact rejection and reports that owner dispatch approval is FALSE. No API key/provider request, GT or GCN.

`AmendedSyntheticContinuationVerifier` enforces the eight-ID 16-call/69-cumulative scope only in fake-wire offline tests, with exact dependency and no retry; no live constructor or runner mode is enabled. A separate prospective owner-reviewed live authorization and integration is REQUIRED in a future slice, never inherited from the earlier stopped batch. Original journal/receipts/prompt/L1/router/arbitration remain untouched.

## Slice 4 — separately approved live continuation adapter (2026-11-06)

`src/llmgnn_sara/sara3/gateway_live_continuation.py` adds a real-network adapter over the existing `DurableGapGPTVerifier`, but does **not** automatically authorize or invoke any request. It preserves the original 53-intent journal/receipts read-only; all new intent/response writes go only to the deterministic private `continuation_amendment_v1/journal` overlay. Exact amendment SHA, execution context, model/price/call contract, frozen eight nodes, cumulative 69/74 ceiling, 16-new-call ceiling, prior node 1814 L1 rejection, completed blind dependency and existing strict L1 are enforced. Preflight replays all 52 original completions and checks the rejected receipt before any network dispatch. It re-verifies saved continuation receipts on restart. An unresolved/REJECTED new attempt stops further dispatch (no retry). No GT, GCN, L1, router, prompt or arbitration changes.

Real invocation requires (1) manual owner approval in a private JSON file, **separate** from the original batch approval, with exact `sara.gapgpt.cora140.continuation_owner_approval.v1` fields and three explicit true consent flags, (2) the explicit `--enable-real-dispatch` CLI switch, and (3) local `GAPGPT_API_KEY` environment variable. Do not store keys or private receipts in Git. The owner must run the CLI locally; no provider calls run in CI. The amendment JSON remains `PROPOSED_NOT_AUTHORIZED` because the separate owner approval is a distinct private act, not an inherited flag. The resulting continuation is still *not* a semantic L2 evaluation or GCN training.

## GT-free Closeout frozen outcome (owner-local, 2026-11-06)

Owner ran the read-only Cora140 v2 continuation closeout on Windows after local merge `10857d9`; private artifact bytes are not available on GitHub. Result from the verified local tool: 67 intents = 66 COMPLETED, 1 REJECTED (node1814 compare), 0 UNCERTAIN; 37 Blind COMPLETED, 29 Comparison COMPLETED, 7 Blind abstentions including continuation nodes2396 and2534. All non-abstaining comparisons present. Automated Concordance v1 screened 29 pairs and generated **zero proposals** (0/37 routed, 0/140 cohort). Reasons: 11 counter-evidence, 9 third-class diagnostic, 7 blind abstentions, 6 auxiliary-method warning, 2 verifier abstentions, 1 topic drift, 1 historical L1 rejection. All 67 attempts have usage; 102376 prompt/41279 completion/23505 reasoning tokens; user-declared-rate estimate USD0.0308771 incl. one rejected attempt; not a verified invoice. Private freeze SHA256 `03625722e672f25acb1001b59a4f4a72dd18ab0286ddb9a58a402b73895a1abb`. Local closeout 6/6 tests PASS; CI for tooling 365 total, 292 PASS, 73 SKIP. Source journals/receipts unmodified; no API/GT/Human L2/GCN run in closeout and no training admission. See `docs/SARA3_GT_FREE_CLOSEOUT.md` for precise provenance and interpretation. Do not retry Live.

## GT-free first-veto findings and next gate (owner-local, 2026-11-06)

Owner's private post-freeze diagnostic reported 11/11 Blind/Comparison class agreement for Counter-evidence (7/11 historical candidate agreement), and Third-class: 9/9 frozen B1/Narrative agreement, 9/9 Blind outside candidates, 7/9 Comparison outside candidates, 7/9 cross-phase agreement. Diagnostic-only class-index counts: 0:3, 1:1, 4:2, 5:1, 6:2. Source freeze SHA-256 `03625722e672f25acb1001b59a4f4a72dd18ab0286ddb9a58a402b73895a1abb` unchanged. This is GT-free owner-reported aggregate analysis, not accuracy or training admission. `gateway_secondary_veto` now supports read-only co-occurring flags; CI at `93896e3` passed 377 tests (304 passed/73 skipped). Future independent evaluation and experimental Arbitration/GCN require separate predeclared protocols and appropriate approval.

## Secondary-veto co-occurrence result and independent evaluation gate (2026-11-06)

Owner-local `gateway_secondary_veto` confirmed 20 focus nodes against the fixed closeout freeze. First-veto Counter-evidence stratum (11): 11/11 auxiliary warnings, 11/11 primary-topic *string* difference, 4/11 no shared target quote, 1/11 uncertainty reason; counter-evidence in both phases 10/11. Third-class stratum (9): 9/9 counter-evidence in either phase, 9/9 auxiliary warnings, 8/9 primary-topic string difference, 4/9 no shared quote; both-phase counter-evidence 5/9 and auxiliary warning 6/9. Overlapping flags are descriptive, not proof of semantic topic drift or counterfactual acceptance. No provider/GT/Human L2/GCN calls; zero admitted labels, same freeze. Next **proposed, unexecuted** study: blinded independent adjudication across all 37 routed nodes (nine third-class exploratory subgroup), net correct/incorrect class corrections vs shared baseline and small-n uncertainty; separate authorization for human evaluation, no GT in inference. Only after evidence may an independently versioned Arbitration/GCN protocol be considered. See `docs/SARA3_GT_FREE_CLOSEOUT.md`.

## Cora GT-only post-hoc scoring tool (2026-11-06; real owner run pending)

A separate `src/llmgnn_sara/evaluation/cora_gt_shadow.py` is committed on existing main at `9d8d530`. It requires the **original pinned** `cora_random_sbert.pt` (SHA256 `9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466`) and checks class-name mapping and 2708-node `data.y`. Frozen 37-node R0 decision/GT-free source proof is verified *before* GT loading; only the isolated evaluator reads GT, never annotation, Arbitration V1, acceptance or training. Reports B1, Narrative v0, Blind (30/37 class coverage), Comparison (27/37 class coverage, including two Comparison abstentions), paired correct/false corrections, per-class counts, 11 Counter-evidence, nine Third-class and seven agreeing Third-class cases. GT-derived aggregate result is content-addressed and owner-private; no node-level labels or correctness outputs. No provider, Human L2 or GCN runs. CI at `9d8d530`: 394 tests, 321 pass/73 skipped including six GT shadow tests. **Real accuracy not yet measured**: graph and private output are owner-local on Windows, not on GitHub. This is exploratory/post-hoc and not an independent test set; do not tune prospective Arbitration V2 or GCN on these evaluated labels. See `docs/CORA140_GT_ONLY_EVALUATION.md`.

## Verified owner-local GT baseline and multi-router audit protocol (2026-11-06)

Owner Windows verified the exact original Graph SHA256 `9285c2af...` and completed both isolated real `cora_gt_shadow` and `cora_node_journey` with pinned R0 Freeze; no API or training. On the 37 genuinely reviewed R0 nodes: B1 16/37 correct, Narrative v0 21/37, Blind 19/30 covered and Comparison 17/27 covered; Narrative vs Blind paired correct/false corrections 7/6, vs Comparison 4/4. On **all 140**, R0 flagged 22/45 nodes where either frozen baseline was wrong, with 15 selected non-errors and 23 missed errors; the 36 same-label, both-wrong nodes included 13 selected and 23 missed. A descriptive but **not admitted** Narrative+Blind fallback had 102/140 correct versus Narrative 101/140. These are post-hoc/oracle descriptive findings, NOT a GCN outcome or independent test of V2.

To ensure comparisons include ALL versions rather than only R0, `src/llmgnn_sara/evaluation/cora_all_routers_gt.py` on existing main at `dfb52b2` now compares R0, Semantic-v0, R1-v1, R1-neutral-v1, R1-v2 and R2-v1 with budget37/140, 5 GT error definitions, nodewise private GT, per-class diagnostics and all 15 paired router overlaps. All selections are recomputed from the identical pinned GT-free frozen 140-node inputs before GT access. The only actual SARA-3 response set remains **R0**; other router/verifier outcomes are not invented, and historical R1 equivalence is not claimed. Synthetic CI: 408 tests, 335 pass/73 skipped including all five new checks. **Owner-local real multi-router GT audit execution still pending** because original graph and private R0 report reside only on Windows. Documentation `docs/CORA140_ALL_ROUTERS_GT_EVALUATION.md`. No router policy, journal, Freeze, training admissions, model calls, GCN or GraphScope work was changed.

## Completed owner-local multi-router Cora GT-only diagnosis (2026-11-06; overrides prior pending status)

Owner Windows log confirms existing main fast-forward to `d60535b`, all five focused `test_cora_all_routers_gt.py` tests PASS, exact trusted original Cora Graph SHA-256 check, and `ALL_ROUTER_GT_AUDIT_VERIFIED_PRIVATE` after content-addressed private JSON SHA-256 verification. Report digest `0a9995617437da309c1272338cb2794f9050fa54dbb940b37dfba7fd7c792ba8`. All six policies recomputed GT-free before diagnostic truth access; fixed budget37 from identical frozen140, error defined as B1 OR Narrative v0 wrong (45/140), and secondary criterion both agree on an incorrect label (36/140). **These are owner-observed post-hoc ROUTER results, not live verifier observations for non-R0 policies.**

| Router | 45 baseline errors selected | 37 selected nonerrors | 45 errors missed | Precision | Recall | agreed-wrong found /36 | overlap with real R0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| R0 (real verifier run) | 22 | 15 | 23 | 59.4595% | 48.8889% | 13 | 37 |
| Semantic-v0 | 19 | 18 | 26 | 51.3514% | 42.2222% | 10 | 25 |
| R1-v1 | 24 | 13 | 21 | 64.8649% | 53.3333% | 17 | 17 |
| R1-neutral-v1 | 21 | 16 | 24 | 56.7568% | 46.6667% | 12 | 18 |
| R1-v2 | 14 | 23 | 31 | 37.8378% | 31.1111% | 8 | 15 |
| R2-v1 | 19 | 18 | 26 | 51.3514% | 42.2222% | 10 | 27 |

R1-v1 has the best descriptive detection on this 140-node cohort: +2 caught errors versus R0, +4 caught **same-label wrong agreements**, but its current implementation is a prospective **reconstruction**, not the unrecovered historical R1. R1-v2 performs worst on this particular post-hoc oracle detection, despite its prior defensible missing-evidence design choice. Equal-budget selections are not interchangeable: R0 and R1-v1 share only17 nodes, with 13 baseline errors shared, 9 errors uniquely caught by R0 and 11 uniquely caught by R1-v1; their union would capture33/45 errors across57 unique nodes, exceeding the fixed37 review budget and NOT constituting an authorized experiment. The original sample was used for development and these differences do not establish statistical/held-out superiority or a GCN improvement.

**Only 37 R0 nodes have actual frozen SARA-3 Blind/Comparison outputs.** Do not use the existing 17 shared nodes to claim an R1-specific Agent evaluation, and do not fabricate completion on non-R0 selections. No new provider calls, Human L2, policy revision, label admission, or GCN training was performed. Full nodewise GT stays solely in owner-private `.local_artifacts/sara3_all_routers_gt_v1/`. Next scientific gate: preregister independent evaluation to compare R1 candidate routing and conditional SARA-3 corrections before training effects. This section records owner-supplied aggregate output only and supersedes older "real multi-router GT audit pending" notes; see `docs/CORA140_ALL_ROUTERS_GT_EVALUATION.md`.

## R1-v1 full real Agent assessment protocol — 2026-11-07; live R1 NOT YET DISPATCHED

The owner requested the same 140-node detection → 37-node actual Blind/Comparison → paired GT label correction → freeze/admission/fallback analysis as the successful R0 run. The prior six-router owner-local GT audit established for R1-v1 (fixed37/140): 24/45 either-baseline errors captured (64.8649% precision, 53.3333% recall), 13 false alarms, 21 missed, 82 true negatives and17/36 agreed-wrong errors captured. **These are ROUTER results only.** R1-v1 selected nodes have no genuine frozen R1-model results yet. The previously recorded R0 37-node real Agent run is NOT a reusable R1 response or new R1 call.

The existing `sara3.runner` / `gateway_run` already accepts router `r1_v1`, supports a separate private journal and explicitly owner-approved `--owner-approval-file`, and must NOT borrow the R0-only `scoped_owner_authorization`. The new standalone post-run module `src/llmgnn_sara/evaluation/cora_r1_real_gt.py` (existing main `a9104bc` and subsequent checks) validates SHA-addressed real R1 Gateway report, its source selection/context, *real positive provider-attempt counts*, no GT/admission in inference, then reads the historical pinned Graph only for an isolated owner-private post-hoc evaluation. Reports complete/partial run status, 140-node baseline GT and R1 flags, 37-node Blind/Comparison selective accuracy/abstentions and paired corrections/damage vs both Baselines, frozen V1 admissions and fixed hypothetical Narrative fallback. No fictitious calls or R1 outcomes. Owner-only node GT stays in private content-addressed JSON, stdout is aggregates only. `docs/CORA140_R1_V1_REAL_AGENT_EVALUATION.md` documents a distinct `live-preflight`, a separate human opt-in for up to 74 possible R1 calls under UNVERIFIED user-declared USD0.40 budget/model/retention conditions, a distinct private R1 journal, no automatic retry and post-run GT stage. R0 freeze, all router policies, response schema, source artifacts and training are unchanged.

CI at `4d860b5` PASS: 414 tests, 341 pass/73 skipped; six focused new R1 tests include complete fake Gateway R1 end-to-end and replay, rejection of unapproved live dispatch, refusal of fake-source GT scoring, split of abstentions versus corrections, corruption fail-closed and private audit readback. **No real provider calls, real R1 results, GCN or L2 performed by the changes.** Genuine R1 Agent scoring requires owner-local Windows data and explicit separate provider spend/privacy approval; do not infer final R1-vs-R0 correction success or GCN improvement from synthetic CI.

## Owner-completed R1-v1 actual GapGPT and GT-only partial-run evaluation (2026-11-07)

Owner Windows transcript confirms fast-forward to `e607d8a`, all 6 focused R1 synthetic integration/scorer tests PASS, local preflight R1_v1 37/140 budget up to74 calls, provider terms/prices/unverified as declared, hidden-key setup and **separate explicit owner R1 approval**. Then a **REAL** new R1_v1 GapGPT Gateway run was attempted with 51 calls; persisted outcome `BLOCKED_NO_AUTOMATIC_RETRY`, **30 Blind phases completed, 20 Comparison phases completed**. Of 37 routed, 9 Blind abstentions and 7 not attempted after halt mean **only 21 Blind class predictions**, while 20 Comparison class predictions are available. No retry, journal deletion or independent new dispatch is authorized. The exact reason for provider stop is NOT determined from the public aggregate. Owner's **separate GT-only scorer** returned `R1_REAL_GT_NODE_JOURNEY_VERIFIED_OWNER_PRIVATE` after SHA verification of its private output and original pinned Graph. The user pasted aggregate results only, not nodewise GT or secret keys. Graph/journal and the private GT report remain local.

R1-v1 router detection, fixed 37/140: of45 nodes where B1 OR Narrative is wrong, TP24 FP13 FN21 TN82, precision64.8649%, recall53.3333%. For the 36 nodes both Baselines agree wrongly, found17 and missed19. R1 selected23/44 B1 errors,20/39 Narrative errors,19/38 both-wrong and7/9 baseline disagreement. R0 in contrast found22/45 and13/36 agreed-wrong, but **its actual verifier run has a different selected cohort and coverage**, so direct selective Accuracy is not a matched causal R1-vs-R0 inference.

R1-v1 GT scoring on its **37 actually routed**: B1 14/37, Narrative17/37; Blind15 correct of21 class predictions (71.4286% selective, 15/37 on all selected, 16 no class including9 abstentions and7 not attempted), Comparison13 correct of20 (65.0% selective, 13/37 on all selected, 17 no class). Paired B1→Blind: 4 corrected /1 damaged, net+3; Narrative→Blind:3/2 net+1; B1→Comparison:3/2 net+1; Narrative→Comparison:2/3 net−1. With fixed hypothetical keep-Narrative fallback, full140 true-label count: Narrative101 →102 (Blind substitutions when available) or100 (Comparison). **These are descriptive label counts, not V1 admission, GCN outcome, or independent held-out validation.** Real V1 admissions for 37 routed=0; total frozen baseline admissions across140=78, so do not misinterpret the latter as Agent admission.

First-veto counts on routed37: AUXILIARY_METHOD_WARNING12, BLIND_ABSTENTION9, COUNTER_EVIDENCE_UNRESOLVED4, L1_QUOTE_NOT_FOUND1, NOT_ATTEMPTED_AFTER_HALT7, THIRD_CLASS_DIAGNOSTIC_ONLY4. Counter-evidence4/4 Blind/Comparison correct but Narrative also4/4; zero net fixes in that stratum. Third-class: Blind2/4, Comparison1/4, Narrative2/4; net Blind0, Comparison−1. Three same-third-class Blind/Comparison cases: Blind/Comparison1/3 correct and Narrative1/3; agreement is not independent evidence. OTHER 29 cases: Blind9/13 class predictions, Comparison8/12, Narrative11/29; net Blind+1, Comparison0. These strata are small and post-hoc; they do not validate a new Arbitration threshold.

This supersedes the prior note that real R1 outputs do not exist: **a blocked partial live run now EXISTS** and was evaluated. Preserve private approval and immutable R1 journal, do not automatically retry or route GT to inference. No additional GCN training, Human L2, new Router, GT-informed admission or policy modification. Independent final GCN validation will require a frozen GT-free policy, clean data partitions and matched seeds.

## R1-v1 owner-private no-retry completion protocol (2026-11-07)

User's READ-ONLY diagnosis of actual partially completed R1-v1 Gateway: 51 attempted phases, 50 COMPLETED, 1 REJECTED, 0 UNCERTAIN. Rejected phase = Comparison, HTTP200, finish_reason stop, JSON parseable, duplicate_pair_count0, exactly `L1_QUOTE_NOT_FOUND` (source-exact quote invalid); provider usage recorded for all51, but invoice/pricing/retention remain externally unverified. Of the 37 R1-selected papers, 30 Blind phases and20 Comparison phases completed; nine Blind abstentions and 7 never-attempted Blinds remain. **Do NOT rerun/retry the original 51, alter their SQLite/content hashes, or treat the rejected class as valid.**

A new isolated `src/llmgnn_sara/sara3/gateway_r1_continuation.py` on existing main `6c148e9` implements hash-pinned read-only preflight of ALL51 original receipts, frozen R1-v1 selection/context, the one exact invalid quote, and original summary/report; a new exact amendment and *separate owner approval* are required for ONE optional live continuation. Only seven never-attempted Blinds and up to seven dependent Comparison calls may be sent, maximum14 new, cumulative maximum65 < existing original call cap74. Original journal remains READ ONLY. The overlay `r1_v1_continuation_v1/` is isolated and refuses retries/overwrites or unsettled states; original Invalid Comparison is never resent and counts as a real L1 rejection. Live CLI refuses dispatch unless all three new explicit owner permission flags match the bound source/template; no real API calls or GT were executed during development.

The separate scorer `src/llmgnn_sara/evaluation/cora_r1_continued_gt.py` verifies original and overlay provenance, cryptographically replays and cross-checks **all 37 nodes' Blind/Comparison class outputs against their exact stored receipts BEFORE** reading the pinned private Cora GT graph, then emits only aggregate post-hoc diagnostics and content-addressed owner-private node rows. It uses the existing `cora_r1_real_gt.analyze`, keeping the original L1 rejection and zero reviewed Admission, no GCN. Run instructions and privacy/cost caveats: `docs/CORA140_R1_V1_CONTINUATION.md`.

CI on `6c148e9`: **421 tests, 348 passed /73 skipped**, including an end-to-end **provider-shaped mocked** run of 51 original (50 complete + one L1 rejected), owner-approved 14-call overlay, private GT scorer with synthetic truths, and negative test proving a fully content-rehashed tampered Blind class FAIL_CLOSED before GT access. All were offline/mocked; user's REAL seven remaining Blinds **have not yet been dispatched**. A fresh owner approval is required, and any new halt is terminal until independent incident diagnosis. No policy, Router, training labels, GraphScope, original Freeze or GCN was changed.

## Owner-verified R1-v1 continuation completion and final GT-only outcome (2026-11-07)

The owner's Windows transcript verifies the **actual** isolated R1-v1 continuation finished with `CONTINUED_PRESERVING_REJECTED_COMPARISON` and separate GT-only scorer printed `R1_FINAL_GT_EVALUATION_VERIFIED`. **11 new live dispatches**, all 11 COMPLETED, 0 new REJECTED and 0 new UNCERTAIN; **62 real attempted calls cumulative** (51 original +11 continuation), with **61 completed + one original Comparison still rejected as `L1_QUOTE_NOT_FOUND`**. All **37 selected Blind phases completed** (original30 +new7); **24 Comparison completed** (original20 +new4). **12 Blind abstentions** (original9 +new3) are legitimate; hence only **25 valid Blind class predictions and24 valid Comparison class predictions**. The original 51-call Journal and all 50 historical successful receipts remain preserved and unchanged; no original rejected request was resent. The local GT scorer verified the complete authentic original/overlay receipts and original pinned Cora graph, then privately persisted owner-only rowwise truth. Owner posted only aggregate output; no node-level GT, API key, raw provider response, authorization or full receipts are in GitHub.

Fixed R1-v1 37/140 routing (unchanged): total45 where either frozen B1/Narrative wrong; TP24, FP13, FN21, TN82, Precision 64.8649%, Recall53.3333%. B1 wrong23/44 selected; Narrative wrong20/39; both wrong19/38; agreed-wrong17/36; disagreements7/9. Selected high-confidence baseline agreements15. R1 v1 remains a prospective reconstruction, not the missing exact historical R1.

**Actual R1 Agent results on routed37:** B114/37 correct, Narrative17/37; **Blind17/25** correct (68% accuracy conditional on a valid class; 17/37 on all selected), **Comparison15/24** correct (62.5% conditional; 15/37 overall). Paired, relative to B1: Blind4 corrections/1 damaged, net+3; Comparison3/2, net+1. Relative to Narrative: Blind3/2, net+1; Comparison2/3, net−1. Other paired outcomes Narrative-vs-Blind: BOTH_CORRECT14, BOTH_INCORRECT6, NO_CLASS12. Narrative-vs-Comparison: BOTH_CORRECT13, BOTH_INCORRECT6, NO_CLASS13. Descriptive, nonadmitted Narrative fallback on all140: Narrative101/140 correct, available Blind substitution102/140 (+1), available Comparison substitution100/140 (−1). **Zero reviewed R1-v1 training admissions**; reported `total_frozen_training_admissions=78` are pre-existing eligible baseline labels, NOT 78 corrected Agent labels. No GCN training.

Final first-veto reasons among selected37: AUXILIARY_METHOD_WARNING15, BLIND_ABSTENTION12, COUNTER_EVIDENCE_UNRESOLVED4, THIRD_CLASS_DIAGNOSTIC_ONLY5, L1_QUOTE_NOT_FOUND1. Counter-evidence stratum: 4/4 Narrative, Blind and Comparison correct; no net correction relative to Narrative. Third-class stratum: 5 nodes, Narrative2/5, Blind2/5, Comparison1/5; Blind +1 correct/−1 harmed (=0 net), Comparison+1/−2 (=−1 net). In 4 third-class Blind/Comparison same-class agreements, only1/4 was correct (not independent agreement evidence). Other28 nodes: 16 Blind classes with11 correct and15 Comparison classes with10 correct; 12 and13 respectively no class; Narrative11/28. New continuation added **four Blind class answers (2 correct)** and **four Comparison class answers (2 correct)**, without changing either narrative substitution net.

**R0 vs R1 are different routed cohorts.** R0 detected22/45 baseline errors vs R1 24/45; R0 Blind19/30 and Comparison17/27 correct, R1 Blind17/25 and Comparison15/24 correct, while both narrative-vs-Blind descriptive fallback net+1 over140. These comparisons do NOT establish matched R1 superiority or causal GCN improvement. This cohort has been used post-hoc with GT; any V2 Arbitration rule designed with these outcomes must be labelled exploratory and evaluated on independent untouched test data. Do not retry the now-completed continuation, reuse the original overlay, feed GT to agent/policy, change Router/Admission without a separate experiment plan, or claim a GCN outcome.

This section **supersedes earlier sections** describing the seven R1 Blind attempts as pending or the initial R1 run as blocked/incomplete. Existing main and all Freeze artifacts, original graph, GraphScope and training were unchanged by the local completion.
