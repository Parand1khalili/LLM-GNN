# Project state

Date: 2026-10-29 (user timezone: America/Los_Angeles).

- **Objective:** recover and independently validate the pre-Codex B1/Narrative v0 baseline before reconstructing SARA-2 or SARA-3.
- **Phase:** R1 approved for local recovery and offline tests; `BLOCKED_REQUIRED_RAW_RESPONSES` at full replay admission. Runtime reconstruction and parser/voter replay have not started.
- **Exact recovery:** 25 source snapshots verified against the accepted audit SHA-256 values. Includes six modified and thirteen added research files; thirteen includes the project-root `startup.py`. No Codex-era source is recovered.
- **Evidence baseline:** canonical Cora/A²X hashes; 840 consistent sample references; frozen 135/140 cohorts and 2568 common test IDs; 100 seed receipts/results and 180 weight byte hashes/ZIP CRC verified in the prior read-only audit. PS deletion orders were independently recalculated on pseudo-labels. GCN results were not re-executed.
- **Raw replay gap:** all 840 response paths/hashes are listed. Only 84 raw files were byte-checked in the prior audit. 48 reused-response folder IDs remain unresolved because of the connector's 1000-item listing cap and empty targeted search results; existence is not disproved. The other raw files still require complete readback and validation.
- **Current architecture:** source evidence + manifests + Colab raw-response exporter + independent offline ZIP admission and synthetic tests. Proposed runtime package is documented in `docs/R1_PLAN.md`; it has not been created.
- **Successful historical environment (receipt-reported):** Python 3.13.16, NumPy 2.1.3, Torch 2.11.0+cpu, PyG 2.7.0. Legacy environment files differ. No dependency installation or historical environment execution occurred.
- **Safety:** no provider calls, training, GT decoding, unsafe unpickling, historical Drive writes or recovered-script execution. Runtime GT-isolation tests are `NOT_RUN` because there is no reconstructed runtime.
- **Git:** one local `main` repository; resolve its current commit with `git rev-parse HEAD`. Local commit author is user-supplied. No remote is configured; all local commits are `PUSH_PENDING`. The user performs pushes manually; remote backup is unverified.
- **Drive backup:** existing historical archive read-only; no new upload. Separate destination and incremental manifest are proposed, not approved or verified.
- **Latest discovery:** complete 21-page connector search plus exact-name search returned no usable folder matches. The 48 responses are unresolved through the connector, not proven missing. A self-contained user-run Colab exporter reads the pinned original manifests; default scope covers all 840 selected responses including all 84 reused.
- **Tool verification:** 26 synthetic recovery/admission tests: 25 passed, one skipped because this Windows account cannot create OS symbolic links; ZIP symlink rejection passed. These are tool safety tests, not historical replay or runtime GT-isolation validation. Actual Colab interactive mounting/downloading is untested here. See `reports/raw_recovery_tool_tests.json`.
- **Initial Git readiness:** commit `b0249a829e31e32ad6c90bc56779d6a9c1cea0ce` and clean tree verified before tooling edits. No unwanted datasets/checkpoints or high-confidence credential patterns were detected in its 40 files. Proposed manual-only private destination: `parand1khalili/llm-gnn-sara`; not created or remotely verified.
- **Next action:** user runs `scripts/colab_recover_responses.py` in the archive-owning Colab account and provides its ZIP. Independently verify all 840 raw bytes; then STOP for user approval before any pure parser/voter implementation or replay. No genuine ZIP has been provided yet; current real-data admission remains BLOCKED.
- **Unrecovered:** Codex-era SARA-2, E0/E1, SARA-3, P0/P1/P2 implementations/tests/ledgers; full executable checkpoint remains unknown.

No annotation or GNN improvement is established by this intake.
