"""Isolated matched Cora: offline plan, explicitly live infer, offline score.

Default plan never initializes a client, reads credentials, or writes files.
Inference follows the frozen 2,100-slot order, with no repairs or retries.
An intent without a settled response is ambiguous and is NEVER resent. After
external review, --resume --abandon-request ID --review-note NOTE may terminalize
an ambiguous slot as failed, without authorizing a replacement request.
Only score loads the trusted graph and accesses ground truth. No GCN is run.
"""

import argparse
import ast
import asyncio
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import itertools
import json
import math
import os
from pathlib import Path
import sys
import time


ARMS = ("b1", "consensus", "narrative_v0", "narrative_v1", "narrative_v2")
CLASSES = ["rule_learning", "neural_networks", "case_based", "genetic_algorithms",
           "theory", "reinforcement_learning", "probabilistic_methods"]
CAPS = dict(zip(ARMS, (0, 256, 320, 416, 480)))
MODEL = "gpt-6-luna"
ENDPOINT = "https://api.gapapi.com/v1/chat/completions"
CONFIRMATION = "RUN_MATCHED_CORA_2100_PRIMARY_CALLS"
PRIMARY_LIMIT = 2100
PER_ARM_LIMIT = 420
TRANSPORT_VERSION = "3.8.5"
PREP_SCRIPT_HASH = "b95446357cc1d2b27e261f6c5dc399eb3eed359a920c114c26df85fc857e3ac8"
PREP_RECEIPT_HASH = "fb6777e8dec547b2aee5ca664ffa566f9148a944c7ee6065072df9fb1b4ad4ab"
REQUEST_MANIFEST_HASH = "8101dd7ad6d050cce8f890d259e8b55ae220f51bb2b438a29e3ca73c679d19c5"
REFERENCE_HASH = "b67684075146731246c4a9c4b2927056647d4b08f3679ed4e0b5c62cf111b928"
ASYNC_SOURCE_HASH = "02847012267126b9a4afba5e345ff8b22df6338facedc8b5bf3ed7e9d56803a9"
GRAPH_HASH = "9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466"


class RunnerError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise RunnerError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "Duplicate JSON key.")
        result[key] = value
    return result


def decode(payload):
    return json.loads(payload, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(RunnerError("Nonfinite JSON.")))


def load(path):
    return decode(path.read_bytes())


def verified(path, expected):
    require(path.is_file() and not path.is_symlink(), f"Missing/unsafe input: {path.name}")
    payload = path.read_bytes()
    require(sha(payload) == expected, f"SHA-256 mismatch: {path.name}")
    return payload


def within(path, parent):
    return path == parent or parent in path.parents


def offline_guard(event, arguments):
    if event.startswith("socket."):
        raise RunnerError("Network access is forbidden in offline modes.")


def remove_block(text, offset, block):
    require(type(offset) is int and isinstance(block, str) and 0 <= offset <= len(text)
            and offset + len(block) <= len(text) and text[offset:offset + len(block)] == block,
            "Invalid preservation metadata.")
    return text[:offset] + text[offset + len(block):]


