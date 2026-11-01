# Offline routing experiment draft v1

Status: **DRAFT / NOT_AUTHORIZED_FOR_LIVE_EXECUTION**. No scientific winner,
pilot cohort freeze, provider compatibility approval or spending authorization.
Manifest: `../manifests/routing_experiment_draft_v1.json`.
SHA256: `dd2cd784e58cbb905ffa6c337782ef67073960a11ca32d07e8f9991dcc71387b`.

## Contract and adapter

The manifest records all140 cohort IDs/order, nine authenticated source hashes,
full typed-input fingerprint, canonical class order, five router versions/selections
and selection hashes. Primary arms are R0 control, R1-v2 and R2-v1 candidates;
Semantic-v0/R1-v1 remain optional exploratory arms. All have37 referrals.
R2 preserves its primary exploration hash/domain, U/O/C stage order and4/17/16
allocation; routers are unchanged. Runtime dispatch still follows cohort order.

`sara3.experiment.load_selection` performs bounded pinned-file admission and
recomputes the entire expected contract. It returns an immutable VerifiedSelection.
`run_offline(..., selection=verified)` rechecks the pinned manifest, full inputs,
selection, budget37, default PolicyConfig and legacy schema before dispatch.
Default router argument must remain `r0` when an explicit selection is supplied;
the result reports `manifest:<arm>`, not a silently substituted R0 selection.
Without selection, existing `r0`/`semantic` defaults and output remain unchanged.

`sara.verifier.legacy.v1` is a new explicit manifest identifier for the unchanged
legacy response schema; it is not a recovered historical schema name or new prompt.
Rich substitution is rejected. Instructions, class atlas, response schema,
per-node target/neighborhood hashes, blind payloads and comparison templates are
pinned. Comparison executes only after valid non-abstaining blind; missing text,
L1 failure, uncertain execution or unavailable audit stops that path. L2 remains
NOT_ASSESSED; no reviewed label or third-class proposal is accepted for training.
Unreviewed labels still follow the existing frozen-candidate baseline policy.

## Request identity and reuse boundaries

Identity is SHA256 over canonical JSON containing identity-version, complete
effective payload, complete explicit offline execution context and dependency.
Context binds fixture version, draft experiment, full cohort fingerprint,
protocol fingerprint and model-settings placeholders. Arm name is excluded so
identical common-node requests can share a response. Node ID remains in payload;
identical text at different IDs does not cause cross-node reuse.

Blind identities are materialized. Comparison templates have no reusable identity:
the actual blind class and SHA256 of the complete decoded raw blind response
must be known. Same class with a different blind response is a different identity.
Payload/context changes produce different keys; unresolved templates are rejected.
Model/provider/endpoint/settings are null placeholders, not compatible live settings.
The identity function accepts only explicitly offline contexts.

`CachedOfflineVerifier` reuses only L1-valid decoded responses from the same
in-process versioned fixture instance, after private audit readback and binding
checks. Each return is detached from caller mutation. Intent precedes dispatch;
malformed/rejected/uncertain attempts are not reusable and are not automatically
retried. Decoded raw outputs and rejection diagnostics stay in private audit,
never training labels or public GraphScope. Cache and pipeline arm ledgers are
distinct: old `offline:node:phase` IDs are arm-local audit IDs, not dedup keys.

This is not cross-process caching, a crash-durable exactly-once system, a live
provider wire identity, or a billing guarantee. Independent replicates must use
separate cache instances; no cross-replicate reuse is supported. A future live
revision must explicitly bind resolved wire/model/revision, account/project and
retention scope, replicate/seed, generation and timeout/retry settings. It requires
separate approval and cannot reuse these synthetic receipts as model responses.

## Bounds versus synthetic execution

| Scope | Selected / blind identities | Potential conditional comparisons | Maximum generation calls |
|---|---:|---:|---:|
| Each arm standalone (including optional arms) |37|37|74|
| Three primary arms standalone sum |111|111|222|
| Three-primary union, one bound blind result per identity |62|62|124|

The62 potential comparison slots are not precomputed request identities. Bounds
assume no retry and one fixed blind result per identity; comparison may never
execute. Optional arms are excluded from primary-union accounting. No prices,
provider token counts, dollar costs or actual future response-dependent totals
are asserted. Generation-call bounds are not billing caps.

The executed fixed modulo4 synthetic fixture exercises blind abstention,
comparison abstention, third-class proposals and candidate agreement. It produces
203 logical requests across the arms,114 underlying fixture dispatches and89
cache hits; all114 unique dispatched identities completed. These are test counts,
not live calls or scientific findings. Per-arm logical requests: R0=69, R1-v2=66,
R2-v1=68. Reviewed accepted labels0 in every arm; third-class accepted0; all
decision/training node IDs unique within each arm. Frozen unreviewed baseline
retention93/73/84 is not verifier approval. Do not combine different arms' labels
into one training set. Raw audit fixtures are private temporary files removed
after each run; no historical response body is involved.

## Reproduce

Use the existing offline environment and nine approved external JSON inputs
described in README; no dependency installation is needed for this slice.

```powershell
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.routing_experiment --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --manifest manifests/routing_experiment_draft_v1.json --output .local_artifacts/routing_experiment_new.json
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_routing_experiment.py -v
```

Output must be new; existing outputs are not overwritten. Both paths are offline;
the command creates only temporary private synthetic audits plus the requested
summary. Authentic source files, private human reviews, P0 and pilot seals are
not modified. Summary: `../reports/routing_experiment_offline.json`.

Verification: initial focused11 tests PASS; the full Python suite includes all12
new tests and ran229 total:228 PASS,1 Windows filesystem-symlink privilege SKIP
in199.481s. ZIP-symlink rejection still runs. No failed tests. Actual human-review
session access and network were guarded; review-schema regressions used temporary
synthetic records. Nonblocking PyTorch deprecation warning observed. No real
model training or untrusted model load. P0/nine inputs/31+13 pilot seal members
remain verified. Unrelated GraphScope frontend checks were not run.

Before any separately approved pilot: review this draft and the selected schema,
resolve provider/model/endpoint/credentials mechanism outside source code, verify
compatibility/privacy, freeze actual wire/generation context and independent
replicate semantics, establish a cost budget with offline parser tests, and use
durable intent/recovery handling. L2 semantic approval remains unimplemented;
this slice establishes engineering integration, not scientific label reliability.
