"""Freeze the live Expanded Atlas vectors after read-only receipt replay.

This module never imports or reads ground truth and never invokes an API.
Treat the single historical REJECTED comparison as absent, not L1-approved.
"""
from collections import Counter
from dataclasses import replace
import argparse
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

from ..io.frozen import reject_gt
from ..io.project import load_project_inputs
from . import atlas, r1_candidate
from .audit import PrivateAudit
from .automated_policy import VERSION as POLICY, screen_validated
from .evidence import EXACT_FIRST
from .experiment import digest
from .gateway_continuation import identity, journal_rows, replay
from .gateway_run import gateway_context, CONTRACT
from .gapgpt_live import contract_from_dict, wire_for
from .rich_evidence import rich_verifier_input_v2, validate_rich_result, target_source

VERSION = "sara.expanded_atlas.gt_free_vector_freeze.v1"
ATLAS_SHA = "6b624adac49e9a8e3a78de6d7628e4fc1b654b21b5307a33ebd9b5ef4a007fe0"
ROOT = Path(".local_artifacts")
REJECTION = "L1_QUOTE_NOT_FOUND"


def _check(condition):
    if not condition:
        raise ValueError("Expanded Atlas freeze provenance mismatch")


def make_vectors(pairs, selected):
    """Pure, GT-free baseline and strictly abstention-only Treatment."""
    pairs = tuple(pairs)
    ids = [p.node_id for p in pairs]
    _check(len(ids) == 140 and len(set(ids)) == 140
           and len(selected) == 37 and len(set(selected)) == 37
           and set(selected) <= set(ids))
    ordered = sorted(pairs, key=lambda p: p.node_id)
    base = {p.node_id: (p.b1.class_index if p.agrees
                        and min(p.b1.confidence, p.narrative_v0.confidence) >= 80
                        else None) for p in ordered}
    treatment = {node: (None if node in selected else value)
                 for node, value in base.items()}
    counts = Counter(value for value in treatment.values() if value is not None)
    matched = set()
    for cls, count in sorted(counts.items()):
        options = [node for node, value in base.items() if value == cls]
        options.sort(key=lambda node: (
            hashlib.sha256(f"expanded-atlas-control-v1|{node}".encode()).hexdigest(),
            node))
        _check(len(options) >= count)
        matched.update(options[:count])
    class_matched = {node: (value if node in matched else None)
                     for node, value in base.items()}
    by_id = {p.node_id: p for p in ordered}
    def rows(labels, source):
        return [dict(node_id=node, class_index=cls,
                     confidence_percent=(None if cls is None else
                         (by_id[node].b1.confidence if source == "B1" else
                          by_id[node].narrative_v0.confidence if source == "Narrative" else
                          min(by_id[node].b1.confidence, by_id[node].narrative_v0.confidence))),
                     confidence_provenance=("NO_ACCEPTED_LABEL" if cls is None else
                         "B1_FROZEN" if source == "B1" else
                         "NARRATIVE_FROZEN" if source == "Narrative" else
                         "HISTORICAL_MIN_BASELINE_CONFIDENCE"))
                for node, cls in labels.items()]
    return {
        "B1": rows({p.node_id: p.b1.class_index for p in ordered}, "B1"),
        "Narrative": rows({p.node_id: p.narrative_v0.class_index for p in ordered}, "Narrative"),
        "C": rows(base, "C"),
        "Expanded_V1": rows(treatment, "C"),
        "Router_only": rows(treatment, "C"),
        "Class_count_matched": rows(class_matched, "C"),
    }


