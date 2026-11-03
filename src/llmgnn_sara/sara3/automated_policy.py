"""Prospective, GT-free concordance screening; NOT semantic L2 validation.

Only call with two independently L1-validated rich phase results from the same
node and a persisted blind-first comparison. No human or second model is implied.
The source-checking pipeline owns provenance and persistence; this pure policy
cannot establish entailment, class correctness, or reviewer independence.
"""

VERSION = "sara.arbitration.automated_concordance.v1"


def screen_validated(pair, blind, comparison):
    """Return a conservative, provisional pseudo-label decision, never L2 PASS."""
    candidates = {pair.b1.class_index, pair.narrative_v0.class_index}
    result = {"policy_version": VERSION, "action": "ABSTAIN", "class_index": None,
              "label_source": None, "reason": "UNRESOLVED",
              "l2_status": "NOT_ASSESSED", "semantic_validation": "NOT_PERFORMED",
              "third_class_proposal": None}

    def stop(reason, action="ABSTAIN", proposal=None):
        return {**result, "action": action, "reason": reason,
                "third_class_proposal": proposal}

    for phase in (blind, comparison):
        if (type(phase) is not dict or phase.get("l1_status") != "PASS"
                or phase.get("l2_status") != "NOT_ASSESSED"
                or type(phase.get("rich_evidence")) is not dict):
            return stop("L1_OR_PROVENANCE_NOT_VALIDATED", "REJECT")
    if blind.get("abstain") or comparison.get("abstain"):
        return stop("VERIFIER_ABSTAINED")
    a, b = blind.get("class_index"), comparison.get("class_index")
    if type(a) is not int or type(b) is not int or not 0 <= a < 7 or not 0 <= b < 7:
        return stop("INVALID_CLASS", "REJECT")
    third = a if a not in candidates else (b if b not in candidates else None)
    if third is not None:
        return stop("THIRD_CLASS_DIAGNOSTIC_ONLY", "REJECT", third)
    if a != b:
        return stop("BLIND_COMPARISON_CONFLICT", "REJECT")
    first, second = blind["rich_evidence"], comparison["rich_evidence"]
    for content in (first, second):
        if content.get("counter_evidence"):
            return stop("COUNTER_EVIDENCE_UNRESOLVED")
        if content.get("auxiliary_method_warning"):
            return stop("AUXILIARY_METHOD_WARNING")
        if content.get("uncertainty_reason"):
            return stop("EXPLICIT_UNCERTAINTY")
        if not isinstance(content.get("primary_topic"), str) or not content["primary_topic"].strip():
            return stop("PRIMARY_TOPIC_MISSING", "REJECT")
    if first["primary_topic"].strip().casefold() != second["primary_topic"].strip().casefold():
        return stop("PRIMARY_TOPIC_DRIFT")
    def quotes(content):
        items = content.get("supporting_evidence")
        if type(items) is not list:
            return set()
        return {item["quote"] for item in items if type(item) is dict and
                item.get("source_id") == "target.text" and type(item.get("quote")) is str}
    if not (quotes(first) & quotes(second)):
        return stop("NO_COMMON_TARGET_EVIDENCE")
    source = ("B1_AND_NARRATIVE_CONCORDANCE" if pair.agrees else
              "B1_CANDIDATE" if a == pair.b1.class_index else "NARRATIVE_V0_CANDIDATE")
    return {**result, "action": "ACCEPT", "class_index": a,
            "label_source": source, "reason": "PROVISIONAL_CROSS_PHASE_CONCORDANCE"}
