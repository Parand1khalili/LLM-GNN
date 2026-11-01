"""Two-phase offline verification and conservative, auditable arbitration.

No provider bridge exists. Supplied verifier implementations must be offline
fixtures. Outputs are engineering demonstrations, never live measured results.
"""
from dataclasses import asdict, dataclass
import math
import json
from pathlib import Path
from typing import Protocol

from ..sara2.policy import Annotation, CLASSES, Pair, PolicyConfig, integer, route_r0, validated_pairs
from .atlas import ATLAS, route_semantic, semantic_support
from .ledger import OfflineLedger
from ..io.evidence import NeighborhoodEvidence
from .inputs import canonical_bytes, verifier_input
import hashlib
from .evidence import EvidenceError, validate_result
from .audit import AuditError, PrivateAudit
from .rich_evidence import RICH_VERSION, rich_verifier_input, target_source, validate_rich_result


@dataclass(frozen=True)
class BlindRequest:
    """First pass never contains prior predictions, confidences or diagnostic GT."""
    node_id: int
    text: str
    classes: tuple[str, ...] = CLASSES
    definitions: tuple[str, ...] = tuple(entry.definition for entry in ATLAS)
    neighborhood: NeighborhoodEvidence | None = None


@dataclass(frozen=True)
class ComparisonRequest:
    node_id: int
    text: str
    historical_candidates: tuple[int, ...]
    blind_class_index: int
    classes: tuple[str, ...] = CLASSES
    definitions: tuple[str, ...] = tuple(entry.definition for entry in ATLAS)
    neighborhood: NeighborhoodEvidence | None = None


class OfflineVerifier(Protocol):
    offline: bool

    def blind(self, request: BlindRequest) -> dict: ...

    def compare(self, request: ComparisonRequest) -> dict: ...


class AbstainingVerifier:
    """Safe default: absence of a real reviewed output never invents a label."""
    offline = True

    def blind(self, request: BlindRequest) -> dict:
        return {"class_index": None, "abstain": True, "evidence": []}

    def compare(self, request: ComparisonRequest) -> dict:
        return {"class_index": None, "abstain": True, "evidence": []}


def _label_confidence(pair: Pair, label: int) -> float:
    return min(ann.confidence for ann in (pair.b1, pair.narrative_v0) if ann.class_index == label)


def _decision(pair: Pair, label: int | None, reason: str, reviewed: bool) -> dict:
    return {"node_id": pair.node_id, "training_class_index": label,
            "label_confidence_percent": _label_confidence(pair, label) if label is not None else None,
            "confidence_provenance": "historical_candidate_not_verifier_calibration",
            "accepted": label is not None, "accepted_label": label,
            "abstain": label is None, "evidence": [], "routed_for_review": reviewed,
            "l2_status": "NOT_ASSESSED" if reviewed else "NOT_APPLICABLE_BASELINE_POLICY",
            "verification_completed": reason in {"L2_NOT_ASSESSED", "THIRD_CLASS_PROPOSAL_ONLY", "VERIFIER_CONFLICT", "COMPARISON_ABSTENTION"},
            "reason": reason,
            "third_class_proposal": None, "third_class_training_allowed": False}


