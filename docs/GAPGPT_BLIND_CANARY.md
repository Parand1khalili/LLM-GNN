# Owner-operated GapGPT blind637 canary v1

This is the sole narrow live entry point, not authorization for the six-node run.
General readiness/experiment guards remain unchanged. No request was sent during
implementation/tests. Router, verifier prompts, six-node seals and labels unchanged.

From the repository root in your own local Windows Terminal/PowerShell, outside
ChatGPT/Codex tool input:

```powershell
.venv\Scripts\python.exe -B -m llmgnn_sara.pilot.canary
```

No command arguments are accepted. Do not place a key in a command, file or chat.
The process uses GAPGPT_API_KEY if already available; otherwise getpass prompts
without echo. Noninteractive execution is refused. Failed secure prompting never
falls back to visible input. Application exceptions are not printed verbatim.

The terminal shows GapGPT, https://api.gapapi.com/v1/chat/completions,
gpt-6-luna, node637, BLIND ONLY and provisional exposure. Enter, only if truthful:

1. `APPROVE PRIVACY`: approve transmitting the sealed article/context under the
   applicable service terms. The program cannot authenticate your service terms.
2. `APPROVE SEALED WIRE`: approve this historical-envelope feasibility attempt,
   including max_tokens512; this is not evidence that the provider will accept it.
3. `APPROVE DECLARED LIMITS`: acknowledge the input reservation16384 and sealed
   output setting512. A conservative local serialized-byte check is used, not a
   verified provider tokenizer. Gateway interpretation/hidden reasoning remains
   a feasibility question. A post-response usage overrun is rejected but cannot
   undo a provider charge already incurred.
4. Type `0.10` to explicitly reserve the full USD0.10 for this single attempt.
   Provisional0.10/M input and0.50/M output imply USD0.0018944 at declared maxima;
   rates/fees and actual billing are unverified. Neither estimate nor reservation
   guarantees an upstream monetary ceiling. If that risk is unacceptable, cancel.
5. Enter the key in the hidden prompt if required, then type
   `gapgpt-blind-637-canary-v1` to authorize exactly one dispatch.

All privacy/compatibility/limit/financial confirmations must succeed before key
entry; final dispatch confirmation follows key entry. Never give the key to an
assistant to run this command for you. No credentials are loaded during import.

## Exact execution and recovery boundaries

The command verifies both known seals and all31+13 members, nine source hashes,
the637 logical blind request against its authenticated builder, and exact wire
bytes/settings. No prompt/schema/endpoint/model conversion or fallback is made.
TLS certificate/hostname verification is enabled; direct fixed-host HTTP uses no
environment proxy, redirects, retries or TLS-key logging. Only Authorization to
the approved endpoint carries the key; no response headers or exception text log it.

Private output/state is fixed at `.local_artifacts/gapgpt_canary_637` and must not
be deleted/moved to obtain a retry. The SQLite context binds endpoint/model,
actual wire hash, owner confirmations, reservation and original readiness/seal
digests. Intent/reservation commits before UNCERTAIN commits, both before network.
Any existing intent blocks the CLI, including PENDING, terminal or uncertain.
No automatic recovery, reservation release, retry, comparison or second node.
This is not an exactly-once guarantee across filesystem deletion, manual overrides,
hardware failure or provider-side behavior. Only one command invocation may own
the fixed state; SQLite uniqueness also blocks concurrent duplicate dispatch.

Raw provider bytes/status/usage are private. Raw/persisted hashes are separate;
known literal/JSON-escaped/decoded secret echoes are redacted and rejected rather
than saved as an unredacted original. The original body hash remains, not its
secret-bearing bytes. Usage and any rate-based cost are not invoices. Missing
usage stays unknown. Unexpected reported model IDs, invalid usage, HTTP errors,
non-stop finish reasons, oversized/malformed replies and L1 failures fail closed.
No class/quote is printed publicly or promoted to a training label.

The existing strict parser/L1 handles decoded model content. Original provider
envelope receipt and inner verifier-response receipt remain distinguishable.
Audit failure/timeout/interruption stops execution with no retry; inspect private
state manually. If final-summary writing fails after a terminal transaction, the
CLI may report uncertain result visibility while SQLite retains its durable
terminal record; never infer permission to dispatch again. All failed/unknown
attempts retain their whole reservation. Later owner approval/reconciliation is
required for any new execution scope.

## Offline verification

Mock-only tests cover exact fixed HTTP host/path/TLS, no redirect/retry, secure
environment/getpass paths, noninteractive rejection, approval gates, original
payload matching, raw/escaped secret echo redaction, HTTP errors, truncation,
malformed/schema/evidence failures, usage caps, wrong model, audit failure,
restart duplicate prevention and no accepted semantic labels. No real key used.
Full guarded regression results are recorded in PROJECT_STATE.md after completion.

Executed: focused18 PASS; full guarded Python256:255 PASS/1 Windows symlink SKIP
(173.906s). Positive exact-quote HTTP smoke also PASS with accepted_label=null.
All31+13 seal members/nine input pins are checked by prepare; P0 verified separately.
No actual human session/network access in tests; no real canary was executed.
Unrelated GraphScope frontend checks were not run.
