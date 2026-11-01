# Authentic Cora SARA-3 pilot preparation

This is an offline engineering run on authentic inputs. Deterministic lexical
fixtures are not LLM outputs, corrections, accuracy or independent scientific results.
No API client or execution command is implemented.
The fixture deliberately uses target keywords, not neighborhood inference; tests
check evidence delivery, not its scientific usefulness to a future real verifier.

## Historical P0 selection reconstruction (separate protocol)

`manifests/historical_p0.json` is a versioned reconstruction of the reported P0
selection contract, not recovered source or byte-identical P1 wire data. It fixes
Group A to 734,2379,2490,682 (Judge002 and SARA3_V1 each), and Group B to
1031,655,1013,1328 (SARA3_V1 only): eight unique nodes, twelve logical node/arm
records. Order and membership are fixed; the validator never reroutes or selects.
The twelve logical records are not the six-node pilot's up-to-twelve stage intents.
Historical V1 generation calls per record remain unknown; do not assume two.

Read-only validation from the checkout root, using the existing three pinned
frozen JSON inputs (B1, Narrative v0 and FeatProp selection):

```powershell
$env:PYTHONPATH = Join-Path $PWD 'src'
python -B -m llmgnn_sara.pilot.historical_p0 --manifest manifests/historical_p0.json --frozen-root .local_artifacts/frozen
python -B -m unittest discover -s tests -p test_historical_p0.py -v
```

The manifest and all three inputs are SHA-256 admitted before JSON use. Source
document hashes identify secondary reports; they do not authenticate lost P1 data.
Group B agreement and HH (both confidences >=80 percent) are checked from frozen
predictions. This descriptive bucket comes from the historical results report;
it does not reconstruct Policy 002. Historical R1 membership and exclusion from
historical R0 remain REPORTED_UNVERIFIED. Exact Judge002/V1 prompts and schemas,
Policy 002 rules, R1 selection evidence, original selection hashes, V1 arbitration
and original P1 wire bytes/hashes remain MISSING_EVIDENCE. No transport or judge
behavior is added. Existing six-node sealed files are unchanged.

## Restore inputs and run from a clean checkout

Use Python3.10+ and the README setup. No third-party dependency is required unless
an explicit local tokenizer cache is requested. Restore the four required frozen
files listed in manifests/frozen_artifacts.json: B1/v0 final predictions, selection
manifest and preparation receipt. Restore the five files in
manifests/authentic_inputs.json under .local_artifacts/authentic/. The manifest
contains exact original Drive paths/IDs, destination names and SHA-256 values.
Download these JSON files with the archive owner's authorized account; do not run
historical Python or deserialize any graph/model .pt. Duplicate original filenames
must be renamed to the destination names in the manifest, not guessed by order.

PowerShell, from the checkout root (the output directory must not exist):

```powershell
$env:PYTHONPATH = Join-Path $PWD 'src'
python -B -m llmgnn_sara pilot-prepare --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --output .local_artifacts/pilot-gapapi
python -B -m unittest discover -s tests -p test_pilot.py -v
```

On the configured machine, use .venv/Scripts/python.exe. Add
`--tokenizer-cache .local_artifacts/tokenizer_cache` only when the installed
tiktoken and pinned cl100k_base public cache are available. No command implicitly
downloads a tokenizer. Without that flag, token estimates are character-based.
cl100k_base plus64 framing tokens is a surrogate, not verified GapAPI tokenization.

Outputs: summary.json; dry_run_r0.json and dry_run_semantic.json with every concrete
fixture request, hash, decision and ledger entry; gcn_plans.json; gapapi/ request
bodies; pilot/ sealed logical requests, conditional templates and protocol;
SHA256.json covers all generated files. Keep outputs external to Git and historical
Drive. A failed earlier attempt may leave a partial new output; never reuse it as
a verified run or overwrite an existing seal. Use another explicit output path.

