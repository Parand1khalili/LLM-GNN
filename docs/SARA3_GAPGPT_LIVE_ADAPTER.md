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
