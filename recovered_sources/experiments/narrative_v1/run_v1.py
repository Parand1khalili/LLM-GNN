"""Standalone frozen Narrative v1: offline plan, explicitly live infer, offline score.

Nothing runs on import. No shared cache, prompt generation, selection, or GCN.
Notebook was not available in the inspected project tree; pinned project source
is authoritative. Inference needs the existing aiohttp==3.8.5 and editdistance
dependencies. Only score imports torch or deserializes the trusted graph.

Default mode is plan. Every mode requires --run-dir. Fresh inference requires a
new directory; --resume accepts only this runner's matching owned run. Credentials
are read from --api-key-env only immediately before live requests. A durable
intent without a complete response is ambiguous and NEVER automatically resent.
After external investigation, --resume --abandon-request REQUEST_ID --review-note
NOTE can terminalize an uncertain request as a failure, without a replacement.
This runner cannot prove whether a provider billed or executed a lost request.
"""

import argparse
import ast
import asyncio
import base64
import copy
import hashlib
import io
import json
import math
import os
import re
import sys
import time
import uuid
from collections import Counter
from contextlib import contextmanager, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


MODEL = "gpt-6-luna"
ENDPOINT = "https://api.gapapi.com/v1/chat/completions"
CONFIRMATION = "RUN_NARRATIVE_V1_420_PRIMARY_CALLS"
PRIMARY_LIMIT = 420
SAMPLES = 3
RETRY_LIMIT = 0
CLASSES = [
    "rule_learning", "neural_networks", "case_based", "genetic_algorithms",
    "theory", "reinforcement_learning", "probabilistic_methods",
]
INPUT_HASHES = {
    "complete_prompts.json": "69d34d3c3ad9b6b72525e6c045efba1c399bfa3574f17f84bcc6fea848b1caaf",
    "target_diagnostics.json": "892d445a0b9e67ea23907d55afd15e2c9720014d2244d18a406c1bf83cd0da9b",
    "preparation_receipt.json": "65ef47f0e2a36cebe7e5e2e7874da86a794835131c8b7cf9c400044eba9cd8af",
}
GRAPH_HASH = "9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466"
ASYNC_SOURCE_HASH = "02847012267126b9a4afba5e345ff8b22df6338facedc8b5bf3ed7e9d56803a9"
_SECRET = None


class RunnerError(Exception):
    """An actionable local error; provider exception messages are never printed."""


def require(condition, message):
    if not condition:
        raise RunnerError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "Duplicate JSON key encountered.")
        result[key] = value
    return result


def decode(payload):
    return json.loads(payload, object_pairs_hook=_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(RunnerError("Nonfinite JSON value.")))


def load(path):
    return decode(path.read_bytes())


