# Outstanding-only feasibility continuation

Version `gapgpt-outstanding-l1-wrapper-v1`. This is an explicitly owner-authorized
post-observation protocol amendment, not a retry or terminal-state migration.
No old ledger, intent, receipt, raw response or diagnostic assessment is modified.
The old halted commands remain blocked. No historical request identity is reused.

## Scope and provenance

Never dispatch637 again: its preserved blind abstained; comparison is forbidden.
Never redispatch1243 blind: its original L1 failure and terminal REJECTED remain.
Read and independently validate the original1243 provider response, request/context,
ledger raw hash, original rejection receipt, approval binding and separate diagnostic
receipt under `sara.l1.decorative_quote_match.v1`. Admit only immutable, fully bound,
HTTP200/stop, exact approved returned revision and diagnostic L1 PASS. A preserved
non-abstaining blind makes its comparison eligible only under this new amendment.
Its proposed class is read privately from the response, never hardcoded in source.
The old blind is not imported as a fabricated COMPLETED intent in the new ledger.

Order: 1243 comparison, then130 blind/conditional comparison,682 blind/conditional
comparison,2396 blind/conditional comparison,653 blind/conditional comparison.
Maximum9 calls; if the admitted preserved blind abstains, omit its comparison and
the bound plan has maximum8. Each new comparison uses the actual validated blind
class and sealed comparison template. Abstention skips only that node's conditional
comparison. Any invalid, rejected, truncated, identity-mismatched or uncertain result
halts all subsequent work. There are no retries, fallbacks, replacements or resume.

Provider GapGPT, endpoint `https://api.gapgpt.app/v1/chat/completions`, request model
`gpt-6-luna`; returned revision must be exactly `gpt-6-luna-2026-09-22` (even the
undated alias alone does not establish that revision in this contract). This is
owner-approved, provider-reported identity, not independent upstream verification.
Temperature1/n1/max_tokens512, reasoning_effort omitted; scientific message bytes,
class definitions and legacy schema unchanged. No router, L2 or arbitration changes.

The contract pins seals, recovered source manifest, active runtime hashes, full
ordered plan and original-response/diagnostic lineage. Preflight rechecks prior
operational ledgers against every outstanding blind and all possible conditional
comparison hashes; actual human-review sessions are excluded. Before dispatch it
rechecks the contract after terminal approvals. SQLite stores an immutable binding,
single run state and ordered cursor; every intent is durably UNCERTAIN before its
single dispatch. A process restart cannot resume the run, including a crash after
start but before the first reservation. An unknown dispatch never frees a reservation.

## Fresh owner-controlled execution

```powershell
cd C:\Users\Admin\Documents\ChatGPT\llm-gnn
.venv\Scripts\python.exe -B -m llmgnn_sara.pilot.outstanding_gapgpt
```

Exact approval phrases, in prompt order:

1. `APPROVE POST-OBSERVATION L1 CONTINUATION`
2. `APPROVE CONTINUATION PRIVACY`
3. `APPROVE EXACT OUTSTANDING LIST`
4. `APPROVE OUTSTANDING DECLARED LIMITS`
5. Fresh aggregate reservation: `0.10`
6. Existing GAPGPT_API_KEY process environment or hidden interactive key prompt.
7. Exact dispatch: `gapgpt-outstanding-l1-wrapper-v1`

Declining any approval prevents dispatch. Never put a key in chat, source, arguments
or logs. Do not rerun after a started run, error, crash or interruption.

For9 calls: declared input cap147456/output4608, reserving16384/512 per call.
At owner-provisional USD0.10/M input and0.50/M output, the conditional maximum
estimate is USD0.0170496 (8 calls: USD0.0151552). Fresh USD0.10 local reservation
is separate from all previous approvals and is not a provider billing guarantee.
Byte preflight is not vendor tokenization. Reported over-cap usage halts subsequent
work but cannot undo billing. Missing usage/charges remain unknown; reasoning tokens
are not added twice to reported completion usage. No token-count API is used.

## Private results

Store: `.local_artifacts/gapgpt_outstanding_l1_v1/`, current-user private audit and
`intent.sqlite`, excluded from Git. Content-addressed `remaining_summary` records
contain all six node rows, distinguishing original/diagnostic blind outcomes from
new comparison outcomes. New totals exclude637 and1243 historical blind usage.
Reported usage, reasoning counts, known estimate subtotal, missingness and unknown
actual billing are separate. Dispatch-attempt upper bounds are not exactly-once
delivery claims. A final summary can be unavailable after audit failure; preserve
the ledger/receipts and stop. Private evidence stays available for later blinded
review; no missing rationale/counter-evidence is fabricated from the legacy schema.
All accepted labels remain null and L2 NOT_ASSESSED. Diagnostic eligibility is not
semantic validity, independent human review or downstream effectiveness.
