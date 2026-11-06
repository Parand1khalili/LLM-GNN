# Cora140 SARA-3 — GT-free Live Closeout v1

This read-only tool analyzes **both** owner-local protected journals, verifies every original and continuation request identity, binding, raw-body SHA, protected receipt SHA, original terminal L1 rejection and every L1-passing receipt. It recomputes Automated Concordance v1 from frozen B1/Narrative candidates and verified Blind/Comparison results, without GT, Human L2 or GCN training. The original response bodies and private report are never exported.

`python -B -m llmgnn_sara.sara3.gateway_closeout --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --output-root .local_artifacts/sara3_gapgpt_live_cora140_r0_4096_20261105 --gateway-config configs/gapgpt_rich_v2_output4096_proposed.json --amendment-file configs/sara3_gapgpt_continuation_amendment_v1.json --private-report-sha256 e5405937b5862a90b128a811bcae8d93c9774c1b7d9c21fea0bf92814ea9f5b6`

The only write is a canonical, content-addressed metadata-only JSON file in the private output root's `closeout_v1/` directory. No original or continuation journal/receipt/phase ledger is written. The stdout JSON reports hash, usage and declared-rate estimated cost per state/origin; if the REJECTED response has no valid usage, the exact total is null with a *known-usage-only lower-bound*, not a fabricated provider invoice.

`accepted=false` and `training_class_index=null` apply to **all provisional proposals**, not necessarily unreviewed frozen baseline decisions. Closeout verifies this against the persisted private final run. It verifies the exact two absent Comparison phases correspond to truly `abstain=true` Blind outputs, and refuses any absent Comparison after non-Abstain. It never restarts the live adapter or grants admission to GCN.

**Local Git preservation:** Owner Windows `main` contains independent research/merge commits (latest owner-reported local merge `10857d9`) and uncommitted GraphScope files. Do not use `git pull --ff-only`, reset, rebase or force-push on this diverged history; fetch then non-destructively merge `origin/main` on the existing `main`. Keep unrelated files uncommitted.

## Observed owner-local final freeze — 2026-11-06

**Evidence:** Successful owner-run Windows closeout stdout and its metadata-only canonical `closeout_v1` JSON, reported after local merge `10857d9`. This is a **locally verified, user-supplied result**, not independent remote access to private bytes. Neither original nor continuation receipts/ledgers, raw model responses, article text, quotes, authorization, or human-review records are included in this repository.

- Frozen protocol: Cora140, R0, 37 selected, Rich Prompt V2, `sara.arbitration.automated_concordance.v1`; context SHA-256 `c41b7a6ecec46a2a99c3b570f7e0b093756db4db98d692f4bb956135584599f8`, gateway contract SHA-256 `59fd3de634a4aabae97fc9df02c396c5c435819e8b7f4cdbde1fe7837a8c165f`, amendment SHA-256 `b73579deeed6c8799ec80e5d9a6558469e571104c9ce489597b845ff6ffe789e`.
- Intent reconciliation: **67 attempts** (53 historical + 14 continuation); **66 COMPLETED, 1 REJECTED, 0 UNCERTAIN**. Phase totals: **37 Blind COMPLETED**, **29 Comparison COMPLETED**, **1 Comparison REJECTED** (`1814/compare`, `L1_DUPLICATE_EVIDENCE`). No duplicate identities or missing non-Abstain comparisons reported; historical journal write operations zero as reported by live runner.
- Seven valid Blind abstentions: **637, 734, 2396, 568, 2534, 94, 552**. For continuation **2396 and 2534** both had actual `abstain=true` validated by the closeout replay; their absent comparisons were conditional omissions, not lost work.
- Automated Concordance: **29 L1-valid paired cases screened; 0 proposals**. Proposal coverage **0/37 routed (0%)**, **0/140 cohort (0%)**. Proposal label-source and class distributions are empty, **not** an observed all-class-accuracy result. The final mutually exclusive reason counts over 37 routed nodes are: `COUNTER_EVIDENCE_UNRESOLVED` 11, `THIRD_CLASS_DIAGNOSTIC_ONLY` 9, `BLIND_ABSTENTION` 7, `AUXILIARY_METHOD_WARNING` 6, `VERIFIER_ABSTAINED` 2, `PRIMARY_TOPIC_DRIFT` 1, `L1_DUPLICATE_EVIDENCE` 1. No `ACCEPT` from the automated screen.
- Provider-reported usage for **all 67 attempts**, including the L1-REJECTED attempt: **102,376 prompt**, **41,279 completion**, **23,505 reported reasoning tokens**. Completed (66): **100,953 prompt / 40,384 completion**, declared-rate estimate **USD 0.0302873**. Rejected (1): **1,423 prompt / 895 completion**, declared-rate estimate **USD 0.0005898**. Combined estimate **USD 0.0308771**; historical **USD 0.0246720**, continuation **USD 0.0062051**. This is **not a verified provider invoice or pricing attestation**.
- The private run report and freeze reconciled; source receipt/identity integrity and cross-journal distinctness reported true. **No proposal was admitted to training** (zero provisional proposals, `accepted=false`/`training_class_index=null` for any proposed item); frozen, unreviewed baseline decisions are a separate category. GT, Human L2 and GCN training were **not** performed. No scientific accuracy or downstream GCN improvement is implied.
- Content-addressed owner-local freeze: schema `sara.gapgpt.cora140.gt_free_closeout.v1`, **SHA-256 `03625722e672f25acb1001b59a4f4a72dd18ab0286ddb9a58a402b73895a1abb`**. Owner's Windows read-only closeout completed without errors; six targeted local tests passed. GitHub CI at commit `9116c0d`: 365 tests, 292 passed / 73 skipped, including all three new closeout tests.

