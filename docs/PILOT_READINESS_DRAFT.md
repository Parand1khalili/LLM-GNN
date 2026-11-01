# Pilot readiness v1 — offline rehearsal complete, live disabled

The existing DurablePilotLedger already binds a pilot manifest, persists intents,
limits calls12 and blocks duplicate identities/payloads and terminal rewrites.
The separate ReadinessLedger finishes the rehearsal without migrating old databases.

The immutable canonical contract digest binds its sealed-bundle reference, six
fixed feasibility nodes, legacy schema recommendation, unresolved execution context
and caps. Every intent stores that contract digest and exact request hash.
Wrong database/context/request/schema bindings fail closed. Startup never converts
uncertain records to pending or retries them. Old rehearsal databases are rejected,
not migrated. SQLite BEGIN IMMEDIATE and synchronous FULL serialize reservations
and durable transitions subject to SQLite/OS/filesystem durability guarantees.

States: PENDING is a reserved unsent intent; mark_dispatched commits UNCERTAIN
before any hypothetical external action. After restart UNCERTAIN remains blocked.
Only actual parser/L1 success plus private audit write/readback permits COMPLETED.
Malformed JSON/schema/fabricated evidence becomes REJECTED. Failed audit leaves
UNCERTAIN. Terminal records cannot be overwritten. No automatic dispatch/retry
or transport exists. No L2 semantic label is accepted, including on parser success.
Raw response bytes have their own SHA256; private audit receipt has a distinct
content-addressed hash. The audit stores raw bytes losslessly as hex, privately.
No raw response is copied into public exports or training labels.

Reservations remain consumed on failure:12 calls,16384 declared input tokens and
512 output tokens per call; aggregate ceilings196608 input/6144 output tokens.
Declared reservations are not measured provider usage. Financial approval,
pricing, spending budget and token-count method remain UNRESOLVED. All live
execution is unconditionally disabled, even if a caller fills those fields.

Recommend unchanged legacy schema, pending explicit approval, to preserve sealed
prompts and512-output-token feasibility setting. Rich supports structured claims
and counter-evidence but requires separately reviewed prompts, new seals and an
output-budget review; neither supplies L2 approval. The sealed GapAPI/gpt-6-luna
proposal contains scenario prices and local token estimates, not verified current
provider pricing/compatibility or financial authorization. The new provider-neutral
contract deliberately leaves provider/model/revision/endpoint/generation/privacy/
credentials unresolved. No credentials are read and no network is contacted.

Feasibility637,1243,130,682,2396,653 is unchanged and separate from historical P0
734,2379,2490,682,1031,655,1013,1328. P0's12 logical arm records do not establish
12 provider generations. Router-selected cohorts replace neither pilot.

Focused3 tests PASS: crash/restart, duplicate intent/dispatch, wrong bindings,
audit persistence/failure, terminal states, call/token exhaustion, actual existing
legacy parser/L1 with malformed JSON, invalid schema, fabricated quote, abstention
and valid quote. All results keep accepted_label=null and L2 NOT_ASSESSED.
Nine pinned inputs, P0 and both31+13-member pilot seals verified unchanged.
Full guarded suite result is recorded in PROJECT_STATE.md after completion.
No production transport, actual billing guarantee, physical power-loss test,
provider compatibility test or real scientific outcome is established.

Full guarded Python suite:232 tests,231 PASS,1 Windows symlink SKIP;339.736s.
No failures. No actual private human-review access or network.
