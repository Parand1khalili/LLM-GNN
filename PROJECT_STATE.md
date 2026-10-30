# Project state

Date: 2026-10-30 (America/Los_Angeles).

- Objective: defensible ground-truth-free annotation and downstream GCN research.
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
- SARA limits: no recovered exact Policy002 thresholds. Defaults are explicit new,
  unvalidated reconstruction decisions. Synthetic verifier demo works; frozen
  real-target text/context is not yet admitted, so actual selected reviews abstain
  with zero completed reviews. Ledger is offline/in-memory, not live-ready.
- Downstream: matched CE/WCE-noPS plans for both arms and both cohorts preserve
  Primary135/Sensitivity140/sharedtest2568/seeds0..9/30epochs/loss semantics.
  Third-class proposals cannot enter training. Optimizer/training never executed.
- Source provenance:25 original pre-Codex snapshots preserved; pure Narrative
  module and GCN class reused. Newly reconstructed code is not recovered Codex-era
  source. Full prompt hash parity for all140 real targets remains NOT_RUN.
- Raw gap:840 references (726fresh/30supplementary/84reused); prior84 raw byte
  readbacks remain prior evidence. This implementation verifies zero raw bodies.
  48reuses remain unresolved-access, not proven missing. Colab ZIP is pending.
- Scientific baseline: historical GCN numbers remain HISTORICAL_REPORTED; neither
  new SARA accuracy nor downstream improvement/generalization is established.
- Git: verified implementation commit c3a4e00b03ad8260e3f2d3be28bec1a976301b56;
  this state/backup-record update is a later metadata commit (resolve current HEAD
  with git rev-parse HEAD). No tags/remotes or verified remote code backup.
  All local commits are PUSH_PENDING. Owner performs pushes manually.
- User work preserved: docs/MANUAL_GITHUB_BACKUP.md contains x; two untracked
  recovery handoff/master-plan documents remain excluded from agent commits.
- Drive backup: historical archive read-only; dedicated destination unapproved,
  no upload/readback. Updated incremental artifact plan is not a completed backup.
- Next approved work: validate the owner's Colab ZIP when supplied; admit pinned
  GT-free real target text/context for offline verifier integration; resolve exact
  Policy002 specification before any historical equivalence claim. Real inference,
  GT evaluation and GCN training still require separate explicit approval.
