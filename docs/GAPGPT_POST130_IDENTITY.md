# Exact identity correction and preserved130 continuation

Policy `sara.gapgpt.identity.exact_alias_revision.v1` accepts exactly two returned
strings: `gpt-6-luna` and `gpt-6-luna-2026-09-22`. Scope is GapGPT at
`https://api.gapgpt.app/v1/chat/completions`, request model `gpt-6-luna`, wire
temperature1/n1/max_tokens512 with reasoning_effort omitted. Other providers,
endpoints, models, revisions, prefixes, missing identities and settings fail closed.
This is an explicit owner-approved execution policy, not independent evidence
of upstream model equivalence. Returned identifiers remain individually recorded.

Root cause: the older remaining_gapgpt.identity_allowed already admitted both
strings. The subsequent revision-only contracts added `model == prior.REVISION`
before that predicate, excluding the exact requested alias. This restriction
reflected the then-exact-revision contract; it was not a key or HTTP failure.
The correction applies only to the new versioned post130 contract. Old contracts,
terminal states, receipts and raw data are not rewritten or retroactively approved.

Node130's immutable HTTP200/stop response is privately replayed through exact
identity policy, legacy JSON parser and current L1: diagnostic PASS, non-abstaining,
source-exact evidence. Original REJECTED/RETURNED_MODEL_MISMATCH remains. Separate
`sara.identity.diagnostic_reassessment.v1` receipt binds original hashes, outcome,
policy version and policy source hash in `.local_artifacts/gapgpt_130_identity_reassessment/`.
Comparison eligibility is a documented post-observation amendment, not an assertion
that the original request completed successfully. L2 remains NOT_ASSESSED; no labels
are accepted. No new raw inference or semantic judge is used for reassessment.

## Only outstanding requests

Scope `gapgpt-post130-exact-identities-v1`:130 comparison,682 blind/conditional
comparison,2396 blind/conditional comparison,653 blind/conditional comparison.
Maximum7 calls. A valid blind abstention forbids its comparison. Never dispatch
637 or1243, nor130 blind. All historical failures remain genuine recorded outcomes.
Sealed scientific messages, router selections, legacy schema and L1 rule are unchanged.
Existing shared engine/ledger/audit/ordered cursor are reused. Preflight verifies
source seals, old raw/context/request/ledger bindings, diagnostic policy hash, and
absence of prior outstanding intents. Any failure halts; no retry or automatic resume.

```powershell
cd C:\Users\Admin\Documents\ChatGPT\llm-gnn
.venv\Scripts\python.exe -B -m llmgnn_sara.pilot.post130_gapgpt
```

Fresh local phrases:

1. `APPROVE EXACT IDENTITY POLICY V1`
2. `APPROVE CONTINUATION PRIVACY`
3. `APPROVE EXACT OUTSTANDING LIST`
4. `APPROVE OUTSTANDING DECLARED LIMITS`
5. Fresh aggregate reservation: `0.10`
6. Key from process GAPGPT_API_KEY or hidden terminal prompt; never chat/arguments.
7. Final dispatch: `gapgpt-post130-exact-identities-v1`

At7 calls reserve114688 declared input/3584 output tokens. With provisional owner
rates USD0.10/M input and0.50/M output, conditional maximum estimate USD0.0132608.
Fresh USD0.10 local reservation is not a billing guarantee; byte preflight is not
vendor tokenization. Cache/reasoning billing and actual charges remain unverified.
No usage is invented or missing billing treated as zero. Historical consumption
stays in historical rows and is excluded from new totals, including130 blind.

Private run store `.local_artifacts/gapgpt_post130_v1/` contains new intents and
raw/provenance/summary receipts. Original six-node history remains separate from
new phase denominators. Never rerun after start/error/crash. Review actual receipts
on a halt, without resetting ledgers or generating retries. Raw data is excluded
from Git and public exports. Independent L2 review is still needed; no GT, training,
correctness or superiority inference follows from this infrastructure.
