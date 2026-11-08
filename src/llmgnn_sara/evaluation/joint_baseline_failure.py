"""Private GT-only failure analysis of the 38 jointly misclassified Cora nodes.

The source stage replays the Expanded-Atlas 65-intent journal and validates the
previously frozen R0/R1 correction features BEFORE original-graph GT is loaded.
This tool is diagnostic only: no HTTP, training, policies, admission or tuning.
"""
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path
from statistics import median
from unittest.mock import patch
import argparse
import json
import re
import sys

from ..io.project import load_project_inputs
from ..sara3 import atlas, r1_candidate
from ..sara3.audit import PrivateAudit
from ..sara3.automated_policy import screen_validated, VERSION as POLICY
from ..sara3.correction_features import (
    validate as validate_historical_features, phase_features)
from ..sara3.expanded_atlas_freeze import (
    ROOT, ATLAS_SHA, validate_freeze, freeze as replay_frozen_run)
from ..sara3.experiment import digest
from ..sara3.gateway_continuation import identity, journal_rows, replay
from ..sara3.gateway_run import gateway_context
from ..sara3.gapgpt_live import contract_from_dict, wire_for
from ..sara3.rich_evidence import (
    rich_verifier_input_v2, validate_rich_result, target_source)
from .cora_gt_shadow import _labels_from_original_graph, _expected_graph_names

VERSION = "sara.evaluation.joint_baseline_failure.v1"
OLD_INVENTORY_SHA = "789a6aea4715c1e7537ede75d82f5e552859c392a0e27acd8cbbbc03b568da83"
ROUTERS = ("r0", "r1_v1", "expanded_r1_v1")
REJECTION = "L1_QUOTE_NOT_FOUND"


def require(ok):
    if not ok:
        raise ValueError("Joint-error analysis source or alignment mismatch")


def _phase(raw, state, pair):
    return phase_features(raw, state, pair)


def read_expanded_phases(inputs, config, saved_atlas, frozen, output_root):
    """Rebind identities and replay every phase without writing to the source."""
    validate_freeze(frozen)
    cfg = contract_from_dict(config)
    entries = tuple(replace(c, keywords=tuple(v)) for c, v in
                    zip(atlas.ATLAS, saved_atlas["expanded"]["vocab"]))
    require(len(entries) == 7)
    with patch.object(atlas, "ATLAS", entries):
        selected, context = gateway_context(
            inputs, "r1_v1", 37, "sensitivity", cfg, fake=False)
        require(list(selected) == frozen["selected"]
                and list(selected) == list(saved_atlas["expanded"]["ids"])
                and list(r1_candidate.route_r1_candidate(inputs.pairs)) == list(selected))
    context_sha = digest(context)
    require(context_sha == frozen["context_sha256"])
    journal, phases = journal_rows(output_root, context_sha, cfg["max_calls"])
    require(len(journal) == 65 and len(phases) == 65)
    audit = PrivateAudit(Path(output_root) / "journal")
    by_id = {p.node_id: p for p in inputs.pairs}
    observed = set()
    results = {}
    for node in selected:
        pair = by_id[node]
        payload = rich_verifier_input_v2(node, pair.text, pair.neighborhood)
        wire = wire_for(payload, cfg)
        ident = identity(context_sha, "blind", payload, wire, None)
        br = phases.get((node, "blind"))
        require(br is not None and br[1][3] == "COMPLETED")
        blind = replay(audit, br, ident, payload, wire, None,
                       context_sha, pair.text, cfg, rejected_code=REJECTION)
        require(blind is not None)
        observed.add((node, "blind"))
        blind_feature = _phase(blind, "COMPLETED", pair)
        comparison, comparison_state = None, "NOT_PERMITTED_ABSTENTION"
        policy_reason = "BLIND_ABSTENTION"
        if not blind["abstain"]:
            payload = rich_verifier_input_v2(
                node, pair.text, pair.neighborhood,
                candidates=tuple(sorted({pair.b1.class_index, pair.narrative_v0.class_index})),
                blind_class=blind["class_index"])
            wire = wire_for(payload, cfg)
            ident = identity(context_sha, "compare", payload, wire, digest(blind))
            cr = phases.get((node, "compare"))
            require(cr is not None)
            comparison_state = cr[1][3]
            require(comparison_state in ("COMPLETED", "REJECTED"))
            comparison = replay(audit, cr, ident, payload, wire,
                                digest(blind), context_sha, pair.text, cfg,
                                rejected_code=REJECTION)
            observed.add((node, "compare"))
            if comparison is None:
                require(comparison_state == "REJECTED")
                policy_reason = REJECTION
            else:
                require(comparison_state == "COMPLETED")
                check = screen_validated(
                    pair, validate_rich_result(blind, (target_source(pair.text),)),
                    validate_rich_result(comparison, (target_source(pair.text),)))
                policy_reason = check["reason"]
        results[node] = {
            "blind": blind_feature, "compare": _phase(comparison, comparison_state, pair),
            "v1_reason": policy_reason,
        }
    require(observed == set(phases))
    return results


