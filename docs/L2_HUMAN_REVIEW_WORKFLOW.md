# Independent human L2 review workflow (offline)

Versions: sara.l2.blinded_packet.v1, sara.l2.human_review.v1 and
sara.l2.review_session.v1. These collect and compare human records; they do not
judge semantics, adjudicate disagreements, certify gold labels or change V1.

## Blinding and reviewer assignment

Use two distinct humans who did not author the cases, have not seen the author's
expected judgments or another review, and will not consult GT/correctness data or
an LLM. The coordinator who already knows expected judgments should not fill a
reviewer slot. reviewer-a/reviewer-b are currently empty role slots, not claims
that real reviewers exist. Bind pseudonyms to actual distinct people privately;
do not commit personal identities. Software verifies self-attestations and packet
bindings, not human identity, honesty or actual independence.

Each packet contains complete admitted article text, real quoted evidence,
controlled topic/claim proposals and a neutral rubric. Case and evidence IDs are
opaque. It excludes original descriptive case IDs, author reviews/rationales,
frozen votes/confidence, class_index, node IDs and GT. An explicit allowlist and
counterfactual tests protect this boundary. Controlled claims themselves remain
visible: they are the object of review, not the author's expected judgment.

Give each human ONLY their working/reviewer-a or working/reviewer-b folder.
Do not share the repository, benchmark, coordinator mapping, the other working
folder, or L2_EVALUATION_RUBRIC.md (its example table contains author judgments).
The neutral rubric is embedded in every packet. No sharing, messaging or upload
is performed by these commands. Local storage uses the existing PrivateAudit ACL
conventions: current Windows user only, POSIX0700/0600. It does not mutually isolate
two humans using the same OS account; distribution/access separation is the
coordinator's responsibility.

## Prepare and fill forms

From the checkout root, with the previously admitted external inputs restored:

```powershell
python -B -m llmgnn_sara.evaluation.l2_reviews prepare --benchmark configs/l2_development_benchmark.json --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic --output .local_artifacts/l2_human_review_session --reviewers reviewer-a reviewer-b
```

Preparation creates a NEW private directory and refuses overwrite. It produces
12 blinded packets and 12 blank forms (six per reviewer), immutable originals
under packets/ and forms/, and editable copies under working/<pseudonym>/ named
case-001.packet.json / case-001.review.json, etc. No assessment is prefilled:
outcomes, timestamps and independence declarations are null. Blank forms are not
valid reviews and are never counted as submitted records. Do not edit packet
copies or content-addressed originals. Humans edit only their *.review.json copies
using a local editor without AI assistance.

The prepared session prints its session_sha256. Keep that digest as the external
coordinator pin; its content-addressed coordinator JSON maps opaque case IDs to
private source IDs and packet/form hashes. No author opinion is copied there.

## Review-record schema

| Required field | Contract |
|---|---|
| schema_version | sara.l2.human_review.v1 |
| case_id, packet_sha256 | Exact assigned opaque case and immutable packet digest |
| reviewer | Assigned lowercase pseudonym; distinct from case author and other slot |
| scope | DEVELOPMENT_ONLY_NOT_HOLDOUT |
| rubric_version | sara.l2.rubric.v1 |
| reviewed_at_utc | Human-entered valid YYYY-MM-DDTHH:MM:SSZ timestamp; not independently authenticated |
| declarations | All six explicit booleans true: human_reviewer, not_case_author, no_author_judgments_seen, no_other_review_seen, no_gt_or_correctness_used, no_llm_assistance |
| assessments | Exactly four rubric dimensions; each has outcome, nonblank rationale and evidence_refs |
| overall | Same judgment structure; entered by the human, never computed |

Outcomes are SUPPORTED, UNSUPPORTED, AMBIGUOUS or NOT_ASSESSED. Assessed judgments
must cite packet evidence IDs (e01 etc.); unknown or duplicate references fail.
NOT_ASSESSED still needs a rationale. Overall NOT_ASSESSED requires all dimensions
unassessed. Extra fields, missing assessments, false declarations, invalid dates,
foreign case/packet IDs and development-to-holdout relabeling are rejected.
Timestamps and declarations are recorded provenance, not verified identity evidence.

## Import and compare

After a real human finishes a form, compute the hash of their private file. Use
the session digest printed by prepare; do not substitute an unrelated session.

```powershell
$reviewFile = '.local_artifacts/l2_human_review_session/working/reviewer-a/case-001.review.json'
$reviewSha = (Get-FileHash -LiteralPath $reviewFile -Algorithm SHA256).Hash.ToLowerInvariant()
python -B -m llmgnn_sara.evaluation.l2_reviews import --root .local_artifacts/l2_human_review_session --session-sha256 SESSION_SHA256 --review-file $reviewFile --review-sha256 $reviewSha
python -B -m llmgnn_sara.evaluation.l2_reviews compare --root .local_artifacts/l2_human_review_session --session-sha256 SESSION_SHA256
```

Repeat import for each completed file; never fill a form with an LLM. Exact retry
is idempotent. A different second record for the same case/reviewer is rejected,
preserving the original; no automatic last-write-wins or adjudication is applied.
Review files remain in private reviews/<pseudonym>/ stores. No rationales/article
bodies enter comparison output or GraphScope.

Comparison reports overall and per-dimension AGREEMENT, DISAGREEMENT,
MISSING_REVIEW, BOTH_NOT_ASSESSED or INCOMPLETE_ASSESSMENT. Missing data is not
invented; two unassessed judgments are not treated as semantic agreement. Reported
counts mean valid human-self-attested records, not authenticated people, accuracy
or gold-standard certification. Runtime L2 remains NOT_ASSESSED and training use
is FORBIDDEN even if both reviewers agree.

This version admits the six development cases only. Future holdout material needs
a separately approved, prospective admission/session contract and private store;
existing fixtures/reviews cannot be relabeled or silently promoted. No holdout is
created here. Unit-test completed-looking records are explicit temporary syntax
fixtures, not genuine or LLM-simulated reviews; none populate the real session.
