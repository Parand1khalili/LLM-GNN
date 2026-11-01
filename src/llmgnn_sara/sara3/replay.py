"""Authentic-input offline boundary replay; fixed synthetic responses, no L2 judge."""
import argparse
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from ..io.frozen import require
from ..io.project import load_project_inputs
from ..downstream.frozen import plan_from_frozen
from ..pilot.protocol import materialize_comparison
from .audit import AuditError, PrivateAudit
from .evidence import EvidenceError, EvidenceSource, validate_claims
from .inputs import canonical_bytes, pair_inputs
from .pipeline import run_offline

CASES = (
    ("valid_quotation", 734, "L2_NOT_ASSESSED"),
    ("irrelevant_genuine_quotation", 90, "L2_NOT_ASSESSED"),
    ("modified_quotation", 734, "L1_QUOTE_NOT_FOUND"),
    ("unknown_source", 734, "L1_CLAIM_SCHEMA_INVALID"),
    ("abstention", 734, "BLIND_ABSTENTION"),
    ("contradictory_abstention", 734, "L1_ABSTENTION_CONTRADICTION"),
    ("historical_disagreement", 734, "VERIFIER_CONFLICT"),
    ("identical_candidates", 1031, "L2_NOT_ASSESSED"),
    ("third_class", 734, "THIRD_CLASS_PROPOSAL_ONLY"),
    ("audit_write_failure", 734, "AUDIT_UNAVAILABLE"),
    ("uncertain_comparison", 734, "TIMEOUT_UNCERTAIN_NO_RETRY"),
)
QUOTE_PINS = {
    734: (0, 112, "06cc13d8c486f73f8c59c8910143fe336c0db98ba7061658e321c6a37e31dcec"),
    90: (1336, 1356, "21f29224bb655170d51b49b23015b779434d5540dc2825f5adf9a2bbc131b5f5"),
    1031: (0, 120, "8362b075546a1ed177345b375a3c3ce0cc6e90ac081f043b9e9da0202eb7f6d3"),
}


