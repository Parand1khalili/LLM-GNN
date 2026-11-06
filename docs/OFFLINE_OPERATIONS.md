# Earlier offline operations reference

Preserved from the root README during the 2026-11-06 documentation update.
Commands below are run from the repository root, not from this directory.
This is an earlier operational snapshot: its statements about absent remotes,
unimplemented adapters and authorization are historical, not current status.
Use the [current README](../README.md) and
[halt/continuation record](SARA3_GAPGPT_LIVE_ADAPTER.md) for current boundaries.
Never restart a halted live run from an older command in this reference.

One evolving research repository for the pre-Codex B1/Narrative baseline and
explicitly reconstructed SARA extensions. Historical artifacts remain read-only.
Live inference and real training are not authorized.

## Run locally

Python 3.10+; the offline runtime has zero third-party dependencies.
Without installing anything, from this repository in PowerShell:

~~~powershell
$env:PYTHONPATH = Join-Path $PWD 'src'
python -B -m llmgnn_sara doctor
python -B -m llmgnn_sara sara3-offline --demo
python -B -m unittest discover -s tests -v
~~~

On this machine the available base Python is:
C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe

An editable installation was actually verified with existing build tools,
without network access or downloaded dependencies:

~~~powershell
python -m venv --system-site-packages .venv
.\.venv\Scripts\python.exe -m pip install --no-index --no-deps --no-build-isolation -e .
.\.venv\Scripts\python.exe -B -m llmgnn_sara doctor
~~~

The install needs existing setuptools>=61. On a fresh machine use the no-install
PYTHONPATH route or explicitly provision build tools. No application command
installs dependencies. Optional CPU Torch, PyG and tiktoken were subsequently
installed in .venv with the owner's permission; the tiny synthetic GCN forward
and cached cl100k_base prompt-budget tests passed. Real training is NOT_RUN.
Versions and the initial resolved TLS failure are recorded in
configs/offline_tested_environment.json. This is not the historical environment.

To recreate the tested optional Windows CPU environment on a fresh machine
(these commands download official dependencies):

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --index-url https://download.pytorch.org/whl/cpu 'torch==2.15.0+cpu'
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r configs/offline_cpu_requirements.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
~~~

The tokenizer's first explicit initialization may download its public vocabulary;
the application never initializes it implicitly. Tests never download the cache.

## Actual frozen replay and integrated dry-run

Supply exact external artifacts under .local_artifacts/frozen/ (Git-ignored),
or pass other read-only paths. Locations/IDs/pins are in
manifests/frozen_artifacts.json; datasets and raw responses are not in Git.

~~~powershell
$inputs = @('--b1', '.local_artifacts/frozen/b1_final_predictions.json',
            '--narrative', '.local_artifacts/frozen/narrative_v0_final_predictions.json',
            '--selection', '.local_artifacts/frozen/selection_manifest.json')
.\.venv\Scripts\python.exe -B -m llmgnn_sara replay-frozen @inputs
.\.venv\Scripts\python.exe -B -m llmgnn_sara pipeline @inputs --cohort primary --loss wce
.\.venv\Scripts\python.exe -B -m llmgnn_sara gcn-plan @inputs --arm both --loss ce
~~~

replay-frozen re-votes 280 target-arm decisions from 840 stored parsed samples,
comparing classes/fallbacks exactly and confidence within 1e-12. This is NOT
raw-response parsing, complete raw recovery, GCN reproduction or improved accuracy.
Raw provenance remains RAW_PROVENANCE_PARTIAL.

pipeline stops on a baseline mismatch, runs the offline SARA policy and prepares
matched B1/v0 and accepted-SARA GCN plans. Without target text, selected reviews
abstain and completed reviews remain zero. Retained high-confidence agreements
are policy decisions, not measured verifier corrections. The explicit synthetic
demo exercises blind-first/comparison verification, evidence, proposals and failures.

## Authentic Cora pilot dry-run

Authentic140 target texts and recorded graph-derived neighborhoods are now
admitted from pinned project JSON, together with frozen votes and the public
Class Atlas. No graph/model pickle or ground truth is read. See
[pilot protocol and input restore instructions](PILOT_PROTOCOL.md).

```powershell
.\.venv\Scripts\python.exe -B -m llmgnn_sara pilot-prepare --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --output .local_artifacts/pilot-gapapi --tokenizer-cache .local_artifacts/tokenizer_cache
```

