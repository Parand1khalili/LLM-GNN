# SARA-3 Rich Prompt V2: durable synthetic runner

Status: **offline integration implemented; LIVE DISABLED; GCN NOT TRAINED**.
Version `sara.runner.rich_v2.synthetic.v1`. The purpose is to establish a
testable transport/persistence boundary against authentic **pinned** Cora140
inputs, never to claim measured L2 or pseudo-label accuracy.

## Execution

```powershell
$common = @('--frozen-root', '.local_artifacts/frozen',
            '--authentic-root', '.local_artifacts/authentic',
            '--router', 'r0', '--budget', '37')
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.runner --mode dry-run @common
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.runner --mode offline @common --output-root .local_artifacts/sara3_rich_runner
```

Re-run the **same** offline command to Resume. Other prospective routers:
`--router r1_v1`, `r1_v2`, `r2_v1`, budget exactly 37; `semantic`
is the separate lexical legacy approximation. R0/semantic retain existing
budget behavior; choosing a prospective router is NOT an experimental freeze.

The dry-run validates pinned data with `load_project_inputs`, computes a
versioned GT-free protocol hash, selects actual nodes and hashes the rich-v2
Blind payloads. No durable state or outbound call is created.

The offline execution uses a purely synthetic hash-derived class fixture
that sees target text, *not* historical candidate labels during Blind.
This fixture exists only to exercise L1, Comparison and Arbitration. A
real but irrelevant exact quote can still pass L1 and concordance screening;
this is never semantic L2.

The original private SQLite `DurableOfflineFixtureVerifier` is extended
with a Rich-V2-specific validator, not forked or replaced. Each effective
request identity includes its full payload, context, and for Comparison the
hash of the saved non-abstaining Blind response. The run context binds all
pinned input artifacts, entire Cora Pair content (including graph evidence),
Router, budget, prompt schema/version and Arbitration version. It also pins
the fixture protocol and requires all provider settings be null. SQLite
`UNCERTAIN` intent is committed **before** the fixture transport call;
terminal `COMPLETED` requires a separately persisted auditable raw-response
receipt and successful Rich L1. No implicit retries occur after failure or
uncertain dispatch. A previous completed response is reread and revalidated
on replay. Each run also creates immutable phase receipts in the original
`run_offline` pipeline.

The private report includes all 140 decisions and full request inputs, so
**never publish or Git-add its private audit directory**. Its content-addressed
SHA-256 stays stable across successful Resume: per-session dispatch/replay
counters are only in the separate aggregate summary. Both Report and
Experimental GCN Plan are independently saved in private content-addressed
files. They have **no training permission**, and routed proposals continue
to have `accepted=false`, `training_class_index=null`, `L2=NOT_ASSESSED`.
`downstream.prospective.controlled_gcn_plan` checks the report/pair pins and
rederives the exact selected nodes and candidate eligibility; it only creates
a matched plan with `training_runs=0`.

The summary records the 140 denominator, routed count, completed Blind and
Comparison, L1 completed/failed-phase counts, baseline and provisional
Coverage/distributions, potential admitted Coverage, journal status, zero paid
calls, and unknown provider usage. Fake mode records zero dollar cost only
because no provider transport is used; it is not a prediction of API cost.

## Checks and limits

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_rich_runner.py" -v
.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_experimental_gcn_admission.py" -v
.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_automated_*.py" -v
.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_precomparison_l2_gate.py" -v
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

GitHub Actions runs the four focused suites and a broad **public-only**
regression on main pushes. Six sealed GapGPT pilot test modules depend on
non-versioned private raw/seal artifacts. They are **not** run by the public
workflow, never recorded as PASS and are NOT weakened or modified; the initial
full-suite attempt showed six setUpClass InputErrors because SHA256.json private
input was absent. A full regression still requires the owner's complete private
checkout. The authentic-Cora integration test similarly runs only if the
hash-pinned Frozen and authentic input roots are present; skipping it proves
nothing about authentic readback. Never report synthetic Coverage as real
LLM effectiveness. Runtime never reads Ground Truth.

**Not implemented:** a verified current GapGPT response/usage adapter,
authorization-controlled paid batch, real provider-side retention/price
preflight, persistent live billable call cap, manual reconciliation of unknown
requests, and real GCN training/evaluation. The CLI's `--mode live` is
explicitly blocked until these receive their own versioned implementation and
separate spending authorization. No API key is read in this slice.
