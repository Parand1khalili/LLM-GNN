# Post-observation L1 decorative quotation amendment

Rule version: `sara.l1.decorative_quote_match.v1`, implemented in the shared
`sara3/evidence.py` validator. This is a post-observation formatting compatibility
amendment after the real node1243 blind response, not a prespecified historical
rule or evidence of semantic correctness. Legacy and rich response schemas are
unchanged; rich supporting and counter quotations share this L1 matching rule.

## Exact rule

For source matching only, remove at most one complete outer ASCII double-quote
pair (`"..."`) or Unicode curly double-quote pair (U+201C/U+201D). A boundary
double-quotation character without the matching permitted partner is rejected.
After removal, another pair of quotation boundaries is rejected as nested outer
wrapping; no recursive unwrapping occurs. Interior quotation marks are preserved.
No trimming, whitespace collapsing, punctuation/case edits, Unicode rewriting,
token matching, fuzzy matching or semantic equivalence is used. The resulting
entire string must occur verbatim in the approved referenced source, just as
unwrapped quotations did under the prior rule. This does not accept partial
matching of a changed quotation. Single quotes and guillemets are not stripped.

Raw quote length limits, lexical floor, source IDs, source hashes, field binding,
schema/class checks, strict abstention and GT exclusion remain enforced. Duplicate
source matches remain duplicates even if differently decorated. Validator outputs
and raw private audit records preserve the original unmodified quotation; the
matching copy is never substituted into the provider response or training labels.
Malformed/nonmatching wrappers retain `L1_QUOTE_NOT_FOUND`; other reason codes
are unchanged. Validation is provenance-only: L2 remains NOT_ASSESSED.

## Preserved node1243 assessment

Original owner execution: HTTP200, approved provider-reported revision, valid
legacy JSON, original L1_QUOTE_NOT_FOUND and terminal REJECTED. One blind only;
no comparison. The original response, readiness receipt, request/context bindings,
summary and SQLite state remain immutable. A separate versioned private diagnostic
receipt binds those original hashes, the rule version and validator source hash.
Under the amendment, the saved quote matches the target exactly after removing
only its curly outer pair; diagnostic L1 PASS. No terminal-state upgrade, original
acceptance claim, semantic approval or accepted training label follows.

Private diagnostic location: `.local_artifacts/gapgpt_1243_l1_reassessment/`.
No raw article text, response, class proposal or receipt is committed. This
reassessment does not restart the halted batch, authorize a comparison or permit
another dispatch. Nodes130,682,2396,653 remain not attempted. A future continuation
requires a separately reviewed execution decision; existing no-resume guards stay.

## Verification

Synthetic regression cases independently cover both permitted pairs; unwrapped
quotes; interior quotation marks and exact whitespace; malformed/mismatched and
nested wrappers; fabricated/edited/case-changed/Unicode-normalized text; unchanged
raw outputs; source permissions, duplicates, lexical/length limits and abstention.
Rich support/counter evidence uses the same checks. Offline pipeline tests confirm
unchanged request payloads and conservative decisions for equivalent valid evidence;
no training-label acceptance. No model/provider/token-count calls are involved.

The batch test fixture now admits sealed inputs into temporary synthetic stores
without consulting real dispatch history during fixture setup. Production admission
remains unchanged; the separate prior-intent rejection test remains active. This
prevents an already executed real pilot from disabling offline regression tests.

Two integration fixtures previously cut the first120 characters of an article,
occasionally leaving a boundary quotation mark without its partner. They now use
an exact source span bounded by the first/last word characters within that same
prefix. This changes synthetic evidence only, never authentic text, sealed
requests, node/class choices, router formulas or real verifier outputs. Assertions
about conditional flow, request hashes and zero label promotion are retained.
