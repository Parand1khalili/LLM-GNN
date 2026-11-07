# R1-v1: safe completion of stopped REAL GapGPT experiment

Owner-observed immutable R1 state: 51 attempts, 50 COMPLETED, 1 REJECTED
Comparison with HTTP 200, valid JSON, finish_reason stop, error
L1_QUOTE_NOT_FOUND, zero UNCERTAIN. 30 Blind and 20 Comparison completed;
9 Blind abstentions; 7 originally selected Blinds never attempted.

**Do NOT rerun the original R1 batch.** All 50 successful model receipts
and the original invalid Comparison remain intact. Only 7 never-attempted
Blinds and their conditional valid Comparisons may be sent. Maximum 14
additional requests, total up to 65 of 74 declared call-cap, under a
conservative USD0.40 declared-rate reservation. Final provider invoice
and terms are not independently verified. Neither GT nor new policies
nor GCN is used during continuation.

A new independent, content-addressed overlay under the original run
root stores the amended results; the original R1 journal is read-only.
An L1_QUOTE_NOT_FOUND is an actual model-output validation failure,
not an invitation to retry the same Comparison.

## 1. Windows offline preflight: absolutely no API calls

From the project root on existing main, enter the following:

    if ((git branch --show-current) -ne "main") { throw "Wrong branch" }
    git fetch origin main
    if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
    git merge --ff-only origin/main
    if ($LASTEXITCODE -ne 0) { throw "Fast-forward blocked" }
    $env:PYTHONPATH = Join-Path $PWD "src"
    $env:PYTHONDONTWRITEBYTECODE = "1"
    $py = ".\.venv\Scripts\python.exe"
    $config = "configs/gapgpt_rich_v2_output4096_proposed.json"
    $root = ".local_artifacts/sara3_gapgpt_live_cora140_r1_v1_4096_20261107"
    & $py -B -m unittest discover -s tests -p test_gateway_r1_continuation.py -v
    if ($LASTEXITCODE -ne 0) { throw "Synthetic tests failed" }
    $raw = & $py -B -m llmgnn_sara.sara3.gateway_r1_continuation --mode preflight --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --output-root $root --gateway-config $config
    if ($LASTEXITCODE -ne 0) { throw "R1 source proof failed; preserve existing journal" }
    $pre = ConvertFrom-Json -InputObject ($raw -join [Environment]::NewLine)
    if ($pre.status -ne "READ_ONLY_R1_CONTINUATION_PROPOSED_NOT_AUTHORIZED" -or $pre.maximum_new_calls -ne 14 -or $pre.maximum_total_calls -ne 65 -or $pre.never_attempted_blind_count -ne 7 -or $pre.preserved_rejection_code -ne "L1_QUOTE_NOT_FOUND") { throw "R1 scope differs: STOP" }
    $pre | Select-Object status,original_completed,original_rejected,original_uncertain,never_attempted_blind_count,maximum_new_calls,maximum_total_calls,declared_maximum_reservation_usd | Format-List

The preflight cryptographically verifies all original 51 receipts and
the sole rejected quote, verifies original frozen report and hashes,
and returns an exact amendment and an initially UNAPPROVED new approval
template. Stop if status or counts differ.

## 2. Optional new 14-request paid continuation; explicit fresh consent