def validate_freeze(item):
    reject_gt(item)
    _check(type(item) is dict and item.get("schema") == VERSION
           and item.get("status") == "FROZEN_GT_NOT_ACCESSED"
           and item.get("l2") == "NOT_ASSESSED"
           and item.get("atlas_sha256") == ATLAS_SHA)
    ids = item.get("selected")
    vectors = item.get("vectors")
    _check(type(ids) is list and len(ids) == 37 and len(set(ids)) == 37)
    _check(type(vectors) is dict and set(vectors) ==
           {"B1", "Narrative", "C", "Expanded_V1", "Router_only", "Class_count_matched"})
    for rows in vectors.values():
        _check(type(rows) is list and len(rows) == 140
               and len({r["node_id"] for r in rows}) == 140)
        for row in rows:
            _check(type(row) is dict and set(row) ==
                   {"node_id", "class_index", "confidence_percent", "confidence_provenance"}
                   and type(row["node_id"]) is int and 0 <= row["node_id"] < 2708
                   and type(row["confidence_provenance"]) is str
                   and (row["class_index"] is None and row["confidence_percent"] is None
                        or type(row["class_index"]) is int and 0 <= row["class_index"] < 7
                        and type(row["confidence_percent"]) in (int, float)
                        and 0 <= row["confidence_percent"] <= 100))
    base_ids = [r["node_id"] for r in vectors["C"]]
    _check(all([r["node_id"] for r in rows] == base_ids for rows in vectors.values()))
    _check(set(ids) <= set(base_ids)
           and vectors["Expanded_V1"] == vectors["Router_only"])
    for k in ("source_summary_sha256", "source_run_sha256", "context_sha256",
              "journal_rows_sha256", "selected_sha256"):
        _check(type(item.get(k)) is str and len(item[k]) == 64)
    _check(item.get("phase_counts", {}).get("blind_completed") == 37
           and item["phase_counts"].get("blind_abstained") == 9
           and item["phase_counts"].get("comparison_completed") == 27
           and item["phase_counts"].get("comparison_rejected") == 1
           and item["phase_counts"].get("uncertain") == 0)
    return item


