# L1 evidence validity and conservative V1 arbitration

Optional [rich evidence v1](RICH_EVIDENCE_SCHEMA.md) adds structured diagnostics
through an explicit new response version; legacy contracts stay the default.

This is new offline engineering, not recovered Policy 002/V1 behavior. Routing,
scientific thresholds, prompts, provider envelopes and call caps are unchanged.
Historical P0 and the existing six-node sealed artifacts remain unchanged.

## Decision boundary

L1 checks provenance and syntax only. A valid quote does not establish semantic
support (L2). No semantic-approval heuristic or L2 implementation is supplied.
Reviewed candidates therefore remain unaccepted with L2_NOT_ASSESSED even when
blind/comparison agree on a frozen B1/v0 candidate. The existing unreviewed
confidence/agreement baseline branch remains separate and unchanged; its labels
are not new verifier-approved findings. No third class is admitted or remapped.

Every public decision has accepted_label, training_class_index, accepted, abstain
and evidence. Abstention always has null labels, accepted=false and evidence=[].
Contradictory raw abstentions fail closed; their evidence is not silently erased
and reported as a valid response. Raw and validated evidence remain private.
The training adapter rejects contradictory normalized records and any reviewed
acceptance while L2 is absent. Existing baseline records retain compatibility.

## L1 checks

The existing verifier wire still has exactly class_index, abstain, evidence.
No new prompt or provider response schema is introduced. String quotes refer
implicitly to the current request's target.text, never a response-supplied source.
The adapter checks exact field set/types, integer class0..6 (not bool), strict
abstention, nonempty positive evidence, maximum four distinct quotes, <=512
characters per quote and exact substring identity. Its explicit lexical floor
is two alphanumeric words totaling at least eight characters. This rejects trivial
fragments; it is not a semantic score or claim that a quote supports the class.

The separate validate_claims boundary validates explicit source_id, field,
source_sha256 and quote references against caller-approved immutable
EvidenceSource records. Source text must match its SHA-256. Unknown sources,
wrong fields/hashes, duplicate claims and changed/fabricated quotes fail closed.
Graph evidence is permitted only if explicitly supplied in this approved source
tuple. The unchanged target-only wire adapter does not allow graph quotations or
new evidence objects; any future graph adapter needs separate review. Source
approval is a trusted caller responsibility, not permission granted by model text.

GT/correctness/E0/E1 keys are rejected. No graph/label decoding occurs. Public
class definitions remain allowed. Blind requests retain the existing exclusion of
prior votes/confidence; their raw decoded response is copied and committed to the
private audit before comparison. Later mutation of the fixture's dictionary
cannot change that snapshot.

## Private audit and failures

Default local directory: `.local_artifacts/private_verifier_audit/`, already
excluded from Git. PrivateAudit can also receive a dedicated local directory.
Windows creates a protected current-user-only DACL and checks native ACE identities;
POSIX uses directory0700/file0600. Public web/GraphScope, docs/reports and historical
archive paths are rejected. These are local access controls, not encryption or
protection against the same account, administrators or filesystem rollback.

Records are exclusive, SHA-256-addressed JSON with request/payload hashes,
canonical decoded raw response, validated evidence or rejection code, and private
arbitration proposals. This preserves available offline decoded data, not absent
original provider wire bytes. Only JSON-serializable finite responses can be
snapshotted; an unserializable return fails closed and is recorded as an uncertain
failure without formatting arbitrary objects. Exception bodies are never logged
or archived; they could contain secrets. No credentials are loaded by this code.

Use PrivateAudit.read(digest) locally for authorized inspection. Do not print raw
records, add them to training labels, publish them in GraphScope, or include this
directory in artifact uploads/backups without a separate privacy review. Public
results contain reason codes only; third_class_proposal remains null there. Actual
third-class suggestions and linked blind/comparison hashes live only in the audit.
Existing backup plans enumerate the old pilot files and do not include this root.