def literal_assignment(payload, name):
    tree = ast.parse(payload.decode("utf-8-sig"))
    values = [node.value for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
    require(len(values) == 1, "Ambiguous pinned source constant.")
    return ast.literal_eval(values[0])


def validate_inputs(root, args):
    """Verify stored prompts, never regenerate them or import project modules."""
    preparation_source = verified(root / "experiments/matched_cora/prepare_matched_prompts.py", PREP_SCRIPT_HASH)
    pins = literal_assignment(preparation_source, "PINNED_HASHES")
    receipt_bytes = verified(args.prep_dir / "preparation_receipt.json", PREP_RECEIPT_HASH)
    receipt = decode(receipt_bytes)
    require((args.prep_dir / "preparation_receipt.sha256").read_text(encoding="ascii")
            == PREP_RECEIPT_HASH + "  preparation_receipt.json\n", "Preparation receipt sidecar differs.")
    require(receipt["schema"] == "matched_cora_five_arm_preparation_v1"
            and receipt["stage"] == "offline_preparation_only" and receipt["arms"] == list(ARMS)
            and receipt["structural_caps"] == CAPS and receipt["ordered_classes"] == CLASSES
            and receipt["class_index_mapping"] == {str(i): name for i, name in enumerate(CLASSES)}
            and receipt["expected_pinned_hashes"] == pins, "Preparation contract differs.")
    require(all(receipt[field] is False for field in ("inference_performed", "evaluation_performed",
            "ground_truth_accessed", "target_or_neighbor_selection_performed", "existing_predictions_accessed")),
            "Unexpected preparation activity flags.")
    relative = {
        "manifest": "experiments/manifests/m1_prompt_variants_b256.json",
        "v0": "src/structure/narrative_topology_v0.py", "v1": "src/structure/narrative_topology_v1.py",
        "v2": "src/structure/narrative_topology_v2.py",
        "frozen_v1_prompts": "experiments/narrative_v1/runs/offline_prep_001/complete_prompts.json",
        "preparation_helpers": "experiments/narrative_v1/prepare_v1_prompts.py",
        "llm": "src/llm.py", "config": "src/openail/config.py", "utils": "src/openail/utils.py",
        "token_counter": "src/structure/prompt_builder.py", "adjacency_helper": "src/structure/selector.py",
        "structure_init": "src/structure/__init__.py",
        "matched_preparation_script": "experiments/matched_cora/prepare_matched_prompts.py",
    }
    require(set(receipt["source_and_input_files"]) == set(relative) | {"graph"}, "Unexpected source provenance keys.")
    source_bytes, source_hashes = {}, {}
    for name, path in [(key, root / value) for key, value in relative.items()] + [("graph", args.graph_file)]:
        expected = PREP_SCRIPT_HASH if name == "matched_preparation_script" else pins[name]
        require(receipt["source_and_input_files"][name]["sha256"] == expected, "Preparation source provenance differs.")
        payload = verified(path, expected)
        if name != "graph":
            source_bytes[name] = payload
        source_hashes[name] = expected
    reference_path = root / "experiments/narrative_v1/run_v1.py"
    reference_bytes = verified(reference_path, REFERENCE_HASH)
    verified(root / "src/openail/asyncapi.py", ASYNC_SOURCE_HASH)
    source_hashes.update(reference_runner=REFERENCE_HASH, async_transport=ASYNC_SOURCE_HASH,
                         runner=sha(Path(__file__).read_bytes()))
    # This pinned module imports only stdlib and defines functions at top level.
    # Its __main__ guard is false; no inference, scoring, credentials or caches.
    reference = {"__name__": "_matched_reference_only", "__file__": str(reference_path)}
    exec(compile(reference_bytes, str(reference_path), "exec"), reference)
    require(reference["MODEL"] == MODEL and reference["ENDPOINT"] == ENDPOINT
            and reference["CLASSES"] == CLASSES and reference["RETRY_LIMIT"] == 0, "Reference protocol differs.")
    files = receipt["output_file_sha256"]
    expected_files = {f"{arm}/{name}.json" for arm in ARMS for name in ("complete_prompts", "target_diagnostics")}
    require(set(files) == expected_files | {"request_manifest.json"}
            and files["request_manifest.json"] == REQUEST_MANIFEST_HASH, "Preparation file inventory differs.")
    actual = set()
    for path in args.prep_dir.rglob("*"):
        require(not path.is_symlink(), "Symlink in preparation.")
        if path.is_file():
            actual.add(path.relative_to(args.prep_dir).as_posix())
    require(actual == set(files) | {"preparation_receipt.json", "preparation_receipt.sha256"},
            "Missing/additional preparation files.")
    objects = {name: decode(verified(args.prep_dir / name, digest)) for name, digest in files.items()}
    prep_hashes = dict(files, **{"preparation_receipt.json": PREP_RECEIPT_HASH,
                               "preparation_receipt.sha256": sha((args.prep_dir / "preparation_receipt.sha256").read_bytes())})
    manifest = decode(source_bytes["manifest"])
    targets = manifest["target_ids"]
    require(len(targets) == len(set(targets)) == 140
            and all(type(node) is int and 0 <= node < 2708 for node in targets)
            and receipt["target_ids_in_manifest_order"] == targets and receipt["target_count"] == 140
            and receipt["num_graph_nodes"] == 2708, "Invalid frozen target coverage/order.")
    keys = {str(node) for node in targets}
    require(set(manifest["targets"]) == keys, "Historical target coverage differs.")
    wrapper = receipt["historical_wrapper"]
    require(wrapper["ordered_class_names"] == CLASSES and wrapper["need_tasks"] is False
            and wrapper["k"] == 3 and wrapper["dataset_name"] == "cora", "Wrapper metadata differs.")
    tree = ast.parse(source_bytes["llm"].decode("utf-8-sig"))
    experiment = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Experiment"]
    require(len(experiment) == 1, "Ambiguous historical Experiment.")
    for body, name, field in ((tree.body, "zero_shot_prompt", "zero_shot_function_source"),
                              (experiment[0].body, "topk_confidence", "topk_method_source")):
        require(ast.get_source_segment(source_bytes["llm"].decode("utf-8-sig"), reference["function"](body, name))
                == wrapper[field], "Historical wrapper source differs.")
    sentinel = "<TARGET_OR_TARGET_PLUS_STRUCTURAL_CONTEXT>"
    template = wrapper["exact_complete_template_with_sentinel"]
    require(template.count(sentinel) == 1, "Invalid wrapper template.")
    prefix, suffix = template.split(sentinel)
    frozen_v1 = decode(source_bytes["frozen_v1_prompts"])
    require(frozen_v1["target_ids_in_manifest_order"] == targets, "Earlier v1 target order differs.")
    prompts, details, counts, structural_counts = {}, {}, {}, {}
    interpretation = literal_assignment(source_bytes["v2"], "EVIDENCE_INTERPRETATION")
    for arm in ARMS:
        prompt_file, diagnostic_file = objects[f"{arm}/complete_prompts.json"], objects[f"{arm}/target_diagnostics.json"]
        for obj in (prompt_file, diagnostic_file):
            require(obj["arm"] == arm and obj["target_ids_in_manifest_order"] == targets
                    and obj["target_count"] == 140 and obj["num_graph_nodes"] == 2708
                    and obj["ordered_classes"] == CLASSES, "Arm metadata differs.")
        prompts[arm], details[arm] = prompt_file["prompts_by_target_id"], diagnostic_file["diagnostics_by_target_id"]
        require(set(prompts[arm]) == set(details[arm]) == keys, "Arm global-ID coverage differs.")
        counts[arm], structural_counts[arm] = [], []
        for target in targets:
            key = str(target)
            prompt, diagnostic, original = prompts[arm][key], details[arm][key], manifest["targets"][key]
            context = diagnostic["structural_prompt"]
            require(isinstance(prompt, str) and isinstance(context, str)
                    and sha(prompt.encode("utf-8")) == diagnostic["complete_prompt_sha256"]
                    and sha(context.encode("utf-8")) == diagnostic["structural_prompt_sha256"], "Prompt hash differs.")
            require(diagnostic["target_id"] == target and diagnostic["arm"] == arm
                    and diagnostic["neighbor_ids_in_frozen_order"] == original["neighbor_ids"]
                    and diagnostic["representative_id"] == original["representative_id"]
                    and diagnostic["target_text_sha256"] == sha(original["target_text"].encode("utf-8"))
                    and diagnostic["historical_consensus_sha256"] == sha(original["variants"]["consensus"]["prompt"].encode("utf-8")),
                    "Frozen target/neighbor provenance differs.")
            attached = original["target_text"] if arm == "b1" else original["target_text"].rstrip() + "\n\n" + context
            require(prompt.encode("utf-8") == (prefix + attached + suffix).encode("utf-8"), "Target-only/attachment/wrapper parity failed.")
            structural, total = diagnostic["structural_tokens"], diagnostic["complete_classification_prompt_tokens"]
            require(type(structural) is int and 0 <= structural <= CAPS[arm] == diagnostic["structural_cap"]
                    and type(total) is int and total > 0, "Stored token counts/caps differ.")
            counts[arm].append(total)
            structural_counts[arm].append(structural)
            if arm == "b1":
                require(context == "" and diagnostic["augmentation_diagnostics"] is None and structural == 0, "B1 contains context.")
            if arm == "consensus":
                require(context == original["variants"]["consensus"]["prompt"]
                        and structural == original["variants"]["consensus"]["structural_tokens"], "Historical Consensus changed.")
            if arm == "narrative_v1":
                require(prompt.encode("utf-8") == frozen_v1["prompts_by_target_id"][key].encode("utf-8"), "Frozen v1 parity failed.")
    for target in targets:
        key = str(target)
        d0, d1, d2 = [details[arm][key]["augmentation_diagnostics"] for arm in ARMS[2:]]
        contexts = {arm: details[arm][key]["structural_prompt"] for arm in ARMS}
        require(d1["v0_diagnostics"] == d0 and d2["v1_diagnostics"] == d1, "Nested preservation provenance differs.")
        require(remove_block(contexts["narrative_v2"], d2["insertion_offset"], d2["inserted_block"]) == contexts["narrative_v1"]
                and d2["inserted_block"] == "\n\n" + interpretation
                and remove_block(contexts["narrative_v1"], d1["excerpt_insertion_offset"], d1["excerpt_block"]) == contexts["narrative_v0"]
                and remove_block(contexts["narrative_v0"], d0["insertion_offset"], d0["inserted_block"]) == contexts["consensus"],
                "Historical UTF-8 preservation chain failed.")
        original = manifest["targets"][key]
        ordered = [original["representative_id"]] + [n for n in original["neighbor_ids"] if n != original["representative_id"]]
        identities = {f"N{i+1}": node for i, node in enumerate(ordered)}
        require(d0["identifier_mapping"] == d1["identifier_mapping"] == identities, "Neighbor identities differ.")
        for entry in d1["excerpt_records"]:
            require(entry["identifier"] != "N1" and identities[entry["identifier"]] == entry["node_id"]
                    and entry["excerpt"] == d1["excerpts"][entry["identifier"]]
                    and len(entry["excerpt"].split()) == entry["word_count"] <= 15, "Excerpt identity/count differs.")
    request_manifest = objects["request_manifest.json"]
    require(request_manifest["arm_order"] == list(ARMS) and request_manifest["request_count"] == PRIMARY_LIMIT
            and request_manifest["samples_per_target_per_arm"] == 3 and request_manifest["completions_per_request"] == 1
            and request_manifest["order"] == "target manifest order, then sample 0/1/2, then five-arm order", "Request order contract differs.")
    requests = request_manifest["requests"]
    require(len(requests) == PRIMARY_LIMIT, "Expected exactly 2,100 slots.")
    for index, (target, sample, arm) in enumerate(itertools.product(targets, range(3), ARMS)):
        require(requests[index] == {"request_index": index, "arm": arm, "target_id": target, "sample_index": sample,
                "prompt_file": f"{arm}/complete_prompts.json", "prompt_key": str(target),
                "prompt_sha256": details[arm][str(target)]["complete_prompt_sha256"],
                "input_content_tokens": details[arm][str(target)]["complete_classification_prompt_tokens"]},
                "Precommitted request manifest slot/order differs.")
    require(Counter(item["arm"] for item in requests) == {arm: PER_ARM_LIMIT for arm in ARMS}, "Per-arm slot counts differ.")
    volumes = {arm: sum(counts[arm]) * 3 for arm in ARMS}
    require(all(receipt["arm_token_summaries"][arm]["input_tokens_for_three_samples"] == volumes[arm] for arm in ARMS)
            and receipt["total_input_tokens_for_three_samples_all_arms"] == sum(volumes.values())
            and receipt["planned_primary_requests_total"] == PRIMARY_LIMIT, "Receipt token/call accounting differs.")
    return {"ref": reference, "receipt": receipt, "source_bytes": source_bytes, "source_hashes": source_hashes,
            "preparation_hashes": prep_hashes, "targets": targets, "prompts": prompts, "details": details,
            "requests": requests, "counts": counts, "volumes": volumes}


def request_id(slot):
    return f"primary_{slot['request_index']:04d}_{slot['arm']}_{slot['target_id']}_{slot['sample_index']}"


def payload(context, slot):
    prompt = context["prompts"][slot["arm"]][str(slot["target_id"])]
    return {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7, "n": 1}


def configuration(args, context):
    return {"schema": "matched_cora_run_v1", "model": MODEL, "endpoint": ENDPOINT, "temperature": 0.7,
            "samples_per_target": 3, "completions_per_request": 1, "message_roles": ["user"],
            "top_p": "omitted", "max_tokens": "omitted", "provider_seed": "omitted",
            "arms": list(ARMS), "primary_call_limit": PRIMARY_LIMIT, "per_arm_primary_limit": PER_ARM_LIMIT,
            "repair_call_limit": 0, "retry_limit": 0, "transport_version": TRANSPORT_VERSION,
            "transport": "Pinned run_v1.post_once: aiohttp ClientSession.post, Bearer header, JSON, no redirects",
            "timeout_seconds": args.timeout, "interval_seconds": args.interval,
            "api_key_environment_variable": args.api_key_env, "ordered_classes": CLASSES,
            "target_ids_in_manifest_order": context["targets"], "source_hashes": context["source_hashes"],
            "preparation_hashes": context["preparation_hashes"], "request_manifest_sha256": REQUEST_MANIFEST_HASH,
            "repair_policy_difference": "Zero repairs differs from historical automatic LLM correction.",
            "retry_policy_difference": "Zero automatic retries; uncertain requests require external review.",
            "failure_policy": "Missing/abandoned completion prevents a partial-sample vote; scoring counts failures as incorrect.",
            "historical_local_fallbacks": "Preserved, including edit-distance class normalization and all-invalid fallback; recorded explicitly.",
            "ground_truth_accessed": False}


def check_configuration(config, context):
    require(config["schema"] == "matched_cora_run_v1" and config["model"] == MODEL and config["endpoint"] == ENDPOINT
            and config["temperature"] == 0.7 and config["samples_per_target"] == 3 and config["completions_per_request"] == 1
            and config["message_roles"] == ["user"] and config["primary_call_limit"] == PRIMARY_LIMIT
            and config["per_arm_primary_limit"] == PER_ARM_LIMIT and config["repair_call_limit"] == config["retry_limit"] == 0
            and config["transport_version"] == TRANSPORT_VERSION and config["arms"] == list(ARMS)
            and config["target_ids_in_manifest_order"] == context["targets"] and config["ordered_classes"] == CLASSES
            and config["source_hashes"] == context["source_hashes"] and config["preparation_hashes"] == context["preparation_hashes"]
            and config["request_manifest_sha256"] == REQUEST_MANIFEST_HASH and config["ground_truth_accessed"] is False,
            "Run protocol/provenance differs.")
    require(all(config[name] == "omitted" for name in ("top_p", "max_tokens", "provider_seed"))
            and math.isfinite(config["timeout_seconds"]) and config["timeout_seconds"] > 0
            and math.isfinite(config["interval_seconds"]) and config["interval_seconds"] >= 0,
            "Recorded common generation/timeout settings differ.")


def owned_run(directory, context, expected=None):
    initial = load(directory / "run_receipt.json")
    check_configuration(initial["configuration"], context)
    require(initial["installed_aiohttp_version"] == TRANSPORT_VERSION, "Recorded runtime transport version differs.")
    if expected is not None:
        require(initial["configuration"] == expected, "Resume configuration differs; use original timeout/interval/environment-variable name.")
    return initial


def identity(context, slot):
    request = payload(context, slot)
    return dict(slot, request_id=request_id(slot), kind="primary", endpoint=ENDPOINT, request=request,
                request_json_sha256=sha(json.dumps(request).encode("utf-8")))


def inspect_slot(directory, context, slot):
    path = directory / "requests" / request_id(slot)
    if not path.exists():
        return None
    require(path.is_dir() and not path.is_symlink(), "Unsafe request journal directory.")
    allowed = {"intent.json", "response.json", "ambiguous.json", "abandoned.json", "parsing.json"}
    require(all(item.is_file() and not item.is_symlink() and item.name in allowed for item in path.iterdir()),
            "Unexpected/temporary request journal file; manual review required.")
    if not (path / "intent.json").exists():
        require(not list(path.iterdir()), "Journal contains evidence without an intent.")
        return None
    intent = load(path / "intent.json")
    require(all(intent.get(key) == value for key, value in identity(context, slot).items()), "Intent identity/payload differs.")
    response_path = path / "response.json"
    state = dict(slot, request_id=request_id(slot), kind="primary", status="ambiguous", response_file_sha256=None)
    if response_path.exists():
        response = load(response_path)
        require(all(response.get(key) == value for key, value in slot.items()) and response["request_id"] == request_id(slot),
                "Response slot identity differs.")
        body = base64.b64decode(response["raw_body_base64"], validate=True)
        require(sha(body) == response["persisted_body_sha256"], "Raw response hash differs.")
        state["response_file_sha256"] = sha(response_path.read_bytes())
        if response["complete"] and type(response["http_status"]) is int and response["http_status"] != 408 and response["http_status"] < 500:
            state["status"] = "response_persisted"
    if (path / "abandoned.json").exists():
        review = load(path / "abandoned.json")
        require(review["request_id"] == request_id(slot) and review["action"] == "abandon_without_resend"
                and review["replacement_request_authorized"] is False, "Invalid manual review record.")
        state["status"] = "manually_abandoned"
    return state


def inventory(directory, context):
    requests = directory / "requests"
    require(requests.is_dir() and not requests.is_symlink(), "Missing/unsafe requests directory.")
    expected = {request_id(slot) for slot in context["requests"]}
    require(all(path.name in expected and path.is_dir() and not path.is_symlink() for path in requests.iterdir()),
            "Unexpected request slot; repairs/replacement requests are forbidden.")
    states = [state for slot in context["requests"] if (state := inspect_slot(directory, context, slot)) is not None]
    require([state["request_index"] for state in states] == list(range(len(states))), "Journal is not a prefix of committed order.")
    require(not any(state["status"] == "ambiguous" for state in states[:-1]), "A later request followed an unresolved ambiguous slot.")
    require(len(states) <= PRIMARY_LIMIT and all(count <= PER_ARM_LIMIT for count in Counter(s["arm"] for s in states).values()),
            "Request hard limit exceeded.")
    return states


def write(context, path, value, same=False):
    context["ref"]["write_same_or_new" if same else "write_new"](path, value)


def sample_record(context, parser, directory, slot, state):
    path = directory / "requests" / request_id(slot)
    require(state["status"] != "ambiguous", "Cannot parse an ambiguous outcome.")
    response = None if state["status"] == "manually_abandoned" else load(path / "response.json")
    text, error = context["ref"]["content"](response)
    record = dict(slot, request_id=request_id(slot), response_file_sha256=state["response_file_sha256"],
                  response_error=error, grammar=context["ref"]["grammar"](parser, text))
    record.update(context["ref"]["individual_parse"](parser, text))
    write(context, path / "parsing.json", record, same=True)
    return record, text


def target_record(context, parser, directory, arm, target, states):
    slots = [context["requests"][context["slot_indices"][(arm, target, sample)]] for sample in range(3)]
    samples_and_text = [sample_record(context, parser, directory, slot, states[slot["request_index"]]) for slot in slots]
    samples, texts = [x[0] for x in samples_and_text], [x[1] for x in samples_and_text]
    result = {"arm": arm, "target_id": target, "prompt_sha256": slots[0]["prompt_sha256"],
              "primary_samples": samples, "repair": {"applied": False, "budget": 0}, "retries": 0,
              "prediction": None, "class_index": None, "confidence_percent_before_tensor_cast": None,
              "failure": None, "ground_truth_accessed": False}
    if any(text is None for text in texts):
        result["failure"] = "one_or_more_primary_requests_failed_or_abandoned; no partial-sample vote"
        return result
    try:
        # Exactly the reference's local three-sample parsing/vote. No correction
        # function is called. The historical consistency branch is common to ALL arms.
        parsed = parser["retrieve_multiple_answers"](parser["self"], [texts], None, 3)[0]
        require(len(parsed) == 3, "Historical parser sample count differs.")
        result["parsed_samples"] = [
            {"sample_index": i, "grammar": context["ref"]["grammar"](parser, text), "parsed_answers": answers,
             "first_answer": answers[0][0] if answers else None,
             "first_confidence": answers[0][1] if answers else None,
             "first_class_index": CLASSES.index(answers[0][0]) if answers and answers[0][0] in CLASSES else None}
            for i, (text, answers) in enumerate(zip(texts, parsed))]
        predictions, confidence, fallback = parser["vote"]([parsed], CLASSES, [0])
        require(len(predictions) == len(confidence) == 1 and type(predictions[0]) is int
                and 0 <= predictions[0] < 7 and math.isfinite(float(confidence[0])), "Invalid historical vote.")
        result.update(prediction=CLASSES[predictions[0]], class_index=predictions[0],
                      confidence_percent_before_tensor_cast=confidence[0], historical_all_invalid_fallback_count=fallback)
    except Exception as exc:
        result["failure"] = "historical_parser_or_vote_failed_" + type(exc).__name__
    return result


def finalize(directory, context, config, initial, states, parser):
    require(len(states) == PRIMARY_LIMIT and all(s["status"] != "ambiguous" for s in states), "Cannot freeze incomplete/unresolved slots.")
    summary = {}
    for arm in ARMS:
        records = {}
        for target in context["targets"]:
            result = target_record(context, parser, directory, arm, target, states)
            write(context, directory / arm / "targets" / f"{target}.json", result, same=True)
            records[str(target)] = result
        write(context, directory / arm / "final_predictions.json", {
            "arm": arm, "target_ids_in_manifest_order": context["targets"], "ordered_classes": CLASSES,
            "predictions_by_target_id": records, "ground_truth_accessed": False}, same=True)
        summary[arm] = {"primary_slots_reserved": sum(s["arm"] == arm for s in states),
                        "responses_persisted": sum(s["arm"] == arm and s["response_file_sha256"] is not None for s in states),
                        "coverage": sum(r["class_index"] is not None for r in records.values()),
                        "failures": sum(r["class_index"] is None for r in records.values()),
                        "literal_parse_failures": sum(bool(s.get("literal_parse_failure")) for r in records.values() for s in r["primary_samples"]),
                        "grammar_failures": sum(not s["grammar"][0] for r in records.values() for s in r["primary_samples"]),
                        "repairs": 0, "retries": 0}
    write(context, directory / "sample_status.json", {"samples": states, "repair_count": 0, "retry_count": 0}, same=True)
    final_path = directory / "final_run_receipt.json"
    finished = load(final_path)["finished_utc"] if final_path.exists() else now()
    write(context, final_path, {"configuration": config, "started_utc": initial["created_utc"], "finished_utc": finished,
          "primary_calls_reserved": len(states), "repair_calls": 0, "retries": 0, "arms": summary,
          "manually_abandoned_requests": [s["request_id"] for s in states if s["status"] == "manually_abandoned"],
          "ground_truth_accessed": False, "scoring_performed": False}, same=True)
    evidence = {}
    for path in sorted(directory.rglob("*")):
        require(not path.is_symlink() and not path.name.startswith(".tmp-"), "Unsafe/temporary evidence requires manual review.")
        if path.is_file() and path.name not in {".runner.lock", "freeze_receipt.json"}:
            evidence[path.relative_to(directory).as_posix()] = sha(path.read_bytes())
    write(context, directory / "freeze_receipt.json", {"schema": "matched_cora_frozen_predictions_v1",
          "frozen_utc": finished, "run_files_sha256": evidence, "runner_sha256": config["source_hashes"]["runner"],
          "request_manifest_sha256": REQUEST_MANIFEST_HASH, "ground_truth_accessed_before_freeze": False})


def verify_frozen(directory, context):
    initial = owned_run(directory, context)
    freeze = load(directory / "freeze_receipt.json")
    require(freeze["schema"] == "matched_cora_frozen_predictions_v1" and freeze["ground_truth_accessed_before_freeze"] is False
            and freeze["runner_sha256"] == context["source_hashes"]["runner"]
            and freeze["request_manifest_sha256"] == REQUEST_MANIFEST_HASH, "Freeze provenance differs.")
    evidence, actual = freeze["run_files_sha256"], set()
    for path in directory.rglob("*"):
        require(not path.is_symlink(), "Symlink in frozen run.")
        if path.is_file() and path.name not in {".runner.lock", "freeze_receipt.json"}:
            actual.add(path.relative_to(directory).as_posix())
    require(actual == set(evidence), "Frozen run evidence inventory differs.")
    for relative, expected in evidence.items():
        path = (directory / relative).resolve()
        require(within(path, directory), "Unsafe freeze evidence path.")
        verified(path, expected)
    states = inventory(directory, context)
    require(len(states) == PRIMARY_LIMIT and all(s["status"] != "ambiguous" for s in states), "Frozen slots incomplete.")
    required = {"run_receipt.json", "sample_status.json", "final_run_receipt.json"}
    required.update(f"{arm}/final_predictions.json" for arm in ARMS)
    require(required <= set(evidence), "Missing frozen outputs.")
    require(load(directory / "sample_status.json") == {"samples": states, "repair_count": 0, "retry_count": 0}, "Frozen sample status differs.")
    predictions = {}
    for arm in ARMS:
        obj = load(directory / arm / "final_predictions.json")
        require(obj["arm"] == arm and obj["target_ids_in_manifest_order"] == context["targets"]
                and obj["ordered_classes"] == CLASSES and obj["ground_truth_accessed"] is False, "Frozen arm metadata differs.")
        records = obj["predictions_by_target_id"]
        require(set(records) == {str(n) for n in context["targets"]}, "Frozen target coverage differs.")
        for target in context["targets"]:
            record = records[str(target)]
            require(record == load(directory / arm / "targets" / f"{target}.json")
                    and record["arm"] == arm and record["target_id"] == target
                    and record["prompt_sha256"] == context["details"][arm][str(target)]["complete_prompt_sha256"]
                    and record["repair"]["applied"] is False and record["retries"] == 0
                    and record["ground_truth_accessed"] is False, "Frozen prediction provenance differs.")
            index = record["class_index"]
            require((index is None and record["prediction"] is None and record["failure"] is not None)
                    or (type(index) is int and 0 <= index < 7 and record["prediction"] == CLASSES[index] and record["failure"] is None),
                    "Invalid frozen class/failure record.")
            require([s["request_id"] for s in record["primary_samples"]] == [
                request_id(context["requests"][context["slot_indices"][(arm, target, i)]]) for i in range(3)], "Frozen sample identities differ.")
            for sample in record["primary_samples"]:
                slot = context["requests"][context["slot_indices"][(arm, target, sample["sample_index"])]]
                require(sample == load(directory / "requests" / request_id(slot) / "parsing.json")
                        and all(sample[field] == value for field, value in slot.items())
                        and sample["response_file_sha256"] == states[slot["request_index"]]["response_file_sha256"],
                        "Frozen sample parsing/raw-response provenance differs.")
        predictions[arm] = records
    final = load(directory / "final_run_receipt.json")
    require(final["configuration"] == initial["configuration"] and final["primary_calls_reserved"] == PRIMARY_LIMIT
            and final["repair_calls"] == final["retries"] == 0 and final["ground_truth_accessed"] is False,
            "Final accounting differs.")
    require(set(final["arms"]) == set(ARMS), "Final arm accounting is incomplete.")
    for arm in ARMS:
        summary = final["arms"][arm]
        covered = sum(record["class_index"] is not None for record in predictions[arm].values())
        require(summary["primary_slots_reserved"] == PER_ARM_LIMIT and summary["coverage"] == covered
                and summary["failures"] == 140 - covered and summary["repairs"] == summary["retries"] == 0
                and summary["responses_persisted"] == sum(s["arm"] == arm and s["response_file_sha256"] is not None for s in states),
                "Final per-arm accounting differs.")
    return predictions, freeze


def infer(args, context, config):
    require(args.live and args.confirm == CONFIRMATION, "Live inference requires --live and the exact confirmation token.")
    import aiohttp
    require(aiohttp.__version__ == TRANSPORT_VERSION
            and importlib.metadata.version("aiohttp") == TRANSPORT_VERSION, "Live transport requires exactly aiohttp==3.8.5; nothing installed/downgraded.")
    parser = context["ref"]["historical_parser"](context)
    if args.run_dir.exists():
        require(args.resume, "Run directory exists; only explicit resume of this owned run is accepted.")
        initial = owned_run(args.run_dir, context, config)
    else:
        require(not args.resume and not args.abandon_request, "Cannot resume/review a nonexistent run.")
        args.run_dir.mkdir(parents=True, exist_ok=False)
        initial = {"configuration": config, "created_utc": now(), "installed_aiohttp_version": aiohttp.__version__,
                   "ground_truth_accessed": False}
        write(context, args.run_dir / "run_receipt.json", initial)
        (args.run_dir / "requests").mkdir()
        for arm in ARMS:
            (args.run_dir / arm / "targets").mkdir(parents=True)
    with context["ref"]["run_lock"](args.run_dir):
        if (args.run_dir / "freeze_receipt.json").exists():
            require(not args.abandon_request, "Cannot change a frozen run.")
            verify_frozen(args.run_dir, context)
            print("Run already frozen; no credentials read and no requests made.")
            return
        states = inventory(args.run_dir, context)
        for identifier in args.abandon_request:
            require(args.resume and args.review_note and args.review_note.strip(), "Manual review requires --resume and --review-note.")
            matches = [s for s in states if s["request_id"] == identifier and s["status"] == "ambiguous"]
            require(len(matches) == 1, "Only an existing ambiguous slot can be abandoned.")
            write(context, args.run_dir / "requests" / identifier / "abandoned.json", {
                "request_id": identifier, "action": "abandon_without_resend", "reviewed_utc": now(),
                "review_note": args.review_note, "replacement_request_authorized": False})
            states = inventory(args.run_dir, context)
        require(not any(s["status"] == "ambiguous" for s in states), "AMBIGUOUS request requires external manual review; no resend.")
        for slot in context["requests"]:
            index = slot["request_index"]
            if index < len(states):
                sample_record(context, parser, args.run_dir, slot, states[index])
                continue
            require(index == len(states) < PRIMARY_LIMIT
                    and sum(s["arm"] == slot["arm"] for s in states) < PER_ARM_LIMIT, "Primary hard limit/order violation.")
            require(not (args.run_dir / "freeze_receipt.json").exists(), "Run became frozen.")
            path = args.run_dir / "requests" / request_id(slot)
            path.mkdir(exist_ok=True)
            require(not list(path.iterdir()), "Existing journal evidence prohibits a new send.")
            if context["ref"]["_SECRET"] is None:
                secret = os.environ.get(args.api_key_env)
                require(isinstance(secret, str) and bool(secret.strip()), "Credential environment variable is missing/empty.")
                context["ref"]["_SECRET"] = secret
            # Durable intent precedes client creation/send. Even a pre-send crash
            # after this point is conservatively ambiguous and is never resent.
            write(context, path / "intent.json", dict(identity(context, slot), intent_created_utc=now()))
            response = asyncio.run(context["ref"]["post_once"](payload(context, slot), args.timeout))
            response.update(slot)
            response.update(request_id=request_id(slot), kind="primary")
            write(context, path / "response.json", response)  # Durable raw bytes BEFORE parsing.
            state = inspect_slot(args.run_dir, context, slot)
            states.append(state)
            if state["status"] == "ambiguous":
                write(context, path / "ambiguous.json", {"request_id": request_id(slot), "marked_utc": now(),
                    "manual_review_required": True, "reason": "Uncertain post-intent outcome; automatic resend prohibited."})
                raise RunnerError("AMBIGUOUS request " + request_id(slot) + "; stopped without retry.")
            sample_record(context, parser, args.run_dir, slot, state)
            if response["http_status"] in (401, 403, 429):
                raise RunnerError("Request rejected and persisted; inspect before explicit resume. No retry.")
            print(f"Persisted {index + 1}/{PRIMARY_LIMIT}: {slot['arm']} target {slot['target_id']} sample {slot['sample_index']}")
            if args.interval:
                time.sleep(args.interval)
        finalize(args.run_dir, context, config, initial, states, parser)
    print("All five arms persisted and frozen. No ground truth accessed.")


def score(args, context):
    require(args.score_output is not None, "score requires --score-output NEW_JSON.")
    destination = args.score_output.expanduser().resolve()
    require(not destination.exists() and not args.score_output.is_symlink() and destination.parent.is_dir(),
            "Score output must be NEW with an existing parent.")
    require(not within(destination, args.run_dir) and not within(destination, args.prep_dir), "Score output must be outside frozen inputs/run.")
    records, freeze = verify_frozen(args.run_dir, context)
    graph_bytes = verified(args.graph_file, GRAPH_HASH)
    import torch
    data = torch.load(io.BytesIO(graph_bytes), map_location="cpu", weights_only=False)
    require(list(data.label_names) == context["receipt"]["historical_wrapper"]["original_ordered_class_names"],
            "Canonical Cora class-index order differs.")
    labels = data.y.detach().cpu()  # ONLY ground-truth access in the entire runner.
    require(labels.ndim == 1 and len(labels) == 2708, "Unexpected canonical label shape.")
    results, correct_sets, per_target = {}, {arm: set() for arm in ARMS}, []
    for arm in ARMS:
        confusion = [[0] * 8 for _ in CLASSES]
        coverage = correct = 0
        for target in context["targets"]:
            actual = int(labels[target])
            require(0 <= actual < 7, "Invalid canonical class index.")
            predicted = records[arm][str(target)]["class_index"]
            valid = predicted is not None
            coverage += valid
            match = valid and predicted == actual
            correct += match
            if match:
                correct_sets[arm].add(target)
            confusion[actual][predicted if valid else 7] += 1
        results[arm] = {"total_targets": 140, "coverage": coverage, "failures": 140 - coverage,
                        "correct_predictions": correct, "raw_accuracy_all_140": correct / 140,
                        "raw_accuracy_percent": correct / 140 * 100,
                        "confusion_rows_true_classes": CLASSES, "confusion_columns_predicted_classes": CLASSES + ["FAILED"],
                        "confusion_matrix": confusion,
                        "predictions_sha256": freeze["run_files_sha256"][f"{arm}/final_predictions.json"]}
    for target in context["targets"]:
        per_target.append({"target_id": target, "true_class_index": int(labels[target]),
                           "arms": {arm: {"predicted_class_index": records[arm][str(target)]["class_index"],
                                          "correct": target in correct_sets[arm],
                                          "failure": records[arm][str(target)]["failure"]} for arm in ARMS}})
    comparisons = []
    for left, right in itertools.combinations(ARMS, 2):
        a, b = correct_sets[left], correct_sets[right]
        comparisons.append({"arm_a": left, "arm_b": right, "both_correct": len(a & b),
                            "a_correct_b_incorrect": len(a - b), "a_incorrect_b_correct": len(b - a),
                            "both_incorrect": 140 - len(a | b),
                            "accuracy_difference_b_minus_a": (len(b) - len(a)) / 140})
    result = {"stage": "offline_matched_raw_accuracy", "scored_utc": now(), "arms": results,
              "total_targets_per_arm": 140, "target_ids_in_manifest_order": context["targets"], "ordered_classes": CLASSES,
              "paired_descriptive_comparisons": comparisons, "per_target": per_target,
              "interpretation": "Exploratory matched-development results; not independent test-set confirmation.",
              "failure_policy": "Failures count as incorrect in all denominators and paired comparisons; no exclusions or ground-truth substitution.",
              "graph_sha256": GRAPH_HASH, "preparation_receipt_sha256": PREP_RECEIPT_HASH,
              "freeze_receipt_sha256": sha((args.run_dir / "freeze_receipt.json").read_bytes()),
              "source_hashes": context["source_hashes"], "inference_or_gcn_performed": False}
    # Exclusive creation outside the frozen inference directory. No run files change.
    with destination.open("xb") as stream:
        stream.write(context["ref"]["encoded"](result))
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({arm: {key: value for key, value in result.items() if key in {
        "coverage", "failures", "correct_predictions", "raw_accuracy_all_140"}} for arm, result in results.items()}, indent=2))


