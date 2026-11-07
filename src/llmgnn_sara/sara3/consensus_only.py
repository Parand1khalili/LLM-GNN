"""Post-observation consensus ablation and private source audit. Not admission."""
import argparse
from collections import Counter
import difflib
import json
from pathlib import Path
import re
import sys

from ..io.frozen import read_pinned_json
from ..io.project import load_project_inputs
from .audit import PrivateAudit
from .correction_features import require, phase_features
from . import correction_features as features
from . import evidence_arbitration_v3 as v3
from .experiment import digest
from .gateway_continuation import identity, journal_rows, replay
from .gateway_run import gateway_context
from .gapgpt_live import contract_from_dict, wire_for
from .rich_evidence import rich_verifier_input_v2, validate_rich_result, target_source

VERSION = "sara.ablation.consensus_only.v1"
CONTRACT = {"version": VERSION, "design": "POST_V1_V2_V3_EXPLORATORY_NOT_INDEPENDENT",
            "require_completed_l1_nonabstaining_agreed_class": True,
            "require_valid_support_each_phase": True, "require_change_from_narrative": True,
            "third_class_allowed": True, "diagnostic_only": ["Q", "A", "C", "T", "P", "N", "U"],
            "score": None, "training_authorization": False}


def decide(row, optional, cfg):
    checked = v3.decide(row, optional, cfg)  # Reuse validity gates, not V3 score.
    result = {**checked, "policy_version": VERSION, "score": None}
    if checked["decision"] == "NO_VALID_AGENT_RESPONSE" or checked["reason"] == "PHASE_CLASS_DISAGREEMENT": return result
    if checked["agent_class"] == row["narrative_class"]: return result
    return {**result, "decision": "SWITCH_TO_AGENT", "label": checked["agent_class"],
            "reason": "CONSENSUS_ONLY_DIAGNOSTIC_SWITCH"}


def score(table, baseline):
    verified = v3.score(table, baseline)
    return [{"router": s["router"], "node_id": s["node_id"], "narrative_class": s["narrative_class"],
             "optional_support": r["optional_support"],
             **decide(s, r["optional_support"], baseline["config"])} for s, r in zip(table["rows"], verified)]


def topic_difference(first, second):
    """Lexical descriptions only. Never a semantic-equivalence judgment."""
    a, b = first.strip().casefold(), second.strip().casefold()
    ta, tb = re.findall(r"\w+", a), re.findall(r"\w+", b)
    if a == b: category = "NORMALIZED_IDENTICAL"
    elif ta == tb: category = "TOKEN_IDENTICAL_FORMATTING_DIFFERENCE"
    elif Counter(ta) == Counter(tb): category = "TOKEN_REORDERING"
    elif any(short == long[i:i+len(short)] for short, long in ((ta, tb), (tb, ta)) if short
             for i in range(len(long)-len(short)+1)): category = "CONTIGUOUS_TOKEN_EXTENSION"
    else: category = "TOKEN_REPLACEMENT_ADDITION_OR_DELETION"
    union = set(ta) | set(tb)
    return {"lexical_category": category, "token_jaccard": len(set(ta) & set(tb))/len(union) if union else None,
            "edit_operations": dict(Counter(tag for tag, *_ in difflib.SequenceMatcher(a=ta, b=tb).get_opcodes() if tag != "equal")),
            "semantic_status": "NOT_ASSESSED"}


