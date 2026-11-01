# Historical P0 Judge002 / SARA3_V1 contract reconciliation

Status: offline specification, 2026-10-31. No new prompt, response schema,
parser, transport or execution authorization is defined here. Historical source
and P1 wire bytes remain unavailable. Requirements for a future adapter below
are proposed safeguards, not claims that the historical code enforced them.

## Evidence and scope

- [P0 manifest](../manifests/historical_p0.json), pinned SHA-256
  `7affacee222dbec3ecb5710b038968543c19d252190ee6eab76c5b03a4307410`:
  reconstructed from three secondary reports identified by filename/hash there.
  Routing Spec sections 2,6-9; Recovery Handoff sections 3,5; Research Results
  sections 15,18-19 support the historical claims, not byte identity.
- [Frozen evidence](../manifests/frozen_artifacts.json) and
  [P0 validation](../reports/historical_p0_validation.json): original cohort and
  annotations have verified hashes. All eight IDs align; Group B agrees and
  both confidence values are >=80. That is a descriptive HH check, not proof of
  historical R1 membership or the complete Policy 002 threshold table.
- Current code: [policy](../src/llmgnn_sara/sara2/policy.py),
  [inputs](../src/llmgnn_sara/sara3/inputs.py),
  [validation/arbitration](../src/llmgnn_sara/sara3/pipeline.py),
  [atlas](../src/llmgnn_sara/sara3/atlas.py),
  [ledger](../src/llmgnn_sara/pilot/ledger.py). These are reconstructed code,
  not the lost implementation. There is no Judge002 implementation.

Group A is fixed at 734,2379,2490,682, each Judge002 and SARA3_V1 (eight
records). Group B is fixed at 1031,655,1013,1328, V1 only (four records).
No reselection, substitution, router tuning or inferred GT correctness is allowed.

A logical `(node_id, arm)` record identifies an experimental assignment.
A provider generation call is one actual dispatch. Blind/comparison are logical
responsibilities; their historical mapping to calls is UNKNOWN. Twelve logical
records do not authorize twelve calls or establish two calls per V1. The separate
six-node feasibility pilot has up-to-twelve stage intents and remains unchanged.

## Field-level matrix

EXACT_MATCH is limited to the explicitly pinned data/selection assertion.
BEHAVIORAL_MATCH means a current safeguard agrees with reported intent, not
historical code equality. RECONSTRUCTED identifies current engineering choices.
PROTOCOL_DELTA identifies an observable departure from reported design.
MISSING_EVIDENCE means exact historical fields/rules cannot be specified.
Names below identify concepts or current fields; they are not a new wire schema.