## Input provenance and blind-first boundary

The loader checks all nine input hashes, 140 IDs, the seven-class order, 280 prompt
hashes against840 sample references and immutable predictions. It removes the exact
historical B1 wrapper to recover target text. Narrative attachment and topology
metadata are checked against the frozen recorded context. Direct neighbors,
representative, degree and complete connected/disconnected neighbor-pair partitions
are explicit immutable evidence. The source receipt anchors the canonical graph
hash. Canonical adjacency is NOT independently recomputed; no graph pickle/GT is read.

Blind inputs contain target text, recorded neighborhood evidence, public Atlas,
instructions and response schema. They contain no B1/v0 classes, votes, confidence,
correctness or diagnostic outcomes. Counterfactual vote changes must preserve the
same node's blind bytes. Comparison explicitly adds original candidate classes and
the validated blind class. Positive replies require substantive exact target-paper
quotes; neighbor-only or whitespace quotes are invalid. Paper/context instructions
are untrusted data. Primary topic takes precedence over auxiliary techniques.

## Fixed pilot and future execution gates

- Six unique nodes: first3 by reconstructed confidence/agreement risk, then first3
  distinct semantic-ranked nodes; ascending node-ID ties. No GT, inspected error
  lists or replacement after outputs. This is purposive feasibility sampling.
- At most12 generation calls: six blind, up to six comparisons. A blind abstention
  can stop its comparison. No token-count API calls or automatic retries. Unknown
  timeouts count as spent intents and abstain until reviewed.
- Blind requests are frozen exactly. Future comparison class is unknown: freeze
  templates with $BLIND_CLASS_INDEX; materialize only after validating class0..6,
  recording template/blind-response/final-request hashes. Fixture-specific concrete
  comparison requests are never represented as future real response bytes.
- Intended historical provider: GapAPI; model gpt-6-luna; Chat Completions endpoint
  https://api.gapapi.com/v1/chat/completions; n1, temperature0.7. The model/settings
  match pinned historical requests, and endpoint matches pinned runner source.
  Current gateway availability, max_tokens support, account tariff and retention
  are UNVERIFIED. No provider API call was made to check them. Public documentation
  lookup was inconclusive. Do not substitute direct OpenAI assumptions.
- Output cap512/call, input estimate cap16384/call, timeout120s. These are local
  proposed controls, not a provider-enforced billing limit. A $1 input/$4 output
  per-million scenario is illustrative, not GapAPI pricing. Approval must identify
  actual rates, data-sharing/retention, credentials mechanism, budget and seal SHA.
- DurablePilotLedger persists intent hashes with a12-intent cap, duplicate/retry
  rejection and terminal uncertainty across restarts. Keep its SQLite file outside
  the immutable seal. No credentials or response bodies are stored there. A future
  reviewed transport must bind this ledger to the approved seal before dispatch.
- Third-class outputs remain proposals and never accepted training labels.
  Malformed replies, unsupported evidence, conflicts and failures abstain.

## Matched downstream and evaluation

The frozen140 cohort is the pilot source pool. CE/noPS is the simple primary
comparison; WCE/noPS is supplementary, selected after earlier exploratory results.
Plan both baselines and future accepted SARA outputs with the same selected pool,
common2568 test IDs, seeds0..9, 30epochs, no early stopping and exact loss semantics.
Historical Primary135 is also prepared as a predefined subset of these frozen
decisions; no excluded/abstained selected node becomes test data. Fixture plans
are engineering checks only. Before real training, replace fixture labels with
independently admitted, frozen authorized verifier outputs. No training ran.

Evaluate feasibility, schema/evidence validity, failures, abstention, coverage,
class retention, calls and resource use. Label quality and downstream improvement
remain unknown. GT evaluation requires separate authorization after decisions
freeze; Cora has prior diagnostic exposure, so results remain exploratory. An
untouched cohort is needed for confirmatory generalization claims.