The original R1 consent does NOT authorize new requests. The private
R1 original SQLite, receipts, full report and original approval are
never overwritten. Review current third-party pricing/privacy terms
before granting fresh consent.

    $amendmentPath = ".local_artifacts/r1_v1_continuation_amendment_private.json"
    $approvalPath = ".local_artifacts/r1_v1_continuation_approval_private.json"
    $overlayPath = Join-Path $root "r1_v1_continuation_v1"
    if ((Test-Path $amendmentPath) -or (Test-Path $approvalPath) -or (Test-Path $overlayPath)) { throw "Prior continuation state exists; no overwrite or retry" }
    $consent = Read-Host "Maximum 14 NEW paid R1 calls, original rejected comparison preserved. Type APPROVE-R1-CONTINUE"
    if ($consent -cne "APPROVE-R1-CONTINUE") { throw "No consent; no HTTP" }
    [System.IO.File]::WriteAllText((Join-Path $PWD $amendmentPath),($pre.amendment_template | ConvertTo-Json -Depth 20),[System.Text.UTF8Encoding]::new($false))
    $approval = $pre.approval_template
    $approval.data_sharing_approved = $true
    $approval.spend_approved = $true
    $approval.explicit_continuation_dispatch_approved = $true
    [System.IO.File]::WriteAllText((Join-Path $PWD $approvalPath),($approval | ConvertTo-Json -Depth 20),[System.Text.UTF8Encoding]::new($false))
    $secret = Read-Host "GapGPT API key (hidden)" -AsSecureString
    $env:GAPGPT_API_KEY = ([System.Management.Automation.PSCredential]::new("gapgpt",$secret)).GetNetworkCredential().Password
    Remove-Variable secret
    if (-not $env:GAPGPT_API_KEY) { throw "No key: STOP" }
    try {
        $liveRaw = & $py -B -m llmgnn_sara.sara3.gateway_r1_continuation --mode live --enable-real-dispatch --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --output-root $root --gateway-config $config --amendment-file $amendmentPath --owner-approval-file $approvalPath
        $exit = $LASTEXITCODE
    } finally {
        Remove-Item Env:GAPGPT_API_KEY -ErrorAction SilentlyContinue
    }
    if ($exit -notin @(0,2)) { throw "Continuation FAIL_CLOSED: preserve all state; do not retry" }
    $continued = ConvertFrom-Json -InputObject ($liveRaw -join [Environment]::NewLine)
    $continued | Select-Object status,original_completed,original_rejected,new_dispatches,new_intents,blinds_completed,comparisons_completed,total_intents,private_summary_sha256 | Format-List
    if ($continued.status -ne "CONTINUED_PRESERVING_REJECTED_COMPARISON") { throw "HALTED: do not retry; request forensic review" }

No automatic retry exists. If the overlay has any REJECTED/UNCERTAIN
new request, it must be independently diagnosed, without a new journal
or response replacement.

## 3. Separate owner-private GT-only assessment after successful continuation

Keep the same real Cora Graph: exact SHA256
9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466.

    $graph = (Resolve-Path -LiteralPath ".local_artifacts\gt_reference\cora_random_sbert.pt").Path
    $expected = "9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466"
    if ((Get-FileHash -LiteralPath $graph -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw "Original Cora SHA mismatch" }
    $scoreRoot = ".local_artifacts/sara3_r1_v1_continued_gt_v1"
    $scoreRaw = & $py -B -m llmgnn_sara.evaluation.cora_r1_continued_gt --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --original-root $root --gateway-config $config --continuation-summary-sha256 $continued.private_summary_sha256 --graph-file $graph --audit-root $scoreRoot
    if ($LASTEXITCODE -ne 0) { throw "R1 GT scorer FAIL_CLOSED" }
    $score = ConvertFrom-Json -InputObject ($scoreRaw -join [Environment]::NewLine)
    if ($score.status -ne "R1_CONTINUED_GT_NODE_JOURNEY_VERIFIED_PRIVATE") { throw "Unexpected result status" }
    $privateFile = Join-Path $scoreRoot $score.relative_path
    if ((Get-FileHash -LiteralPath $privateFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $score.artifact_sha256) { throw "Private GT report hash mismatch" }
    $score.aggregate | ConvertTo-Json -Depth 12

This remains an exploratory post-hoc analysis. Do not upload raw
node-level Ground Truth, original/overlay journals, full provider output
or approval files. Only share aggregated results. The original invalid
Comparison is still marked as a genuine rejection; it is not repaired
or rerun. GCN and training admission are still disabled.