def freeze(inputs, config, saved_atlas, journal_root, summary_sha):
    """Verify all 65 settled phases; no HTTP transport or database writes."""
    _check(type(saved_atlas) is dict and "expanded" in saved_atlas)
    entries = tuple(replace(c, keywords=tuple(v)) for c, v in
                    zip(atlas.ATLAS, saved_atlas["expanded"]["vocab"]))
    _check(len(entries) == 7)
    cfg = contract_from_dict(config)
    with patch.object(atlas, "ATLAS", entries):
        selected, context = gateway_context(
            inputs, "r1_v1", 37, "sensitivity", cfg, fake=False)
        _check(list(selected) == saved_atlas["expanded"]["ids"]
               and list(r1_candidate.route_r1_candidate(inputs.pairs)) == list(selected))
    context_sha = digest(context)
    audit = PrivateAudit(Path(journal_root) / "journal")
    summary = audit.read(summary_sha)
    _check(summary.get("schema") == CONTRACT
           and summary.get("status") == "COMPLETE_LIVE_WITH_VERIFIED_L1_REJECTION"
           and summary.get("gateway_context_sha256") == context_sha
           and summary.get("selected_node_ids") == list(selected)
           and summary.get("journal_states") ==
           {"COMPLETED": 64, "REJECTED": 1, "UNCERTAIN": 0}
           and summary.get("blind_completed") == 37
           and summary.get("comparison_completed") == 27
           and summary.get("attempted_calls") == 65
           and summary.get("rejection_codes") == {REJECTION: 1})
    run_sha = summary["private_report_sha256"]
    run = audit.read(run_sha)
    reject_gt(run)
    _check(run.get("gateway_context_sha256") == context_sha
           and run.get("selected_node_ids") == list(selected)
           and len(run.get("decisions", [])) == 140)
    rows, states = journal_rows(journal_root, context_sha, cfg["max_calls"])
    _check(len(rows) == 65 and len(states) == 65)
    pairs = {p.node_id: p for p in inputs.pairs}
    _check(len(pairs) == 140)
    seen = set()
    counts = Counter()
    for node in selected:
        pair = pairs[node]
        bp = rich_verifier_input_v2(node, pair.text, pair.neighborhood)
        bw = wire_for(bp, cfg)
        bid = identity(context_sha, "blind", bp, bw, None)
        record = states.get((node, "blind"))
        _check(record is not None and record[1][3] == "COMPLETED")
        blind = replay(audit, record, bid, bp, bw, None, context_sha,
                       pair.text, cfg, rejected_code=REJECTION)
        _check(blind is not None)
        counts["blind_completed"] += 1
        seen.add((node, "blind"))
        if blind["abstain"]:
            _check((node, "compare") not in states)
            counts["blind_abstained"] += 1
            continue
        cp = rich_verifier_input_v2(
            node, pair.text, pair.neighborhood,
            candidates=tuple(sorted({pair.b1.class_index, pair.narrative_v0.class_index})),
            blind_class=blind["class_index"])
        cw = wire_for(cp, cfg)
        dep = digest(blind)
        cid = identity(context_sha, "compare", cp, cw, dep)
        record = states.get((node, "compare"))
        _check(record is not None)
        comparison = replay(audit, record, cid, cp, cw, dep, context_sha,
                            pair.text, cfg, rejected_code=REJECTION)
        seen.add((node, "compare"))
        if comparison is None:
            counts["comparison_rejected"] += 1
        else:
            counts["comparison_completed"] += 1
            screen_validated(pair, validate_rich_result(blind, (target_source(pair.text),)),
                             validate_rich_result(comparison, (target_source(pair.text),)))
    _check(seen == set(states) and counts["blind_abstained"] == 9
           and counts["comparison_completed"] == 27
           and counts["comparison_rejected"] == 1)
    counts["uncertain"] = 0
    vectors = make_vectors(inputs.pairs, selected)
    actual = {r["node_id"]: r for r in run["decisions"]}
    _check(set(actual) == set(pairs))
    for r in vectors["Expanded_V1"]:
        decision = actual[r["node_id"]]
        _check(decision.get("training_class_index") == r["class_index"]
               and decision.get("label_confidence_percent") == r["confidence_percent"]
               and decision.get("abstain") == (r["class_index"] is None)
               and decision.get("routed_for_review") == (r["node_id"] in selected))
    item = {
        "schema": VERSION, "status": "FROZEN_GT_NOT_ACCESSED",
        "scientific_status": ["LIMITED_PROVENANCE_EXPLORATORY", "EXPLORATORY_NOT_INDEPENDENT"],
        "l2": "NOT_ASSESSED", "policy_version": POLICY,
        "atlas_sha256": ATLAS_SHA,
        "source_summary_sha256": summary_sha, "source_run_sha256": run_sha,
        "context_sha256": context_sha,
        "journal_rows_sha256": digest(sorted(rows.items())),
        "selected_sha256": digest(list(selected)), "selected": list(selected),
        "phase_counts": dict(counts), "vectors": vectors,
        "training_admission": "NOT_GRANTED", "training_runs": 0, "GT_accessed": False,
    }
    validate_freeze(item)
    return item


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--summary-sha256", required=True)
    args = p.parse_args(argv)
    try:
        input_data = load_project_inputs(ROOT / "frozen", ROOT / "authentic")
        config = json.loads(Path("configs/gapgpt_rich_v2_output4096_proposed.json").read_text())
        config["max_spend_usd"] = "1.00"
        atlas_receipt = PrivateAudit(ROOT / "expanded_atlas_ablation").read(ATLAS_SHA)
        result = freeze(input_data, config, atlas_receipt,
                        ROOT / "expanded_atlas_agent3_v1", args.summary_sha256)
        output = PrivateAudit(ROOT / "expanded_atlas_freeze_v1")
        sha = output.write(result)
        _check(output.read(sha) == result)
        counts = {name: sum(row["class_index"] is not None for row in rows)
                  for name, rows in result["vectors"].items()}
        print(json.dumps({"status": "FROZEN_GT_NOT_ACCESSED", "freeze_sha256": sha,
                          "accepted_counts": counts, "phase_counts": result["phase_counts"],
                          "training_runs": 0}, ensure_ascii=False))
        return 0
    except Exception:
        print('{"status":"FAIL_CLOSED_NO_GT_NO_API"}', file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
