"""One-command GT-free SARA-3 rich-v2 synthetic runner, with durable Resume.

No live API, credentials or GCN training. It reuses the pinned Cora input
admission, routing, rich L1, conservative screening and private SQLite audit.
All output derived from this runner is SYNTHETIC, never semantic L2 evidence.
"""
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import sys

from ..downstream.plan import GCNConfig
from ..downstream.prospective import (
    VERSION as ADMISSION_VERSION, controlled_gcn_plan,
    frozen_pair_digest, offline_report_digest)
from ..io.project import load_project_inputs
from ..sara2.policy import CLASSES, PolicyConfig
from .audit import PrivateAudit
from .automated_policy import VERSION as AUTOMATED_VERSION
from .durable_rich import DurableRichOfflineVerifier, EXPERIMENT_VERSION
from .experiment import FIXTURE_VERSION, MODEL_PLACEHOLDERS, digest
from .inputs import canonical_bytes
from .pipeline import run_offline
from .rich_evidence import RICH_PROMPT_V2, RICH_RESPONSE_SCHEMA, RICH_VERSION, rich_verifier_input_v2
from .selection import ROUTERS, select_router

RUNNER_VERSION = "sara.runner.rich_v2.synthetic.v1"


class SyntheticRichVerifier:
    """Deliberately non-semantic; BLIND does not read B1/Narrative candidates."""
    offline = True
    fixture_version = FIXTURE_VERSION

    def __init__(self):
        self.dispatches = 0

    def _respond(self, request):
        self.dispatches += 1
        text = request.text
        words = list(re.finditer(r"\w", text[:160]))
        if len(words) < 12:
            return {"schema_version": RICH_VERSION, "class_index": None,
                    "abstain": True, "primary_topic": None,
                    "supporting_evidence": [], "counter_evidence": [],
                    "auxiliary_method_warning": None,
                    "uncertainty_reason": "No substantial excerpt for synthetic fixture"}
        quote = text[words[0].start():words[-1].end()]
        label = hashlib.sha256(text.encode("utf-8")).digest()[0] % len(CLASSES)
        return {"schema_version": RICH_VERSION, "class_index": label, "abstain": False,
                "primary_topic": "Synthetic fixture: no semantic topic assessment",
                "supporting_evidence": [{"source_id": "target.text", "quote": quote,
                                         "claim": "Exact source excerpt for schema testing only"}],
                "counter_evidence": [], "auxiliary_method_warning": None,
                "uncertainty_reason": None}

    def blind(self, request):
        return self._respond(request)

    def compare(self, request):
        return self._respond(request)


def _context(inputs, router, budget):
    """Bind Frozen inputs, exact prospective versions and router to SQLite."""
    rows = inputs.pairs
    if router not in ROUTERS or type(budget) is not int or budget <= 0:
        raise ValueError("Explicit router and positive call budget required")
    selected = select_router(rows, budget, router)
    if not selected:
        raise ValueError("No routed nodes")
    protocol = {
        "runner_version": RUNNER_VERSION, "prompt_version": RICH_PROMPT_V2,
        "response_version": RICH_VERSION, "response_schema": RICH_RESPONSE_SCHEMA,
        "arbitration_version": AUTOMATED_VERSION,
        "router": router, "budget": budget, "policy": asdict(PolicyConfig()),
        "source_hashes": dict(inputs.provenance)}
    return selected, {"mode": "OFFLINE_SYNTHETIC_ONLY", "fixture_version": FIXTURE_VERSION,
                      "experiment_version": EXPERIMENT_VERSION,
                      "cohort_sha256": digest([asdict(p) for p in rows]),
                      "protocol_sha256": digest(protocol),
                      "model_settings": dict(MODEL_PLACEHOLDERS)}


def dry_run(inputs, router="r0", budget=37):
    selected, context = _context(inputs, router, budget)
    pairs = {p.node_id: p for p in inputs.pairs}
    blind = [rich_verifier_input_v2(n, pairs[n].text, pairs[n].neighborhood)
             for n in selected]
    # Comparison is conditional and depends on a *saved* valid blind response.
    return {"schema": RUNNER_VERSION, "mode": "DRY_RUN_NO_DISPATCH",
            "input_count": len(inputs.pairs), "router": router, "review_budget": budget,
            "selected_node_ids": list(selected), "selected_count": len(selected),
            "maximum_conditional_calls": 2 * len(selected),
            "blind_payload_sha256": [digest(item) for item in blind],
            "blind_input_tokens_heuristic": (sum(len(str(x)) for x in blind) + 3) // 4,
            "provider_calls": 0, "training_runs": 0, "GT_accessed": False,
            "estimated_cost_usd": None, "price_status": "UNVERIFIED_NO_PROVIDER_PRICES",
            "prompt_version": RICH_PROMPT_V2, "response_version": RICH_VERSION,
            "automated_policy_version": AUTOMATED_VERSION,
            "execution_context_sha256": digest(context),
            "frozen_pairs_sha256": frozen_pair_digest(inputs.pairs),
            "source_hashes": dict(inputs.provenance),
            "scientific_status": "OFFLINE_DRY_RUN_NO_MODEL_INFERENCE"}


