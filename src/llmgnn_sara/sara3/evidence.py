"""Deterministic L1 provenance checks, never semantic approval or L2 scoring."""
from dataclasses import dataclass
import hashlib
import re

from ..io.frozen import reject_gt

QUOTE_MATCH_VERSION = "sara.l1.decorative_quote_match.v1"
_QUOTE_PAIRS = {('"', '"'), ('\u201c', '\u201d')}
_QUOTE_BOUNDARIES = frozenset('"\u201c\u201d')


def quote_for_matching(quote):
    """Strip one balanced decorative double-quote pair, for matching only.

    Post-observation L1 amendment: no trimming, rewriting or recursive stripping.
    Interior quotation marks remain verbatim; nested outer wrappers are rejected.
    """
    if type(quote) is not str:
        raise EvidenceError("L1_CLAIM_SCHEMA_INVALID")
    if not quote:
        return quote
    if quote[0] in _QUOTE_BOUNDARIES or quote[-1] in _QUOTE_BOUNDARIES:
        if len(quote) < 2 or (quote[0], quote[-1]) not in _QUOTE_PAIRS:
            raise EvidenceError("L1_QUOTE_NOT_FOUND")
        quote = quote[1:-1]
        if len(quote) >= 2 and quote[0] in _QUOTE_BOUNDARIES and quote[-1] in _QUOTE_BOUNDARIES:
            raise EvidenceError("L1_QUOTE_NOT_FOUND")
    return quote


class EvidenceError(ValueError):
    CODES = frozenset({"L1_SOURCE_PROVENANCE_INVALID", "L1_EVIDENCE_MISSING_OR_MALFORMED",
        "L1_CLAIM_SCHEMA_INVALID", "L1_UNKNOWN_SOURCE", "L1_REFERENCE_MISMATCH",
        "L1_TRIVIAL_QUOTE", "L1_QUOTE_NOT_FOUND", "L1_DUPLICATE_EVIDENCE",
        "L1_SCHEMA_INVALID", "L1_GT_FIELD_FORBIDDEN", "L1_ABSTENTION_CONTRADICTION",
        "L1_CLASS_INVALID", "L1_SCHEMA_VERSION_INVALID", "TIMEOUT_UNCERTAIN_NO_RETRY", "VERIFIER_FAILURE_UNCERTAIN"})

    def __init__(self, code):
        self.code = code if type(code) is str and code in self.CODES else "VERIFIER_FAILURE_UNCERTAIN"
        super().__init__(self.code)


@dataclass(frozen=True)
class EvidenceSource:
    source_id: str
    field: str
    text: str
    sha256: str

    def __post_init__(self):
        if (any(type(v) is not str or not v for v in (self.source_id, self.field, self.text, self.sha256))
                or hashlib.sha256(self.text.encode("utf-8")).hexdigest() != self.sha256):
            raise EvidenceError("L1_SOURCE_PROVENANCE_INVALID")
        try:
            reject_gt({self.source_id: None, self.field: None})
        except ValueError:
            raise EvidenceError("L1_GT_FIELD_FORBIDDEN") from None


def validate_claims(claims, approved_sources):
    """Sources must be supplied by the trusted request, never by the response.

    Graph evidence is disallowed unless explicitly present in approved_sources.
    This checks quote identity and references, not whether a class is supported.
    """
    if (type(approved_sources) is not tuple or not approved_sources
            or any(type(s) is not EvidenceSource for s in approved_sources)
            or len({s.source_id for s in approved_sources}) != len(approved_sources)):
        raise EvidenceError("L1_SOURCE_PROVENANCE_INVALID")
    if type(claims) is not list or not 1 <= len(claims) <= 4:
        raise EvidenceError("L1_EVIDENCE_MISSING_OR_MALFORMED")
    sources = {s.source_id: s for s in approved_sources}
    result = []
    matched = set()
    for claim in claims:
        if type(claim) is not dict or set(claim) != {"source_id", "field", "source_sha256", "quote"}:
            raise EvidenceError("L1_CLAIM_SCHEMA_INVALID")
        if any(type(v) is not str for v in claim.values()):
            raise EvidenceError("L1_CLAIM_SCHEMA_INVALID")
        source = sources.get(claim["source_id"])
        if source is None:
            raise EvidenceError("L1_UNKNOWN_SOURCE")
        if claim["field"] != source.field or claim["source_sha256"] != source.sha256:
            raise EvidenceError("L1_REFERENCE_MISMATCH")
        quote = claim["quote"]
        # Lexical floor only, not a semantic-support heuristic or evidence score.
        words = re.findall(r"[^\W_]+", quote, re.UNICODE)
        if len(quote) > 512 or len(words) < 2 or sum(map(len, words)) < 8:
            raise EvidenceError("L1_TRIVIAL_QUOTE")
        matching_quote = quote_for_matching(quote)
        if matching_quote not in source.text:
            raise EvidenceError("L1_QUOTE_NOT_FOUND")
        item = (source.source_id, source.field, source.sha256, quote)
        match_identity = (source.source_id, source.field, source.sha256, matching_quote)
        if match_identity in matched:
            raise EvidenceError("L1_DUPLICATE_EVIDENCE")
        matched.add(match_identity)
        result.append(item)
    return tuple(result)


def validate_result(value, text):
    """Existing three-field wire; each quote implicitly references target.text.

    No prompt/schema expansion. Explicit-source claims are validated separately;
    graph quotations cannot be smuggled through this target-only wire adapter.
    """
    if type(value) is not dict:
        raise EvidenceError("L1_SCHEMA_INVALID")
    try:
        reject_gt(value)
    except ValueError:
        raise EvidenceError("L1_GT_FIELD_FORBIDDEN") from None
    if set(value) != {"class_index", "abstain", "evidence"}:
        raise EvidenceError("L1_SCHEMA_INVALID")
    label, abstain, quotes = value["class_index"], value["abstain"], value["evidence"]
    if type(abstain) is not bool or type(quotes) is not list:
        raise EvidenceError("L1_SCHEMA_INVALID")
    if abstain:
        if label is not None or quotes != []:
            raise EvidenceError("L1_ABSTENTION_CONTRADICTION")
        return {"class_index": None, "abstain": True, "evidence": (), "l1_status": "PASS"}
    if type(label) is not int or not 0 <= label < 7:
        raise EvidenceError("L1_CLASS_INVALID")
    if type(text) is not str or not text.strip():
        raise EvidenceError("L1_SOURCE_PROVENANCE_INVALID")
    if any(type(q) is not str for q in quotes):
        raise EvidenceError("L1_CLAIM_SCHEMA_INVALID")
    source = EvidenceSource("target.text", "text", text, hashlib.sha256(text.encode()).hexdigest())
    claims = [{"source_id": source.source_id, "field": source.field,
               "source_sha256": source.sha256, "quote": q} for q in quotes]
    validate_claims(claims, (source,))
    return {"class_index": label, "abstain": False, "evidence": tuple(quotes), "l1_status": "PASS"}
