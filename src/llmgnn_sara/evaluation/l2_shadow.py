"""Private, post-hoc L2 observations. Runtime never imports this module."""
import hashlib

from .l2_reviews import validate_review, PACKET_VERSION, RUBRIC, SCOPE
from ..io.frozen import require, reject_gt
from ..sara3.audit import PrivateAudit, AuditError
from ..sara3.inputs import canonical_bytes
from ..sara3.evidence import EvidenceError, validate_result
from ..sara3.rich_evidence import RICH_VERSION, target_source, validate_rich_result

VERSION = "sara.l2.shadow.v1"


def check_l1(binding, packet):
    require(digest(binding["raw_response"]) == binding["response_sha256"], "Response differs")
    text = packet["article"]["text"]
    require(hashlib.sha256(text.encode()).hexdigest() == binding["source_sha256"], "Source differs")
    raw = binding["raw_response"]
    if raw.get("schema_version") == RICH_VERSION:
        validate_rich_result(raw, (target_source(text),))
    else:
        validate_result(raw, text)
    require(binding["l1_status"] == "PASS", "L1 differs")


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def bind_response(audit, case_id, response, text):
    """Snapshot source/response privately and recompute L1; never assess semantics."""
    require(type(audit) is PrivateAudit and type(case_id) is str and bool(case_id), "Invalid binding")
    reject_gt(response)
    status, reason = "PASS", "L1_PASS"
    try:
        if response.get("schema_version") == RICH_VERSION:
            validate_rich_result(response, (target_source(text),))
            quotes = [e["quote"] for key in ("supporting_evidence", "counter_evidence") for e in response[key]]
        else:
            validate_result(response, text)
            quotes = response["evidence"]
    except (EvidenceError, TypeError, AttributeError) as error:
        status, reason, quotes = "FAIL", getattr(error, "code", "L1_SCHEMA_INVALID"), []
    return audit.write({"schema_version": VERSION, "kind": "binding", "case_id": case_id,
        "raw_response": response, "response_sha256": digest(response),
        "source_sha256": hashlib.sha256(text.encode()).hexdigest(), "l1_status": status,
        "l1_reason": reason, "quotes": quotes, "training_use": "FORBIDDEN"})


