# L2 semantic evaluation foundation (development only)

The [offline human-review workflow](L2_HUMAN_REVIEW_WORKFLOW.md) now prepares
blinded packets, validates separate self-attested human records and compares them.
The original illustrative benchmark remains unchanged; genuine reviews are pending.

Rubric: `sara.l2.rubric.v1`. Benchmark: `sara.l2.development_benchmark.v1`,
configs/l2_development_benchmark.json. Status: illustrative, not a gold standard;
independent review is pending. This document defines human-review questions,
not a semantic judge, prompt, score, threshold or runtime acceptance gate.

## Review unit and outcomes

Review one controlled rich response against its cited quotations AND the complete
admitted target text. Do not infer the Cora node label. A proposed class in a
response is an author-controlled hypothesis, never dataset GT or a gold label.
Use public class definitions if needed, without B1/v0 votes, confidence, E0/E1,
correctness flags or test outcomes. Do not use model-generated rationales as review
evidence. Source text and explicit argument are the basis of review.

Record an outcome, nonblank rationale and cited evidence IDs for each dimension
and for the reviewer's overall conclusion:

| Dimension | Question; orientation of SUPPORTED |
|---|---|
| primary_topic_relevance | Does the interpretation concern the stated research question/contribution rather than incidental text? |
| quote_claim_support | Does the quote in context warrant the associated claim, without adding unstated conclusions? |
| counter_evidence_resolution | Is material counter-evidence absent for the narrow claim or explicitly resolved? UNSUPPORTED means a material conflict remains unresolved, not that the counter-quote is fabricated. |
| topic_method_separation | Does the interpretation distinguish the research aim from an auxiliary component, tool or technique? |

| Outcome | Reviewer meaning |
|---|---|
| SUPPORTED | Cited context warrants the narrowly stated assessment; no unresolved material conflict identified within the reviewed scope. Not proof of the correct node class. |
| UNSUPPORTED | The interpretation is unwarranted, contradicted or promotes an incidental method to the research topic; cite the specific failure. |
| AMBIGUOUS | Review performed, but multiple readings or incomplete context prevent a defensible resolution. Record what evidence is missing. |
| NOT_ASSESSED | No semantic assessment recorded. Do not convert this into ambiguity, agreement, abstention quality or a negative judgment. |

Overall outcome is recorded by a reviewer, never computed from dimension votes
or counts. Structure validation cannot certify a rationale or resolve reviewer
disagreement. Runtime rich responses and current V1 still have L2 NOT_ASSESSED;
even an illustrative SUPPORTED record cannot approve a training label.

## Six controlled cases

All are Codex-author text-based examples, NOT independent human reviews. There is
no scoring heuristic being tested or used to produce expected outcomes. Arguments
and evidence references are recorded for a separate reviewer to challenge.

| Case | Node | Controlled interpretation / illustrative overall outcome |
|---|---:|---|
| cbr_narrow_description | 90 | Repeats the explicit aim of evaluating a case-based system: SUPPORTED as a narrow descriptive claim. |
| copyright_is_not_topic_evidence | 90 | Uses a genuine rights notice as scientific-topic evidence: UNSUPPORTED. |
| auxiliary_rule_method_promoted | 90 | Treats a named rule-based component as proof of a rule-learning contribution, despite the stated evaluation aim: UNSUPPORTED. |
| finite_size_claim_contradicted | 130 | Claims that the contribution requires a finite network-size limit; the text explicitly discusses an infinite limit and no need for a size bound: UNSUPPORTED. |
| bayesian_neural_boundary_ambiguous | 130 | Bayesian priors and neural networks are both explicit; a unique taxonomy emphasis is not established here: AMBIGUOUS. |
| title_only_unassessed | 734 | Title-only recovered text, no semantic review recorded: NOT_ASSESSED. |

These interpretations are illustrative author opinions, not verified gold
judgments or Cora classification results. The same full texts can support narrower
claims without settling a unique class. In particular, quote provenance passing L1
does not warrant the assertion attached to that quote.

## Provenance, admission and future review

The benchmark stores quote spans/hashes rather than duplicating paper bodies.
The validator admits the pinned benchmark plus the existing nine project JSON
inputs, resolves target.text IDs, verifies source and quote hashes, and reuses
the rich-schema/L1 validator for all controlled responses. No raw model response
or provider-generated judgment is created. Existing private audit and arbitration
code are unchanged; evaluation code is never imported by the runtime.

Each review records reviewer_id, kind, independence status, textual basis, rubric
version, four dimension records and an overall record with evidence references.
This initial pinned version permits ILLUSTRATIVE author records only; a changed
flag or different name is not independent-review evidence. No reviewer identity
or signed receipt has been authenticated. Reported independently reviewed count
is therefore zero, and structural PASS is not semantic accuracy.

Next smallest step: obtain two separate offline reviews of these six cases.
Initially hide author outcomes/rationales from reviewers. Provide full GT-free
texts, quote references, controlled claims and rubric; exclude prior predictions
and diagnostics. Record pseudonymous reviewer IDs, date, case/rubric/source hashes,
independence declarations and cited rationales in new immutable review records.
Keep original opinions and disagreements; adjudicate explicitly without tuning a
judge. Approve the review-record contract before adding an importer. No sharing or
review dispatch is performed or authorized by this document.

All examples are DEVELOPMENT_FIXTURE_NOT_HOLDOUT, training_use=FORBIDDEN and
future_holdout_eligible=false. They were selected by text inspection and controlled
perturbation, never E0/E1 correctness. Their three nodes and the previously inspected
140-node cohort must not be described as untouched confirmatory data. Reserve a
future holdout prospectively from genuinely uninspected material before selecting
or tuning any L2 method; none is created or claimed here.

## Offline use

```powershell
python -B -m llmgnn_sara.evaluation.l2_benchmark --benchmark configs/l2_development_benchmark.json --frozen-root .local_artifacts/frozen --authentic-root .local_artifacts/authentic
python -B -m unittest discover -s tests -p test_l2_benchmark.py -v
```

The command emits a body-free structure/L1 report. For authorized local reading,
materialize_case(case, admitted_target_text) returns the full source text, resolved
quotes and controlled rich response. It computes no semantic judgment. Keep this
material separate from public exports and do not treat fixture text as model output.
The benchmark pin protects the current draft; future reviews should be new records,
not silent overwrites of the original evidence or opinions.
