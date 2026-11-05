# SARA-3 / GapGPT Rich V2 Gateway Bridge

**Status:** versioned bridge and Fake HTTP test harness; real paid calls not
authorized or performed. No semantic L2, accuracy claims or GCN training.

### Contract

The historical Pilot requested GapGPT Chat Completions at
https://api.gapgpt.app/v1/chat/completions with model `gpt-6-luna`,
temperature 1, n=1 and max_tokens=512. The returned model occasionally had
a revision suffix. These are **historical observations only**.
The proposed JSON configuration in `configs/gapgpt_rich_v2_proposed.json`
pins those fields and both exact returned model identifiers. Provider current
availability, tokenizer, pricing, output size and retention are **unverified**.
The example per-million rates (USD0.10 input, USD0.50 output) and USD0.40
reservation are declared assumptions, not verified Gateway prices or
hard provider billing guarantees.

### Fake integration and reproducibility

~~~powershell
$common = @('--frozen-root', '.local_artifacts/frozen',
            '--authentic-root', '.local_artifacts/authentic',
            '--router', 'r0', '--budget', '37',
            '--gateway-config', 'configs/gapgpt_rich_v2_proposed.json')
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.runner --mode live-preflight @common
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.runner --mode live-fake @common --output-root .local_artifacts/sara3_gapgpt_fake_v1
~~~

Repeat the same `live-fake` command and output directory to prove cached
Completed requests are not redispached. Fake HTTP serializes the same actual
Chat Completions wire request, decodes a complete Chat Completions envelope,
captures synthetic token usage, and executes the existing Rich Prompt V2
Blind, L1, Comparison, L1 and Automated Consistency Screening. All outputs
are synthetic. Full report and GCN Plan are private content-addressed JSON
under the Git-ignored `.local_artifacts` directory.

### Live execution boundary

The `--mode live` CLI is default-denied. Real calls require a new
independent user approval after verification of third-party model
compatibility and exact returned identity, third-party data sharing and
retention, price and declared budget. `live-preflight` emits the
exact-context-bound owner approval template with **all authorization flags
false**. Only a private approval file under `.local_artifacts`, whose exact
context/model/router/budget hashes match and whose approval flags are all
explicitly true, may unlock real dispatch. A separate
`--enable-real-dispatch` switch is required. The API key comes only from
the `GAPGPT_API_KEY` environment variable. The real output directory must
be new and distinct from the historical pilot and fake directories.
No key, response or dataset goes into Git.

The bridge reuses the private SQLite Journal and its write-locked
`BEGIN IMMEDIATE` reservation, with a **distinct live journal version**,
strict protocol/config/cohort hash and unique node+phase intent.
Intent and effective wire SHA are committed before sending; responses are
stored privately with bounded raw bytes and Usage. All resumed Completed
responses are re-read, hash-checked, parsed and L1-validated again.
Unknown HTTP/timeouts retain UNCERTAIN and never auto-retry. Rejected
responses never auto-retry and block new sends. A saved non-abstaining valid
Blind response is required before Comparison. Only a single fixed-host
TLS request is allowed; no redirects, proxy fallback or retries.
A credential echoed in a response is redacted before any audit write and
causes immediate rejection.

Input byte length is a conservative local proxy, **not** provider tokenization.
The local budget uses a worst-case reservation for every attempted request,
including unknown ones, and a user-declared rate. Neither this limit nor
reported Usage guarantees the final invoice. A real response with truncated
finish_reason, missing/invalid usage, unexpected model identifier, schema
failure or inexact quote is rejected. Authentication/transport errors do not
switch models or retry.

### Label and evaluation boundaries

`accepted=false`, `training_class_index=null`,
`L2=NOT_ASSESSED` and `semantic_validation=NOT_PERFORMED` remain mandatory
for routed proposals. Fake outputs may generate an Experimental GCN **Plan**,
not training. Live reports have provider_calls greater than zero and are
**not** accepted by the existing offline-only GCN Adapter. A separately
versioned admission path must be reviewed before any real-GCN experiment.

### Verification

~~~powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_gapgpt_gateway.py" -v
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
~~~

CI tests Fake HTTP on public fixtures. The six sealed Pilot suites and
authentic Cora140 checks still require the owner's local private checkout;
skips are never treated as confirmations. No scientific outcome, raw
accuracy or downstream GCN improvement is implied by the Fake run.

### Contract verification update — November 5, 2026