def _phase_label(phase):
    if phase is None or phase.get("state") != "COMPLETED":
        return None
    label = phase.get("class_index")
    return label if type(label) is int else None


def _route_outcome(row, truth, selected, detail):
    """Mutually exclusive routing funnel, separate from policy diagnostics."""
    if not selected:
        require(detail is None)
        return {
            "selected": False, "stage": "NOT_SELECTED",
            "blind_correct": False, "compare_correct": False,
            "any_phase_correct": False, "policy_reason": None,
            "blind_state": "NOT_ROUTED", "compare_state": "NOT_ROUTED",
        }
    require(type(detail) is dict)
    first, second = detail["blind"], detail["compare"]
    require(first["state"] == "COMPLETED"
            and second["state"] in
            ("COMPLETED", "REJECTED", "NOT_PERMITTED_ABSTENTION"))
    b = _phase_label(first)
    c = _phase_label(second)
    bc, cc = b == truth, c == truth
    # Both baseline labels are wrong. Any correct verifier class is a third
    # class, explicitly forbidden by Automated V1's acceptance condition.
    require(truth not in (row.b1.class_index, row.narrative_v0.class_index))
    stage = ("CORRECT_PHASE_BUT_NOT_ADMITTED" if bc or cc else
             "BLIND_ABSTAINED" if first["abstain"] is True else
             "COMPARISON_REJECTED" if second["state"] == "REJECTED" else
             "COMPARISON_ABSTAINED" if second["abstain"] is True else
             "PHASE_CLASS_INCORRECT")
    return {
        "selected": True, "stage": stage,
        "blind_correct": bc, "compare_correct": cc,
        "any_phase_correct": bc or cc,
        "policy_reason": detail["v1_reason"],
        "blind_state": first["state"],
        "compare_state": second["state"],
        "blind_class": b, "compare_class": c,
        "blind_abstain": first["abstain"],
        "compare_abstain": second["abstain"],
        "counter_present": [first["counter_count"], second["counter_count"]],
        "warning_present": [first["auxiliary_warning"], second["auxiliary_warning"]],
        "uncertainty_present": [first["uncertainty"], second["uncertainty"]],
        "topic_digests": [first["topic_digest"], second["topic_digest"]],
    }


