# L2 Shadow Mode v1 — diagnostic only

Contract: sara.l2.shadow.v1. Implemented solely in evaluation/l2_shadow.py;
no runtime module imports it. No new judge, prompt, router, verifier, arbitration
or acceptance rule is introduced. Do not attach shadow records to training labels.

API workflow (coordinator only):
1. bind_response(private_audit, opaque_case_id, decoded_response, authorized_text)
   privately snapshots the decoded response, its canonical hash, source hash,
   recomputed exact L1 status/reason and ordered evidence quotations. Legacy and
   rich support/counter quotations use existing L1 validators. No L2 is inferred.
2. ingest(audit, binding_receipt, blinded_packet, completed_review, author_id,
   provenance_kind=...) validates the existing sara.l2.human_review.v1 schema,
   four sara.l2.rubric.v1 dimensions, overall rationale/evidence references and
   all independence declarations. Inputs must be explicitly supplied completed
   records; the module never searches session folders or reads editable forms.
   For a real review use EXTERNAL_HUMAN_SELF_ATTESTED; tests exclusively use
   SYNTHETIC_TEST_ONLY. Forged authenticated/gold provenance labels are rejected.
3. compare(audit, left_receipt, right_receipt) reads exact immutable receipts,
   validates their common response/case binding and different reviewer pseudonyms,
   reports overall/dimension agreement/disagreement and missingness without
   adjudication, accuracy or promotion to gold. Synthetic and human records cannot
   be mixed. Give reviewers only their own blinded packet, never other responses
   or author judgments. Use an explicitly independent case-author identifier.

States:
- NOT_ASSESSED: no supplied review, or validated explicit unassessed overall
  judgment (all dimensions must also be unassessed). Missingness is not support.
- ASSESSED: structurally valid supplied assessment; NOT semantic truth/approval.
- INVALID: schema/hash/reference/provenance/blinding/L1 inconsistency; private
  rejection receipt preserves the submitted diagnostic record when serializable.
- UNAVAILABLE: private audit cannot write/read; no usable receipt or acceptance.
Comparison missing inputs yield MISSING_ASSESSMENT; invalid/unavailable inputs
fail closed. Private content-addressed receipts bind all four judgments, rationale,
reviewer timestamp/declarations, packet and response. Exact retries can reuse
identical content; disagreements are never selected/adjudicated automatically.

L1 passing proves quotation provenance only. Genuine but irrelevant evidence may
still carry UNSUPPORTED/AMBIGUOUS human observations. No semantic judgments are
generated here; the six author-illustrative development cases are neither loaded
as shadow answers nor treated as gold. There is no holdout promotion. Packet
scope remains the existing development-only scope. Human identity, independence,
honesty and absence of prior exposure cannot be authenticated by validation.
A claimed human record remains self-attested; coordinator must establish genuine
independence separately. No genuine assessment has been ingested in this slice.

Synthetic tests use newly constructed schema fixtures, not the real review session.
They compare unchanged runtime before/after ingestion: selections, request payloads,
conditional calls, L1/arbitration decisions and training acceptance are identical.
Attempts to promote a reviewed record are rejected by the existing downstream
boundary. Private raw responses/reviews never appear in GraphScope or public reports.
Historical P0, six-node seals, routing experiment manifest and frozen inputs remain
unchanged. Existing full regressions exercise authentic inputs and schema behavior.

Run focused tests:
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_l2_shadow.py -v

Real work still required: two actually independent blinded human reviews of the
same bound case/claims, truthful declarations and coordinator-reviewed provenance.
No synthetic agreement establishes semantic accuracy or reliable training labels.

Verification: focused6 PASS; guarded full238 tests,237 PASS/1 Windows symlink
SKIP (167.383s). Actual human session and network access denied; only temporary
synthetic review records exercised. No GraphScope frontend tests run.