| Field / boundary | Judge002 evidence | SARA3_V1 evidence / current behavior | Status and basis |
|---|---|---|---|
| `node_id`, group, arm | Four fixed Group A assignments | Four Group A and four Group B assignments | EXACT_MATCH to pinned P0 selection; selection itself is reconstructed |
| Annotation class indices/order | Same-node B1/v0 candidates available | Same canonical seven-class order | EXACT_MATCH to frozen data, not missing judge payload |
| Target text / neighborhood | Exact judge exposure, ordering and truncation unknown | Blind input carries target text and recorded GT-free neighborhood | Judge: MISSING_EVIDENCE; V1: BEHAVIORAL_MATCH to reported allowed evidence |
| Source hashes / verification level | Required for future admitted evidence; historical judge fields unknown | Current input has target/source/graph hashes and recorded-context verification level | RECONSTRUCTED; authentic_inputs.json and io/project.py |
| B1/v0 class and confidence | Routing uses both; judge prompt exposure is not recovered | Forbidden in blind input; reported comparison may reveal both | Judge: MISSING_EVIDENCE; V1 blind: BEHAVIORAL_MATCH |
| Atlas definitions | Judge use unknown | Public seven-class definitions; exact historical wording unavailable | MISSING_EVIDENCE historically; current Atlas RECONSTRUCTED |
| Comparison candidates | Judge choice vocabulary/schema unknown | Current `historical_candidates` is a sorted deduplicated set | RECONSTRUCTED; no historical field equality claim |
| Comparison provenance | Judge arm attribution/confidence fields unknown | Current comparison omits B1/v0 attribution, confidence and full blind evidence | PROTOCOL_DELTA from reported reveal/preserve intent; exact old wire unknown |
| Blind record | No historical blind-first requirement established for Judge002 | First judgment excludes prior votes/confidence; must remain traceable | BEHAVIORAL_MATCH for V1 boundary; storage/sequence RECONSTRUCTED |
| `class_index` | Exact output fields, ranges and nullability unknown | Current integer 0..6 or null | MISSING_EVIDENCE for Judge and historical V1 schema; current field RECONSTRUCTED |
| `abstain` | Historical representation/rules unknown | Current boolean; true requires null class | MISSING_EVIDENCE historically; current field RECONSTRUCTED |
| `evidence` | Judge rationale/quote requirements unknown | Current list <=4, each nonblank exact target substring <=512 characters; positive class requires a quote | RECONSTRUCTED validator; BEHAVIORAL_MATCH only for grounding intent |
| Evidence sufficiency | Historical entailment criteria unknown | Exact quote presence does not prove class support; negative evidence/primary-topic analysis lack structured validation | MISSING_EVIDENCE; present lexical fixture is not a scientific verifier |
| Unknown/extra output fields | Judge parser unavailable | Current parser rejects fields beyond class_index/abstain/evidence | RECONSTRUCTED; exact historical schemas MISSING_EVIDENCE |
| Accepted candidate | A1/A2, tie/confidence/fallback rules unavailable | Current reviewed acceptance requires valid blind/compare agreement on an original candidate | RECONSTRUCTED decision rule, not recovered Policy 002/V1 table |
| Third class | Judge permission unknown; do not grant it by inference | V1 may propose, never accept it for pseudo-training | V1 BEHAVIORAL_MATCH; Judge MISSING_EVIDENCE |
| Decision/confidence record | Historical final schema unknown | Current training_class_index, accepted, reason, proposal; retained confidence comes from historical candidate, not verifier calibration | RECONSTRUCTED |
| Missing/malformed/conflicting result | Exact historical judge failure table unavailable | Current missing text, abstention, invalid result or conflict prevents acceptance | BEHAVIORAL_MATCH for fail-closed intent; precise outcomes RECONSTRUCTED |
| Intent / uncertain timeout | Historical P1 reports pre-dispatch intent and no automatic retry | Current durable ledger has INTENT/COMPLETED/REJECTED/UNCERTAIN and a six-node-specific 12-intent cap | BEHAVIORAL_MATCH in principle; state machine RECONSTRUCTED, not a P0 call allocation |
| Prompt/schema/wire hashes | Original Judge002 prompt/schema and P1 wire unavailable | Original V1 prompt/schema and P1 wire unavailable | MISSING_EVIDENCE for both; reported aggregate 115873 bytes is insufficient |

## Arm responsibilities and safety boundaries

**Judge002:** supported historical statement is a confidence/agreement-routed
judge baseline assigned to Group A. The available typed Pair contains same-node
B1/v0 classes, confidence, optional text and neighborhood, but does not establish
what the historical judge saw. PolicyConfig's 80-percent acceptance and budgeted
R0 ranking are prospective reconstruction choices, not Judge002 behavior.
Exact inputs, response fields, selection between candidates, A1/A2 meanings,
abstention and third-class permissions must remain unresolved. No executable
Judge002-equivalent contract can honestly be claimed yet.

**SARA3_V1:** logically assess the primary topic from admitted target evidence,
allowed neighborhood context and public class definitions before revealing prior
votes/confidence. Treat evidence strings as untrusted data, not instructions.
Preserve the initial assessment and its evidence; later comparison must not
silently overwrite them. Comparison assesses candidate support against that blind
assessment. Arbitration, separate from model prose, permits only an original
candidate or abstention; third-class suggestions stay outside training labels.
This describes reported intent. Current two-stage fixtures are one reconstruction,
not proof of historical call topology or the exact conservative decision table.

