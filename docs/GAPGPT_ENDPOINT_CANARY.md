# Fresh account-panel endpoint canary — preparation only

Owner confirms the same GapGPT key worked previously and was correctly entered.
No key was requested/read in this investigation. No new network request was sent.

## Evidence versus diagnosis

Recovered matched/narrative source configures
`https://api.gapapi.com/v1/chat/completions`, gpt-6-luna, one user message,
temperature0.7/n1. Its transport uses Authorization: Bearer plus the key and a
JSON POST without redirects/retries. The failed canary uses that same header
format and endpoint; it adds the sealed512 output cap and new verifier task.
This is hash-verified source evidence, not an independently recovered successful
HTTP receipt proving the endpoint of every prior live request. Earlier success
is also owner-confirmed; the currently admitted parsed outputs do not establish
wire-level HTTP/usage history. No historical source or endpoint is rewritten.

The preserved attempt returned HTTP401, invalid_api_key/authentication_error.
It reached an HTTP service but gives no evidence of model execution, balance
failure, model rejection or token-limit failure. Actual charges remain UNKNOWN.
The current owner-supplied account panel specifies api.gapgpt.app/v1, while the
supplied guide also mentions gapapi.com as an external-CDN option. Together with
correct key entry and matching Bearer construction, endpoint/CDN authentication
routing or current endpoint policy is the leading operational hypothesis. It is
not proven: changing hosts has not been tested and may still return an error.
No user-entry error is assumed, and no alternative provider/model is proposed.

## Separate scope; no bypass/reset

New identity: `gapgpt-app-blind-637-canary-v1`.
New endpoint: `https://api.gapgpt.app/v1/chat/completions`.
New fixed state: `.local_artifacts/gapgpt_app_canary_637`.
Original identity/directory remain `gapgpt-blind-637-canary-v1` /
`.local_artifacts/gapgpt_canary_637`, with REJECTED intent unchanged. Do not delete,
move, reset or reuse them. The new scope is explicit owner-requested preparation,
not automatic fallback or a retry of the failed identity.

The sealed scientific message and entire JSON body stay byte-for-byte unchanged;
only the approved destination, context identity and state directory differ. Model,
node637, blind phase, n1, temperature0.7/max_tokens512, timeout120, no retry,
no comparison, TLS validation, private audit and L1/no-label behavior are reused.
Two explicit endpoint profiles are whitelisted; no arbitrary host argument or
environment override is exposed. Old confirmation text does not authorize the
new identity. Old command/default target behavior is retained, not silently changed.

## Owner execution after fresh local approval

From the repository root in your own local PowerShell, not chat/Codex tool input:

```powershell
.venv\Scripts\python.exe -B -m llmgnn_sara.pilot.canary_gapgpt
```

Review the displayed account-panel URL. All existing confirmations are required
again: privacy, sealed wire, declared token limits and full USD0.10 reservation.
If GAPGPT_API_KEY is absent, use the hidden key prompt. Never send the key in chat,
arguments or files. Final confirmation must be exactly:
`gapgpt-app-blind-637-canary-v1`.

This authorizes at most one fresh blind request. Existing old reservation is not
released by the401 response; the new0.10 reservation is separate (0.20 combined
local reservation across both attempts, not actual billing). No provider billing
cap is guaranteed. Any new intent blocks another invocation, including after
timeout, audit failure or rejection. If the new attempt also fails, stop and obtain
fresh diagnosis/authorization; never switch back or cycle endpoints automatically.

See GAPGPT_BLIND_CANARY.md for unchanged key/audit/reservation limitations.
Preparation does not attest current model/token compatibility or real tokenization.
No actual new credential was used, endpoint probed or canary dispatched here.

Verification: focused21 canary tests PASS; guarded relevant43 (canary/readiness/
pilot/P0) PASS in15.812s. Real network and human-review session access denied.
Original failed SQLite/all receipt bytes unchanged.31+13 seals/nine inputs/exact
wire/P0 pins PASS. Full Python suite not rerun for this narrow profile change.