def _clean(value):
    """Protect secrets even if a provider unexpectedly echoes its credential."""
    if isinstance(value, str):
        return value.replace(_SECRET, "[REDACTED_API_KEY]") if _SECRET else value
    if isinstance(value, dict):
        return {str(_clean(key)): _clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite_python_float": repr(value)}
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return {"non_json_python_repr": _clean(repr(value))}


def encoded(value):
    return (json.dumps(_clean(value), ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def write_new(path, value):
    """Fsync then rename within an owned, exclusively locked run directory."""
    require(not path.exists() and not path.is_symlink(), f"Refusing existing output: {path.name}")
    payload = encoded(value)
    temporary = path.with_name(".tmp-" + path.name + "-" + uuid.uuid4().hex)
    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    require(not path.exists() and not path.is_symlink(), f"Output appeared concurrently: {path.name}")
    # No runner can race this rename: all inference writers hold the run lock.
    os.rename(temporary, path)
    if os.name != "nt":
        descriptor = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def write_same_or_new(path, value):
    if path.exists():
        require(path.read_bytes() == encoded(value), f"Existing derived file differs: {path.name}")
    else:
        write_new(path, value)


@contextmanager
def run_lock(directory):
    """OS lock releases on process death; its marker contains no credentials."""
    with (directory / ".runner.lock").open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RunnerError("Run is locked by another process.") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def offline_guard(event, arguments):
    if event.startswith("socket."):
        raise RunnerError("Network operations are forbidden in plan/score mode.")


def within(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def function(body, name):
    matches = [node for node in body if isinstance(node, ast.FunctionDef) and node.name == name]
    require(len(matches) == 1, f"Missing or ambiguous historical function: {name}")
    return matches[0]


def remove_block(text, offset, block):
    require(type(offset) is int and offset >= 0 and text[offset:offset + len(block)] == block,
            "Prepared insertion metadata is inconsistent.")
    return text[:offset] + text[offset + len(block):]


def validate_inputs(root, preparation):
    """Read pinned JSON/source only. Never load the graph or regenerate prompts."""
    files = {}
    objects = {}
    for filename, expected in INPUT_HASHES.items():
        payload = (preparation / filename).read_bytes()
        require(sha(payload) == expected, f"Immutable preparation hash mismatch: {filename}")
        files[filename] = expected
        objects[filename] = decode(payload)
    prompts_file = objects["complete_prompts.json"]
    diagnostics_file = objects["target_diagnostics.json"]
    receipt = objects["preparation_receipt.json"]
    require(receipt["stage"] == "offline_preparation_only", "Unexpected preparation stage.")
    require(all(receipt[key] is False for key in (
        "inference_performed", "evaluation_performed", "ground_truth_accessed", "target_or_neighbor_selection_performed"
    )), "Unexpected preparation activity flags.")
    require(receipt["output_file_sha256"] == {name: files[name] for name in (
        "complete_prompts.json", "target_diagnostics.json"
    )}, "Preparation receipt output hashes differ.")
    sources = {
        "v0": root / "src/structure/narrative_topology_v0.py",
        "v1": root / "src/structure/narrative_topology_v1.py",
        "manifest": root / "experiments/manifests/m1_prompt_variants_b256.json",
        "llm": root / "src/llm.py", "config": root / "src/openail/config.py",
        "utils": root / "src/openail/utils.py",
        "token_counter": root / "src/structure/prompt_builder.py",
        "adjacency_helper": root / "src/structure/selector.py",
        "structure_init": root / "src/structure/__init__.py",
        "preparation_script": root / "experiments/narrative_v1/prepare_v1_prompts.py",
    }
    source_bytes = {}
    source_hashes = {}
    for name, path in sources.items():
        payload = path.read_bytes()
        actual = sha(payload)
        require(actual == receipt["source_and_input_files"][name]["sha256"], f"Source hash differs from preparation: {name}")
        source_bytes[name] = payload
        source_hashes[name] = actual
    transport = (root / "src/openail/asyncapi.py").read_bytes()
    require(sha(transport) == ASYNC_SOURCE_HASH, "Historical aiohttp transport source changed.")
    source_hashes["async_transport"] = ASYNC_SOURCE_HASH
    source_hashes["runner"] = sha(Path(__file__).read_bytes())
    require(receipt["source_and_input_files"]["graph"]["sha256"] == GRAPH_HASH,
            "Unexpected prepared graph provenance.")
    for name, expected in receipt["expected_pinned_hashes"].items():
        require(receipt["source_and_input_files"][name]["sha256"] == expected, "Pinned source/input inconsistency.")
    manifest = decode(source_bytes["manifest"])
    targets = manifest["target_ids"]
    require(len(targets) == 140 and len(set(targets)) == 140
            and all(type(item) is int and 0 <= item < 2708 for item in targets), "Invalid frozen target IDs.")
    require(manifest["dataset"] == "cora" and manifest["structural_token_budget"] == 256,
            "Unexpected frozen manifest metadata.")
    for obj in (prompts_file, diagnostics_file, receipt):
        require(obj["target_ids_in_manifest_order"] == targets and obj["target_count"] == 140
                and obj["num_graph_nodes"] == 2708, "Preparation target order/count differs from manifest.")
    wrapper = receipt["historical_wrapper"]
    require(wrapper["ordered_class_names"] == CLASSES, "Ordered Cora classes differ.")
    require(wrapper["class_index_mapping"] == {str(i): name for i, name in enumerate(CLASSES)}, "Class indices differ.")
    require([wrapper["cora_name_mapping"][name].lower() for name in wrapper["original_ordered_class_names"]] == CLASSES,
            "Original class metadata differs.")
    require(wrapper["need_tasks"] is False and wrapper["k"] == 3 and wrapper["dataset_name"] == "cora",
            "Historical consistency wrapper settings differ.")
    llm_text = source_bytes["llm"].decode("utf-8-sig")
    llm_tree = ast.parse(llm_text)
    experiment = [node for node in llm_tree.body if isinstance(node, ast.ClassDef) and node.name == "Experiment"]
    require(len(experiment) == 1, "Historical Experiment class is ambiguous.")
    require(ast.get_source_segment(llm_text, function(llm_tree.body, "zero_shot_prompt")) == wrapper["zero_shot_function_source"],
            "Zero-shot wrapper differs from receipt.")
    require(ast.get_source_segment(llm_text, function(experiment[0].body, "topk_confidence")) == wrapper["topk_method_source"],
            "Top-3 wrapper differs from receipt.")
    template = wrapper["exact_complete_template_with_sentinel"]
    sentinel = "<TARGET_TEXT_PLUS_V1_STRUCTURAL_CONTEXT>"
    require(template.count(sentinel) == 1, "Invalid historical wrapper sentinel.")
    prefix, suffix = template.split(sentinel)
    prompts = prompts_file["prompts_by_target_id"]
    details = diagnostics_file["diagnostics_by_target_id"]
    keys = {str(item) for item in targets}
    require(set(prompts) == set(details) == keys, "Prompt/diagnostic global-ID coverage mismatch.")
    counts = []
    for target in targets:
        key = str(target)
        prompt = prompts[key]
        diagnostic = details[key]
        record = manifest["targets"][key]
        v1 = diagnostic["v1_diagnostics"]
        require(isinstance(prompt, str) and sha(prompt.encode("utf-8")) == diagnostic["complete_prompt_sha256"],
                f"Prompt hash mismatch for target {target}.")
        require(diagnostic["target_id"] == v1["target_id"] == target, "Diagnostic target ID mismatch.")
        require(diagnostic["neighbor_ids_in_frozen_order"] == record["neighbor_ids"]
                and diagnostic["representative_id"] == record["representative_id"], "Frozen neighbor metadata changed.")
        require(sha(record["target_text"].encode("utf-8")) == diagnostic["target_text_sha256"], "Frozen target text hash mismatch.")
        structural = diagnostic["structural_prompt"]
        require(sha(structural.encode("utf-8")) == diagnostic["structural_prompt_sha256"], "Structural prompt hash mismatch.")
        require(prompt == prefix + record["target_text"].rstrip() + "\n\n" + structural + suffix,
                f"Prepared complete wrapper/text mismatch for target {target}.")
        recovered_v0 = remove_block(structural, v1["excerpt_insertion_offset"], v1["excerpt_block"])
        v0 = v1["v0_diagnostics"]
        historical = remove_block(recovered_v0, v0["insertion_offset"], v0["inserted_block"])
        require(historical.encode("utf-8") == record["variants"]["consensus"]["prompt"].encode("utf-8"),
                "Historical Consensus recovery failed.")
        require(v1["original_prompt_preserved"] and v1["v0_prompt_preserved"] and v0["original_prompt_preserved"],
                "Missing preservation confirmations.")
        require(0 <= v1["original_structural_tokens"] <= 256 and 0 <= v1["v0_structural_tokens"] <= 320
                and 0 <= diagnostic["structural_tokens"] == v1["v1_structural_tokens"] <= 416, "Prepared structural budget invalid.")
        count = diagnostic["complete_classification_prompt_tokens"]
        require(type(count) is int and count > 0, "Invalid stored complete prompt token count.")
        counts.append(count)
    require(receipt["structural_caps"] == {"historical": 256, "v0": 320, "v1": 416}, "Structural caps differ.")
    return {
        "targets": targets, "prompts": prompts, "details": details, "classes": CLASSES,
        "preparation_hashes": files, "source_hashes": source_hashes,
        "source_bytes": source_bytes, "receipt": receipt, "token_counts": counts,
    }


def configuration(args, context):
    return {
        "schema": "narrative_v1_standalone_run_v1", "method": "consistency_struct_narrative_v1",
        "model": MODEL, "endpoint": ENDPOINT, "temperature": 0.7,
        "samples_per_target": SAMPLES, "completions_per_request": 1,
        "message_roles": ["user"], "top_p": "omitted", "max_tokens": "omitted",
        "provider_seed": "omitted", "primary_call_limit": PRIMARY_LIMIT,
        "repair_call_limit": args.repair_budget, "retry_limit": RETRY_LIMIT,
        "repair_temperature": 1, "repair_group_size": 3, "repair_passes_per_target": 1,
        "repair_trigger": "Historical check_grammar of FIRST primary completion only.",
        "repair_replaces": "All three target completions; no recursive repair.",
        "repair_policy_difference": "Budgeted/disabled repairs differ from historical automatic repair.",
        "retry_policy_difference": "Zero automatic retries; historical transport retried transient failures.",
        "timeout_seconds": args.timeout, "interval_seconds": args.interval,
        "api_key_environment_variable": args.api_key_env,
        "transport": "aiohttp==3.8.5 ClientSession.post, Bearer header, JSON; redirects disabled",
        "preparation_hashes": context["preparation_hashes"],
        "source_hashes": context["source_hashes"],
        "target_ids_in_manifest_order": context["targets"], "ordered_classes": CLASSES,
        "prompt_hashes": {str(t): context["details"][str(t)]["complete_prompt_sha256"] for t in context["targets"]},
        "notebook_reference": "No Notebook found in inspected project tree; pinned project sources used.",
        "ground_truth_accessed": False,
    }


def inventory(directory, context, config):
    result = []
    requests = directory / "requests"
    if not requests.exists():
        return result
    for slot in sorted(requests.iterdir()):
        require(slot.is_dir() and not slot.is_symlink(), "Unexpected request-directory entry.")
        match = re.fullmatch(r"(primary|repair)_(\d+)_([012])", slot.name)
        require(match is not None and int(match[2]) in context["targets"], "Unexpected request identity.")
        intent_file = slot / "intent.json"
        if not intent_file.exists():
            require(not list(slot.iterdir()), "Incomplete request journal requires manual review.")
            continue
        intent = load(intent_file)
        require(intent["request_id"] == slot.name and intent["kind"] == match[1]
                and intent["target_id"] == int(match[2]) and intent["sample_index"] == int(match[3]), "Intent identity mismatch.")
        require(intent["prompt_sha256"] == config["prompt_hashes"][str(intent["target_id"])], "Intent prompt provenance mismatch.")
        response_file = slot / "response.json"
        abandoned = (slot / "abandoned.json").exists()
        status = "ambiguous"
        response_sha = None
        if response_file.exists():
            response = load(response_file)
            require(response["request_id"] == slot.name, "Response identity mismatch.")
            body = base64.b64decode(response["raw_body_base64"], validate=True)
            require(sha(body) == response["persisted_body_sha256"], "Raw response body hash mismatch.")
            response_sha = sha(response_file.read_bytes())
            if response["complete"] and response["http_status"] not in (408,) and response["http_status"] < 500:
                status = "response_persisted"
        if abandoned:
            review = load(slot / "abandoned.json")
            require(review["request_id"] == slot.name and review["action"] == "abandon_without_resend", "Invalid review record.")
            status = "manually_abandoned"
        result.append({
            "request_id": slot.name, "target_id": intent["target_id"],
            "sample_index": intent["sample_index"], "kind": intent["kind"],
            "status": status, "response_file_sha256": response_sha,
        })
    require(sum(item["kind"] == "primary" for item in result) <= PRIMARY_LIMIT, "Primary-call hard limit exceeded.")
    require(sum(item["kind"] == "repair" for item in result) <= config["repair_call_limit"], "Repair-call hard limit exceeded.")
    return result


def owned_run(directory, config):
    receipt = load(directory / "run_receipt.json")
    require(receipt["configuration"] == config, "Run configuration/provenance differs; cannot resume.")
    return receipt


def plan(args, context, config):
    run = args.run_dir
    states = []
    if run.exists():
        require(args.resume, "Run directory exists: use --resume only for a matching owned run.")
        owned_run(run, config)
        states = inventory(run, context, config)
    else:
        require(not args.resume, "Cannot resume a nonexistent run.")
    volume = sum(context["token_counts"])
    print(json.dumps({
        "mode": "plan", "configuration": config,
        "primary_calls_planned_total": PRIMARY_LIMIT,
        "primary_intents_already_reserved": sum(item["kind"] == "primary" for item in states),
        "ambiguous_requests_requiring_review": [item["request_id"] for item in states if item["status"] == "ambiguous"],
        "unique_prompt_token_volume": volume, "three_sample_prompt_token_volume": volume * SAMPLES,
        "complete_prompt_token_range": [min(context["token_counts"]), max(context["token_counts"])],
        "token_volume_note": "Stored project-counter content tokens; excludes chat framing, responses, and conditional repairs.",
        "output_directory": str(run),
        "outputs": ["run_receipt.json", "requests/<request_id>/{intent,response,ambiguous,abandoned}.json",
                    "targets/<global_id>.json", "sample_status.json", "final_predictions.json",
                    "final_run_receipt.json", "freeze_receipt.json"],
        "live_requirements": ["--live", "--confirm " + CONFIRMATION],
        "credentials_read": False, "api_client_initialized": False,
    }, indent=2))


def historical_parser(context):
    """Execute only hash-pinned pure parsing/voting AST, never llm.py imports."""
    try:
        import editdistance
    except ImportError as exc:
        raise RunnerError("Existing project dependency editdistance is required; nothing was installed.") from exc
    tree = ast.parse(context["source_bytes"]["llm"].decode("utf-8-sig"))
    utils = ast.parse(context["source_bytes"]["utils"].decode("utf-8-sig"))
    experiment = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Experiment")
    nodes = [copy.deepcopy(function(tree.body, name)) for name in ("get_closest_label", "most_common_number")]
    nodes.append(copy.deepcopy(function(utils.body, "retrieve_dict")))
    nodes += [copy.deepcopy(function(experiment.body, name)) for name in ("check_grammar", "retrieve_multiple_answers")]
    correction = copy.deepcopy(function(experiment.body, "correct_grammar"))
    call_position = next(i for i, statement in enumerate(correction.body)
                         if isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "new_res" for t in statement.targets))
    correction.name = "repair_template"
    correction.body = correction.body[:call_position] + [ast.Return(value=ast.Name(id="prompt", ctx=ast.Load()))]
    nodes.append(correction)
    evaluator = function(experiment.body, "eval_result")
    loops = [node for node in evaluator.body if isinstance(node, ast.For)]
    require(len(loops) == 1, "Cannot isolate historical prediction loop.")
    # This is the ORIGINAL loop, including fallback and confidence arithmetic.
    # Only the outer label lookup, tensor conversion, saving, and scoring are omitted.
    vote = ast.parse(
        "def vote(res, label_names, select_ids):\n"
        "    pred = []\n    conf = []\n    cannot_fix = 0\n"
        "    method = 'consistency_struct_narrative_v1'\n"
        "    return pred, conf, cannot_fix\n"
    ).body[0]
    vote.body.insert(-1, copy.deepcopy(loops[0]))
    nodes.append(vote)
    forbidden = {"gt", "gt_y", "data_obj", "openai", "torch", "openai_text_api", "openai_text_api_with_backoff"}
    require(not any(isinstance(node, ast.Name) and node.id in forbidden for item in nodes for node in ast.walk(item)),
            "Historical extraction contains a forbidden scoring/API dependency.")
    namespace = {"ast": ast, "Counter": Counter, "editdistance": editdistance, "print": lambda *a, **k: None}
    module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    exec(compile(module, "<pinned historical parser/vote/templates>", "exec"), namespace)
    namespace["self"] = SimpleNamespace(label_names=CLASSES)
    return namespace


def grammar(parser, text):
    if not isinstance(text, str):
        return [False, "grammar error", None]
    return list(parser["check_grammar"](parser["self"], text))


def individual_parse(parser, text):
    """Diagnostic first answer only; never vote, repair, or contact a provider."""
    if text is None:
        return {"individual_prediction": None, "parse_failure": "no_completion_text"}
    literal_failure = None
    structure_failure = None
    try:
        literal_answers = parser["retrieve_dict"](text.lower())
    except Exception as exc:
        literal_failure = type(exc).__name__
    if literal_failure is None:
        try:
            for answer in literal_answers:
                answer["answer"], answer["confidence"]
        except Exception as exc:
            structure_failure = type(exc).__name__
    try:
        answers = parser["retrieve_multiple_answers"](parser["self"], [[text]], None, 1)[0][0]
        first = answers[0]
        return {
            "parsed_answers": answers, "first_answer": first[0], "first_confidence": first[1],
            "individual_prediction": first[0] if first[0] in CLASSES else None,
            "individual_class_index": CLASSES.index(first[0]) if first[0] in CLASSES else None,
            "literal_parse_failure": literal_failure,
            "answer_structure_failure": structure_failure,
            "historical_edit_distance_fallback_used": literal_failure is not None or structure_failure is not None,
            "parse_failure": None,
        }
    except Exception as exc:
        return {"individual_prediction": None, "literal_parse_failure": literal_failure,
                "answer_structure_failure": structure_failure,
                "parse_failure": "historical_individual_parser_failed_" + type(exc).__name__}


def payload(prompt, repair=False):
    return {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "temperature": 1 if repair else 0.7, "n": 1}


async def post_once(request, timeout):
    """Actual project aiohttp POST, with no redirect or retry wrapper."""
    import aiohttp
    status = None
    headers = {}
    body = bytearray()
    started = now()
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout), trust_env=False) as session:
            async with session.post(ENDPOINT, headers={"Authorization": "Bearer " + _SECRET},
                                    json=request, allow_redirects=False) as response:
                status = response.status
                headers = {key: value for key, value in response.headers.items()
                           if key.lower() in {"content-type", "date", "x-request-id", "request-id"}}
                async for chunk in response.content.iter_chunked(65536):
                    body.extend(chunk)
        complete = True
        failure = None
    except BaseException as exc:
        complete = False
        failure = type(exc).__name__  # Never serialize exception text/headers/credentials.
    raw = bytes(body)
    safe = raw.replace(_SECRET.encode("utf-8"), b"[REDACTED_API_KEY]")
    return {
        "started_utc": started, "finished_utc": now(), "http_status": status,
        "headers": headers, "complete": complete, "transport_failure_type": failure,
        "raw_body_base64": base64.b64encode(safe).decode("ascii"),
        "original_body_sha256": sha(raw), "persisted_body_sha256": sha(safe),
        "credential_redaction_required": safe != raw,
    }


def perform_request(args, context, config, kind, target, sample, request):
    global _SECRET
    request_id = f"{kind}_{target}_{sample}"
    slot = args.run_dir / "requests" / request_id
    slot.mkdir(exist_ok=True)
    intent_path = slot / "intent.json"
    identity = {
        "request_id": request_id, "kind": kind, "target_id": target, "sample_index": sample,
        "prompt_sha256": config["prompt_hashes"][str(target)], "endpoint": ENDPOINT,
        "request": request, "request_json_sha256": sha(json.dumps(request).encode("utf-8")),
    }
    if intent_path.exists():
        existing = load(intent_path)
        require(all(existing.get(key) == value for key, value in identity.items()), "Persisted request identity/payload mismatch.")
        if (slot / "abandoned.json").exists():
            return None
        response_path = slot / "response.json"
        require(response_path.exists(), f"AMBIGUOUS request {request_id}: intent exists without response; manual review required. No resend.")
        response = load(response_path)
        require(response["complete"] and response["http_status"] not in (408,) and response["http_status"] < 500,
                f"AMBIGUOUS request {request_id}: uncertain provider outcome; manual review required. No resend.")
        return response
    states = inventory(args.run_dir, context, config)
    limit = PRIMARY_LIMIT if kind == "primary" else config["repair_call_limit"]
    require(sum(item["kind"] == kind for item in states) < limit, f"{kind} call hard limit reached.")
    if _SECRET is None:
        _SECRET = os.environ.get(args.api_key_env)
        require(isinstance(_SECRET, str) and bool(_SECRET.strip()), "Live credential environment variable is missing/empty.")
    # Durable reservation BEFORE handing control to the HTTP client. A crash in
    # even the pre-send interval is conservatively ambiguous on resume.
    write_new(intent_path, dict(identity, intent_created_utc=now()))
    response = asyncio.run(post_once(request, args.timeout))
    response.update({"request_id": request_id, "target_id": target, "sample_index": sample, "kind": kind})
    write_new(slot / "response.json", response)  # Raw bytes durable before JSON/content parsing.
    if not response["complete"] or response["http_status"] in (408,) or response["http_status"] >= 500:
        write_new(slot / "ambiguous.json", {
            "request_id": request_id, "marked_utc": now(), "manual_review_required": True,
            "reason": "Outcome after possible send is uncertain; automatic resend prohibited.",
        })
        raise RunnerError(f"AMBIGUOUS request {request_id}: stopped for manual review; no automatic retry.")
    if response["http_status"] in (401, 403, 429):
        raise RunnerError(f"Request {request_id} was rejected; response persisted. No retry; inspect before resume.")
    if args.interval:
        time.sleep(args.interval)
    return response


def content(response):
    """Called only AFTER raw response persistence; no repairs or network calls."""
    if response is None:
        return None, "manually_abandoned"
    if response["credential_redaction_required"]:
        return None, "provider_echoed_credential_response_redacted"
    if not 200 <= response["http_status"] < 300:
        return None, "http_rejection"
    try:
        obj = decode(base64.b64decode(response["raw_body_base64"], validate=True))
        choices = obj["choices"]
        require(isinstance(choices, list) and len(choices) == 1, "Expected exactly one choice.")
        text = choices[0]["message"]["content"]
        require(isinstance(text, str), "Expected textual completion.")
        return text, None
    except Exception as exc:
        return None, "invalid_response_envelope_" + type(exc).__name__


def target_record(args, context, config, parser, target):
    prompt = context["prompts"][str(target)]
    primary = [perform_request(args, context, config, "primary", target, sample, payload(prompt)) for sample in range(SAMPLES)]
    text_errors = [content(response) for response in primary]
    primary_texts = [item[0] for item in text_errors]
    result = {
        "target_id": target, "prompt_sha256": config["prompt_hashes"][str(target)],
        "primary_samples": [{"sample_index": i, "request_id": f"primary_{target}_{i}",
                             "response_error": error, "grammar": grammar(parser, text)}
                            for i, (text, error) in enumerate(text_errors)],
        "repair": {"applied": False, "policy": "first-primary-only trigger; replace all three"},
        "prediction": None, "class_index": None, "confidence_percent_before_tensor_cast": None,
        "failure": None, "finished_utc": now(),
    }
    for sample, text in zip(result["primary_samples"], primary_texts):
        sample.update(individual_parse(parser, text))
    if any(text is None for text in primary_texts):
        result["failure"] = "one_or_more_primary_requests_failed_or_abandoned; no partial-sample vote"
        result["finished_utc"] = now()
        return result
    effective = primary_texts
    first_check = result["primary_samples"][0]["grammar"]
    if not first_check[0]:
        states = inventory(args.run_dir, context, config)
        repairs_used = sum(item["kind"] == "repair" for item in states)
        target_repairs = sum(item["kind"] == "repair" and item["target_id"] == target for item in states)
        if repairs_used + (3 - target_repairs) <= config["repair_call_limit"]:
            repair_prompt = parser["repair_template"](
                parser["self"], prompt, primary_texts[0], first_check[1],
                temperature=0.7, n=3, error_message=first_check[2],
            )
            repairs = [perform_request(args, context, config, "repair", target, sample, payload(repair_prompt, True))
                       for sample in range(SAMPLES)]
            repaired = [content(response) for response in repairs]
            result["repair"] = {
                "applied": True, "policy": "historical one-pass replacement of all three samples",
                "request_ids": [f"repair_{target}_{i}" for i in range(SAMPLES)],
                "repair_prompt_sha256": sha(repair_prompt.encode("utf-8")),
                "samples": [{"sample_index": i, "response_error": error, "grammar": grammar(parser, text)}
                            for i, (text, error) in enumerate(repaired)],
            }
            for sample, (text, error) in zip(result["repair"]["samples"], repaired):
                sample.update(individual_parse(parser, text))
            if any(text is None for text, error in repaired):
                result["failure"] = "repair_request_failed_or_abandoned; no silent reversion to primary samples"
                result["finished_utc"] = now()
                return result
            effective = [text for text, error in repaired]
        else:
            result["repair"]["skipped_reason"] = "explicit repair budget cannot fund the historical three-call replacement"
    try:
        parsed = parser["retrieve_multiple_answers"](parser["self"], [effective], None, 3)[0]
        result["parsed_samples"] = [
            {"sample_index": i, "grammar": grammar(parser, text), "parsed_answers": answers,
             "first_answer": answers[0][0] if answers else None,
             "first_confidence": answers[0][1] if answers else None,
             "first_class_index": CLASSES.index(answers[0][0]) if answers and answers[0][0] in CLASSES else None}
            for i, (text, answers) in enumerate(zip(effective, parsed))
        ]
        require(len(parsed) == SAMPLES, "Historical parser returned unexpected sample count.")
        predictions, confidences, fallback_count = parser["vote"]([parsed], CLASSES, [0])
        require(len(predictions) == len(confidences) == 1 and type(predictions[0]) is int,
                "Historical vote did not return one class index.")
        require(math.isfinite(float(confidences[0])), "Historical confidence is nonfinite.")
        result.update({"prediction": CLASSES[predictions[0]], "class_index": predictions[0],
                       "confidence_percent_before_tensor_cast": confidences[0],
                       "historical_all_invalid_fallback_count": fallback_count})
    except Exception as exc:
        result["failure"] = "historical_parser_or_vote_failed_" + type(exc).__name__
    result["finished_utc"] = now()
    return result


def apply_manual_reviews(args, context, config):
    if not args.abandon_request:
        return
    require(bool(args.review_note and args.review_note.strip()), "Manual abandonment requires --review-note.")
    states = {item["request_id"]: item for item in inventory(args.run_dir, context, config)}
    for request_id in args.abandon_request:
        require(request_id in states and states[request_id]["status"] == "ambiguous",
                "Only an existing ambiguous request can be manually abandoned.")
        write_new(args.run_dir / "requests" / request_id / "abandoned.json", {
            "request_id": request_id, "action": "abandon_without_resend", "reviewed_utc": now(),
            "review_note": args.review_note, "replacement_request_authorized": False,
        })


def finalize(args, context, config, initial):
    states = inventory(args.run_dir, context, config)
    require(not any(item["status"] == "ambiguous" for item in states), "Cannot freeze unresolved ambiguous requests.")
    require(sum(item["kind"] == "primary" for item in states) == PRIMARY_LIMIT, "Cannot freeze before 420 primary slots are terminal.")
    records = {str(t): load(args.run_dir / "targets" / f"{t}.json") for t in context["targets"]}
    for target in context["targets"]:
        require(records[str(target)]["target_id"] == target and records[str(target)]["prompt_sha256"] == config["prompt_hashes"][str(target)],
                "Persisted target result provenance mismatch.")
    predictions = {
        "method": config["method"], "target_ids_in_manifest_order": context["targets"],
        "ordered_classes": CLASSES, "predictions_by_target_id": records,
        "ground_truth_accessed": False,
    }
    write_same_or_new(args.run_dir / "final_predictions.json", predictions)
    write_same_or_new(args.run_dir / "sample_status.json", {"samples": states, "retry_count": 0})
    existing = args.run_dir / "final_run_receipt.json"
    finished = load(existing)["finished_utc"] if existing.exists() else now()
    summary = {
        "configuration": config, "started_utc": initial["created_utc"], "finished_utc": finished,
        "primary_calls_reserved": sum(item["kind"] == "primary" for item in states),
        "repair_calls_reserved": sum(item["kind"] == "repair" for item in states),
        "requests_with_persisted_response": sum(item["response_file_sha256"] is not None for item in states),
        "manually_abandoned_requests": [item["request_id"] for item in states if item["status"] == "manually_abandoned"],
        "retries": 0, "target_prediction_count": sum(item["class_index"] is not None for item in records.values()),
        "target_failures": sum(item["class_index"] is None for item in records.values()),
        "primary_literal_parse_failures": sum(bool(sample.get("literal_parse_failure"))
                                               for item in records.values() for sample in item["primary_samples"]),
        "primary_grammar_failures": sum(not sample["grammar"][0]
                                         for item in records.values() for sample in item["primary_samples"]),
        "ground_truth_accessed": False, "scoring_performed": False,
    }
    write_same_or_new(existing, summary)
    require(not any(path.name.startswith(".tmp-") for path in args.run_dir.rglob("*")), "Temporary journal files require manual review before freezing.")
    evidence = {}
    for path in sorted(args.run_dir.rglob("*")):
        require(not path.is_symlink(), "Symlinks are not permitted in run evidence.")
        if path.is_file() and path.name not in {".runner.lock", "freeze_receipt.json"}:
            evidence[path.relative_to(args.run_dir).as_posix()] = sha(path.read_bytes())
    write_new(args.run_dir / "freeze_receipt.json", {
        "schema": "narrative_v1_frozen_predictions_v1", "frozen_utc": finished,
        "run_files_sha256": evidence, "runner_sha256": config["source_hashes"]["runner"],
        "ground_truth_accessed_before_freeze": False,
    })


def verify_frozen(directory, context):
    freeze = load(directory / "freeze_receipt.json")
    require(freeze["schema"] == "narrative_v1_frozen_predictions_v1"
            and freeze["ground_truth_accessed_before_freeze"] is False, "Invalid prediction freeze receipt.")
    require(freeze["runner_sha256"] == context["source_hashes"]["runner"], "Frozen runner source differs.")
    evidence = freeze["run_files_sha256"]
    require({"run_receipt.json", "final_predictions.json", "final_run_receipt.json", "sample_status.json"} <= set(evidence),
            "Frozen evidence is incomplete.")
    actual_files = set()
    for path in directory.rglob("*"):
        require(not path.is_symlink(), "Symlinks are not permitted in frozen evidence.")
        if path.is_file() and path.name not in {".runner.lock", "freeze_receipt.json"}:
            actual_files.add(path.relative_to(directory).as_posix())
    require(actual_files == set(evidence), "Frozen run contains missing or additional evidence files.")
    for relative, expected in evidence.items():
        path = directory / relative
        require(not path.is_symlink() and within(path.resolve(), directory.resolve()), "Unsafe frozen evidence path.")
        require(sha(path.read_bytes()) == expected, f"Frozen evidence changed: {relative}")
    initial = load(directory / "run_receipt.json")
    config = initial["configuration"]
    require(config["preparation_hashes"] == context["preparation_hashes"]
            and config["source_hashes"] == context["source_hashes"]
            and config["target_ids_in_manifest_order"] == context["targets"]
            and config["ordered_classes"] == CLASSES, "Frozen run provenance differs.")
    states = inventory(directory, context, config)
    require(sum(item["kind"] == "primary" for item in states) == PRIMARY_LIMIT
            and not any(item["status"] == "ambiguous" for item in states), "Frozen request coverage is incomplete.")
    return load(directory / "final_predictions.json"), freeze


def infer(args, context, config):
    require(args.live and args.confirm == CONFIRMATION, "Live inference requires BOTH --live and the exact --confirm token shown by plan.")
    # Client import is exclusive to live mode; check the actual project transport
    # version so internal retry behavior is the reviewed aiohttp 3.8.5 behavior.
    try:
        import aiohttp
    except ImportError as exc:
        raise RunnerError("Project dependency aiohttp==3.8.5 is required; nothing was installed.") from exc
    require(aiohttp.__version__ == "3.8.5", "Live transport requires project-pinned aiohttp==3.8.5; review other versions first.")
    parser = historical_parser(context)
    if args.run_dir.exists():
        require(args.resume, "Inference requires a NEW run directory unless --resume is explicit.")
        initial = owned_run(args.run_dir, config)
    else:
        require(not args.resume, "Cannot resume a nonexistent run.")
        args.run_dir.mkdir(parents=True, exist_ok=False)
        initial = {"configuration": config, "created_utc": now(), "ground_truth_accessed": False}
        write_new(args.run_dir / "run_receipt.json", initial)
        (args.run_dir / "requests").mkdir()
        (args.run_dir / "targets").mkdir()
    with run_lock(args.run_dir):
        if (args.run_dir / "freeze_receipt.json").exists():
            verify_frozen(args.run_dir, context)
            print("Run is already frozen; no requests made and no credentials read.")
            return
        apply_manual_reviews(args, context, config)
        states = inventory(args.run_dir, context, config)
        require(not any(item["status"] == "ambiguous" for item in states),
                "Run contains ambiguous requests; external manual review is required before resume.")
        for target in context["targets"]:
            destination = args.run_dir / "targets" / f"{target}.json"
            if destination.exists():
                record = load(destination)
                require(record["target_id"] == target and record["prompt_sha256"] == config["prompt_hashes"][str(target)],
                        "Existing target result does not belong to this run.")
                continue
            result = target_record(args, context, config, parser, target)
            write_new(destination, result)
            print(f"Persisted target {target}: {'prediction' if result['class_index'] is not None else 'failure'}")
        finalize(args, context, config, initial)
    print("Predictions and raw responses frozen. Ground truth has not been accessed.")


def score(args, context):
    require(args.score_output is not None, "Score requires a NEW explicit --score-output file.")
    destination = args.score_output.expanduser().absolute()
    require(not destination.exists() and not destination.is_symlink(), "Score output already exists.")
    require(not within(destination.resolve(), args.prep_dir) and not within(destination.resolve(), args.run_dir),
            "Score output must be outside immutable preparation and frozen run directories.")
    predictions, freeze = verify_frozen(args.run_dir, context)
    require(predictions["target_ids_in_manifest_order"] == context["targets"]
            and predictions["ordered_classes"] == CLASSES, "Frozen prediction IDs/classes differ.")
    records = predictions["predictions_by_target_id"]
    require(set(records) == {str(item) for item in context["targets"]}, "Frozen target predictions are incomplete.")
    # This is the ONLY mode that opens a serialized dataset or accesses data.y.
    graph_bytes = args.graph_file.read_bytes()
    require(sha(graph_bytes) == GRAPH_HASH, "Trusted Cora graph hash mismatch; scoring stopped.")
    import torch
    data = torch.load(io.BytesIO(graph_bytes), map_location="cpu", weights_only=False)
    original_names = context["receipt"]["historical_wrapper"]["original_ordered_class_names"]
    require(list(data.label_names) == original_names, "Scoring graph class-index order differs.")
    labels = data.y.detach().cpu()
    require(labels.ndim == 1 and len(labels) == 2708, "Unexpected canonical Cora label shape.")
    confusion = [[0 for _ in range(len(CLASSES) + 1)] for _ in CLASSES]
    correct = covered = 0
    per_target = []
    for target in context["targets"]:
        record = records[str(target)]
        require(record["target_id"] == target, "Scoring target record ID mismatch.")
        actual = int(labels[target])
        require(0 <= actual < len(CLASSES), "Invalid canonical class index.")
        predicted = record["class_index"]
        valid = type(predicted) is int and 0 <= predicted < len(CLASSES)
        require(predicted is None or valid, "Invalid persisted prediction index.")
        require(not valid or record["prediction"] == CLASSES[predicted], "Prediction name/index mismatch.")
        covered += valid
        match = bool(valid and predicted == actual)
        correct += match
        confusion[actual][predicted if valid else len(CLASSES)] += 1
        per_target.append({"target_id": target, "true_class_index": actual, "predicted_class_index": predicted,
                           "correct": match, "failure": record["failure"]})
    result = {
        "stage": "offline_raw_accuracy_only", "scored_utc": now(), "total_targets": 140,
        "coverage": covered, "coverage_fraction": covered / 140, "failures": 140 - covered,
        "correct_predictions": correct, "raw_accuracy_all_140": correct / 140,
        "primary_literal_parse_failures": sum(bool(sample.get("literal_parse_failure"))
                                               for record in records.values() for sample in record["primary_samples"]),
        "primary_grammar_failures": sum(not sample["grammar"][0]
                                         for record in records.values() for sample in record["primary_samples"]),
        "failure_policy": "Failed predictions count as incorrect; no labels substituted or targets excluded.",
        "confusion_rows_true_classes": CLASSES, "confusion_columns_predicted_classes": CLASSES + ["FAILED"],
        "confusion_matrix": confusion, "per_target": per_target,
        "graph_sha256": GRAPH_HASH, "freeze_receipt_sha256": sha((args.run_dir / "freeze_receipt.json").read_bytes()),
        "final_predictions_sha256": freeze["run_files_sha256"]["final_predictions.json"],
        "inference_or_gcn_performed": False,
    }
    require(destination.parent.is_dir(), "Score-output parent directory must already exist.")
    # Exclusive output creation; no changes to the frozen inference run.
    with destination.open("xb") as handle:
        handle.write(encoded(result))
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({key: result[key] for key in ("total_targets", "coverage", "failures", "correct_predictions", "raw_accuracy_all_140")}, indent=2))


