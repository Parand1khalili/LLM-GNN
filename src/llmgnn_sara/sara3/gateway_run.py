"""Single, versioned prospective GapGPT adapter for fake and explicitly approved HTTP.

Reuses run_offline and the private SQLite state machine; no GT, semantic L2 or
GCN training. Never imports historical pilot entry points or secrets.
"""
from collections import Counter
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path

from ..downstream.plan import GCNConfig
from ..downstream.prospective import (
    VERSION as ADMISSION_VERSION, controlled_gcn_plan,
    frozen_pair_digest, offline_report_digest)
from ..sara2.policy import CLASSES
from .audit import PrivateAudit
from .automated_policy import VERSION as AUTOMATED_VERSION
from .experiment import digest
from .gapgpt_live import (
    VERSION, KEY_VARIABLE, RETENTION_STATUS, DurableGapGPTVerifier,
    contract_from_dict, wire_for, worst_call_cost)
from .inputs import canonical_bytes
from .pipeline import run_offline
from .rich_evidence import RICH_PROMPT_V2, RICH_VERSION
from .runner import SyntheticRichVerifier, _context, _journal_phases
from .selection import select_router

CONTRACT = "sara.runner.gapgpt_transport.v1"
APPROVAL = "sara.gapgpt.owner_batch_approval.v1"


def gateway_context(inputs, router, budget, cohort, config, *, fake):
    cfg = contract_from_dict(config)
    selected, existing = _context(inputs, router, budget)
    if cfg["max_calls"] > 2 * len(selected):
        raise ValueError("Call cap exceeds maximum conditional cohort calls")
    if cohort not in ("sensitivity", "primary"):
        raise ValueError("Unsupported cohort")
    return selected, {"version": VERSION,
                      "mode": "FAKE_HTTP" if fake else "LIVE_HTTPS",
                      "runner_contract_version": CONTRACT,
                      "gateway_contract_sha256": digest(cfg),
                      "inputs_context_sha256": digest(existing),
                      "frozen_pairs_sha256": frozen_pair_digest(inputs.pairs),
                      "source_hashes": dict(inputs.provenance),
                      "router": router, "selected": list(selected),
                      "budget": budget, "cohort": cohort,
                      "prompt_version": RICH_PROMPT_V2,
                      "response_version": RICH_VERSION,
                      "arbitration_version": AUTOMATED_VERSION}


def approval_template(inputs, router, budget, cohort, config):
    selected, ctx = gateway_context(inputs, router, budget, cohort, config, fake=False)
    cfg = contract_from_dict(config)
    return {"version": APPROVAL,
            "execution_context_sha256": digest(ctx),
            "gateway_contract_sha256": digest(cfg),
            "requested_model": cfg["model"],
            "router": router, "selected_count": len(selected),
            "call_cap": cfg["max_calls"], "spend_cap_usd": cfg["max_spend_usd"],
            "provider_format_verified": False, "returned_identity_verified": False,
            "current_gateway_prices_verified": False,
            "gateway_privacy_and_retention_reviewed": False,
            "data_sharing_approved": False, "spend_approved": False,
            "explicit_batch_dispatch_approved": False}


def require_approval(value, inputs, router, budget, cohort, config):
    expected = approval_template(inputs, router, budget, cohort, config)
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError("Exact user-approved execution contract required")
    for key, declared in expected.items():
        if type(declared) is bool:
            if value[key] is not True:
                raise ValueError("Required real-dispatch preflight was not approved")
        elif value[key] != declared:
            raise ValueError("Approval bound to another input, model, price or router")


