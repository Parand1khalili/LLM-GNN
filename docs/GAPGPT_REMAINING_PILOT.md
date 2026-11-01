# Authorized remaining feasibility batch

Owner-authorized continuation, not a new cohort or historical replay. Execute on
main only after offline tests and fresh local approvals. Node637 is permanently
excluded from dispatch: its original terminal REJECTED ledger remains intact;
the preserved HTTP200 response is diagnostic L1-valid abstention, no comparison.

## Fixed execution contract

Entry point: `llmgnn_sara.pilot.remaining_gapgpt`. Contract version:
`gapgpt-six-node-remaining-t1-v1`. Exact provider GapGPT, endpoint
`https://api.gapgpt.app/v1/chat/completions`, requested model `gpt-6-luna`.
Allowed returned names are exactly `gpt-6-luna` and `gpt-6-luna-2026-09-22`.
The latter mapping is explicitly approved by the owner based on an observed
provider response; it is provider-reported, not independent upstream identity
verification. No prefix, wildcard, other revision, endpoint or provider is allowed.
Earlier canary identity rules and receipts are unchanged.

Order: 1243,130,682,2396,653. One blind per node; at most one comparison only
after an L1-valid non-abstaining blind. Actual blind class binds the existing
sealed comparison template, with immutable template/response/request hashes.
Abstention ends that node. Any failure/uncertainty halts the entire batch.
No retry, fallback, replacement, skipping failures or automatic crash recovery.

Wire variant: temperature1, n1, max_tokens512, omitted reasoning_effort and native
response_format. Original temperature0.7 seals, scientific message bytes and class
definitions are preserved. Source manifests, all sealed members, authentic input
hashes, cohort/order and original637 receipts/ledger are checked before start.
Operational pilot ledgers are checked for prior remaining-node intents; actual
human-review sessions and submissions are never scanned.

Ten calls maximum. Reserve16384 declared input and512 output tokens for each
call, without refund on rejection or uncertainty. Aggregate caps163840/5120.
The serialized-byte preflight is not provider tokenization. Observed over-cap
usage rejects and halts, but cannot undo incurred billing. At provisional owner
rates USD0.10/M input and0.50/M output, maximum exposure *under these token and
pricing assumptions* is USD0.018944. Reasoning is not counted again on top of
reported completion tokens. Fresh aggregate USD0.10 local reservation is mandatory;
neither reservation nor estimate is a provider billing guarantee. Missing usage
or invoices remains unknown. No previous canary financial approval is reused.

## Owner execution

```powershell
cd C:\Users\Admin\Documents\ChatGPT\llm-gnn
.venv\Scripts\python.exe -B -m llmgnn_sara.pilot.remaining_gapgpt
```

Enter the exact local approval phrases when prompted:

1. `APPROVE BATCH PRIVACY`
2. `APPROVE TEMPERATURE 1 SEALED WIRE`
3. `APPROVE 10 CALL DECLARED LIMITS`
4. `APPROVE EXACT OBSERVED REVISION`
5. Aggregate reservation: `0.10`
6. API key via existing process GAPGPT_API_KEY or hidden terminal prompt only.
7. Exact dispatch: `gapgpt-six-node-remaining-t1-v1`

No credential in chat, command arguments, files, logs or Git. A declined approval
prevents dispatch. No interactive terminal or missing secure credential input
blocks execution. Do not rerun after any start, crash or error; review private
state first. A fixed SQLite singleton binds the contract, approvals and request
pins before any intent. Each intent is reserved and committed UNCERTAIN before
the single HTTP dispatch. Duplicate/terminal states cannot be reused. The
singleton prevents a restarted CLI from resuming even if it crashed before the
first intent. No reset or second run identity is provided.

## Private outputs and interpretation

Private location: `.local_artifacts/gapgpt_remaining_pilot_v1/` (Git-ignored,
current-user ACL). Content-addressed approval, request, raw-provider, readiness,
progress and final summary records; durable `intent.sqlite`. Read receipts whose
kind is `remaining_summary` for six original-node rows with separate phase
states, HTTP/parse/L1, class/abstention, usage including reported reasoning,
identity observation, evidence/review eligibility and billing limitations.
New-batch totals exclude historical637, whose usage is retained separately in
its row. A dispatch-attempt upper bound is distinguished from confirmed HTTP
responses; a PENDING reservation is not a confirmed call. Missing usage is not
zero consumption. On audit failure a final summary may be unavailable; the
durable ledger and surviving immutable receipts are authoritative and no retry
is permitted. Public CLI output contains only state/counts and the private path.

All accepted training labels remain null and L2 NOT_ASSESSED. Legacy evidence
provides quotations only, not fabricated rationales or counter-evidence. An
abstention is available for process review but supplies no positive class evidence.
No GT, correctness evaluation, router changes, semantic approval or training.

Offline checks use synthetic responses, temporary private stores and blocked
network connections. Synthetic results are not scientific pilot findings.