def offline_run(inputs, output_root, *, router="r0", budget=37,
                cohort="sensitivity"):
    selected, context = _context(inputs, router, budget)
    root = Path(output_root).resolve(strict=False)
    if ".local_artifacts" not in root.parts or root.is_symlink():
        raise ValueError("Output root must be under a private .local_artifacts directory")
    journal_audit = PrivateAudit(root / "journal")
    phase_audit = PrivateAudit(root / "phases")
    fixture = SyntheticRichVerifier()
    durable = DurableRichOfflineVerifier(fixture, context, journal_audit,
                                         maximum_calls=2 * len(selected))
    run = run_offline(inputs.pairs, budget=budget, router=router, verifier=durable,
                      audit=phase_audit, response_version=RICH_VERSION,
                      prompt_version=RICH_PROMPT_V2,
                      automated_arbitration_version=AUTOMATED_VERSION)
    states = durable.states
    run["runner_version"] = RUNNER_VERSION
    run["execution_context_sha256"] = digest(context)
    run["frozen_pairs_sha256"] = frozen_pair_digest(inputs.pairs)
    run["source_hashes"] = dict(inputs.provenance)
    run["ledger_persistence"] = "PRIVATE_SQLITE_INTENTS_AND_HASH_BOUND_RESPONSES"
    # Dispatch/replay counts are session diagnostics, not report identity: replay
    # must reproduce the EXACT same content-addressed scientific run report.
    run["fixture_intent_states"] = dict(Counter(states.values()))
    run["data_kind"] = "SYNTHETIC_RESPONSE_ON_AUTHENTIC_CORA_NOT_SCIENTIFIC_RESULT"
    report_sha = offline_report_digest(run)
    if journal_audit.write(run) != report_sha:
        raise ValueError("Private report hashing mismatch")
    blocked = any(v != "COMPLETED" for v in states.values())
    plan = None
    if not blocked:
        try:
            exclusions = (tuple(p.target_id for p in inputs.frozen.by_arm("b1")
                           if p.samples[0].source_kind == "supplementary")
                           if cohort == "primary" else ())
            plan = controlled_gcn_plan(
                inputs.pairs, run, admission_version=ADMISSION_VERSION,
                frozen_pairs_sha256=frozen_pair_digest(inputs.pairs),
                report_sha256=report_sha, cohort=cohort,
                excluded_ids=exclusions, config=GCNConfig())
        except ValueError as exc:
            if str(exc) != "No baseline or provisional candidates to plan":
                raise
    plan_sha = journal_audit.write(plan) if plan is not None else None
    summary = {
        "schema": RUNNER_VERSION,
        "status": "BLOCKED_RECONCILIATION_REQUIRED" if blocked else "COMPLETE_SYNTHETIC",
        "router": router, "cohort": cohort, "denominator": len(inputs.pairs),
        "selected_count": len(selected), "selected_node_ids": list(selected),
        "new_fixture_dispatches": durable.dispatches,
        "successful_fixture_replays": durable.hits,
        "blind_responses": sum(p == "blind" and x == "COMPLETED"
                               for (_, p), x in _journal_phases(durable).items()),
        "comparison_responses": sum(p == "compare" and x == "COMPLETED"
                                    for (_, p), x in _journal_phases(durable).items()),
        "journal_states": dict(Counter(states.values())),
        "l1_pass_phase_count": sum(s == "COMPLETED" for s in states.values()),
        "rejected_phase_count": sum(s == "REJECTED" for s in states.values()),
        "uncertain_phase_count": sum(s == "UNCERTAIN" for s in states.values()),
        "l1_failed_node_count": sum(d.get("l1_status") == "FAIL" for d in run["decisions"]),
        "reviewed_abstain_count": sum(d["routed_for_review"] and d["decision"] == "ABSTAIN"
                                      for d in run["decisions"]),
        "abstain_count": run["abstention_count"],
        "baseline_accepted_count": run["accepted_count"],
        "provisional_count": run["provisional_count"],
        "baseline_coverage": run["coverage"],
        "provisional_coverage": run["provisional_coverage"],
        "potential_coverage": run["potential_coverage_if_experimentally_admitted"],
        "initial_b1_class_distribution": {
            name: sum(p.b1.class_index == i for p in inputs.pairs)
            for i, name in enumerate(CLASSES)},
        "initial_narrative_class_distribution": {
            name: sum(p.narrative_v0.class_index == i for p in inputs.pairs)
            for i, name in enumerate(CLASSES)},
        "initial_frozen_coverage": 1.0,
        "baseline_class_distribution": run["class_retention_counts"],
        "provisional_class_distribution": run["provisional_class_distribution"],
        "no_label_without_experimental_admission": run["abstention_count"],
        "provider_calls": 0, "input_tokens": None, "output_tokens": None,
        "token_status": "NO_PROVIDER_USAGE_FAKE_TRANSPORT",
        "estimated_cost_usd": 0.0, "cost_status": "NO_PAID_CALLS",
        "GT_accessed": False, "training_runs": 0,
        "prompt_version": RICH_PROMPT_V2, "policy_version": AUTOMATED_VERSION,
        "frozen_pairs_sha256": frozen_pair_digest(inputs.pairs),
        "execution_context_sha256": digest(context),
        "private_report_sha256": report_sha,
        "private_plan_sha256": plan_sha,
        "private_audit_directory": str(journal_audit.root),
        "gc_plan_status": "PLAN_ONLY" if plan is not None else "NOT_AVAILABLE",
        "scientific_status": "SYNTHETIC_NOT_MEASURED_ACCURACY"}
    summary_sha = journal_audit.write(summary)
    summary["private_summary_sha256"] = summary_sha
    summary["private_summary_file"] = str(journal_audit.root / (summary_sha + ".json"))
    return summary