def run_offline(pairs, budget: int, router: str = "r0", verifier: OfflineVerifier | None = None,
                config: PolicyConfig | None = None, ledger: OfflineLedger | None = None,
                audit: PrivateAudit | None = None, response_version: str | None = None) -> dict:
    """Run GT-free frozen pairs through an explicitly offline verifier.

    With no text/verifier, reviewed cases abstain; no response is fabricated.
    Both routers have exactly min(budget, cohort size) review slots. Defaults
    deliberately do not attempt to recover historical R0/R1 selection counts.
    """
    rows = validated_pairs(pairs)
    if response_version is not None and (type(response_version) is not str or response_version != RICH_VERSION):
        raise EvidenceError("L1_SCHEMA_VERSION_INVALID")
    integer(budget, "review budget")
    if router not in {"r0", "semantic"}:
        raise ValueError("Unknown router")
    config = config if config is not None else PolicyConfig()
    if type(config) is not PolicyConfig:
        raise TypeError("Expected PolicyConfig")
    verifier = verifier if verifier is not None else AbstainingVerifier()
    if getattr(verifier, "offline", None) is not True:
        raise ValueError("Live verifier is disabled; an offline fixture is required")
    ledger = ledger if ledger is not None else OfflineLedger()
    if audit is not None and type(audit) is not PrivateAudit:
        raise TypeError("PrivateAudit required")
    audit_store, responses = audit, {}
    selected = (route_r0 if router == "r0" else route_semantic)(rows, budget)
    chosen = set(selected)
    decisions, requests, estimated_chars, exact_inputs = [], 0, 0, []

    def invoke(node: int, phase: str, request):
        nonlocal requests, estimated_chars, audit_store
        input_builder = verifier_input if response_version is None else rich_verifier_input
        payload = input_builder(request.node_id, request.text, request.neighborhood,
                                 candidates=request.historical_candidates if phase == "compare" else None,
                                 blind_class=request.blind_class_index if phase == "compare" else None)
        if audit_store is None:
            audit_store = PrivateAudit(Path(__file__).resolve().parents[3] / ".local_artifacts/private_verifier_audit")
        request_id = f"offline:{node}:{phase}"
        ledger.begin(request_id, payload)
        exact_inputs.append({"request_id": request_id, "payload": payload,
                             "sha256": hashlib.sha256(canonical_bytes(payload)).hexdigest()})
        estimated_chars += len(str(payload))
        requests += 1
        raw = None
        try:
            response = getattr(verifier, phase)(request)
            # Freeze decoded raw data immediately; comparison cannot mutate blind evidence.
            raw = json.loads(canonical_bytes(response))
            validated = (validate_result(response, request.text) if response_version is None else
                         validate_rich_result(response, (target_source(request.text),)))
        except Exception as error:
            code = (error.code if isinstance(error, EvidenceError) else
                    "TIMEOUT_UNCERTAIN_NO_RETRY" if isinstance(error, TimeoutError) else
                    "VERIFIER_FAILURE_UNCERTAIN")
            try:
                audit_store.write({"kind": "response", "request_id": request_id,
                                   "payload_sha256": exact_inputs[-1]["sha256"],
                                   "raw_response": raw, "reason": code,
                                   "l1_status": "FAIL" if code.startswith("L1_") else "NOT_ASSESSED"})
            except AuditError:
                ledger.settle(request_id, "REJECTED")
                raise
            ledger.settle(request_id, "REJECTED" if code.startswith("L1_") else "UNCERTAIN")
            raise EvidenceError(code) from None
        try:
            responses[(node, phase)] = audit_store.write({"kind": "response", "request_id": request_id,
                "payload_sha256": exact_inputs[-1]["sha256"], "raw_response": raw,
                "validated": validated, "reason": "L1_PASS_L2_NOT_ASSESSED", "l1_status": "PASS"})
        except AuditError:
            ledger.settle(request_id, "REJECTED")
            raise
        ledger.settle(request_id, "COMPLETED")
        return validated

    def reviewed_decision(pair, reason, proposal=None):
        decision = _decision(pair, None, reason, True)
        audit_store.write({"kind": "arbitration", "node_id": pair.node_id,
                           "decision": decision, "third_class_proposal": proposal,
                           "blind_response_sha256": responses.get((pair.node_id, "blind")),
                           "comparison_response_sha256": responses.get((pair.node_id, "compare"))})
        return decision

    for pair in rows:
        if pair.node_id not in chosen:
            reliable_agreement = pair.agrees and min(pair.b1.confidence, pair.narrative_v0.confidence) >= config.agreement_acceptance_percent
            decisions.append(_decision(pair, pair.b1.class_index if reliable_agreement else None,
                                       "UNREVIEWED_AGREEMENT" if reliable_agreement else "UNREVIEWED_ABSTENTION", False))
            continue
        if not pair.text.strip():
            decisions.append(_decision(pair, None, "MISSING_TARGET_TEXT", True))
            continue
        candidates = tuple(sorted({pair.b1.class_index, pair.narrative_v0.class_index}))
        try:
            first = invoke(pair.node_id, "blind", BlindRequest(pair.node_id, pair.text, neighborhood=pair.neighborhood))
            if first["abstain"]:
                decisions.append(reviewed_decision(pair, "BLIND_ABSTENTION"))
                continue
            blind_class = first["class_index"]
            second = invoke(pair.node_id, "compare", ComparisonRequest(
                pair.node_id, pair.text, candidates, blind_class, neighborhood=pair.neighborhood))
            proposal = blind_class if blind_class not in candidates else None
            if second["class_index"] is not None and second["class_index"] not in candidates:
                proposal = second["class_index"]
            if second["abstain"]:
                decisions.append(reviewed_decision(pair, "COMPARISON_ABSTENTION", proposal))
            elif second["class_index"] != blind_class:
                decisions.append(reviewed_decision(pair, "VERIFIER_CONFLICT", proposal))
            elif blind_class not in candidates:
                decisions.append(reviewed_decision(pair, "THIRD_CLASS_PROPOSAL_ONLY", proposal))
            else:
                decisions.append(reviewed_decision(pair, "L2_NOT_ASSESSED"))
        except (EvidenceError, AuditError) as error:
            code = error.code if isinstance(error, EvidenceError) else "AUDIT_UNAVAILABLE"
            decisions.append(_decision(pair, None, code, True))
        except Exception:
            # Exception bodies may contain payloads or credentials; never log them.
            decisions.append(_decision(pair, None, "VERIFIER_FAILURE_UNCERTAIN", True))
    accepted = [d for d in decisions if d["accepted"]]
    counts = {name: sum(d["training_class_index"] == index for d in accepted)
              for index, name in enumerate(CLASSES)}
    available = sum(max(semantic_support(pair.text)) > 0 for pair in rows)
    return {"status": "OFFLINE_TESTED", "evidence_level": "OFFLINE_RECONSTRUCTION_NOT_LIVE_MEASURED",
            "policy_provenance": config.provenance, "historical_policy_002_equivalence": False,
            "policy": asdict(config), "router": router, "router_parameters": {
                "semantic_mismatch_weight": 100.0, "calibration": "PREDECLARED_UNVALIDATED_HEURISTIC"},
            "ordered_classes": list(CLASSES), "target_count": len(rows), "review_budget": budget,
            "selected_node_ids": list(selected), "review_count": len(selected),
            "completed_review_count": sum(d["verification_completed"] for d in decisions),
            "semantic_evidence_available_count": available,
            "semantic_evidence_status": "AVAILABLE" if available else "UNAVAILABLE_NO_SUPPORTED_TARGET_TEXT",
            "accepted_count": len(accepted), "abstention_count": len(rows) - len(accepted),
            "coverage": len(accepted) / len(rows) if rows else 0.0, "class_retention_counts": counts,
            "decisions": decisions, "ledger": ledger.snapshot(), "ledger_persistence": "IN_MEMORY_OFFLINE_ONLY_NOT_LIVE_READY",
            "verifier_inputs": exact_inputs,
            "mock_verifier_calls": requests, "estimated_input_tokens_heuristic": math.ceil(estimated_chars / 4),
            "token_estimate_method": "payload_character_count_divided_by_4_NOT_PROVIDER_TOKENIZATION",
            "estimated_cost_usd": None, "cost_status": "NO_PROVIDER_PRICES_OR_LIVE_USAGE",
            "provider_calls": 0, "training_runs": 0, "GT_accessed": False,
            "raw_response_exported": False, "l2_semantic_validation": "NOT_IMPLEMENTED",
            "scientific_limitations": ["No measured verifier accuracy or downstream GCN improvement.",
                                       "L1 provenance is not L2 semantic support; reviewed candidates remain unaccepted.",
                                       "No exact recovered Policy 002 threshold table.",
                                       "Lexical semantic heuristic cannot establish primary-topic correctness.",
                                       "Historical confidence attached to retained candidates is not verifier calibration."]}