The output must be new; existing seals are never overwritten. Omit the tokenizer
flag on a standard-library-only checkout (estimates then use character counts).
Exact fixture request inputs, routing decisions, abstentions, matched GCN plans
and the six-node/twelve-call pilot seal are written outside Git. Fixture outputs
are not measured scientific findings. Canonical graph adjacency is not independently
recomputed. GapAPI/gpt-6-luna matches historical configuration; current gateway,
output-cap support, tariff and retention need preflight and separate approval.

## Scientific boundaries

Read docs/SCIENTIFIC_PROTOCOL.md for the published paper/proposal/historical/
reconstruction lineage. FeatProp is not C-Density; B1 is not an exact paper B0
reproduction; Uniform2Path3 is not a literal random walk. Both historical arms
used the same underlying LLM.

SARA defaults are new unvalidated decisions, not restored Policy002 thresholds
or historical routing parity. Class semantics are public; no GT diagnostics
enter prompts, routing, filtering or pseudo-training labels. Third-class proposals
cannot become training labels. The default offline ledger is in-memory; only the opt-in synthetic fixture journal is durable. Neither is live-ready.

Exact recovered Narrative topology and the reviewed GCN class are reused.
Frozen PS deletion orders/class guards are checked for both arms/cohorts.
Float64 neighbor selection is not claimed identical to historical Torch float32
near ties. Frozen FeatProp target IDs are replayed, not reselected. The historical
wrapper is pinned; full140-target regenerated prompt hash parity is NOT_RUN.

GCN plans preserve the selected140 pool, Primary135/Sensitivity140, sharedtest2568,
pairedseeds0..9, 30epochs, no validation/early stopping and mean(CE_i*w_i).
Selected exclusions/abstentions never become test nodes. Evaluation is a separate
module with no runtime import edges; tests use synthetic labels only. No GT
decoding or real training occurred. The prepared optional backend is default-denied,
not exposed as an offline training command. Its synthetic forward is tested;
the optimizer/training path remains unexecuted and numerically unverified.

## Offline routing experiment

The draft three-arm router experiment connects hash-verified R0/R1-v2/R2-v1
selections to the unchanged legacy verifier contract, using only offline fixtures.
See [offline routing experiment](OFFLINE_ROUTING_EXPERIMENT.md) for the pinned
manifest, exact commands, conditional request identities and call-budget bounds.
It is DRAFT and NOT_AUTHORIZED_FOR_LIVE_EXECUTION; no provider calls or training.

## Crash-durable OFFLINE fixture replay (no API)

The pinned three-router synthetic experiment has an optional private SQLite journal.
It persists each complete request identity and an UNCERTAIN intent **before**
dispatch. A completed L1-valid fixture can be replayed after restart without
reinvoking the fixture. REJECTED and UNCERTAIN requests never auto-retry.
A failure between dispatch and journal settlement deliberately requires manual
reconciliation; it is not exactly-once delivery or a live provider runner.

~~~powershell
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.routing_experiment --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --manifest manifests/routing_experiment_draft_v1.json --journal-root .local_artifacts/routing_fixture_journal --output .local_artifacts/routing_fixture_run_1.json
# To verify replay, rerun with the SAME journal-root and a NEW output filename.
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.routing_experiment --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --manifest manifests/routing_experiment_draft_v1.json --journal-root .local_artifacts/routing_fixture_journal --output .local_artifacts/routing_fixture_run_2.json
~~~

Both runs use synthetic fixture responses, **zero paid API calls** and **zero
training**. On an unchanged contract, the second run must have zero underlying
fixture dispatches, the same per-arm decisions, and independently revalidated
private receipt bindings. This does not validate semantic L2 or freeze a router.

## Optional prospective L2 boundary (offline only)

Rich Prompt V2 can opt into `run_offline(..., response_version=RICH_VERSION,
prompt_version=RICH_PROMPT_V2, precomparison_l2_gate=True)`. A valid
non-abstaining blind L1 response then becomes `L2_PENDING_BEFORE_COMPARISON`;
no comparison request is sent and no reviewed training label is accepted.
Abstentions and L1 failures are not queued. `l2_pending_node_ids` contains
the eligible IDs, not semantic approvals. This is a **one-way offline checkpoint**,
not an L2 evaluator, resumed human-reviewed Comparison runner, or a live adapter.
The default (ungated) historical fixture behavior and manifests are unchanged.

## Opt-in automatic concordance arbitration (experimental)

