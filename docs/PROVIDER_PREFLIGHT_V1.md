# GapGPT preflight — fixed provider decision, 2026-11-01

Update: the owner requested a separately identified fresh blind637 canary using
`https://api.gapgpt.app/v1/chat/completions`, as specified by the current account
panel. Preparation only; historical endpoint/failed intent remain intact. See
[GAPGPT_ENDPOINT_CANARY.md](GAPGPT_ENDPOINT_CANARY.md) for evidence, command and
required fresh local confirmations. No new live request was made.

Provider fixed by owner: **GapGPT (gapgpt.app), GPT-6 Luna**. Do not research
alternatives or migrate providers. Live execution remains NO-GO pending the five
items below. This update supersedes the earlier provider-identity uncertainty and
reference-provider comparisons; historical artifacts are not rewritten.

## Evidence and reusable historical contract

Owner confirms earlier successful use of this service/model. Independently checked
repository evidence is narrower: recovered source hashes and frozen parsed outputs,
not a fresh successful HTTP request or complete raw-response/billing recovery.

- Exact recovered matched-run configuration: model `gpt-6-luna`, endpoint
  `https://api.gapapi.com/v1/chat/completions`, temperature0.7, n1, one user message.
  max_tokens, top_p and provider seed omitted. No automatic retries or redirects.
  Source: recovered_sources/experiments/matched_cora/run_matched.py, payload and
  configuration functions; run_v1.py supplies the historical aiohttp post_once.
- recovered_sources/src/openail/utils.py also names its helper GapGPT while using
  api.gapapi.com. GapGPT is the owner's confirmed service; the actual stored
  endpoint is preserved as historical evidence. Do not silently replace it with
  another hostname or assume a current domain mapping.
- Historical response extraction expects a2xx status, exactly one
  choices[0].message.content string, after private raw-body persistence. Receipts
  contain status, whitelisted request headers, body/hash and transport-failure
  metadata. This describes source behavior, not newly observed response receipts.
- All nine currently admitted JSONs were scanned: no provider usage, prompt_tokens,
  completion_tokens or total_tokens fields. They establish no actual historical
  token charge, reasoning charge or successful current API/model availability.
  Frozen parsed replay PASS is not raw-body parsing or provider compatibility.

The six-node sealed wrappers reuse model, temperature, n and user-message envelope.
They additionally set max_tokens512 and present the new sealed legacy-verifier
JSON task. Reuse the historical choices/message/content response envelope; then
apply the existing JSON parser/L1 rather than the historical annotation grammar.
The512 cap, JSON-task compliance and current endpoint acceptance remain canary
questions. Do not impose another provider's reasoning rules or silently add new
parameters based on unrelated documentation.

Sealed message-content bytes, six nodes, inputs and prompts stay unchanged.
Any confirmed endpoint/wire adjustment needs an explicitly approved derivative and
hash, preserving the original seals. Adding native response_format is unnecessary
for the first unchanged-wire canary unless GapGPT specifically requires it; it
must not be silently added. No transport or credentials were changed here.

## Provisional price evidence and conditional estimate

Owner attributes the rates below to a GapGPT pricing screenshot:
USD0.10/M input and USD0.50/M output. The screenshot itself was not available for
independent inspection in this slice. Treat these as owner-supplied provisional
rates, not a verified tariff, invoice or spending authorization.
Owner's page: https://gapgpt.app/platform-v2/pricing . Its earlier public fetch
returned a loader rather than a readable tariff; no further browsing was repeated.

For at most12 calls, assuming all declared input/output caps are real billable
limits, no hidden retry, and no extra gateway/reasoning/cache/currency charges:

- Full reservations:12*16384=196608 input,12*512=6144 output;
  cost =196608*0.10/1e6 +6144*0.50/1e6 = **USD0.0227328**.
- Existing local input estimate12542 plus6144 output gives **USD0.0043262**;
  this lower scenario is not a measured provider-token count.

The reservation scenario is more conservative under those assumptions, not a
billing guarantee. GapGPT's actual tokenization, whether512 includes reasoning,
fee/currency treatment, usage fields and current credit availability are unknown.
No monetary cap is approved; do not invent one or treat these small estimates as
permission. Preserve actual raw usage and charges when a later authorized request
provides them; mark absent fields unknown.

## Only remaining blockers / minimum canary sequence

| Item | Minimum resolution |
|---|---|
| Current wire compatibility | Confirm current endpoint and exact model ID for the owner's GapGPT service; review unchanged historical parameters plus512 cap. Canary tests new JSON/L1 behavior; prior success is not a universal guarantee. |
| Privacy | Owner explicitly approves transmitting the six sealed article/context payloads under applicable gateway/upstream retention terms; no assumed ZDR. |
| Actual limits/cost | Confirm token-cap/usage semantics and provisional tariff/fees; owner states a monetary spending cap. |
| Credentials available | Owner confirms an authorized credential source is available to the eventual executor; no key read, requested in chat or exposed here. |
| Live authorization | Explicit owner approval of exact canary request/context and cost exposure; current unconditional execution guard remains closed. |

After those five are resolved: review the minimal existing-integration invocation
and ledger/audit wiring, persist intent before the first blind request for637,
then send only that separately authorized canary. Preserve raw response/usage,
parse and run L1. Stop on incompatibility, truncation, uncertainty or audit failure;
no automatic retry, node substitution, comparison or full-pilot continuation by
implication. Further conditional steps require the scope of the owner's approval.
Do not require a paid compatibility probe before authorizing the canary itself:
current acceptance is one of its explicit feasibility questions.

## Checks executed

Three recovered source files byte-verified against recovered_sources manifest;
no historical module imported/executed. Nine input pins and frozen parsed replay
PASS;31+13 seal members PASS. Stored wire settings and response-parser source
inspected; provider usage-key scan returned0 occurrences in admitted inputs.
Both Decimal calculations recomputed. Documentation-only: no new unit/full suite,
network/model call, credential access, GT, training, seal/manifest/runtime change.