The upstream **OpenAI** GPT-6 Luna model documentation confirms Chat Completions
support and Standard rates of USD 0.10 input / USD 0.50 output per million
tokens: https://developers.openai.com/api/docs/models/gpt-6-luna .
These facts **do not confirm** access, format, final tariff, billing mode or
retention **at third-party GapGPT**. No current authenticated GapGPT response
or contract proving those facts was obtained. Owner approvals for all of them
must remain false until independently evidenced.

The exact proposed protocol keeps the pilot's `temperature=1`, `n=1`,
`max_tokens=512`, R0, 37/140 and at most 74 requests. The upstream
model's maximum output capacity is not evidence that 512 tokens are enough
for a **specific Rich Evidence V2 JSON response**. Truncated, nonfinal or
over-cap responses terminate the run; the system never silently increases
`max_tokens` or switches models. A future higher-output setting would
require a **new explicitly reviewed contract and separate journal root**.

The `live-preflight` CLI now runs `sara.gapgpt.wire_preflight.v1` for
**every selected node**. It serializes the exact Blind wire and enumerates
seven hypothetical Blind classes for the conditional Comparison, validates
the largest wire byte count against the configured conservative cap, and
checks that worst-case per-attempt reservations times the declared call cap
do not exceed the declared spending cap. Its `wire_preflight` JSON contains
the selected IDs, measured byte bounds and declared maximum monetary
reservation. This is a **local wire/budget check**, not provider tokenization,
model availability, billing approval or proof of successful Rich JSON output.

The private response receipt now persists a **safe explicit incompatibility
code** (e.g. `RETURNED_MODEL_MISMATCH`, `TRUNCATED_OR_NONFINAL`,
`PROVIDER_USAGE_MISSING`, `PROVIDER_USAGE_OVER_CAP`,
`PROVIDER_TOTAL_TOKENS_CONFLICT`, or the L1 validation error). The public
Summary aggregates the exact provider-reported `returned_models` for
Completed phases, `rejection_codes` for Rejected phases and
`unknown_billing_attempts` for Rejected/Uncertain attempts. Token usage
and modeled spend **only cover Completed responses**; incomplete attempts
may still be billed by the Gateway. Do not infer that the reported
`estimated_cost_usd` is a full invoice.

**Backward compatibility:** these diagnostics are separate from the
content-addressed scientific report and do not alter valid existing
Fake-HTTP response metadata. The previous Cora Fake-HTTP journal should
therefore replay with zero new dispatches and the same scientific report
SHA; a session Summary SHA may differ by design.

Before paid dispatch: the owner must independently verify current Gateway
model availability and returned identity, account-specific rates and
limits, data handling and consent, 512-token Rich JSON compatibility,
full regression on the local private checkout, and approve the exact
router/call cap/budget. None of these is self-approved by `live-preflight`.

### Owner-authorized live batch without provider-tariff attestation

On 2026-11-05, the owner explicitly authorized the **exact** previously
preflighted Cora-140 R0/37 batch with at most 74 Blind/Comparison requests,
a declared USD 0.40 batch budget and no automatic retry. The owner further
clarified that externally unverified third-party pricing must **not**
prevent the first model response or the batch. This authorizes data sharing
of the fixed text prompts and the scoped run; it does **not** establish
current Gateway pricing, data retention, successful Rich JSON compatibility
or upstream model identity.

The CLI supports the following **one-action owner-operated execution**,
provided `GAPGPT_API_KEY` has been set securely in the same Windows session:

~~~powershell
git pull --ff-only origin main
$common = @('--frozen-root','.local_artifacts/frozen',
            '--authentic-root','.local_artifacts/authentic',
            '--router','r0','--budget','37',
            '--gateway-config','configs/gapgpt_rich_v2_proposed.json')
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.runner --mode live @common --enable-real-dispatch --output-root .local_artifacts/sara3_gapgpt_live_cora140_r0_20261105
~~~

The owner must deliberately execute this command; CI and ChatGPT tools
**never** fetch the key or dispatch paid calls. No additional per-phase
approval file or manual verification flag editing is necessary for this
specific owner-approved scope. The activation flag derives a private
owner authorization with exactly three positive permissions:
`data_sharing_approved`, `spend_approved`, and
`explicit_batch_dispatch_approved`. It does **not** turn any of the four
provider-verification flags from false to true. The exact Frozen input,
model/settings, Router and budget must match the prior published
`execution_context_sha256` and `gateway_contract_sha256` from
`live-preflight`; anything different fails closed, with no network call.
This one-time scoped convenience path cannot authorize other experiments.