`run_offline(..., response_version=RICH_VERSION, prompt_version=RICH_PROMPT_V2,
automated_arbitration_version=VERSION)` executes Blind, L1 and Comparison,
then applies a versioned deterministic consistency screen. It can provisionally
retain B1/Narrative candidates but **does not perform semantic L2 validation**.
No independent judge, human prerequisite, API or training is added.
The existing `precomparison_l2_gate` remains an optional separate path.
Routed proposals now have `accepted=false` and `training_class_index=null`.
Only a separately pinned, explicitly versioned **experimental GCN plan adapter**
can admit them for a controlled *plan*, never automatically for training.
See [automated arbitration and experimental admission](AUTOMATED_ARBITRATION_V1.md).

## Crash-durable SARA-3 Rich V2 synthetic runner (no live API)

The package now exposes a single CLI for authenticated Cora140 dry-run and
durable offline integration, without importing GT or running GCN training.
This is a *prospective synthetic test*, not a measured LLM result:

```powershell
$common = @('--frozen-root', '.local_artifacts/frozen',
            '--authentic-root', '.local_artifacts/authentic',
            '--router', 'r0', '--budget', '37')
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.runner --mode dry-run @common
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.runner --mode offline @common --output-root .local_artifacts/sara3_rich_runner
# Resume: rerun EXACTLY the same offline command and output-root.
```

The offline Runner uses a private SQLite intent journal and content-addressed
Rich V2 response/audit receipts. Completed calls replay without new fixture
dispatches; uncertain/rejected calls are never automatically retried. It writes
private complete reports and plan-only artifacts, and prints a GT-free aggregate
summary containing their SHA-256 paths. `r1_v1`, `r1_v2` and `r2_v1`
are optional fixed-37 *prospective* router variants; `r0` is the reconstructed
baseline. The historical Policy002 is not claimed to be recovered.

The `--mode live` option **refuses execution**. No provider adapter, current
GapGPT preflight, price/retention verification or approval-ready live contract
is implemented in this slice. Never use this command for paid inference.
See [Rich V2 runner contract](SARA3_RICH_RUNNER.md).

## GapGPT Rich V2 Gateway bridge — separate paid approval required

The existing SARA-3 CLI supports `live-preflight` (read-only contract and
approval template), `live-fake` (synthetic HTTP envelope + durable SQLite
Resume) and `live` (default-denied until separately owner-approved).
The adapter retains Blind-first, two-stage L1 and independent training-label
quarantine. No API calls or GCN training were performed by its development.

~~~powershell
$common = @('--frozen-root', '.local_artifacts/frozen',
            '--authentic-root', '.local_artifacts/authentic',
            '--router', 'r0', '--budget', '37',
            '--gateway-config', 'configs/gapgpt_rich_v2_proposed.json')
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.runner --mode live-preflight @common
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.runner --mode live-fake @common --output-root .local_artifacts/sara3_gapgpt_fake_v1
~~~

**Do not use live mode until the owner approves the exact batch and verifies
the Gateway's price, format, retention and privacy policy.** The proposed
config is unverified. Real dispatch requires the private approved contract
file, `--enable-real-dispatch` and an environment credential.
See [the Gateway bridge safety contract](SARA3_GAPGPT_LIVE_ADAPTER.md).

## Raw recovery and backups

For the post-observation blind-only completion on682,2396,653, see
[GAPGPT_BLIND_ONLY_COMPLETION.md](GAPGPT_BLIND_ONLY_COMPLETION.md).
Fresh local amendment/privacy/budget/dispatch approvals are mandatory. Preserved
637/1243 blind requests are never repeated; old halted commands remain blocked.
No automatic resume or training-label acceptance is enabled.

Use scripts/colab_recover_responses.py in the owner's fresh CPU Colab notebook;
see docs/RAW_RESPONSE_RECOVERY.md. For package use in Colab, upload the source tree,
put its src/ directory on sys.path and supply actual external artifact paths.
Do not run historical startup.py or notebook cells.

The former D:\SARA2 source is lost. recovered_sources/ contains pre-Codex
evidence, not a second active implementation. Keep original hashes and attribution.
Review applicable upstream licensing before wider redistribution.

The owner performs GitHub pushes manually. No remote is configured or verified.
The existing docs/MANUAL_GITHUB_BACKUP.md user edit is preserved; its original
instructions remain in commit ee6dd5c. Never push to CurryTang/LLMGNN.
Historical Drive stays read-only; independent artifact backup is proposed,
not uploaded or verified. A local cache is not a remote backup.

See PROJECT_STATE.md, EXPERIMENT_REGISTRY.jsonl, reports/, and
manifests/implementation_lineage.json.

Slice 1 (2026-11-06): offline-only reporting fixes and a receipt-verified read-only usage reconciliation CLI. See docs/SARA3_GAPGPT_LIVE_ADAPTER.md. A halted live batch remains blocked; this does not authorize dispatch.