class SyntheticGapGPTHttp:
    """Fake HTTP exercises *real* wire/envelope/usage parsing without networking."""

    def __init__(self, returned_model):
        self.returned_model = returned_model
        self.dispatches = 0

    def __call__(self, wire, key):
        if type(wire) is not bytes or type(key) is not str:
            raise ValueError("Fake transport contract violated")
        payload = json.loads(json.loads(wire)["messages"][0]["content"])
        if payload["phase"] == "blind" and (
                "historical_candidates" in payload or "blind_class_index" in payload):
            raise ValueError("Blind-first violation")
        from types import SimpleNamespace
        request = SimpleNamespace(text=payload["target"]["text"])
        fixture = SyntheticRichVerifier()
        content = fixture._respond(request)
        self.dispatches += 1
        envelope = {"model": self.returned_model,
                    "choices": [{"finish_reason": "stop",
                                 "message": {"role": "assistant",
                                             "content": canonical_bytes(content).decode("utf-8")}}],
                    "usage": {"prompt_tokens": (len(wire) + 3) // 4,
                              "completion_tokens": 256, "total_tokens": (len(wire) + 3) // 4 + 256}}
        return 200, canonical_bytes(envelope)


def gateway_run(inputs, output_root, *, router, budget, cohort, config,
                fake=True, transport=None, approval=None, key=None):
    cfg = contract_from_dict(config)
    selected, context = gateway_context(inputs, router, budget, cohort, cfg, fake=fake)
    if type(fake) is not bool:
        raise TypeError("Explicit fake/live boolean required")
    if fake:
        if approval is not None or key is not None:
            raise ValueError("Fake HTTP must not receive live approval or credential")
        key = "synthetic-local-key-unknown"
        transport = transport if transport is not None else SyntheticGapGPTHttp(cfg["model"])
    else:
        if transport is not None:
            raise ValueError("Actual live mode forbids injected external transport")
        require_approval(approval, inputs, router, budget, cohort, cfg)
        key = key if key is not None else os.environ.get(KEY_VARIABLE)
        if type(key) is not str or not key:
            raise ValueError("Gateway credential must be supplied from environment")
    root = Path(output_root).resolve(strict=False)
    if ".local_artifacts" not in root.parts or root.is_symlink():
        raise ValueError("Private .local_artifacts output directory required")
    journal = PrivateAudit(root / "journal")
    phases = PrivateAudit(root / "phases")
    verifier = DurableGapGPTVerifier(cfg, context, journal,
                                   transport=transport, key=key, authorized_fake=fake)
    run = run_offline(inputs.pairs, budget, router=router, verifier=verifier,
                      audit=phases, response_version=RICH_VERSION,
                      prompt_version=RICH_PROMPT_V2,
                      automated_arbitration_version=AUTOMATED_VERSION)
    # This path uses the shared offline interface, but real provider calls
    # are never represented as mock fixture counts in the persisted report.
    run["verifier_phase_attempts"] = run.pop("mock_verifier_calls")
    stats = verifier.stats()
    states = stats["state_counts"]
    blocked = verifier.halted or states["UNCERTAIN"] or states["REJECTED"]
    run["gateway_runner_version"] = CONTRACT
    run["gateway_context_sha256"] = digest(context)
    run["frozen_pairs_sha256"] = frozen_pair_digest(inputs.pairs)
    run["source_hashes"] = dict(inputs.provenance)
    run["ledger_persistence"] = "PRIVATE_SQLITE_GAPGPT_INTENT_AND_WIRE_HASH_V1"
    run["gateway_statistics"] = {k: v for k, v in stats.items()
                                if k not in ("new_dispatches", "successful_replays")}
    run["provider_calls"] = 0 if fake else stats["attempted_calls"]
    run["estimated_cost_usd"] = stats["estimated_cost_usd"]
    run["cost_status"] = ("SYNTHETIC_DECLARED_RATES_NOT_BILLING" if fake else
                          "USER_DECLARED_RATE_ESTIMATE_NOT_INVOICE")
    run["data_kind"] = ("SYNTHETIC_FAKE_HTTP_NOT_SCIENTIFIC_RESULT" if fake else
                        "GAPGPT_LIVE_RAW_UNVERIFIED_SEMANTIC_L2")
    run["label_status"] = "BASELINE_ELIGIBLE_PROVISIONAL_QUARANTINED"
    run["usage_status"] = ("SYNTHETIC_USAGE" if fake else
                           "PROVIDER_REPORTED_NOT_INVOICE")
    run_sha = offline_report_digest(run)
    if journal.write(run) != run_sha:
        raise ValueError("Gateway full report audit mismatch")
    plan_sha = None
    if fake and not blocked:
        try:
            exclusions = (tuple(p.target_id for p in inputs.frozen.by_arm("b1")
                           if p.samples[0].source_kind == "supplementary")
                           if cohort == "primary" else ())
            plan = controlled_gcn_plan(inputs.pairs, run,
                admission_version=ADMISSION_VERSION,
                frozen_pairs_sha256=frozen_pair_digest(inputs.pairs),
                report_sha256=run_sha, cohort=cohort,
                excluded_ids=exclusions, config=GCNConfig())
            plan_sha = journal.write(plan)
        except ValueError as error:
            if str(error) != "No baseline or provisional candidates to plan":
                raise
    # A LIVE report must use a separately versioned, explicitly approved GCN
    # adapter, never silently remove the existing provider_calls==0 restriction.
    summary = {"schema": CONTRACT,
               "status": ("BLOCKED_NO_AUTOMATIC_RETRY" if blocked else
                          "COMPLETE_FAKE_HTTP" if fake else "COMPLETE_LIVE_UNASSESSED"),
               "mode": "FAKE_HTTP" if fake else "LIVE_HTTPS",
               "router": router, "selected_node_ids": list(selected),
               "selected_count": len(selected), "denominator": len(inputs.pairs),
               "blind_completed": sum(p == "blind" and v == "COMPLETED"
                                      for (_, p), v in _journal_phases(verifier).items()),
               "comparison_completed": sum(p == "compare" and v == "COMPLETED"
                                           for (_, p), v in _journal_phases(verifier).items()),
               "new_dispatches": stats["new_dispatches"],
               "successful_replays": stats["successful_replays"],
               "attempted_calls": stats["attempted_calls"],
               "journal_states": states,
               "usage": stats["verified_usage"],
               "estimated_cost_usd": stats["estimated_cost_usd"],
               "reserved_cost_upper_usd": stats["reserved_cost_upper_usd"],
               "cost_status": stats["cost_status"],
               "baseline_accepted": run["accepted_count"],
               "provisional_count": run["provisional_count"],
               "provisional_coverage": run["provisional_coverage"],
               "baseline_coverage": run["coverage"],
               "potential_coverage": run["potential_coverage_if_experimentally_admitted"],
               "provisional_class_distribution": run["provisional_class_distribution"],
               "baseline_class_distribution": run["class_retention_counts"],
               "no_training_label_for_routed_proposals": all(
                   d["training_class_index"] is None for d in run["decisions"]
                   if d["routed_for_review"]),
               "GT_accessed": False, "training_runs": 0,
               "provider": "GapGPT", "requested_model": cfg["model"],
               "retention_status": RETENTION_STATUS,
               "prompt_version": RICH_PROMPT_V2,
               "arbitration_version": AUTOMATED_VERSION,
               "gateway_context_sha256": digest(context),
               "frozen_pairs_sha256": frozen_pair_digest(inputs.pairs),
               "private_report_sha256": run_sha,
               "private_plan_sha256": plan_sha,
               "plan_status": ("PLAN_ONLY_NO_TRAINING" if plan_sha is not None else
                               "LIVE_GCN_ADMISSION_NOT_AUTHORIZED" if not fake else
                               "NO_VALID_PLAN"),
               "scientific_status": ("SYNTHETIC_NOT_ACCURACY" if fake else
                                    "LIVE_NO_SEMANTIC_L2_OR_GT_EVALUATION")}
    summary_sha = journal.write(summary)
    summary["private_summary_sha256"] = summary_sha
    return summary