def audit_candidates(table, decisions, inputs, roots, config):
    cfg = contract_from_dict(config)
    pairs = {p.node_id: p for p in inputs.pairs}
    private, summaries = [], {}
    for router in ("r0", "r1_v1"):
        selected, ctx = gateway_context(inputs, router, 37, "sensitivity", cfg, fake=False)
        context_sha = digest(ctx)
        require(context_sha == table["sources"][router]["context_sha256"] and
                digest(cfg) == table["sources"][router]["contract_sha256"])
        root = Path(roots[router]); overlay = "continuation_amendment_v1" if router == "r0" else "r1_v1_continuation_v1"
        journals, entries, merged = {}, {}, {}
        for path in (root, root/overlay):
            ids, phases = journal_rows(path, context_sha, cfg["max_calls"])
            require(not set(ids) & set(merged) and not set(phases) & set(entries))
            merged.update(ids); entries.update(phases)
            journals.update({k: PrivateAudit(path/"journal") for k in phases})
        require(digest(sorted(merged.items())) == table["sources"][router]["journal_rows_sha256"])
        sources = {r["node_id"]: r for r in table["rows"] if r["router"] == router}
        records = []
        for decision in (r for r in decisions if r["router"] == router and r["decision"] == "SWITCH_TO_AGENT"):
            node = decision["node_id"]; require(node in selected)
            pair = pairs[node]; values, provenance = {}, {}
            for phase in ("blind", "compare"):
                payload = rich_verifier_input_v2(node, pair.text, pair.neighborhood,
                    **({} if phase == "blind" else {"candidates": tuple(sorted({pair.b1.class_index, pair.narrative_v0.class_index})),
                                                   "blind_class": values["blind"]["class_index"]}))
                dependency = None if phase == "blind" else digest(values["blind"])
                wire = wire_for(payload, cfg); entry = entries[node, phase]
                require(entry[1][3] == "COMPLETED")
                value = replay(journals[node, phase], entry, identity(context_sha, phase, payload, wire, dependency),
                               payload, wire, dependency, context_sha, pair.text, cfg)
                require(phase_features(value, "COMPLETED", pair) == sources[node][phase])
                values[phase] = value
                receipt = journals[node, phase].read(entry[1][4])
                provenance[phase] = {k: receipt[k] for k in ("response_sha256", "wire_sha256", "identity", "context_sha256")}
                provenance[phase]["receipt_sha256"] = entry[1][4]
            rich = {p: validate_rich_result(v, (target_source(pair.text),))["rich_evidence"] for p, v in values.items()}
            shared = len({i["quote"] for i in rich["blind"]["supporting_evidence"]} &
                         {i["quote"] for i in rich["compare"]["supporting_evidence"]})
            require(shared == sources[node]["shared_support"])
            lexical = topic_difference(*(rich[p]["primary_topic"] for p in ("blind", "compare")))
            record = {"router": router, "node_id": node, "provenance": provenance, "rich_evidence": rich,
                      "shared_quote_count": shared, "third_class": decision["third_class"],
                      "topic_difference": lexical, "semantic_assessment": "NOT_ASSESSED",
                      "warning_type_vs_primary_topic_counterevidence": "UNVALIDATED_NO_AUTOMATIC_SEMANTIC_CLASSIFICATION"}
            records.append(record)
        private.extend(records)
        summaries[router] = {"candidate_count": len(records),
            "shared_quote_counts": dict(Counter(str(r["shared_quote_count"]) for r in records)),
            "third_class_count": sum(r["third_class"] for r in records),
            "topic_lexical_categories": dict(Counter(r["topic_difference"]["lexical_category"] for r in records)),
            "warning_present_each_phase": {p: sum(bool(r["rich_evidence"][p]["auxiliary_method_warning"]) for r in records) for p in ("blind", "compare")},
            "counter_present_each_phase": {p: sum(bool(r["rich_evidence"][p]["counter_evidence"]) for r in records) for p in ("blind", "compare")}}
    return {"schema": "sara.consensus_source_audit.v1", "private_candidates": private, "summary": summaries,
            "source_feature_sha256": v3.base.FEATURE_SHA, "semantic_status": "NOT_ASSESSED"}


def validate_report(report, table, baseline):
    require(report["schema"] == VERSION and report["contract"] == CONTRACT
            and report["rule_sha256"] == digest(CONTRACT) and report["training_admissions"] == 0
            and report["source_feature_sha256"] == v3.base.FEATURE_SHA
            and report["base_report_sha256"] == v3.BASE_REPORT_SHA
            and report["rows"] == score(table, baseline))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("features", "base-report", "frozen-root", "authentic-root", "r0-root", "r1-root", "config", "output"):
        p.add_argument("--"+name, type=Path, required=True)
    args = p.parse_args(argv)
    try:
        table = read_pinned_json(args.features, v3.base.FEATURE_SHA)
        baseline = read_pinned_json(args.base_report, v3.BASE_REPORT_SHA)
        require(".local_artifacts" in args.output.absolute().parts)
        store = PrivateAudit(args.output); rule_sha = store.write(CONTRACT)
        decisions = score(table, baseline)
        audit = audit_candidates(table, decisions, load_project_inputs(args.frozen_root, args.authentic_root),
                                 {"r0": args.r0_root, "r1_v1": args.r1_root}, json.loads(args.config.read_text(encoding="utf-8")))
        require([audit["summary"][r]["candidate_count"] for r in ("r0", "r1_v1")] == [10, 6])
        diagnostic_sha = store.write(audit)
        report = {"schema": VERSION, "contract": CONTRACT, "rule_sha256": rule_sha, "diagnostic_sha256": diagnostic_sha,
                  "source_feature_sha256": v3.base.FEATURE_SHA, "base_report_sha256": v3.BASE_REPORT_SHA,
                  "rows": decisions, "training_admissions": 0}
        validate_report(report, table, baseline)
        sha = store.write(report); require(store.read(sha) == report)
        print(json.dumps({"status": "CONSENSUS_ABLATION_GT_FREE_FROZEN", "rule_sha256": rule_sha,
                          "report_sha256": sha, "diagnostic_sha256": diagnostic_sha, "summary": audit["summary"]}))
        return 0
    except Exception:
        print('{"status":"FAIL_CLOSED"}', file=sys.stderr); return 1


if __name__ == "__main__": raise SystemExit(main())
