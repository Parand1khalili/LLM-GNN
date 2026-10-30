"""Export a pinned, allowlisted atlas. JSON only; no research imports or execution."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent.parent
GRAPH = "9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pinned(path, digest):
    blob = path.read_bytes()
    require(len(blob) < 2_000_000, f"Oversized input: {path.name}")
    require(hashlib.sha256(blob).hexdigest() == digest, f"Hash conflict: {path.name}")
    return json.loads(blob)


def number(value, low, high):
    require(type(value) in (int, float) and math.isfinite(value) and low <= value <= high,
            "Invalid number")
    return value


def build(frozen, authentic, seed_cache, pins):
    sources = []

    def read(group, name):
        row = pins[group][name]
        directory = {"frozen": frozen, "authentic": authentic, "historical": seed_cache,
                     "reports": ROOT / "reports"}[group]
        require(directory is not None, "Historical cache directory is required")
        obj = pinned(directory / row["file"], row["sha256"])
        sources.append({"id": f"{group}/{name}", "sha256": row["sha256"],
                        "status": "REPRODUCED" if group == "reports" else "RECOVERED_EXACT"})
        return obj

    selection = read("frozen", "selection_manifest.json")
    classes = read("frozen", "preparation_receipt.json")["ordered_classes"]
    require(len(classes) == 7 and len(set(classes)) == 7, "Class mapping differs")
    ids = selection["selected_global_node_ids_sorted"]
    require(len(ids) == len(set(ids)) == 140 and selection["graph_sha256"] == GRAPH,
            "Selection identity differs")
    require(selection["ground_truth_accessed"] is False, "GT boundary failed")
    for node in ids:
        require(type(node) is int and 0 <= node < 2708, "Invalid global node ID")
    arms = {arm: read("frozen", name) for arm, name in
            (("b1", "b1_final_predictions.json"), ("narrative", "narrative_v0_final_predictions.json"))}
    prompts = read("authentic", "b1_prompts.json")
    narrative_prompts = read("authentic", "narrative_prompts.json")
    contexts = read("authentic", "neighborhoods.json")["by_target_id"]
    receipt = read("authentic", "prompt_receipt.json")
    require(receipt["no_ground_truth_access"] is True and receipt["graph_sha256"] == GRAPH,
            "Prompt receipt boundary failed")
    require(receipt["outputs_sha256"]["target_diagnostics.json"] ==
            pins["authentic"]["neighborhoods.json"]["sha256"], "Context receipt chain differs")
    for arm, doc in arms.items():
        require(doc["ground_truth_accessed"] is False and doc["ordered_classes"] == classes,
                f"Class/GT mapping differs: {arm}")
        require(set(doc["predictions_by_target_id"]) == set(map(str, ids)), "Annotation IDs differ")
    require(set(contexts) == set(map(str, ids)) == set(prompts["prompts_by_target_id"]),
            "Text/context identities differ")
    nodes = {}
    edges = {}

    def edge(a, b, target):
        require(type(a) is int and type(b) is int and a != b and 0 <= a < 2708 and 0 <= b < 2708,
                "Invalid recorded edge")
        a, b = sorted((a, b))
        edges.setdefault((a, b), set()).add(target)
        nodes.setdefault(a, {"id": a, "target": False})
        nodes.setdefault(b, {"id": b, "target": False})

    for node in ids:
        key = str(node)
        context = contexts[key]
        detail = context["v0_details"]
        require(detail["target_id"] == node and set(detail["identifier_mapping"].values()) ==
                set(context["neighbor_ids"]), "Neighbor mapping differs")
        for arm, prompt_doc, hash_key in (("b1", prompts, "b1_prompt_sha256"),
                                          ("narrative", narrative_prompts, "v0_prompt_sha256")):
            prompt = prompt_doc["prompts_by_target_id"][key]
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
            require(prompt_hash == context[hash_key] == arms[arm]["predictions_by_target_id"][key]["prompt_sha256"],
                    "Target/prompt identity differs")
        prompt = prompts["prompts_by_target_id"][key]
        prefix, separator = "Question: Paper: \n", "\nTask: \n"
        require(prompt.startswith(prefix) and prompt.count(separator) == 1, "Unsupported paper boundary")
        paper = prompt[len(prefix):prompt.index(separator)]
        for neighbor in context["neighbor_ids"]:
            edge(node, neighbor, node)
        for a, b in detail["connected_node_pairs"]:
            require(a in context["neighbor_ids"] and b in context["neighbor_ids"], "Foreign context edge")
            edge(a, b, node)
        annotations = {}
        for arm, doc in arms.items():
            value = doc["predictions_by_target_id"][key]
            require(value["target_id"] == node and value["ground_truth_accessed"] is False and
                    classes[value["class_index"]] == value["prediction"], "Annotation mapping differs")
            annotations[arm] = {
                "label": value["prediction"],
                "confidence": number(value["confidence_percent_before_tensor_cast"], 0, 100),
                "promptHash": value["prompt_sha256"],
                "fallbackCount": value["historical_all_invalid_fallback_count"],
                "samples": [{"index": s["sample_index"], "label": s["first_answer_for_vote"],
                             "confidence": number(s["first_confidence_for_vote"], 0, 100),
                             "valid": s["grammar_valid"], "responseHash": s["source_response_sha256"]}
                            for s in value["primary_samples"]],
            }
        nodes[node] = {"id": node, "target": True, "text": paper[:1200],
                       "textTruncated": len(paper) > 1200, "title": None,
                       "recordedDegree": context["degree"],
                       "selectedNeighbors": context["neighbor_ids"],
                       "representative": context["representative_id"],
                       "narrativeEvidence": detail["narrative_text"], "annotations": annotations}
    # Reject contradictory positive/negative evidence across the recorded partial topology.
    for context in contexts.values():
        for pair in context["v0_details"]["disconnected_node_pairs"]:
            require(tuple(sorted(pair)) not in edges, "Contradictory recorded edge evidence")

    replay = read("reports", "offline_implementation_verification.json")
    require(replay["frozen_replay"]["status"] == "PASS" and
            replay["frozen_replay"]["predictions_matched"] == 280 and
            replay["frozen_replay"]["raw_hashes_verified_by_this_replay"] == 0,
            "Recorded offline replay boundary differs")
    routing = read("reports", "authentic_pilot_verification.json")
    require(routing["status"] == "OFFLINE_FIXTURE_RUN_NOT_SCIENTIFIC_VERIFIER_RESULTS" and
            routing["provider_calls"] == routing["training_runs"] == 0 and routing["GT_decoded"] is False,
            "Offline routing report boundary differs")
    for arm, digest in (("b1", pins["frozen"]["b1_final_predictions.json"]["sha256"]),
                        ("narrative_v0", pins["frozen"]["narrative_v0_final_predictions.json"]["sha256"])):
        require(routing["admission"]["source_sha256"][arm] == digest, "Routing annotation source differs")
    r0 = set(routing["routers"]["r0"]["selected_node_ids"])
    semantic = set(routing["routers"]["semantic"]["selected_node_ids"])
    pilot = set(routing["pilot"]["selection"]["selected_node_ids"])
    require(r0 <= set(ids) and semantic <= set(ids) and pilot <= set(ids), "Routing IDs differ")
    for node in ids:
        nodes[node]["routing"] = {"r0Review": node in r0, "semanticReview": node in semantic,
                                  "pilotSelected": node in pilot}
    inputs = read("historical", "protocol/gt_isolated_training_inputs.json")
    protocol = read("historical", "protocol/protocol.json")
    require(inputs["ordered_classes"] == classes and inputs["no_ground_truth_access"] is True
            and inputs["graph_sha256"] == GRAPH, "Downstream class mapping/GT boundary differs")
    require(protocol["upstream_pins"]["featprop_selection_manifest_sha256"] ==
            pins["frozen"]["selection_manifest.json"]["sha256"], "GCN selection chain differs")
    expected_test = sorted(set(range(2708)) - set(ids))
    require(inputs["common_test_global_node_ids"] == expected_test, "Shared test IDs differ")
    ps_manifests = {cohort: read("frozen", f"ps_{cohort}.json") for cohort in ("primary", "sensitivity")}
    groups = {}
    for name in sorted(pins["historical"]):
        if not name.endswith("/paired_seed_result.json"):
            continue
        value = read("historical", name)
        require(value["graph_sha256"] == GRAPH and value["GT_training_leakage"] is False and
                value["GT_labels_or_per_node_correctness_serialized"] is False and
                value["API"] is False and value["common_test_count"] == 2568 and
                value["epochs_per_fit"] == 30 and value["paired_same_initial_parameters"] is True,
                "Historical run protocol differs")
        cohort = "primary" if value["cohort"] == "original_complete_case" else "sensitivity"
        require(value["cohort"] in ("original_complete_case", "all_node_replacement"), "Unknown cohort")
        ps, weighted = value["PS"], value["weighted_CE"]
        group_id = f'{cohort}-{"wce" if weighted else "ce"}-{"ps" if ps else "nops"}'
        group = groups.setdefault(group_id, {"id": group_id, "cohort": cohort, "weighted": weighted,
                                            "postFilter": ps, "seeds": []})
        seed = value["seed"]
        require(type(seed) is int and seed in range(10), "Invalid GCN seed")
        row = {"seed": seed, "source": f"historical/{name}"}
        for arm, source_arm in (("b1", "b1"), ("narrative", "narrative_v0")):
            result = value["by_arm"][source_arm]
            require(result["seed"] == seed and result["raw_GT_labels_serialized"] is False and
                    result["test_global_node_ids"] == expected_test, "Saved result identity differs")
            predicted = result["test_predicted_class_indices"]
            require(len(predicted) == 2568 and all(type(c) is int and 0 <= c < 7 for c in predicted),
                    "Saved prediction mapping differs")
            row[arm] = number(result["accuracy"], 0, 1) * 100
            require(abs(row[arm] / 100 - result["correct_on_common_test"] / 2568) < 1e-12,
                    "Aggregate/count mismatch")
            group[f"{arm}TrainCount"] = result["train_count"]
            if ps:
                manifest = ps_manifests[cohort]
                require(manifest["GT_or_evaluation_results_used_in_selection"] is False,
                        "PS ground-truth boundary failed")
                labels = manifest["selection_by_arm"][source_arm]["retained_pseudo_class_indices_in_order"]
            else:
                labels = inputs["cohorts"][value["cohort"]]["by_arm"][source_arm]["class_index_in_train_target_order"]
            require(len(labels) == result["train_count"] and all(type(c) is int and c in range(7) for c in labels),
                    "Retained class mapping differs")
            group[f"{arm}ClassCount"] = len(set(labels))
            for target, prediction in zip(expected_test, predicted):
                if target in nodes:
                    saved = nodes[target].setdefault("gcn", {}).setdefault(group_id, {})
                    saved.setdefault(arm, []).append({"seed": seed, "label": classes[prediction]})
        require(abs(row["narrative"] - row["b1"] -
                    value["paired_delta_v0_minus_b1_percentage_points"]) < 1e-10, "Paired delta differs")
        group["seeds"].append(row)
    require(len(groups) == 8, "Expected eight separate FeatProp conditions")
    for group in groups.values():
        group["seeds"].sort(key=lambda r: r["seed"])
        require([r["seed"] for r in group["seeds"]] == list(range(10)), "Missing or duplicate seed")
        group["summary"] = {}
        for arm in ("b1", "narrative"):
            values = [r[arm] for r in group["seeds"]]
            group["summary"][arm] = {"mean": statistics.mean(values), "sd": statistics.pstdev(values)}
        deltas = [r["narrative"] - r["b1"] for r in group["seeds"]]
        group["delta"] = {"mean": statistics.mean(deltas), "sd": statistics.pstdev(deltas)}

    for node in nodes.values():
        for saved in node.get("gcn", {}).values():
            for arm in ("b1", "narrative"):
                values = sorted(saved[arm], key=lambda r: r["seed"])
                require([r["seed"] for r in values] == list(range(10)), "Incomplete saved predictions")
                saved[arm] = [classes.index(r["label"]) for r in values]
    return {"schema": "graphscope.atlas.v2", "snapshotDate": "2026-10-30", "graphHash": GRAPH,
            "classes": classes, "sources": sources, "nodes": sorted(nodes.values(), key=lambda n: n["id"]),
            "edges": [{"source": a, "target": b, "evidenceTargets": sorted(targets)}
                      for (a, b), targets in sorted(edges.items())],
            "experiments": sorted(groups.values(), key=lambda g: g["id"]),
            "boundaries": {"topology": "PARTIAL_RECORDED", "rawParsing": "NOT_RUN",
                           "saraVerifier": "NO_REAL_VERIFIER_RESULT_IN_THIS_EXPORT",
                           "pageRank2": "SOURCE_ARTIFACTS_UNAVAILABLE", "newTrainingRuns": 0}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen", type=Path, default=ROOT / ".local_artifacts/frozen")
    parser.add_argument("--authentic", type=Path, default=ROOT / ".local_artifacts/authentic")
    parser.add_argument("--seed-cache", type=Path, required=True)
    args = parser.parse_args()
    pins = json.loads((HERE / "scripts/source-pins.json").read_text())
    data = build(args.frozen, args.authentic, args.seed_cache, pins)
    blob = (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    destination = HERE / "public/data/atlas.v2.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(blob)
    digest = hashlib.sha256(blob).hexdigest()
    (HERE / "src/data-pin.ts").write_text(f'export const ATLAS_SHA256 = "{digest}";\n', encoding="utf-8")
    print(json.dumps({"nodes": len(data["nodes"]), "edges": len(data["edges"]), "targets": 140,
                      "experiments": len(data["experiments"]), "historicalFits": 160,
                      "bytes": len(blob), "sha256": digest, "modelCalls": 0, "newTraining": 0}))


if __name__ == "__main__":
    main()
