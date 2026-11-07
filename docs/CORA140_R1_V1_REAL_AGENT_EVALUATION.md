# R1-v1 real Agent evaluation (owner-only)

This reuses the EXISTING R1-v1 router and the EXISTING GapGPT Rich V2 runner;
it does not create a new router or inference model. Historical R1 is not
proven to equal this reconstructed R1-v1. R0's already-approved scope
is NOT valid authorization for R1. The current R1-v1 has no real frozen
Blind/Comparison results, so post-hoc R1 error discovery does not provide
R1 Agent correction accuracy.

The earlier six-router GT oracle audit found 24/37 selected true baseline
errors, 13/37 false alarms, 21/45 missed errors, and 17/36 agreed-wrong
errors caught by R1-v1. These are post-hoc router metrics ONLY.

## 1. R1 local preflight: zero HTTP calls

Execute from the existing main repository root on Windows:

    git fetch origin main
    if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
    git merge --ff-only origin/main
    if ($LASTEXITCODE -ne 0) { throw "Non-fast-forward: do not reset" }
    $env:PYTHONPATH = Join-Path $PWD "src"
    $env:PYTHONDONTWRITEBYTECODE = "1"
    $py = ".\.venv\Scripts\python.exe"
    $config = "configs/gapgpt_rich_v2_output4096_proposed.json"
    $raw = & $py -B -m llmgnn_sara.sara3.runner --mode live-preflight --router r1_v1 --budget 37 --cohort sensitivity --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --gateway-config $config
    if ($LASTEXITCODE -ne 0) { throw "R1 preflight failed" }
    $pre = ConvertFrom-Json ($raw -join [Environment]::NewLine)
    if ($pre.status -ne "PROPOSED_NO_DISPATCH" -or $pre.wire_preflight.selected_count -ne 37 -or $pre.wire_preflight.call_cap -gt 74 -or $pre.approval_template.spend_cap_usd -ne "0.40") { throw "R1 scope mismatch" }
    $pre.wire_preflight | ConvertTo-Json -Depth 10

The declared limit is 74 calls and USD 0.40 estimated under the config's
UNVERIFIED provider rates, not a guaranteed third-party invoice cap.
The provider model, terms, retention, rates and compatibility must be
reviewed externally. Do not paste or upload API keys or private papers.

## 2. Optional paid live R1 dispatch: explicit NEW owner approval

Do this ONLY if the owner has separately consented to R1 provider transfer
and possible charges. Do NOT reuse an R0 approval or journal.

    $approval = $pre.approval_template
    $approval.data_sharing_approved = $true
    $approval.spend_approved = $true
    $approval.explicit_batch_dispatch_approved = $true
    $approvalFile = ".local_artifacts/r1_v1_live_approval_private.json"
    $runRoot = ".local_artifacts/sara3_gapgpt_live_cora140_r1_v1_4096_20261107"
    if (Test-Path $approvalFile) { throw "Existing approval: do not overwrite" }
    if (Test-Path $runRoot) { throw "Existing journal: no automatic retries or resets" }
    $consent = Read-Host "R1-v1 live: up to 74 paid calls / declared USD 0.40, provider/privacy unverified. Type APPROVE-R1 to consent"
    if ($consent -cne "APPROVE-R1") { throw "Not authorized" }
    [System.IO.File]::WriteAllText((Join-Path $PWD $approvalFile), ($approval | ConvertTo-Json -Depth 15), (New-Object System.Text.UTF8Encoding $false))
    if (-not $env:GAPGPT_API_KEY) { throw "Set key privately in this session; never paste it in chat" }
    $liveRaw = & $py -B -m llmgnn_sara.sara3.runner --mode live --enable-real-dispatch --owner-approval-file $approvalFile --router r1_v1 --budget 37 --cohort sensitivity --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --gateway-config $config --output-root $runRoot
    $code = $LASTEXITCODE
    if ($code -notin @(0,2)) { throw "R1 gateway FAIL_CLOSED; preserve receipts, no retry" }
    $live = ConvertFrom-Json ($liveRaw -join [Environment]::NewLine)
    $live | Select-Object status,router,selected_count,blind_completed,comparison_completed,attempted_calls,new_dispatches,private_report_sha256,private_summary_sha256 | Format-List

If blocked by a rejection/uncertainty, DO NOT restart or use a new
journal to avoid the failure. Investigate and reconcile without retrying.
The GT scorer can describe a partial frozen response, clearly labeled.

## 3. R1 GT-only scorer in a SEPARATE process after any live dispatch

The evaluator never sends HTTP or uses GT for routing, prompt generation,
Arbitration or training. It authenticates the private live run and graph
BEFORE reading per-node labels.

    $env:PYTHONPATH = Join-Path $PWD "src"
    $env:PYTHONDONTWRITEBYTECODE = "1"
    $py = ".\.venv\Scripts\python.exe"
    $graph = (Resolve-Path ".local_artifacts/gt_reference/cora_random_sbert.pt").Path
    $hash = "9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466"
    if ((Get-FileHash -LiteralPath $graph -Algorithm SHA256).Hash.ToLowerInvariant() -ne $hash) { throw "Original Cora graph changed" }
    & $py -B -m unittest discover -s tests -p test_cora_r1_real_gt.py -v
    if ($LASTEXITCODE -ne 0) { throw "Synthetic tests failed" }
    $scoreRoot = ".local_artifacts/sara3_r1_v1_real_gt_v1"
    $scoreRaw = & $py -B -m llmgnn_sara.evaluation.cora_r1_real_gt --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --r1-root $runRoot --gateway-config $config --summary-sha256 $live.private_summary_sha256 --graph-file $graph --audit-root $scoreRoot
    if ($LASTEXITCODE -ne 0) { throw "R1 GT-only evaluation FAIL_CLOSED" }
    $score = ConvertFrom-Json ($scoreRaw -join [Environment]::NewLine)
    if ($score.status -ne "R1_REAL_GT_NODE_JOURNEY_VERIFIED_OWNER_PRIVATE") { throw "Unexpected scorer status" }
    $path = Join-Path $scoreRoot $score.relative_path
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $score.artifact_sha256) { throw "Private result integrity failed" }
    $score.aggregate | ConvertTo-Json -Depth 12

The report includes all 140 GT/B1/Narrative node labels, R1 selection
and 37 Blind/Comparison results including abstentions, per-method
correctness, paired correct/damaging changes, hypothetical Narrative
fallback, real V1 admissions and actual run status. Only AGGREGATES
print to terminal. The node-level content-addressed JSON stays private.
Never feed it to the LLM, an independent reviewer or GCN admission.

Important: This is a post-hoc exploratory study, not proof of R1-vs-R0
GCN improvement. The entire cohort has already been examined with GT.
A separate untouched test and prespecified admission policy are required
for an independent model-improvement claim.
