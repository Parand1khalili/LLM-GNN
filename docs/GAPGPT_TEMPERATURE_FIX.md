# Explicit temperature1 compatibility derivative

## Observed owner execution: do not rerun this identity

The owner subsequently dispatched this identity once. The saved response is HTTP200,
finish_reason stop, with returned model `gpt-6-luna-2026-09-22`. The client rejected
the revision identifier because its exact allowlist contains only `gpt-6-luna`.
Thus INVALID_ENVELOPE_OR_USAGE was a misleading umbrella diagnosis, not an HTTP
rejection or evidence that authentication failed. The original terminal ledger and
audit remain unchanged. No fresh identity or revision authorization is introduced.

Read-only offline parsing of the saved content passes legacy schema/L1 and shows
abstention with empty evidence. This does not retroactively complete the rejected
intent, assess L2, prove the returned revision's identity, or accept a training label.
Usage is 689 prompt and 165 completion tokens (140 reasoning tokens included in
completion); total854. At owner-provisional rates the estimate is USD0.0001514,
not verified billing. The old result's missing usage reflects validation order.

The diagnostic correction retains available usage before model identity checking
and reports RETURNED_MODEL_MISMATCH explicitly. Unknown revisions still fail
closed. Approval/documentation of an exact revision mapping is a separate decision;
no wildcard acceptance, network request, retry, or reset is part of this correction.

## Original preparation record

Observed second attempt: api.gapgpt.app returned HTTP400, invalid_request_error,
unsupported_value, param temperature. Sanitized message: temperature does not
support0.7 for this model; only default1 is supported. No usage/charge was supplied.
This differs from the original api.gapapi.com401 authentication rejection. The
current observed problem is a model-parameter rejection, not evidence of key-entry
error or insufficient balance. Historical source configured0.7; it cannot establish
current backend acceptance or explain why provider behavior changed over time.

The only new body change is temperature0.7 ->1, derived in memory from the verified
original sealed body. Message-content bytes, node637, model, n1, max_tokens512,
legacy schema, blind-first boundary and all sealed files stay unchanged. No other
parameter adaptation is automatic. This is a versioned compatibility addendum,
not a silently rewritten scientific protocol or claim of identical generation.

New identity: gapgpt-app-t1-blind-637-canary-v1.
Endpoint: https://api.gapgpt.app/v1/chat/completions .
New state: .local_artifacts/gapgpt_app_t1_canary_637 .
Both existing failed identities/ledgers/receipts remain intact. No dispatch occurred
while implementing this change. There is no automatic retry/fallback on HTTP400.

Owner command, from repository root in a local terminal:

```powershell
.venv\Scripts\python.exe -B -m llmgnn_sara.pilot.canary_gapgpt_t1
```

All previous local approvals remain required, plus the explicit additional phrase
`APPROVE TEMPERATURE 1`. Enter the key only through the hidden terminal prompt
(or existing GAPGPT_API_KEY environment); never in chat or command arguments.
Final dispatch phrase: `gapgpt-app-t1-blind-637-canary-v1`.
Reserve a new USD0.10 explicitly; prior reservations are not released or assumed
unbilled. Monetary/token reservations are not guaranteed provider billing limits.
At most one fresh blind request, no comparison or retry; any intent blocks repeats.

This change addresses exactly the observed temperature error. Actual success and
support for all remaining sealed settings can only be established by a separately
authorized execution. If another error occurs, stop and inspect its private receipt;
do not cycle profiles or relax parameters automatically. Parser/L1 cannot approve
L2 semantics or training labels. General live/experiment guards remain unchanged.

Checks: focused23 PASS; guarded relevant45 PASS (15.761s). Both prior failed
ledger/receipt trees byte-unchanged; seals/nine inputs/P0 PASS; body/message diff
confirms temperature only. Full Python suite not repeated for this narrow fix.