def ingest(audit, binding_sha256, packet, review, author_id, *, provenance_kind):
    """Explicit completed-record intake only; no directories/forms/session discovery.

    Human provenance is self-attested, never independently authenticated by code.
    """
    try:
        binding = audit.read(binding_sha256)
        require(binding["kind"] == "binding" and binding["schema_version"] == VERSION, "Binding differs")
        require(digest(binding["raw_response"]) == binding["response_sha256"], "Response hash differs")
        if review is None:
            return {"state": "NOT_ASSESSED", "receipt": None, "training_use": "FORBIDDEN"}
        require(provenance_kind in {"SYNTHETIC_TEST_ONLY", "EXTERNAL_HUMAN_SELF_ATTESTED"}, "Unverifiable provenance claim")
        reject_gt(packet)
        require(set(packet) == {"schema_version", "case_id", "assigned_reviewer", "scope", "rubric", "article", "evidence", "proposal"}, "Packet leakage/fields differ")
        require(packet["schema_version"] == PACKET_VERSION and packet["rubric"] == RUBRIC
                and packet["scope"] == SCOPE and packet["case_id"] == binding["case_id"], "Case/rubric differs")
        require(packet["article"]["sha256"] == binding["source_sha256"]
                == hashlib.sha256(packet["article"]["text"].encode()).hexdigest(), "Source differs")
        evidence = packet["evidence"]
        require(set(packet["article"]) == {"source_id", "text", "sha256"}
                and packet["article"]["source_id"] == "target.text", "Article leakage")
        require(set(packet["proposal"]) == {"primary_topic", "supporting_evidence", "counter_evidence"}, "Proposal leakage")
        require(packet["proposal"]["primary_topic"] is None or type(packet["proposal"]["primary_topic"]) is str, "Malformed topic")
        require(len({e["evidence_id"] for e in evidence}) == len(evidence), "Duplicate evidence IDs")
        for group in ("supporting_evidence", "counter_evidence"):
            require(type(packet["proposal"][group]) is list, "Malformed proposal")
            for item in packet["proposal"][group]:
                require(set(item) == {"evidence_ref", "claim"} and type(item["claim"]) is str,
                        "Proposal leakage")
                require(item["evidence_ref"] in {e["evidence_id"] for e in evidence}, "Unknown evidence")
        require(type(evidence) is list and [e["quote"] for e in evidence] == binding["quotes"], "Evidence differs")
        for e in evidence:
            require(set(e) == {"evidence_id", "source_id", "quote", "quote_sha256"}
                    and e["source_id"] == "target.text"
                    and e["quote_sha256"] == hashlib.sha256(e["quote"].encode()).hexdigest(), "Malformed evidence")
        validate_review(review, packet, digest(packet), author_id)
        check_l1(binding, packet)
        require(binding["l1_status"] == "PASS", "Failed L1 cannot acquire shadow assessment")
        normalized_packet = {k: v for k, v in packet.items() if k != "assigned_reviewer"}
        state = "NOT_ASSESSED" if review["overall"]["outcome"] == "NOT_ASSESSED" else "ASSESSED"
        receipt = audit.write({"schema_version": VERSION, "kind": "assessment", "state": state,
            "binding_sha256": binding_sha256, "case_packet_sha256": digest(normalized_packet),
            "packet": packet, "review": review, "author_id": author_id,
            "provenance_kind": provenance_kind, "training_use": "FORBIDDEN"})
        audit.read(receipt)
        return {"state": state, "receipt": receipt, "training_use": "FORBIDDEN"}
    except AuditError:
        return {"state": "UNAVAILABLE", "receipt": None, "training_use": "FORBIDDEN"}
    except (ValueError, KeyError, TypeError):
        try:
            receipt = audit.write({"schema_version": VERSION, "kind": "rejection",
                "binding_sha256": binding_sha256, "review": review, "reason": "INVALID_SHADOW_RECORD"})
            return {"state": "INVALID", "receipt": receipt, "training_use": "FORBIDDEN"}
        except (AuditError, TypeError):
            return {"state": "UNAVAILABLE", "receipt": None, "training_use": "FORBIDDEN"}


def compare(audit, left_sha256=None, right_sha256=None):
    """Read only explicit immutable completed receipts; no accuracy/adjudication."""
    if left_sha256 is None or right_sha256 is None:
        return {"status": "MISSING_ASSESSMENT", "accuracy": None}
    try:
        a, b = audit.read(left_sha256), audit.read(right_sha256)
        for r in (a, b):
            require(r["kind"] == "assessment" and r["schema_version"] == VERSION, "Receipt differs")
            validate_review(r["review"], r["packet"], digest(r["packet"]), r["author_id"])
            check_l1(audit.read(r["binding_sha256"]), r["packet"])
            require(r["state"] == ("NOT_ASSESSED" if r["review"]["overall"]["outcome"] == "NOT_ASSESSED" else "ASSESSED"), "State differs")
            require(r["provenance_kind"] in {"SYNTHETIC_TEST_ONLY", "EXTERNAL_HUMAN_SELF_ATTESTED"}, "Forged provenance")
        require(a["binding_sha256"] == b["binding_sha256"] and a["case_packet_sha256"] == b["case_packet_sha256"], "Case differs")
        require(a["review"]["reviewer"] != b["review"]["reviewer"], "Reviewers not independent")
        require(a["provenance_kind"] == b["provenance_kind"], "Synthetic/human mixing forbidden")
        if a["state"] != "ASSESSED" or b["state"] != "ASSESSED":
            return {"status": "NOT_ASSESSED", "accuracy": None}
        dimensions = {k: "AGREEMENT" if a["review"]["assessments"][k]["outcome"] == b["review"]["assessments"][k]["outcome"] else "DISAGREEMENT" for k in a["review"]["assessments"]}
        return {"status": "AGREEMENT" if a["review"]["overall"]["outcome"] == b["review"]["overall"]["outcome"] else "DISAGREEMENT",
                "dimensions": dimensions, "provenance": a["provenance_kind"], "accuracy": None,
                "limitation": "Self-attestations do not authenticate identity or genuine independence"}
    except (ValueError, KeyError, TypeError):
        return {"status": "INVALID_OR_UNAVAILABLE", "accuracy": None}