class LexicalFixtureVerifier:
    """Synthetic demonstration fixture, not an LLM or a validated classifier."""
    offline = True

    def _result(self, text: str) -> dict:
        scores = semantic_support(text)
        if not max(scores):
            return {"class_index": None, "abstain": True, "evidence": []}
        label = max(range(len(scores)), key=lambda i: (scores[i], -i))
        # shortcut: target-prefix quotes exercise schemas, not scientific evidence quality; replace for a live study.
        return {"class_index": label, "abstain": False, "evidence": [text.strip()[:512]]}

    def blind(self, request: BlindRequest) -> dict:
        return self._result(request.text)

    def compare(self, request: ComparisonRequest) -> dict:
        return self._result(request.text)


def offline_demo() -> dict:
    rows = (
        Pair(Annotation(1, 1, 95), Annotation(1, 1, 96), "Neural networks and backpropagation."),
        Pair(Annotation(2, 1, 95), Annotation(2, 4, 90), "Bayesian probability and likelihood."),
        Pair(Annotation(3, 0, 70), Annotation(3, 4, 85), "A theorem about complexity bounds."),
    )
    result = run_offline(rows, 2, "semantic", LexicalFixtureVerifier())
    result["input_provenance"] = "SYNTHETIC_DEMONSTRATION_NOT_HISTORICAL_ARTIFACT"
    return result