Audit initialization fails before the first verifier call if privacy cannot be
established. Failed writes prevent comparison/acceptance. Timeout or other fixture
failure becomes uncertain, with no automatic retry. Failed archival means raw
preservation is incomplete and the decision is AUDIT_UNAVAILABLE, never success.

| Reason | Meaning |
|---|---|
| L1_SCHEMA_INVALID / L1_CLAIM_SCHEMA_INVALID | Wrong types, missing/extra fields or malformed claims |
| L1_ABSTENTION_CONTRADICTION | Abstain with a class or nonempty evidence |
| L1_CLASS_INVALID / L1_GT_FIELD_FORBIDDEN | Invalid class or forbidden diagnostic field |
| L1_EVIDENCE_MISSING_OR_MALFORMED / L1_TRIVIAL_QUOTE | Missing evidence or lexical floor/length violation |
| L1_SOURCE_PROVENANCE_INVALID / L1_UNKNOWN_SOURCE / L1_REFERENCE_MISMATCH | Invalid source record, unauthorized source or inconsistent reference |
| L1_QUOTE_NOT_FOUND / L1_DUPLICATE_EVIDENCE | Fabricated/changed quote or duplicate claim |
| BLIND_ABSTENTION / COMPARISON_ABSTENTION / VERIFIER_CONFLICT | Valid abstention or differing judgments; no label |
| THIRD_CLASS_PROPOSAL_ONLY | Proposal kept privately; no training label |
| L2_NOT_ASSESSED | L1-valid candidate agreement lacks semantic approval |
| AUDIT_UNAVAILABLE / TIMEOUT_UNCERTAIN_NO_RETRY / VERIFIER_FAILURE_UNCERTAIN | Storage or execution failure; no acceptance |

Run the focused independent tests and existing regressions from the checkout:

```powershell
python -B -m unittest discover -s tests -p test_evidence_l1.py -v
python -B -m unittest discover -s tests -v
```

Next testable work is an independently reviewed offline L2 decision contract and
fixtures, including genuine but irrelevant quotes. It requires explicit semantic
criteria and provenance; keyword agreement must not become automatic approval.

## Authentic replay and the L2 boundary

The offline replay harness uses the nine pinned JSON inputs described in
PILOT_PROTOCOL.md. It preserves the existing runtime, routing, prompts and policies.
Restore those external inputs first; from the checkout root run:

```powershell
python -B -m llmgnn_sara.sara3.replay --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --audit-root .local_artifacts/authentic_l2_boundary_audit
python -B -m unittest discover -s tests -p test_authentic_replay.py -v
```

The command prints a body-free JSON coverage report. Raw synthetic responses stay
in private audit subdirectories, excluded from Git/public exports. The executed
report is reports/authentic_l2_replay.json. Eleven fixed cases cover quotes,
sources, abstention, contradiction, candidate disagreement/agreement, third class,
audit failure and comparison timeout. Every case and both full140 routers run
twice with identical outcomes; private audit readback checks exact fixture data,
request hashes and immutable blind references. The full140 fixture always returns
the frozen B1 candidate and the first120 target characters, with no semantic
inference. It is not blind model performance despite the blind input boundary.

The genuine quotation fixture at node90 is a copyright notice (fixed span/hash).
Its lack of topical support is a manual fixture diagnostic, not an L2 algorithm,
correctness label or acceptance criterion. L1 passes but L2 remains NOT_ASSESSED;
the label stays unaccepted. Unknown explicit sources are checked at validate_claims;
the unchanged string-only wire separately rejects evidence objects. No new source
schema or graph quotation permission is introduced.

Expected fault injection is reported honestly: audit-write failure leaves no raw
archive; comparison timeout preserves blind data but has no comparison response.
Both prevent acceptance. Full140 unreviewed baseline retention is separate from
V1 approval. The harness verifies pseudo-training masks without running training,
and checks that input hashes remain unchanged. It makes no accuracy, semantic
support, historical raw-response recovery or graph-recomputation claim.