def plan(args, context, config):
    if args.run_dir.exists():
        require(args.resume, "Existing run requires explicit --resume for a read-only plan.")
        owned_run(args.run_dir, context, config)
        states = inventory(args.run_dir, context)
        if (args.run_dir / "freeze_receipt.json").exists():
            verify_frozen(args.run_dir, context)
    else:
        require(not args.resume, "Cannot resume a nonexistent run.")
        states = []
    try:
        installed = importlib.metadata.version("aiohttp")
    except importlib.metadata.PackageNotFoundError:
        installed = "not installed"
    print(json.dumps({"mode": "plan", "configuration": config, "primary_calls_planned_total": PRIMARY_LIMIT,
          "per_arm_accounting": {arm: {"planned_slots": PER_ARM_LIMIT,
              "reserved_slots": sum(s["arm"] == arm for s in states), "unique_prompt_tokens": sum(context["counts"][arm]),
              "input_tokens_for_three_samples": context["volumes"][arm],
              "prompt_token_range": [min(context["counts"][arm]), max(context["counts"][arm])]} for arm in ARMS},
          "total_expected_input_content_tokens": sum(context["volumes"].values()),
          "token_accounting_note": "Verified stored project-counter content counts; excludes chat framing/output/cache discounts.",
          "ambiguous_requests_requiring_review": [s["request_id"] for s in states if s["status"] == "ambiguous"],
          "required_aiohttp_version": TRANSPORT_VERSION, "installed_distribution_version": installed,
          "output_directory": str(args.run_dir), "score_output": str(args.score_output) if args.score_output else None,
          "outputs": ["run_receipt.json", "requests/<slot>/{intent,response,parsing,ambiguous,abandoned}.json",
                      "<arm>/targets/<global_id>.json", "<arm>/final_predictions.json", "sample_status.json",
                      "final_run_receipt.json", "freeze_receipt.json"],
          "live_requirements": ["--live", "--confirm " + CONFIRMATION],
          "credentials_read": False, "api_client_initialized": False}, indent=2))


