# Rich evidence response v1 (offline, opt-in)

Version: `sara.verifier.rich_evidence.v1`. The machine-readable schema is
`RICH_RESPONSE_SCHEMA` in src/llmgnn_sara/sara3/rich_evidence.py. This is a newly
reconstructed diagnostic contract, not recovered historical Judge002/V1 wire.
It introduces no semantic judge, inference transport or live-execution permission.

| Required field | Type / responsibility |
|---|---|
| schema_version | Exact version string above |
| class_index | Integer0..6, or null for abstention; never inferred from prose |
| abstain | Boolean |
| primary_topic | Nonblank diagnostic topic hypothesis, or null on abstention |
| supporting_evidence | Array of source/quote/claim items; at least one for a proposed class |
| counter_evidence | Array of source/quote/claim items; legitimately empty |
| auxiliary_method_warning | Nonblank diagnostic text or null |
| uncertainty_reason | Nonblank diagnostic text or null; required nonnull on abstention |

Each evidence item has exactly source_id, quote and claim. Claim is a nonblank
textual assertion, not a class ID, nested object or semantic-support certificate.
Topic, claim, warning and reason strings have a 2000-character limit. Four total
evidence items are allowed across both arrays. Extra fields, including confidence,
are rejected. The JSON schema describes shape; the deterministic L1 validator also
enforces the cross-array limit, nonblank text and provenance constraints.

## Provenance and abstention

Both evidence arrays use the same existing validate_claims checks. Source IDs
must resolve to caller-approved EvidenceSource records. Field and source SHA-256
are taken from that trusted registry, never supplied or overridden by a response.
The current pipeline approves target.text only; neighborhood delivery does not
implicitly authorize graph quotations. The standalone validator can use an
explicitly approved source tuple, following the existing L1 API.

Quotes must be exact source substrings, <=512 characters, with at least two
alphanumeric words totaling eight characters. No whitespace/case repair occurs.
Unknown sources, modified/fabricated quotations and duplicate references fail
closed, including in counter-evidence. Reusing the same source quotation in both
arrays is currently a duplicate under the existing L1 rule, not a semantic verdict.
GT/correctness/E0/E1 fields remain forbidden.

Abstention requires class_index=null, primary_topic=null, both arrays empty and
a nonblank uncertainty_reason. Contradictions are rejected, not normalized into
apparently valid model responses. Public decisions still have null accepted/training
labels and evidence=[] on abstention. Rich diagnostics remain in private audit.

## Integration and compatibility

run_offline(..., response_version=RICH_VERSION) explicitly chooses the new parser
and new unsealed rich_verifier_input payload. Its schema/version and allowed source
IDs are bound into the request hash. No model executes these diagnostic instructions
in this slice. Future provider/prompt compatibility and execution need separate review.

Omitting response_version keeps the old three-field response contract and old
request bytes. Rich responses are not silently accepted by the legacy parser.
Existing frozen predictions, historical P0, six-node sealed files and replay
fixtures are unchanged. Exact legacy authentic-replay report equality is tested.
No new historical wire equivalence is claimed.

The existing private audit stores raw decoded responses, validated rich diagnostic
fields and failure codes before comparison. Audit failures still prevent progress.
No rich response bodies or claims enter public results, training labels or GraphScope.
Arbitration is unchanged: candidate agreement still has L2_NOT_ASSESSED; third-class
suggestions remain audit-only and never become accepted training labels.

## L2 questions intentionally unresolved

L1 cannot determine whether a claim follows from its quote, whether primary_topic
matches class_index, whether counter-evidence refutes a class, or whether an
auxiliary method was mistaken for the topic. A well-typed semantically mismatched
claim can pass L1 but remains L2 NOT_ASSESSED and does not enable acceptance.
Wrong claim types, missing source/quote/claim fields and mismatched provenance are
structural errors and are rejected. No keyword or self-reported-confidence gate
is introduced. Semantic criteria and evaluation need independent review.

Checks from the existing checkout/venv:

```powershell
python -B -m unittest discover -s tests -p test_rich_evidence.py -v
python -B -m unittest discover -s tests -v
python -B -m pip wheel . --no-deps --no-build-isolation --no-index --wheel-dir .local_artifacts/rich_schema_build
```

No static type checker is configured in this repository; syntax/import, contract
tests and an isolated stdlib-only wheel import validate this Python slice.