**Conclusion:** The exact frozen Automated Concordance policy produces zero provisional training proposals despite 29 structurally valid paired evaluations. This establishes zero *proposal coverage under that strict policy*, not label inaccuracy or model failure. Further GT-free diagnosis is descriptive only; any human L2, admission change or GCN experiment requires a separate protocol.

## Next stage: strictly post-freeze GT-free veto diagnosis

The `gateway_failure_diagnostics` command reads **only** the existing SHA256-frozen closeout summary and the immutable, content-addressed private *final run report* (no response-receipt, article text, GT or model call). It computes sanitized aggregate breakdowns for the observed 11 `COUNTER_EVIDENCE_UNRESOLVED` and 9 `THIRD_CLASS_DIAGNOSTIC_ONLY` cases: baseline-candidate agreement, Blind/Comparison class agreement, which phases selected outside the frozen candidate set, and the index distribution of *diagnostic-only* third classes. It cross-checks final reasons, 37 routed nodes, 29 screened pairs, frozen counts, and zero training admission; any mismatch fails closed. No per-node predictions, article/quote text, raw body, Human Review or private report fields appear in its JSON output.

```powershell
$root = ".local_artifacts/sara3_gapgpt_live_cora140_r0_4096_20261105"
$env:PYTHONPATH = Join-Path $PWD "src"
$env:PYTHONDONTWRITEBYTECODE = "1"
& .\.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.gateway_failure_diagnostics `
    --output-root $root `
    --freeze-sha256 03625722e672f25acb1001b59a4f4a72dd18ab0286ddb9a58a402b73895a1abb `
    --private-report-sha256 e5405937b5862a90b128a811bcae8d93c9774c1b7d9c21fea0bf92814ea9f5b6
if ($LASTEXITCODE -ne 0) { throw "Post-freeze diagnosis failed closed" }
```

This is a descriptive **post-hoc analysis of an already observed cohort**, not evidence of accuracy, ground-truth validation, a retuned arbitration policy, or training eligibility. The scientific freeze SHA remains unchanged. This command writes no new files; capture only its whitelisted stdout if a local derived result is needed.

## Optional post-freeze secondary-flag audit (GT-free, no API)

Run `gateway_secondary_veto` locally **after** the immutable v1 closeout. This small diagnostic validates the private terminal run, content-addressed arbitration and Blind/Comparison phase audits, frozen request payload hashes and exact-quote L1, and reports **aggregate-only** co-occurrence of Counter-evidence, Auxiliary warning, Uncertainty, Topic drift and Missing shared target quote within the 11 Counter-evidence and 9 Third-class first-veto groups. All screening criteria and source Freeze remain unchanged. Later guards were not evaluated by the original first-veto decision, so these flags are descriptive, **not counterfactual accepted labels**.

```powershell
$env:PYTHONPATH = Join-Path $PWD "src"
$env:PYTHONDONTWRITEBYTECODE = "1"
& .\.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.gateway_secondary_veto `
 --output-root .local_artifacts/sara3_gapgpt_live_cora140_r0_4096_20261105 `
 --freeze-sha256 03625722e672f25acb1001b59a4f4a72dd18ab0286ddb9a58a402b73895a1abb `
 --private-report-sha256 e5405937b5862a90b128a811bcae8d93c9774c1b7d9c21fea0bf92814ea9f5b6
if ($LASTEXITCODE -ne 0) { throw "Secondary veto audit FAIL_CLOSED" }
```

No source journal writes, model calls, GT, Human L2 or GCN training. Do not commit the private audit inputs. Independent semantic evaluation and any prospective new Arbitration/GCN protocol are **separate later studies**.

## Owner-observed post-freeze first-veto results (2026-11-06)

**Source:** Owner's Windows `gateway_failure_diagnostics` output, reconciled against the immutable closeout freeze SHA-256 `03625722e672f25acb1001b59a4f4a72dd18ab0286ddb9a58a402b73895a1abb`. The underlying private report/receipts are **not on GitHub**, so these are owner-local observed aggregates, not newly replayed remote data. Local targeted tests: **7/7 PASS**.

| First-veto group | Count | Frozen baseline agreement | Cross-phase agreement | Third-class breakdown |
| --- | ---: | ---: | ---: | --- |
| `COUNTER_EVIDENCE_UNRESOLVED` | 11 | B1/Narrative 7/11 | Blind/Comparison 11/11 | Neither phase outside frozen candidates |
| `THIRD_CLASS_DIAGNOSTIC_ONLY` | 9 | B1/Narrative 9/9 | Blind/Comparison 7/9 | Blind 9/9, Comparison 7/9 outside candidates |

Diagnostic-only third-class index distribution: **0:3, 1:1, 4:2, 5:1, 6:2**. These indices are not verified labels. The frozen first-veto policy stops at the first barrier, so later evidence-related flags may co-occur. `gateway_secondary_veto` (above) is a separate **metadata-only descriptive check** of those co-occurrences, not a rule change or estimate of how many cases would be accepted if a veto were suppressed.

**Research progression (distinct protocols):** (1) classify co-occurring veto flags on the same frozen 20 nodes; (2) separately preregister an independent semantic evaluation and its GT isolation/bias controls without tuning on evaluation labels; (3) only after supporting evidence, preregister an experimental Arbitration policy and matched GCN ablation including coverage, per-class retention, seeds and evaluation separation. No new API calls or GCN training are part of the current diagnostic.