def _journal_phases(durable):
    """Read SQLite phase/status without decoding private request content."""
    from contextlib import closing
    with closing(durable._connection()) as db:
        durable._verify_binding(db)
        return {(n, p): s for n, p, s in db.execute(
            "SELECT node_id,phase,state FROM intents")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("dry-run", "offline", "live-preflight", "live-fake", "live"), required=True)
    parser.add_argument("--frozen-root", type=Path, required=True)
    parser.add_argument("--authentic-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--router", choices=ROUTERS, default="r0")
    parser.add_argument("--budget", type=int, default=37)
    parser.add_argument("--cohort", choices=("primary", "sensitivity"),
                        default="sensitivity")
    parser.add_argument("--gateway-config", type=Path,
                        help="Versioned non-secret model, prices and call/spend caps")
    parser.add_argument("--owner-approval-file", type=Path,
                        help="Separate private owner approval, bound to exact contract")
    parser.add_argument("--enable-real-dispatch", action="store_true",
                        help="Required along with separate signed-off owner approval")
    args = parser.parse_args(argv)
    try:
        inputs = load_project_inputs(args.frozen_root, args.authentic_root)
        if args.mode in ("live-preflight", "live-fake", "live"):
            from .gateway_run import approval_template, gateway_run
            if args.gateway_config is None or args.gateway_config.is_symlink():
                raise ValueError("Explicit versioned gateway configuration file required")
            config = json.loads(args.gateway_config.read_text(encoding="utf-8"))
            if args.mode == "live-preflight":
                if args.enable_real_dispatch or args.owner_approval_file is not None:
                    raise ValueError("Preflight never approves or sends requests")
                result = {"status": "PROPOSED_NO_DISPATCH",
                          "approval_template": approval_template(
                              inputs, args.router, args.budget, args.cohort, config),
                          "provider_calls": 0, "training_runs": 0,
                          "pricing_status": "OWNER_DECLARED_GATEWAY_UNVERIFIED",
                          "retention_status": "GATEWAY_RETENTION_NOT_VERIFIED"}
            else:
                if args.output_root is None:
                    raise ValueError("Private output root required")
                if args.mode == "live":
                    if not args.enable_real_dispatch or args.owner_approval_file is None:
                        raise ValueError("Paid mode requires explicit opt-in and owner approval")
                    if (args.owner_approval_file.is_symlink()
                            or ".local_artifacts" not in args.owner_approval_file.resolve().parts):
                        raise ValueError("Approval file must be in private .local_artifacts")
                    approval = json.loads(args.owner_approval_file.read_text(encoding="utf-8"))
                else:
                    if args.enable_real_dispatch or args.owner_approval_file is not None:
                        raise ValueError("Fake mode forbids real-dispatch approval")
                    approval = None
                result = gateway_run(
                    inputs, args.output_root, router=args.router, budget=args.budget,
                    cohort=args.cohort, config=config, fake=args.mode == "live-fake",
                    approval=approval)
        elif args.mode == "offline":
            if args.output_root is None:
                raise ValueError("Private --output-root is required for durable offline run")
            result = offline_run(inputs, args.output_root, router=args.router,
                                 budget=args.budget, cohort=args.cohort)
        else:
            if args.enable_real_dispatch or args.gateway_config or args.owner_approval_file:
                raise ValueError("Dry/offline modes forbid gateway options")
            result = dry_run(inputs, args.router, args.budget)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 2 if result.get("status") in ("BLOCKED_RECONCILIATION_REQUIRED",
                                             "BLOCKED_NO_AUTOMATIC_RETRY") else 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        # Never echo untrusted target text, raw responses, paths to credentials.
        print(json.dumps({"status": "FAIL_CLOSED", "reason_type": type(exc).__name__}),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