def analyze(inputs, truth, historical_features, expanded_phases, frozen, *,
            expanded_vocab=None, expected_joint_wrong=38):
    """Pure diagnostic join; neither input nor vector is modified."""
    validate_freeze(frozen)
    validate_historical_features(historical_features)
    require(expanded_vocab is not None and len(expanded_vocab) == 7
            and all(len(words) == 12 for words in expanded_vocab))
    require(len(truth) == 2708 and
            all(type(t) is int and 0 <= t < 7 for t in truth))
    pairs = tuple(inputs.pairs)
    by_id = {p.node_id: p for p in pairs}
    require(len(pairs) == 140 and len(by_id) == 140)
    old = defaultdict(dict)
    for r in historical_features["rows"]:
        old[r["router"]][r["node_id"]] = r
    require(set(old) == {"r0", "r1_v1"}
            and all(len(r) == 37 for r in old.values()))
    new_selected = set(frozen["selected"])
    require(len(new_selected) == 37 and set(expanded_phases) == new_selected)
    joint = sorted(node for node, p in by_id.items()
                   if p.b1.class_index != truth[node]
                   and p.narrative_v0.class_index != truth[node])
    require(len(joint) == expected_joint_wrong)
    same = sum(by_id[node].b1.class_index == by_id[node].narrative_v0.class_index
               for node in joint)
    if expected_joint_wrong == 38:
        require(same == 36)
    groups = {
        "joint_wrong": joint,
        "other_102": sorted(set(by_id) - set(joint)),
    }
    public = {
        "schema": VERSION,
        "status": "POST_HOC_EXPLORATORY_NOT_INDEPENDENT",
        "source_freeze_summary_sha256": frozen["source_summary_sha256"],
        "source_freeze_context_sha256": frozen["context_sha256"],
        "source_features_sha256": digest(historical_features),
        "joint_wrong_count": len(joint),
        "same_wrong_class_count": same,
        "joint_wrong_kept_by_C": sum(
            p.agrees and min(p.b1.confidence, p.narrative_v0.confidence) >= 80
            for node in joint for p in [by_id[node]]),
        "routing": {}, "features": {},
        "policy_constraint": {
            "correct_third_class_required": len(joint),
            "automated_v1_can_accept_correct_class_for_joint_wrong": 0,
            "reason": "THIRD_CLASS_DIAGNOSTIC_ONLY",
        },
        "training_runs": 0, "provider_calls": 0,
    }
    def hits(text):
        tokens = set(re.findall(r"[a-z]+", text.lower()))
        return tuple(len(tokens.intersection(words)) for words in expanded_vocab)

    rows = []
    for node in joint:
        p = by_id[node]
        original = atlas.semantic_support(p.text)
        expanded_hits = hits(p.text)
        route = {}
        for name in ROUTERS:
            item = expanded_phases.get(node) if name == "expanded_r1_v1" else old[name].get(node)
            out = _route_outcome(p, truth[node], item is not None, item)
            route[name] = out
        nb = p.neighborhood
        rows.append({
            "node_id": node, "ground_truth_class": truth[node],
            "b1_class": p.b1.class_index, "narrative_class": p.narrative_v0.class_index,
            "same_wrong_class": p.agrees,
            "b1_confidence": p.b1.confidence,
            "narrative_confidence": p.narrative_v0.confidence,
            "survives_fusion_C": (p.agrees and
                                  min(p.b1.confidence, p.narrative_v0.confidence) >= 80),
            "text_length_chars": len(p.text),
            "text_word_count": len(p.text.split()),
            "old_atlas_class_hits": list(original),
            "old_atlas_no_match": max(original) == 0,
            "expanded_atlas_class_hits": list(expanded_hits),
            "expanded_atlas_no_match": max(expanded_hits) == 0,
            "degree": nb.degree if nb is not None else None,
            "selected_neighbor_count": len(nb.neighbor_ids) if nb is not None else None,
            "neighbor_connected_pairs": len(nb.connected_pairs) if nb is not None else None,
            "neighbor_disconnected_pairs": len(nb.disconnected_pairs) if nb is not None else None,
            "routed": route,
            "target_text_for_manual_semantic_review": p.text,
        })
    for name in ROUTERS:
        outcomes = [r["routed"][name] for r in rows]
        count = Counter(x["stage"] for x in outcomes)
        selected = [x for x in outcomes if x["selected"]]
        require(len(outcomes) == len(joint) and
                count["CORRECT_PHASE_BUT_NOT_ADMITTED"] ==
                sum(x["any_phase_correct"] for x in selected))
        public["routing"][name] = {
            "selected_joint_wrong": len(selected),
            "selected_wrong_surviving_C": sum(
                r["survives_fusion_C"] for r in rows if r["routed"][name]["selected"]),
            "unselected_joint_wrong": count["NOT_SELECTED"],
            "blind_correct": sum(x["blind_correct"] for x in selected),
            "comparison_correct": sum(x["compare_correct"] for x in selected),
            "any_phase_correct": sum(x["any_phase_correct"] for x in selected),
            "failure_stages": dict(sorted(count.items())),
            "policy_reasons_on_selected": dict(sorted(
                Counter(x["policy_reason"] for x in selected).items())),
            "no_correct_class_admitted_by_automated_v1": True,
        }
    public["ground_truth_class_counts"] = dict(sorted(
        Counter(str(r["ground_truth_class"]) for r in rows).items()))
    public["wrong_label_confusions"] = dict(sorted(
        Counter(f'{r["ground_truth_class"]}->{r["b1_class"]}|{r["narrative_class"]}'
                for r in rows).items()))
    for name, nodes in groups.items():
        ps = [by_id[n] for n in nodes]
        lens = [len(p.text.split()) for p in ps]
        conf = [min(p.b1.confidence, p.narrative_v0.confidence) for p in ps]
        degree = [p.neighborhood.degree for p in ps if p.neighborhood is not None]
        no_match = sum(max(atlas.semantic_support(p.text)) == 0 for p in ps)
        expanded_no_match = sum(max(hits(p.text)) == 0 for p in ps)
        edge_ratio = [
            len(p.neighborhood.connected_pairs) /
            (len(p.neighborhood.connected_pairs) +
             len(p.neighborhood.disconnected_pairs))
            for p in ps if p.neighborhood is not None
            and (len(p.neighborhood.connected_pairs) +
                 len(p.neighborhood.disconnected_pairs)) > 0
        ]
        public["features"][name] = {
            "count": len(ps),
            "median_text_words": median(lens),
            "median_min_baseline_confidence": median(conf),
            "median_graph_degree": median(degree) if degree else None,
            "old_atlas_no_match_count": no_match,
            "expanded_atlas_no_match_count": expanded_no_match,
            "median_recorded_neighbor_connected_pair_ratio":
                median(edge_ratio) if edge_ratio else None,
            "baseline_min_confidence_at_least_80": sum(
                min(p.b1.confidence, p.narrative_v0.confidence) >= 80 for p in ps),
            "baseline_agreement_count": sum(p.agrees for p in ps),
        }
    return public, rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        frozen = PrivateAudit(ROOT / "expanded_atlas_freeze_v1").read(args.freeze_sha256)
        validate_freeze(frozen)
        inputs = load_project_inputs(ROOT / "frozen", ROOT / "authentic")
        config = json.loads(Path("configs/gapgpt_rich_v2_output4096_proposed.json").read_text())
        config["max_spend_usd"] = "1.00"
        saved_atlas = PrivateAudit(ROOT / "expanded_atlas_ablation").read(ATLAS_SHA)
        verified = replay_frozen_run(
            inputs, config, saved_atlas, ROOT / "expanded_atlas_agent3_v1",
            frozen["source_summary_sha256"])
        require(verified == frozen)
        expanded = read_expanded_phases(
            inputs, config, saved_atlas, frozen, ROOT / "expanded_atlas_agent3_v1")
        old_inventory = PrivateAudit(ROOT / "expanded_gcn_inventory_v1").read(OLD_INVENTORY_SHA)
        old_features = PrivateAudit(ROOT / "sara3_correction_features_v1").read(
            old_inventory["source_features_sha256"])
        validate_historical_features(old_features)
        # Both historical router selections must still be compatible with
        # the saved GT-free input cohort, not just 74 well-formed rows.
        from ..sara3.selection import select_router
        for old_router in ("r0", "r1_v1"):
            old_selected = [r["node_id"] for r in old_features["rows"]
                            if r["router"] == old_router]
            require(old_selected == list(select_router(inputs.pairs, 37, old_router))
                    and old_features["sources"][old_router]["selected_ids_sha256"] ==
                    digest(old_selected))
        # Feature integrity / source-specific receipt hashes must match the
        # immutable historical inventory. GT remains unopened at this point.
        truth = _labels_from_original_graph(
            ROOT / "gt_reference" / "cora_random_sbert.pt",
            _expected_graph_names(ROOT / "frozen"))
        public, rows = analyze(
            inputs, truth, old_features, expanded, frozen,
            expanded_vocab=tuple(tuple(words) for words in saved_atlas["expanded"]["vocab"]))
        public["freeze_sha256"] = args.freeze_sha256
        public["old_inventory_sha256"] = OLD_INVENTORY_SHA
        private = {
            "schema": VERSION, "status": public["status"],
            "source_freeze_sha256": args.freeze_sha256,
            "joint_wrong_node_details": rows,
            "no_private_data_in_public_summary": True,
        }
        store = PrivateAudit(ROOT / "joint_baseline_failure_v1")
        private_sha = store.write(private)
        public["private_analysis_sha256"] = private_sha
        public_sha = store.write(public)
        require(store.read(public_sha) == public and store.read(private_sha) == private)
        print(json.dumps({
            "status": public["status"], "aggregate_sha256": public_sha,
            "private_sha256": private_sha,
            "joint_wrong": public["joint_wrong_count"],
            "same_wrong_class": public["same_wrong_class_count"],
            "retained_wrong_C": public["joint_wrong_kept_by_C"],
            "routing": public["routing"], "features": public["features"],
            "policy_constraint": public["policy_constraint"],
            "training_runs": 0, "provider_calls": 0,
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception:
        print('{"status":"FAIL_CLOSED_JOINT_FAILURE_ANALYSIS"}', file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
