"""Admit authentic frozen paper/context JSON, without opening graph pickle or GT."""
from dataclasses import dataclass
import hashlib
from pathlib import Path

from .frozen import FrozenDataset, load_frozen, read_pinned_json, require
from .evidence import NeighborhoodEvidence
from ..annotation.prompts import FrozenPromptTemplate, SENTINEL
from ..sara2.policy import Annotation, Pair

GRAPH_SHA256 = "9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466"
PINS = {
    "b1_prompts.json": "d7416cb83070b4a5d1ceaee061fe3fb81b6646abcee5cdabe58db33c5b8fdf29",
    "narrative_prompts.json": "cc8b51db94ecf9c8f4d37a8a2ace2746ec0805cb0b3fd44cc8eac54088a7f8ed",
    "neighborhoods.json": "1bd0be9dba2760159f30d72f77dc6036729b2ff10182d220f7673823af95f56e",
    "prompt_receipt.json": "bdd95ba25cacc20efe94567317c1fb747e565218273351d2520a54ca02f2ab19",
    "request_manifest.json": "7a0266129f99ef87fd3e715ab68c015176b48b90bb8b2955c65285aac5492ab1",
}


@dataclass(frozen=True)
class ProjectInputs:
    frozen: FrozenDataset
    pairs: tuple[Pair, ...]
    provenance: tuple[tuple[str, str], ...]


def _hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_project_inputs(frozen_root, authentic_root) -> ProjectInputs:
    frozen_root, authentic_root = Path(frozen_root), Path(authentic_root)
    dataset = load_frozen(frozen_root / "b1_final_predictions.json",
                          frozen_root / "narrative_v0_final_predictions.json",
                          frozen_root / "selection_manifest.json")
    template = FrozenPromptTemplate.from_receipt(frozen_root / "preparation_receipt.json")
    objects = {name: read_pinned_json(authentic_root / name, pin) for name, pin in PINS.items()}
    pairs = _validate_project(dataset, template, objects)
    hashes = tuple(dataset.artifact_hashes) + tuple(PINS.items()) + (("preparation", template.source_sha256),)
    return ProjectInputs(dataset, pairs, hashes)


def _validate_project(dataset, template, objects):
    """Semantic validation after pinned reads; also useful for negative tests."""
    from .frozen import validate_dataset, reject_gt
    validate_dataset(dataset)
    reject_gt(objects)
    receipt = objects["prompt_receipt.json"]
    require(receipt.get("graph_sha256") == GRAPH_SHA256 and receipt.get("targets") == 140
            and receipt.get("no_ground_truth_access") is True
            and receipt.get("no_api") is True and receipt.get("no_training") is True,
            "Frozen prompt source contract differs")
    expected = {"b1/complete_prompts.json": PINS["b1_prompts.json"],
                "narrative_v0/complete_prompts.json": PINS["narrative_prompts.json"],
                "target_diagnostics.json": PINS["neighborhoods.json"],
                "request_manifest.json": PINS["request_manifest.json"]}
    require(all(receipt["outputs_sha256"].get(k) == v for k, v in expected.items()), "Prompt receipt chain differs")
    order = list(dataset.target_ids)
    ids = {str(t) for t in order}
    for name, arm in (("b1_prompts.json", "b1"), ("narrative_prompts.json", "narrative_v0")):
        obj = objects[name]
        require(obj.get("arm") == arm and obj.get("target_ids_in_manifest_order") == order
                and set(obj.get("prompts_by_target_id", {})) == ids, "Prompt node alignment differs")
    neighborhoods = objects["neighborhoods.json"]
    require(neighborhoods.get("target_ids_in_manifest_order") == order
            and set(neighborhoods.get("by_target_id", {})) == ids, "Neighborhood node alignment differs")
    manifest = objects["request_manifest.json"]
    rows = manifest.get("requests")
    require(manifest.get("request_count") == 840 and type(rows) is list and len(rows) == 840,
            "Prompt request count differs")
    references = {}
    for r in rows:
        key = r["target_id"], r["arm"], r["sample_index"]
        require(type(r["target_id"]) is int and type(r["sample_index"]) is int
                and key not in references, "Duplicate/invalid prompt reference")
        require(r.get("model") == "gpt-6-luna" and r.get("n") == 1
                and r.get("temperature") == 0.7, "Historical provider request settings differ")
        references[key] = r["prompt_sha256"]
    require(set(references) == {(t, a, s) for t in order for a in ("b1", "narrative_v0") for s in range(3)},
            "Incomplete prompt identities")
    predictions = {(p.target_id, p.arm): p for p in dataset.predictions}
    prefix, suffix = template.text.split(SENTINEL)
    pairs = []
    for node in order:
        prompts = {a: objects[name]["prompts_by_target_id"][str(node)] for a, name in
                   (("b1", "b1_prompts.json"), ("narrative_v0", "narrative_prompts.json"))}
        for arm, prompt in prompts.items():
            require(type(prompt) is str and prompt.startswith(prefix) and prompt.endswith(suffix),
                    "Historical wrapper differs")
            pin = _hash(prompt)
            require(all(references[(node, arm, s)] == pin and
                        predictions[(node, arm)].samples[s].prompt_sha256 == pin for s in range(3)),
                    "Frozen prediction/request prompt hash differs")
        text = prompts["b1"][len(prefix):len(prompts["b1"]) - len(suffix) if suffix else None]
        require(bool(text.strip()) and template.wrap(text) == prompts["b1"], "Target text extraction differs")
        body = prompts["narrative_v0"][len(prefix):len(prompts["narrative_v0"]) - len(suffix) if suffix else None]
        attachment = text.rstrip() + "\n\n"
        require(body.startswith(attachment), "Narrative target attachment differs")
        context = body[len(attachment):]
        d = neighborhoods["by_target_id"][str(node)]
        detail = d["v0_details"]
        require(d["b1_prompt_sha256"] == _hash(prompts["b1"])
                and d["v0_prompt_sha256"] == _hash(prompts["narrative_v0"]), "Neighborhood prompt hash differs")
        neighbors = tuple(d["neighbor_ids"])
        require(detail["target_id"] == node and type(detail["target_id"]) is int
                and detail["selected_neighbor_count"] == len(neighbors)
                and detail["identifier_mapping"] == {f"N{i+1}": n for i, n in enumerate(neighbors)}
                and detail["original_prompt_preserved"] is True, "Neighborhood identities differ")
        block, offset = detail["inserted_block"], detail["insertion_offset"]
        require(type(offset) is int and 0 <= offset <= len(context) and type(block) is str
                and block.strip() and context[offset:offset+len(block)] == block,
                "Recorded Narrative topology differs")
        require(d["representative_id"] == neighbors[0]
                and type(d["support_count"]) is int and 1 <= d["support_count"] <= len(neighbors)
                and 0 < d["consensus_tokens"] <= 256
                and d["v0_structural_tokens"] == detail["new_structural_tokens"] <= 320,
                "Recorded context bounds differ")
        connected = tuple(sorted(tuple(sorted(p)) for p in detail["connected_node_pairs"]))
        disconnected = tuple(sorted(tuple(sorted(p)) for p in detail["disconnected_node_pairs"]))
        evidence = NeighborhoodEvidence(node, neighbors, d["representative_id"], d["degree"],
                                         connected, disconnected, context, GRAPH_SHA256, PINS["neighborhoods.json"])
        a, b = predictions[(node, "b1")], predictions[(node, "narrative_v0")]
        pairs.append(Pair(Annotation(node, a.class_index, a.confidence_percent),
                          Annotation(node, b.class_index, b.confidence_percent), text, evidence))
    return tuple(pairs)
