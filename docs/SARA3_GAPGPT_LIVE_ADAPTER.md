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
v2. The owner separately and explicitly approved the v2 amendment after
the documented preflight. Its new execution and configuration hash pins are
independent of the originally approved 512-token batch. Do not flip
provider-verification flags to true.

Read-only local preflight for v2 (no HTTP, no fee):

~~~powershell
$amended = @('--frozen-root','.local_artifacts/frozen',
             '--authentic-root','.local_artifacts/authentic',
             '--router','r0','--budget','37',
             '--gateway-config','configs/gapgpt_rich_v2_output4096_proposed.json')
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.runner --mode live-preflight @amended
~~~

Preserve the halted v1
`.local_artifacts/sara3_gapgpt_live_cora140_r0_20261105` folder
unaltered, especially its REJECTED SQLite intent and private HTTP raw
receipt. The separately approved v2 batch must use a different
`.local_artifacts` output root and never overwrite or reset the original
attempt. The v2 output-cap change is a new, explicitly amended protocol,
not a retry of the same v1 wire. None of the automated tests execute
paid HTTP.

### V2 authorization and owner-operated live execution

The owner explicitly approved the **512 → 4096** amendment following the
successful read-only Cora140 v2 preflight. Both new hashes are pinned:

- `execution_context_sha256=c41b7a6ecec46a2a99c3b570f7e0b093756db4db98d692f4bb956135584599f8`
- `gateway_contract_sha256=59fd3de634a4aabae97fc9df02c396c5c435819e8b7f4cdbde1fe7837a8c165f`

The same R0/37/Cora140/74 max-calls/declared USD0.40 parameters
apply, with `temperature=1`, `n=1`, the unchanged Rich Prompt V2 and
Automated Concordance V1. The code's scoped owner authorization now
accepts only the original exact v1 hash pair or the separately approved
exact v2 hash pair, and it writes an amendment identifier in the private
authorization receipt before the first network attempt. Neither the
existence of an API key nor the live CLI flag validates provider tariff,
retention or response format; those remain explicitly unverified.

After confirming that `GAPGPT_API_KEY` is already set in the same
PowerShell session, the owner runs:

~~~powershell
git pull --ff-only origin main
if ($LASTEXITCODE -ne 0) { throw "Git pull failed" }

$amended = @(
  '--frozen-root', '.local_artifacts/frozen',
  '--authentic-root', '.local_artifacts/authentic',
  '--router', 'r0',
  '--budget', '37',
  '--gateway-config', 'configs/gapgpt_rich_v2_output4096_proposed.json'
)

if (-not $env:GAPGPT_API_KEY) { throw 'GAPGPT_API_KEY is missing' }

.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.runner --mode live @amended --enable-real-dispatch --output-root .local_artifacts/sara3_gapgpt_live_cora140_r0_4096_20261105
~~~

This command is **real paid inference**, not dry-run. The first invalid
or interrupted request halts the remaining batch; `max_tokens=4096`
does not guarantee success. Never create another output root just to
bypass an existing REJECTED or UNCERTAIN intent. On a successful
completion the report is a frozen LLM annotation result; Ground Truth
accuracy and actual GCN training remain separate private evaluation
steps and are not implemented by this CLI.

### Real v2 Batch halt: L1 duplicate evidence, no retry

The owner reported the first real v2/4096 execution stopped with
`BLOCKED_NO_AUTOMATIC_RETRY`, after **53 real attempts**. Its private
journal summary records **52 COMPLETED** (29 Blind + 23 Comparison),
**1 REJECTED**, **0 UNCERTAIN**, rejection code
`L1_DUPLICATE_EVIDENCE`. The 52 completed responses reported
79,337 prompt tokens and 32,297 completion tokens; their modeled
cost under **unverified user-declared rates** is USD 0.0240822.
The rejected attempt may separately be billed. All 52 successful
returned model IDs were permitted by the contract (22 alias, 30 dated
revision). These are *owner-reported* live-run facts, not new
assistant-executed network requests.

