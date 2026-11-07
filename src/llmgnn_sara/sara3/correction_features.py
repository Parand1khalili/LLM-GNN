"""Receipt-derived GT-free features, frozen before separately invoked evaluation."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re
import sys

from ..io.frozen import reject_gt
from ..io.project import load_project_inputs
from .audit import PrivateAudit
from .automated_policy import VERSION as POLICY, screen_validated
from .gateway_continuation import identity, journal_rows, replay
from .gateway_run import gateway_context
from .gapgpt_live import contract_from_dict, wire_for
from .inputs import canonical_bytes
from .experiment import digest
from .rich_evidence import rich_verifier_input_v2, validate_rich_result, target_source

VERSION = "sara.correction_features.v1"
PHASE_FIELDS = {"state", "l1", "class_index", "abstain", "support_count",
                "counter_count", "quote_lengths", "auxiliary_warning", "uncertainty",
                "topic_digest", "third_class"}
ROW_FIELDS = {"router", "node_id", "b1_class", "narrative_class", "b1_confidence",
              "narrative_confidence", "confidence_min", "confidence_max", "confidence_gap",
              "baseline_agrees", "blind", "compare", "phase_agrees", "shared_support",
              "topic_consistent", "changes_narrative", "v1_reason", "shadow_decision"}


def require(value):
    if not value:
        raise ValueError("Feature integrity or GT isolation failure")


def validate(table):
    reject_gt(table)
    require(set(table) == {"schema", "measurement_status", "policy_version", "sources", "rows"}
            and table["schema"] == VERSION and table["policy_version"] == POLICY
            and table["measurement_status"] == "GT_FREE_FROZEN_BEFORE_OUTCOME_JOIN")
    rows = table["rows"]
    require(set(table["sources"]) == {"r0", "r1_v1"})
    for source in table["sources"].values():
        require(type(source) is dict and set(source) == {
            "context_sha256", "contract_sha256", "journal_rows_sha256", "selected_ids_sha256"})
        require(all(type(v) is str and re.fullmatch(r"[0-9a-f]{64}", v) for v in source.values()))
    require(type(rows) is list and len(rows) == 74
            and len({(r["router"], r["node_id"]) for r in rows}) == 74
            and len({r["node_id"] for r in rows}) == 57)
    require(Counter(r["router"] for r in rows) == {"r0": 37, "r1_v1": 37})
    for row in rows:
        require(set(row) == ROW_FIELDS and type(row["node_id"]) is int and 0 <= row["node_id"] < 2708)
        require(all(type(row[k]) in (int, float) and math.isfinite(row[k]) and 0 <= row[k] <= 100
                    for k in ("b1_confidence", "narrative_confidence", "confidence_min", "confidence_max", "confidence_gap")))
        for field in ("b1_class", "narrative_class"):
            require(type(row[field]) is int and 0 <= row[field] < 7)
        for phase in ("blind", "compare"):
            p = row[phase]
            require(type(p) is dict and set(p) == PHASE_FIELDS)
            require(p["state"] in ("COMPLETED", "REJECTED", "NOT_PERMITTED_ABSTENTION"))
            if p["state"] != "COMPLETED":
                require(p["class_index"] is None and p["abstain"] is None)
            elif p["abstain"] is True:
                require(p["class_index"] is None)
            else:
                require(p["abstain"] is False and type(p["class_index"]) is int
                        and 0 <= p["class_index"] < 7 and p["l1"] == "PASS")
        require(row["shadow_decision"] in ("KEEP_BASELINE", "SHADOW_PROPOSE", "ABSTAIN"))


def phase_features(value, state, pair):
    result = dict.fromkeys(PHASE_FIELDS)
    result.update(state=state, l1="PASS" if state == "COMPLETED" else
                  "FAIL" if state == "REJECTED" else "NOT_ASSESSED")
    if value is None:
        return result
    valid = validate_rich_result(value, (target_source(pair.text),))
    e = valid["rich_evidence"]
    result.update(class_index=valid["class_index"], abstain=valid["abstain"],
                  support_count=len(e["supporting_evidence"]), counter_count=len(e["counter_evidence"]),
                  quote_lengths=[len(i["quote"]) for i in e["supporting_evidence"]],
                  auxiliary_warning=bool(e["auxiliary_method_warning"]),
                  uncertainty=bool(e["uncertainty_reason"]),
                  topic_digest=digest(e["primary_topic"].strip().casefold()) if e["primary_topic"] else None,
                  third_class=valid["class_index"] is not None and valid["class_index"] not in
                  (pair.b1.class_index, pair.narrative_v0.class_index))
    return result


def extract_run(inputs, root, config, router):
    require(router in ("r0", "r1_v1"))
    cfg = contract_from_dict(config)
    selected, ctx = gateway_context(inputs, router, 37, "sensitivity", cfg, fake=False)
    context_sha = digest(ctx)
    overlay = "continuation_amendment_v1" if router == "r0" else "r1_v1_continuation_v1"
    rejection = "L1_DUPLICATE_EVIDENCE" if router == "r0" else "L1_QUOTE_NOT_FOUND"
    rows, phases, audits = {}, {}, {}
    for origin, path in (("original", Path(root)), ("overlay", Path(root) / overlay)):
        require((path / "journal").is_dir())
        ids, entries = journal_rows(path, context_sha, cfg["max_calls"])
        require(not set(ids) & set(rows) and not set(entries) & set(phases))
        audit = PrivateAudit(path / "journal")
        rows.update(ids); phases.update(entries)
        audits.update({key: audit for key in entries})
    expected_calls = 67 if router == "r0" else 62
    require(len(rows) == expected_calls and Counter(r[3] for r in rows.values()) ==
            {"COMPLETED": expected_calls - 1, "REJECTED": 1})
    pairs = {p.node_id: p for p in inputs.pairs}
    observed, result = set(), []
    def get(node, phase, payload, dependency):
        entry = phases.get((node, phase))
        require(entry is not None)
        wire = wire_for(payload, cfg)
        expected = identity(context_sha, phase, payload, wire, dependency)
        value = replay(audits[node, phase], entry, expected, payload, wire, dependency,
                       context_sha, pairs[node].text, cfg, rejected_code=rejection)
        observed.add(expected)
        return value, entry[1][3]
    for node in selected:
        pair = pairs[node]
        blind, bs = get(node, "blind", rich_verifier_input_v2(node, pair.text, pair.neighborhood), None)
        require(bs == "COMPLETED" and blind is not None)
        comparison, cs = None, "NOT_PERMITTED_ABSTENTION"
        if blind["abstain"]:
            require((node, "compare") not in phases)
        else:
            payload = rich_verifier_input_v2(node, pair.text, pair.neighborhood,
                       candidates=tuple(sorted({pair.b1.class_index, pair.narrative_v0.class_index})),
                       blind_class=blind["class_index"])
            comparison, cs = get(node, "compare", payload, digest(blind))
        b, c = phase_features(blind, bs, pair), phase_features(comparison, cs, pair)
        shared, topic, agrees = None, None, None
        reason, decision = "BLIND_ABSTENTION" if blind["abstain"] else rejection, "ABSTAIN"
        if comparison is not None:
            first, second = [validate_rich_result(v, (target_source(pair.text),)) for v in (blind, comparison)]
            def quotes(v):
                return {i["quote"] for i in v["rich_evidence"]["supporting_evidence"] if i["source_id"] == "target.text"}
            shared = len(quotes(first) & quotes(second))
            topic = b["topic_digest"] == c["topic_digest"] if b["topic_digest"] and c["topic_digest"] else None
            agrees = b["class_index"] == c["class_index"] if not c["abstain"] else None
            screened = screen_validated(pair, first, second)
            reason = screened["reason"]
            if screened["action"] == "ACCEPT":
                decision = "KEEP_BASELINE" if screened["class_index"] == pair.narrative_v0.class_index else "SHADOW_PROPOSE"
        confidences = (pair.b1.confidence, pair.narrative_v0.confidence)
        result.append(dict(router=router, node_id=node, b1_class=pair.b1.class_index,
                           narrative_class=pair.narrative_v0.class_index, b1_confidence=confidences[0],
                           narrative_confidence=confidences[1], confidence_min=min(confidences),
                           confidence_max=max(confidences), confidence_gap=abs(confidences[0]-confidences[1]),
                           baseline_agrees=pair.agrees, blind=b, compare=c, phase_agrees=agrees,
                           shared_support=shared, topic_consistent=topic,
                           changes_narrative=b["class_index"] != pair.narrative_v0.class_index if not b["abstain"] else None,
                           v1_reason=reason, shadow_decision=decision))
    require(observed == set(rows))
    return result, {"context_sha256": context_sha, "contract_sha256": digest(cfg),
                    "journal_rows_sha256": digest(sorted(rows.items())), "selected_ids_sha256": digest(list(selected))}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("frozen-root", "authentic-root", "r0-root", "r1-root", "config", "output"):
        p.add_argument("--" + arg, type=Path, required=True)
    args = p.parse_args(argv)
    try:
        inputs = load_project_inputs(args.frozen_root, args.authentic_root)
        config = json.loads(args.config.read_text(encoding="utf-8"))
        table = {"schema": VERSION, "measurement_status": "GT_FREE_FROZEN_BEFORE_OUTCOME_JOIN",
                 "policy_version": POLICY, "sources": {}, "rows": []}
        for router, root in (("r0", args.r0_root), ("r1_v1", args.r1_root)):
            rows, source = extract_run(inputs, root, config, router)
            table["sources"][router] = source; table["rows"].extend(rows)
        validate(table)
        require(".local_artifacts" in args.output.absolute().parts)
        audit = PrivateAudit(args.output)
        sha = audit.write(table); require(audit.read(sha) == table)
        # Zero-proposal sanity plans only; no live-label admission adapter or training.
        from ..downstream.plan import GCNConfig, PseudoLabel, gcn_plan
        from .pipeline import _decision
        plans = {}
        if all(r["shadow_decision"] == "ABSTAIN" for r in table["rows"]):
            for router in ("r0", "r1_v1"):
                selected = {r["node_id"] for r in table["rows"] if r["router"] == router}
                labels = []
                for pair in inputs.pairs:
                    if pair.node_id not in selected and pair.agrees and min(pair.b1.confidence, pair.narrative_v0.confidence) >= 80:
                        d = _decision(pair, pair.b1.class_index, "UNREVIEWED_AGREEMENT", False)
                        labels.append(PseudoLabel(pair.node_id, d["training_class_index"], d["label_confidence_percent"]))
                plan = gcn_plan([p.node_id for p in inputs.pairs], labels, config=GCNConfig(), allow_abstention=True)
                plan.update(source_feature_sha256=sha, authorization="NOT_RUN_BLOCKED_SEPARATE_TRAINING_APPROVAL",
                            independent_test_status="UNVERIFIED_CONTAMINATION_AUDIT_REQUIRED")
                plan_sha = audit.write(plan); require(audit.read(plan_sha) == json.loads(canonical_bytes(plan)))
                plans[router] = {"control_sha256": plan_sha, "treatment_sha256": plan_sha,
                                 "training_count": len(labels), "identical_no_op": True}
        print(json.dumps({"status": "FEATURES_FROZEN_GT_NOT_ACCESSED", "feature_sha256": sha,
                          "observations": 74, "unique_nodes": 57,
                          "no_op_plans": plans,
                          "shadow_decisions": dict(Counter(r["shadow_decision"] for r in table["rows"]))}))
        return 0
    except (ValueError, OSError, KeyError, TypeError):
        print('{"status":"FAIL_CLOSED"}', file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