def _sha(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _reply(label, quote):
    return {"class_index": label, "abstain": False, "evidence": [quote]}


class _FixedVerifier:
    """Precomputed synthetic responses; no inference, lexical scoring or GT."""
    offline = True

    def __init__(self, first, second, uncertain=False):
        self.first, self.second, self.uncertain = first, second, uncertain

    def blind(self, request):
        return json.loads(canonical_bytes(self.first[request.node_id]))

    def compare(self, request):
        if self.uncertain:
            raise TimeoutError("Synthetic offline uncertainty")
        return json.loads(canonical_bytes(self.second[request.node_id]))


def _check_run(result, pairs):
    by_id = {p.node_id: p for p in pairs}
    require(result["provider_calls"] == result["training_runs"] == 0 and result["GT_accessed"] is False,
            "Execution boundary violated")
    for item in result["verifier_inputs"]:
        payload = item["payload"]
        blind, comparison = pair_inputs(by_id[payload["node_id"]])
        expected = blind if payload["phase"] == "blind" else materialize_comparison(
            comparison, payload["blind_class_index"])
        require(payload == expected and item["sha256"] == _sha(payload), "Verifier evidence/boundary differs")
    for d in result["decisions"]:
        if d["routed_for_review"]:
            require(d["abstain"] is True and d["accepted"] is False and d["accepted_label"] is None
                    and d["training_class_index"] is None and d["evidence"] == []
                    and d["third_class_proposal"] is None and d["l2_status"] == "NOT_ASSESSED",
                    "Reviewed response entered labels or public proposal output")


def _audit_summary(audit, result, expected_raw):
    records = [audit.read(p.stem) for p in sorted(audit.root.glob("*.json"))]
    responses = [r for r in records if r["kind"] == "response"]
    requests = {r["request_id"]: r["sha256"] for r in result["verifier_inputs"]}
    for response in responses:
        identity = response["request_id"]
        require(identity in requests and response["payload_sha256"] == requests[identity]
                and response["raw_response"] == expected_raw[identity], "Raw audit fixture/provenance differs")
    for record in records:
        if record["kind"] == "arbitration":
            blind = audit.read(record["blind_response_sha256"])
            require(blind["request_id"] == f"offline:{record['node_id']}:blind", "Blind snapshot reference differs")
    return {"records_verified": len(records), "response_records": len(responses),
            "raw_responses_available": sum(r["raw_response"] is not None for r in responses),
            "private_proposals": sum(r.get("third_class_proposal") is not None for r in records),
            "l1_statuses": sorted(r["l1_status"] for r in responses)}


def replay_authentic(frozen_root, authentic_root, audit_root):
    """Return a body-free coverage report; raw synthetic data stays in private audit."""
    frozen_root, authentic_root = Path(frozen_root), Path(authentic_root)
    paths = {"b1": frozen_root / "b1_final_predictions.json",
             "narrative_v0": frozen_root / "narrative_v0_final_predictions.json",
             "selection": frozen_root / "selection_manifest.json",
             "preparation": frozen_root / "preparation_receipt.json"}
    for name in ("b1_prompts.json", "narrative_prompts.json", "neighborhoods.json",
                 "prompt_receipt.json", "request_manifest.json"):
        paths[name] = authentic_root / name
    inputs = load_project_inputs(frozen_root, authentic_root)
    pins = dict(inputs.provenance)
    require({k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in paths.items()} == pins,
            "Initial input bytes differ")
    PrivateAudit(audit_root)
    by_id = {p.node_id: p for p in inputs.pairs}
    cases = []
    for name, node, expected_reason in CASES:
        pair = by_id[node]
        start, end, pin = QUOTE_PINS[node]
        quote = pair.text[start:end]
        require(hashlib.sha256(quote.encode()).hexdigest() == pin, "Fixed quote fixture differs")
        first, second = _reply(pair.b1.class_index, quote), _reply(pair.b1.class_index, quote)
        boundary_reason = None
        if name == "modified_quotation":
            first["evidence"] = [quote + " [synthetic alteration]"]
            require(first["evidence"][0] not in pair.text, "Modified fixture is not invalid")
        elif name == "unknown_source":
            source = EvidenceSource("target.text", "text", pair.text,
                                    hashlib.sha256(pair.text.encode()).hexdigest())
            claim = {"source_id": "unapproved:source", "field": "text",
                     "source_sha256": source.sha256, "quote": quote}
            try:
                validate_claims([claim], (source,))
            except EvidenceError as error:
                boundary_reason = error.code
            require(boundary_reason == "L1_UNKNOWN_SOURCE", "Unknown-source boundary admitted claim")
            # The unchanged wire permits strings only; explicit objects must also fail there.
            first["evidence"] = [claim]
        elif name == "abstention":
            first = {"class_index": None, "abstain": True, "evidence": []}
        elif name == "contradictory_abstention":
            first.update(class_index=None, abstain=True)
        elif name == "historical_disagreement":
            require(not pair.agrees, "Disagreement fixture changed")
            second["class_index"] = pair.narrative_v0.class_index
        elif name == "identical_candidates":
            require(pair.agrees, "Same-class fixture changed")
        elif name == "third_class":
            third = min(set(range(7)) - {pair.b1.class_index, pair.narrative_v0.class_index})
            first["class_index"] = second["class_index"] = third
        audit = PrivateAudit(Path(audit_root) / name)
        results = []
        for _ in range(2):
            verifier = _FixedVerifier({node: first}, {node: second}, name == "uncertain_comparison")
            fault = patch.object(audit, "write", side_effect=AuditError()) if name == "audit_write_failure" else nullcontext()
            with fault:
                result = run_offline((pair,), 1, verifier=verifier, audit=audit)
            _check_run(result, (pair,))
            require(result["decisions"][0]["reason"] == expected_reason, "Case reason differs")
            results.append(result)
        require(results[0] == results[1], "Case replay is nondeterministic")
        summary = _audit_summary(audit, result, {f"offline:{node}:blind": first,
            f"offline:{node}:compare": None if name == "uncertain_comparison" else second})
        if name == "third_class":
            require(summary["private_proposals"] == 1, "Third-class proposal not preserved privately")
        if name == "audit_write_failure":
            require(summary["records_verified"] == 0, "Injected audit failure unexpectedly archived data")
        else:
            require(summary["response_records"] == result["mock_verifier_calls"], "Missing response audit")
        cases.append({"case": name, "node_id": node, "status": "PASS", "reason": expected_reason,
                      "historical_candidate_count": len({pair.b1.class_index, pair.narrative_v0.class_index}),
                      "explicit_source_boundary_reason": boundary_reason, "l2_status": "NOT_ASSESSED",
                      "accepted_label": None, "normalized_abstention": True, "deterministic": True,
                      "synthetic_response_sha256": _sha([first, second]), "outcome_sha256": _sha(result),
                      "mock_calls": result["mock_verifier_calls"], "audit": summary,
                      "audit_availability": "EXPECTED_INJECTED_FAILURE" if name == "audit_write_failure" else
                          "RESPONSE_UNAVAILABLE_ON_EXPECTED_TIMEOUT" if name == "uncertain_comparison" else "VERIFIED",
                      "semantic_diagnostic": "MANUAL_NON_TOPIC_COPYRIGHT_NOTICE_NOT_L2_APPROVAL"
                          if name == "irrelevant_genuine_quotation" else "NONE"})
    full = {}
    # Fixed non-semantic fixture: first120 target characters, frozen B1 candidate.
    first = {p.node_id: _reply(p.b1.class_index, p.text[:120]) for p in inputs.pairs}
    for router in ("r0", "semantic"):
        audit = PrivateAudit(Path(audit_root) / ("full140_" + router))
        result = run_offline(inputs.pairs, 37, router, _FixedVerifier(first, first), audit=audit)
        repeated = run_offline(inputs.pairs, 37, router, _FixedVerifier(first, first), audit=audit)
        _check_run(result, inputs.pairs)
        require(result == repeated, "Full cohort replay is nondeterministic")
        require(result["review_count"] == 37 and all(d["reason"] == "L2_NOT_ASSESSED"
                for d in result["decisions"] if d["routed_for_review"]), "Full cohort L2 boundary differs")
        plan = plan_from_frozen(inputs.frozen, "sensitivity", "ce", accepted=result["decisions"])
        require(all(plan["pseudo_y"][n] == -1 for n in result["selected_node_ids"]), "Reviewed nodes entered training mask")
        summary = _audit_summary(audit, result, {f"offline:{p.node_id}:{phase}": first[p.node_id]
            for p in inputs.pairs for phase in ("blind", "compare")})
        require(summary["response_records"] == result["mock_verifier_calls"], "Full cohort response audit incomplete")
        full[router] = {"targets": result["target_count"], "reviewed": result["review_count"],
                        "reviewed_accepted": 0, "baseline_unreviewed_retained": result["accepted_count"],
                        "abstained": result["abstention_count"], "mock_calls": result["mock_verifier_calls"],
                        "training_mask_check": "PASS", "deterministic": True, "audit": summary,
                        "outcome_sha256": _sha(result)}
    require({k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in paths.items()} == pins,
            "Frozen inputs mutated during replay")
    return {"schema": "sara.authentic_l2_boundary_replay.v1", "status": "PASS",
            "response_provenance": "DETERMINISTIC_SYNTHETIC_NOT_LLM_OUTPUTS",
            "case_count": len(cases), "cases": cases, "full140": full,
            "authentic_targets": 140, "recorded_neighborhoods": 140, "frozen_predictions": 280,
            "mock_calls_per_pass": sum(c["mock_calls"] for c in cases) + sum(r["mock_calls"] for r in full.values()),
            "total_mock_calls_two_passes": 2 * (sum(c["mock_calls"] for c in cases) + sum(r["mock_calls"] for r in full.values())),
            "source_sha256": pins, "frozen_input_immutability": "PASS",
            "l2_status": "NOT_ASSESSED", "raw_responses_in_report": False,
            "fixture_rule": "Full140: first120 target characters, frozen B1 candidate; no semantic scoring",
            "determinism": "Each case and full140 router executed twice with identical outcomes",
            "limitations": ["No semantic judge, accuracy or correction claim.",
                            "Unknown explicit source tested at validate_claims; unchanged wire rejects evidence objects.",
                            "Injected audit failure and timeout do not fabricate unavailable responses.",
                            "Recorded neighborhood evidence is delivered, not recomputed from graph bytes.",
                            "Unreviewed baseline retention is not verifier approval."],
            "provider_calls": 0, "token_count_calls": 0, "training_runs": 0, "GT_accessed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-root", required=True)
    parser.add_argument("--authentic-root", required=True)
    parser.add_argument("--audit-root", required=True)
    args = parser.parse_args()
    print(json.dumps(replay_authentic(args.frozen_root, args.authentic_root, args.audit_root), indent=2))


if __name__ == "__main__":
    main()