The original strict `sara.l1.decorative_quote_match.v1` policy
rejects duplicate normalized exact-source quotations across **both**
`supporting_evidence` and `counter_evidence`. A duplicate citation
is a structural failure, not itself proof of a wrong primary class.
The implementation must not silently deduplicate, change L1 rules,
or automatically retry the terminal REJECTED request. Coverage and
accuracy cannot be inferred from a partially completed and halted run.
GT and GCN training remain unperformed.

For exact **read-only, content-free** diagnosis of the rejection,
the owner runs this against the *existing* v2 output root; it does not
require or read an API key:

~~~powershell
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.gateway_diagnostics `
  --output-root .local_artifacts/sara3_gapgpt_live_cora140_r0_4096_20261105 `
  --expected-context-sha256 c41b7a6ecec46a2a99c3b570f7e0b093756db4db98d692f4bb956135584599f8
~~~

The diagnostic opens the SQLite journal with `mode=ro` and
`PRAGMA query_only`, verifies the journal's exact context
binding and the private content-addressed HTTP response receipt
hashes, and prints only whitelisted metadata: rejected node ID,
phase, HTTP status, safe error code, model whitelist ID, finish
reason, provider-reported usage, support/counter counts and the
number/category of repeated exact quotes. It does **not** print
quotes, claims, target papers, raw HTTP bodies, response IDs,
API keys or other prompts. If it detects a broken receipt/binding,
it fails closed. Existing run data must remain immutable.

## Slice 1 (2026-11-06): reporting-only repair

The owner reports a halted, local-only Cora-140 R0 Rich V2/4096 live run: 53 recorded attempts (52 COMPLETED, one REJECTED for node 1814 compare / L1_DUPLICATE_EVIDENCE; zero UNCERTAIN). The private journal was **not** available to the GitHub editing session. No new dispatch, GT evaluation, L2 approval or GCN training was performed. The batch remains halted; never resume it from these changes.

The corrected run-report layer distinguishes nodes with no persisted intent after halt from genuine UNCERTAIN intents. The new `python -B -m llmgnn_sara.sara3.gateway_usage_report` reconciles only local, content-hash-verified private receipts with declared tariff inputs. COMPLETED/REJECTED/UNCERTAIN and ALL ATTEMPTS are separate, and incomplete provider usage produces a null total estimate rather than a fabricated invoice. Historical summary JSON and terminal states remain immutable. The reported 80760 input / 33192 output / 18619 reasoning tokens and USD 0.0246720 are **owner-provided observations**, pending local read-only reconciliation, not independently verified by this GitHub change. L1/prompt/router/arbitration remain unchanged.

## Slice 2 continuation preparation — 2026-11-06

Historical Cora140/R0 Rich V2/4096 remains halted: owner read-only evidence reports 52 COMPLETED, one L1_DUPLICATE_EVIDENCE REJECTED (node 1814 / compare), zero UNCERTAIN. This is a valid structural L1 rejection; the semantic polarity of its claims is NOT established. No reclassification, retry or training proposal for node 1814.

`python -B -m llmgnn_sara.sara3.gateway_continuation` is a **read-only local preflight** requiring existing frozen/authentic inputs, original private output root, exact gateway config, and context hash. It reconstructs and validates EVERY historical identity, wire/payload digest, saved Blind dependency, receipt SHA and strict L1/usage for completed responses. It refuses uncertainty/tampering. It reports never-dispatched blind IDs, conditional comparisons, cumulative capacity, and fresh amendment/authorization requirement. No API key or HTTP is used.

A minimal **synthetic-only** continuation overlay verifier exists for regression: original SQLite/receipts are read-only, any new fixture intents are appended exclusively under a distinct continuation directory tied to the original run; original REJECTED remains a terminal abstention. This is NOT a new experiment or a fresh 74-call budget. It does not enable live dispatch or create an owner approval. A separate amendment and explicit future authorization are required before extending this adapter to live traffic; do not invoke the old live runner to resume the halted run. No GT, GCN, L1, Prompt, Router or Arbitration modifications were made.