def main(argv=None):
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", choices=("plan", "infer", "score"), default="plan")
    parser.add_argument("--prep-dir", type=Path, default=root / "experiments/matched_cora/offline_matched_prep_001")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--api-key-env", default="GAPAPI_API_KEY", help="Environment-variable NAME, never the credential itself.")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--interval", type=float, default=1.5)
    parser.add_argument("--abandon-request", action="append", default=[])
    parser.add_argument("--review-note")
    parser.add_argument("--graph-file", type=Path, default=root.parent / "LLMGNN_data/cora_random_sbert.pt")
    parser.add_argument("--score-output", type=Path)
    args = parser.parse_args(argv)
    sys.dont_write_bytecode = True
    require(math.isfinite(args.timeout) and args.timeout > 0 and math.isfinite(args.interval) and args.interval >= 0,
            "Invalid common timeout/interval.")
    require(not args.run_dir.is_symlink() and not args.prep_dir.is_symlink(), "Symlink run/preparation path refused.")
    args.run_dir, args.prep_dir, args.graph_file = [path.expanduser().resolve() for path in (args.run_dir, args.prep_dir, args.graph_file)]
    protected = [args.prep_dir, root / "src", root / "experiments/narrative_v1",
                 root / "experiments/manifests", root / "experiments/audits", root.parent / "LLMGNN_data"]
    require(not any(within(args.run_dir, path.resolve()) or within(path.resolve(), args.run_dir) for path in protected),
            "Run output overlaps frozen/preparation/source locations.")
    if args.score_output is not None:
        score_path = args.score_output.expanduser().resolve()
        require(not any(within(score_path, path.resolve()) for path in protected), "Score output overlaps protected artifacts.")
    if args.mode != "infer":
        require(not args.live and not args.confirm and not args.abandon_request and not args.review_note,
                "Live and manual-review flags are exclusive to infer mode.")
        sys.addaudithook(offline_guard)
    else:
        require(args.live and args.confirm == CONFIRMATION, "infer requires --live and the exact confirmation token.")
        require(not args.score_output, "Inference cannot score.")
    context = validate_inputs(root, args)
    context["slot_indices"] = {(slot["arm"], slot["target_id"], slot["sample_index"]): slot["request_index"] for slot in context["requests"]}
    config = configuration(args, context)
    if args.mode == "plan":
        plan(args, context, config)
    elif args.mode == "infer":
        infer(args, context, config)
    else:
        score(args, context)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Never show third-party exception text, headers or credential-bearing tracebacks.
        print("STOP: " + (str(exc) if isinstance(exc, RunnerError) else type(exc).__name__) + "; no automatic retry.", file=sys.stderr)
        raise SystemExit(2)
