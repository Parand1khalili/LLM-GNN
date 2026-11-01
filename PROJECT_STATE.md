# Project state

Date: 2026-10-31 (America/Los_Angeles).

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