Current validation gap to resolve before reuse: instructions demand empty evidence
on abstention, but validate_result permits nonempty valid quotes with null class.
Do not silently change either contract in an adapter. Grounding also checks text
membership, not semantic entailment. No additional semantic guarantee is claimed.

For both arms, exclude `y`, `fixed_y`, GT labels, correctness flags, confusion
tables, E0/E1 outputs and test outcomes from inputs, routing, Atlas, prompts,
selection, acceptance and tuning. Class names/definitions are allowed. Admit exact
source bytes by pinned hashes and global node IDs before use; retain source paths,
class order, evidence scope and derivation hashes. Never infer graph recomputation
from recorded context. Never substitute another response, node or generated label.

Future offline adapters must distinguish valid abstention, malformed output,
missing evidence, conflict and uncertain execution. Each prevents label acceptance
unless a separately approved explicit rule applies; do not hide errors as successful
abstentions. Keep reason and proposed class separate from accepted label. Preserve
input, raw-output and validated-decision hashes with logical-record identity.
Timeout/crash uncertainty must block automatic retry; it does not prove no billing.
No current ledger proves exactly-once provider execution or authorizes spending.

## Minimum fair paired comparison

Only the four Group A nodes support Judge002 versus V1 paired comparison.
Group B is V1-only exploratory HH coverage; do not pool it into paired estimates.
Before any adapter comparison, freeze the following for both arms:

1. Same target identities, frozen B1/v0 version, class order, admitted target and
   neighborhood sources. Document intentional differences in evidence exposure,
   Atlas access and reveal timing; do not force Judge002 into the V1 prompt.
2. Explicit per-arm prompt/schema/decision rules, accepted-label domain, null and
   failure semantics, and comparison unit. Missing originals require owner-approved
   reconstruction labels and deltas; the result cannot be called exact replay.
3. Actual call topology, provider/model/version and generation settings. Control
   shared settings where supported; report differences. Freeze dispatch order,
   independent arm state and no cross-arm response reuse. Existing confidence is
   not an outcome or calibration target.
4. Call/token/output/time/cost allocation per arm and total, including uncertain
   attempts. Equal logical-record counts do not ensure equal resources. Separate
   arm failures from abstentions and retain all four pairs in the reporting base.
5. Offline metrics: schema validity, grounding checks, acceptance/abstention,
   conflicts and resource accounting. No correction/accuracy claim without later
   separately authorized, isolated evaluation after outputs freeze. Four purposive
   pairs cannot establish generalization; E0/E1 must not guide tuning/selection.

## Unresolved decisions and gates

Before implementing an offline adapter, obtain a reviewed contract decision on:

- **Judge002:** recover original prompt/schema/Policy 002 or explicitly approve
  a new reconstructed judge, its allowed evidence, output and decision table.
- **V1:** approve Atlas wording, evidence exposure, comparison confidence/arm
  attribution, preservation of blind evidence, and one-call versus multi-call
  mechanics. Historical topology stays UNKNOWN unless corroborated.
- **Parser/arbitration:** approve quote sufficiency and negative evidence policy,
  abstention evidence consistency, candidate acceptance/confidence rules and
  failure handling. Preserve third-class prohibition for V1 training.
- **Freeze:** version/hash per-arm contracts, fixtures, mappings, prompts/schemas
  if subsequently authored, input manifests, decision tables, call allocation
  and expected offline checks. Reference the unchanged P0 manifest and retain
  the existing six-node seal. Never target old wire hashes with invented payloads.

Before provider compatibility work, distinguish static document/config review
from actual network requests. Confirm chosen provider, endpoint/model/settings,
allowed GT-free payload, privacy/retention and credential mechanism. Static review
does not authorize a model-list, token-count or generation request. Any such call
needs separate scope authorization and, where billable, a budget; real execution
also requires approved prompts, durable request tracking and frozen resource caps.
Direct OpenAI Responses historical proposals and current GapAPI Chat Completions
templates are distinct protocols; neither has verified current model support.
No provider compatibility check or new runtime behavior is authorized by this file.