The authorization receipt is written privately **before the first dispatch**.
The run uses a **new** Live output root; never reuse the Fake HTTP journal.
Only a successful complete response (HTTP status, exact allowed returned
model, `finish_reason=stop`, strict Rich V2 JSON, exact source quotes and
bounded provider usage) can complete a phase. The first invalid response
halts all further sends. After interruption, a re-run of the **same command
with the same private output root** can replay completed phases. Unknown or
rejected intents are never retried automatically.

`max_tokens=512` is **unchanged**, deliberately. If the first real
response is truncated, the run stops and records
`TRUNCATED_OR_NONFINAL`; do **not** increase tokens silently or restart
under another output root without a separately reviewed scientific protocol
amendment. Until independent Gateway rate verification, the observed
token usage is provider-reported and the monetary estimate uses
user-declared, not verified, rates. The USD 0.40 budget gate is calculated
against those declared rates only, so it is **not** a genuine invoice limit.
The **74-call ceiling is independently enforced** in SQLite.

The existing live mode only freezes and privately audits the LLM annotation
report; it does not automatically read Ground Truth or train GCN. Those
are separate *post-freeze* stages with independent GT boundaries and
matching graph/features/splits. No evaluation or training result should be
claimed without execution against the owner's private artifacts.

### Proposed, NOT dispatched: reasoning-token exhaustion amendment (2026-11-05)

The owner-operated first actual LIVE HTTPS request from the frozen v1/512
contract returned HTTP 200 and allowed `model=gpt-6-luna`. Private
diagnostic metadata reported:

- `node_id=25`, `phase=blind`, `finish_reason=length`
- `prompt_tokens=1522`, `completion_tokens=512`,
  `completion_tokens_details.reasoning_tokens=512`
- `message.content` had zero characters; a response ID existed
- Journal: **1 REJECTED, 0 COMPLETED, 0 UNCERTAIN**, fail-closed halt
- This rejected request's usage is **not** part of the completed-only
  `estimated_cost_usd`; actual invoice remains unknown.

This directly establishes that the 512-output-token limit was consumed by
reasoning before any visible rich JSON could be emitted for that one request.
It does NOT establish how many output tokens are needed for all 37 nodes,
nor that increasing tokens guarantees L1-valid JSON.

The historical v1 manifest `configs/gapgpt_rich_v2_proposed.json` remains
**byte-unchanged**. A separate, explicit *proposal* exists at
`configs/gapgpt_rich_v2_output4096_proposed.json`:

- Protocol version `sara.gapgpt.rich_v2.gateway.v2`
- Only changed research parameter: `max_tokens: 4096`
- `model=gpt-6-luna`, `temperature=1`, `n=1`, Rich Prompt V2,
  R0, 37/140, 74 calls, `max_input_tokens=32768`, and USD 0.40 declared
  budget are **unchanged**.
- Worst-case 74-attempt reservation using user-declared (unverified)
  USD 0.10/0.50 input/output rates: **USD 0.3940352**.
  The remainder under 0.40 is only USD 0.0059648 under those rates.
  **Neither amount guarantees actual Gateway billing.**

Only a version-bound `4096` is accepted with v2, and only `512` is
accepted with v1. The old v1 authorization Hash **does not** authorize
v2. A separately verified, explicit amendment approval must be established
before attempting live v2; it must not be represented as part of the
original 512-token batch. Do not flip provider-verification flags to true.

Read-only local preflight for v2 (no HTTP, no fee):

~~~powershell
$amended = @('--frozen-root','.local_artifacts/frozen',
             '--authentic-root','.local_artifacts/authentic',
             '--router','r0','--budget','37',
             '--gateway-config','configs/gapgpt_rich_v2_output4096_proposed.json')
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.runner --mode live-preflight @amended
~~~

**Do not run v2 with `--mode live` yet.** Preserve the halted v1
`.local_artifacts/sara3_gapgpt_live_cora140_r0_20261105` folder
unaltered, especially its REJECTED SQLite intent and private HTTP raw
receipt. A new *approved* v2 batch must use an entirely different
`.local_artifacts` output root, never overwrite, reset, or silently retry
the original attempt. None of the tests execute paid HTTP.
