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
from .gateway_preflight import validate_batch_wire
from .inputs import canonical_bytes
from .pipeline import run_offline
from .rich_evidence import RICH_PROMPT_V2, RICH_VERSION
from .runner import SyntheticRichVerifier, _context, _journal_phases
from .selection import select_router

CONTRACT = "sara.runner.gapgpt_transport.v1"
APPROVAL = "sara.gapgpt.owner_batch_approval.v2"
OWNER_PERMISSIONS = ("data_sharing_approved", "spend_approved",
                     "explicit_batch_dispatch_approved")
APPROVED_SCOPE_CONTEXT_SHA256 = "5e41ae8ab228ce607897df7015e4fe56972147811e2367f5fd8da88d01fb4abe"
APPROVED_SCOPE_CONFIG_SHA256 = "d3a66b47e7be095b54c58bcdd1f24beae13d1edc2a7ef433e92b8027da7a5126"
UNVERIFIED_PROVIDER_FIELDS = ("provider_format_verified",
                              "returned_identity_verified",
                              "current_gateway_prices_verified",
                              "gateway_privacy_and_retention_reviewed")


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


def scoped_owner_authorization(inputs, router, budget, cohort, config):
    """Build the exact owner-scoped authorization under an explicit CLI opt-in.

    Provider verification fields remain FALSE. The caller's intentional
    --enable-real-dispatch is the single positive authorization for this
    predeclared batch, not a claim that external pricing or retention was verified.
    """
    approval = approval_template(inputs, router, budget, cohort, config)
    # The user's one-time batch authorization is scoped to the exact Cora140
    # Frozen input set and approved $0.40 contract recorded in prior preflight.
    # Changes to inputs, model, settings, router or limits must NOT silently
    # receive a new authorization via this convenience pathway.
    if (approval["execution_context_sha256"] != APPROVED_SCOPE_CONTEXT_SHA256
            or approval["gateway_contract_sha256"] != APPROVED_SCOPE_CONFIG_SHA256
            or approval["router"] != "r0"
            or approval["selected_count"] != 37
            or approval["call_cap"] != 74
            or approval["spend_cap_usd"] != "0.40"):
        raise ValueError("Automated owner authorization exceeds frozen Cora140 batch scope")
    for field in OWNER_PERMISSIONS:
        approval[field] = True
    return approval


def require_approval(value, inputs, router, budget, cohort, config):
    expected = approval_template(inputs, router, budget, cohort, config)
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError("Exact user-authorized execution contract required")
    for field, declared in expected.items():
        actual = value[field]
        if field in OWNER_PERMISSIONS:
            if actual is not True:
                raise ValueError("Missing explicit owner authorization")
        elif field in UNVERIFIED_PROVIDER_FIELDS:
            # False means the check has NOT been verified; this is never a
            # fabricated prerequisite for a first observed real HTTP request.
            if type(actual) is not bool:
                raise ValueError("Invalid provider-evidence status")
        elif actual != declared or type(actual) is not type(declared):
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
    # No private journal or HTTP transport is initialized before this bound.
    validate_batch_wire(inputs, router, budget, cfg)
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
    if not fake:
        # Durable private authorization receipt must exist before any network
        # dispatch; retains false/unverified provider flags verbatim.
        approved = {"kind": "gapgpt_owner_batch_authorization_v2",
                    "approval": approval,
                    "gateway_context_sha256": digest(context),
                    "pricing_status": "USER_DECLARED_UNVERIFIED_GATEWAY_RATES",
                    "retention_status": RETENTION_STATUS}
        if journal.read(journal.write(approved)) != approved:
            raise ValueError("Unverifiable owner authorization receipt")
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
                                if k not in ("new_dispatches", "successful_replays",
                                             "returned_models", "rejection_codes",
                                             "unknown_billing_attempts",
                                             "verified_usage_scope")}
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
               "returned_models": stats["returned_models"],
               "rejection_codes": stats["rejection_codes"],
               "unknown_billing_attempts": stats["unknown_billing_attempts"],
               "verified_usage_scope": stats["verified_usage_scope"],
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
