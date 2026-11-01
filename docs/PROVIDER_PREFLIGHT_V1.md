# Minimal provider preflight — 2026-11-01

Decision: **NO-GO**. Documentation-only; no model, models-list, token-count or
authenticated API requests. No provider selection/change, transport or credentials.

## Historical evidence versus current facts

The sealed provider proposal is GapAPI at
`https://api.gapapi.com/v1/chat/completions`, model `gpt-6-luna`, n1,
temperature0.7, max_tokens512. It is a Chat Completions JSON body with one user
message containing the canonical logical request. It does not set reasoning
effort, response_format, service tier or retention controls. Sealed six-node scope,
12-call/16384-input/512-output reservations, timeout120 and retries0 remain unchanged.

The historical provider homepage https://gapapi.com returned404 through the web
tool; https://api.gapapi.com was inaccessible through that tool. Targeted searches
did not establish current official GapAPI model, endpoint, parameter, pricing or
privacy documentation. This is missing evidence, not proof the service is absent.
The similarly named gpapi.co was not treated as the same company/service. Owner's
public official documentation link is requested; no credentials are requested.

For comparison only, official OpenAI documentation lists `gpt-6-luna`, Chat
Completions/Responses, Structured Outputs and128000 maximum output tokens.
This verifies the public catalog, not account access, an immutable dated revision,
GapAPI availability or gateway pass-through. No alternative provider is approved.
[Model reference](https://developers.openai.com/api/docs/models/gpt-6-luna).

The GPT-6 guide permits reasoning none for Luna and disallows temperature when
reasoning is not none. Luna's documented default effort is medium. Therefore the
sealed omitted-effort/temperature0.7 combination needs explicit gateway evidence
or an approved wire derivative; compatibility is not established.
[Parameter guide](https://developers.openai.com/api/docs/guides/latest-model),
[model default](https://developers.openai.com/api/docs/models/gpt-6-luna).

## Wire and JSON consequences

OpenAI's documented endpoint is `https://api.openai.com/v1/chat/completions`,
accepting model/messages JSON. It documents max_completion_tokens as the total
visible/reasoning output limit and max_tokens as deprecated. response_format can
request JSON schema or JSON object mode. These facts do not establish GapAPI
support or that the current sealed requests use native structured output.
[API reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).

Existing response_schema is inside user-message content; there is no outer
response_format, so server-side schema enforcement must not be claimed. Current
local parser/L1 remains necessary even with a future constrained decoder.
No strict-schema subset compatibility or actual512-token completion was tested.

Prompt content can be retained byte-for-byte as the same decoded UTF-8 message
string, preserving target/context, instructions and schema. Original logical and
provider-wrapper files remain unchanged. A future max_tokens ->
max_completion_tokens conversion, explicit reasoning_effort=none, service/retention
setting or native JSON response format changes effective wire bytes/context and
requires a separately reviewed hashed derivative. Responses API would additionally
require a different envelope/output parser. None is silently interchangeable.
If GapAPI supports the original envelope, conversion may be unnecessary, but that
is currently unverified. Do not remove temperature or enlarge512 to get a success.

## Pricing and conditional estimate — NOT GapAPI pricing

OpenAI Standard short-context rates shown in current official documentation:
uncached input USD0.10/M, output USD0.50/M;30-minute cache writes USD0.125/M.
Do not confuse the lower Flex/Batch table with Standard. No tools/discounts are
assumed. [Pricing](https://developers.openai.com/api/docs/pricing).
Reasoning is billed as output; total-output limits must include it.
[Reasoning billing](https://developers.openai.com/api/docs/guides/reasoning).

For12 calls, declared maxima I=196608 input and O=6144 total output tokens:
`I*0.10/1e6 + O*0.50/1e6 = USD0.0227328`.
Using the higher30-minute cache-write rate for every input token gives the more
conservative conditional scenario USD0.027648. This assumes Standard/global
short-context, no extra cache tier, regional surcharge, gateway markup, minimum
charge, currency conversion or hidden retry, and a functioning total-output cap.
Changing those assumptions requires recalculation. These are not a financial cap.

The sealed local input estimate12542, with the same6144 output assumption, gives
USD0.0043262 at uncached Standard rates; it is less conservative and NOT a
provider-token measurement. Actual usage and charges are unknown. GapAPI cost
cannot be priced numerically without its tariff; the reservation-based formula is
`USD = 0.196608*P_input_per_M + 0.006144*P_output_per_M + other charges`.
All monetary estimates are hypothetical reference calculations, not authorization,
guaranteed billing, credit sufficiency or a reason to switch providers.

## Privacy and unresolved go/no-go decisions

For direct OpenAI API only, documentation says training use is opt-in; default
abuse-monitoring retention for Chat Completions is30 days, with separate application
state/caching exceptions. ZDR requires eligible account configuration; store=false
does not establish it. These conditions cannot be attributed to GapAPI.
[Data controls](https://developers.openai.com/api/docs/guides/your-data).

| Unresolved blocker | Required evidence/owner action |
|---|---|
| GapAPI identity/docs/model/revision/account entitlement | Official URL/support statement; exact model/revision and endpoint mapping |
| Parameters/JSON/output cap | Document temperature/reasoning/max-token handling and native JSON support; review any wire derivative |
| Gateway and upstream privacy | Retention, logging, subprocessors, training use and account-specific terms; owner data-sharing approval |
| Price and spending | Gateway tariff, reasoning/cache/fees, explicit monetary authorization and reservation plan |
| Final execution approval | Approve exact endpoint/model/wire/context and spending; current guard stays unconditionally closed |

Existing minimal bridge/ledger integration remains a prerequisite after these
decisions, not another framework to build in this slice. Public documentation
alone does not complete account preflight or authorize even a canary request.

Checks: sealed settings inspected; both31+13-member manifests and12 wrapper-to-
logical content mappings checked read-only; arithmetic recomputed with Decimal.
No seals/manifests/runtime/human records modified. No unit/full suite rerun for
documentation-only work; no actual provider compatibility test performed.