def main(argv=None):
    root = Path(__file__).resolve().parents[2]
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("mode", nargs="?", choices=("plan", "infer", "score"), default="plan")
    argument_parser.add_argument("--prep-dir", type=Path, default=root / "experiments/narrative_v1/runs/offline_prep_001")
    argument_parser.add_argument("--run-dir", type=Path, required=True)
    argument_parser.add_argument("--resume", action="store_true")
    argument_parser.add_argument("--live", action="store_true")
    argument_parser.add_argument("--confirm", default="")
    argument_parser.add_argument("--repair-budget", type=int, default=0, help="0..420, in groups of three; default disables paid repair.")
    argument_parser.add_argument("--api-key-env", default="GAPAPI_API_KEY", help="Environment-variable NAME; never pass the key itself.")
    argument_parser.add_argument("--timeout", type=float, default=120.0)
    argument_parser.add_argument("--interval", type=float, default=1.5)
    argument_parser.add_argument("--abandon-request", action="append", default=[], metavar="REQUEST_ID")
    argument_parser.add_argument("--review-note")
    argument_parser.add_argument("--graph-file", type=Path, default=root.parent / "LLMGNN_data/cora_random_sbert.pt")
    argument_parser.add_argument("--score-output", type=Path)
    args = argument_parser.parse_args(argv)
    sys.dont_write_bytecode = True
    require(0 <= args.repair_budget <= 420 and args.repair_budget % 3 == 0, "Repair budget must be 0..420 and divisible by three.")
    require(math.isfinite(args.timeout) and args.timeout > 0 and math.isfinite(args.interval) and args.interval >= 0,
            "Timeout/interval must be finite and valid.")
    args.prep_dir = args.prep_dir.expanduser().resolve()
    args.run_dir = args.run_dir.expanduser().resolve()
    args.graph_file = args.graph_file.expanduser().resolve()
    require(not within(args.run_dir, args.prep_dir) and not within(args.prep_dir, args.run_dir),
            "Run output must be separate from immutable preparation.")
    if args.mode != "infer":
        require(not args.live and not args.confirm and not args.abandon_request, "Live/review flags are only accepted in infer mode.")
        sys.addaudithook(offline_guard)
    context = validate_inputs(root, args.prep_dir)
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
    except RunnerError as exc:
        print("STOP: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
    except Exception as exc:
        # Avoid exception messages/tracebacks that might contain transport keys.
        print("STOP: " + type(exc).__name__ + "; inspect local inputs/journal. No automatic retry.", file=sys.stderr)
        raise SystemExit(2)
