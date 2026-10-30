"""Authentic-input offline run and pilot artifacts; no network or training path."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import ast

from ..io.project import load_project_inputs
from ..annotation.replay import replay_dataset
from ..sara3.pipeline import LexicalFixtureVerifier, run_offline
from ..sara3.inputs import canonical_bytes, pair_inputs
from ..downstream.frozen import baseline_plans, plan_from_frozen
from .protocol import _safe_path, _request, seal_pilot


GAPAPI = {"model": "gpt-6-luna", "temperature": 0.7, "n": 1, "max_tokens": 512}


def historical_compatibility():
    root = Path(__file__).resolve().parents[3]
    name = "recovered_sources/experiments/matched_cora/run_matched.py"
    manifest = json.loads((root / "manifests/recovered_sources.json").read_text(encoding="utf-8"))
    entry = next(r for r in manifest["files"] if r["local_path"] == name)
    blob = (root / name).read_bytes()
    if hashlib.sha256(blob).hexdigest() != entry["sha256"]:
        raise ValueError("Historical provider source hash differs")
    constants = {n.targets[0].id: ast.literal_eval(n.value)
                 for n in ast.parse(blob.decode("utf-8-sig")).body
                 if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                 and n.targets[0].id in ("MODEL", "ENDPOINT")}
    if constants != {"MODEL": GAPAPI["model"], "ENDPOINT": "https://api.gapapi.com/v1/chat/completions"}:
        raise ValueError("Historical provider/model differs")
    return {"source_sha256": entry["sha256"], "model_and_endpoint": "STATIC_SOURCE_VERIFIED",
            "request_model_n_temperature": "VERIFIED_IN_ALL_840_PINNED_PROMPT_REFERENCES",
            "current_gateway_compatibility": "UNVERIFIED_NO_API_REQUESTS", "max_tokens_support": "UNVERIFIED"}


def gapapi_body(logical_request):
    """Static Chat Completions envelope; current gateway acceptance is unverified."""
    if type(logical_request) is not dict:
        raise ValueError("Explicit logical verifier request required")
    comparison = logical_request.get("phase") == "compare"
    logical_request = _request(logical_request, logical_request.get("node_id"), comparison=comparison,
                               conditional=logical_request.get("blind_class_index") == "$BLIND_CLASS_INDEX")
    return {**GAPAPI, "messages": [{"role": "user", "content": canonical_bytes(logical_request).decode()}]}


def _local_counter(cache):
    if cache is None:
        return None
    import os
    import tiktoken
    path = Path(cache)
    blob = (path / "9b5ad71b2ce5302211f9c61530b329a4922fc6a4").read_bytes()
    if hashlib.sha256(blob).hexdigest() != "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7":
        raise ValueError("Pinned tokenizer vocabulary unavailable")
    # Only the supplied verified cache can be used; no implicit download.
    previous = os.environ.get("TIKTOKEN_CACHE_DIR")
    os.environ["TIKTOKEN_CACHE_DIR"] = str(path.resolve())
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    finally:
        if previous is None:
            os.environ.pop("TIKTOKEN_CACHE_DIR", None)
        else:
            os.environ["TIKTOKEN_CACHE_DIR"] = previous
    return lambda text: len(encoding.encode(text)) + 64


def prepare_authentic(frozen_root, authentic_root, output_dir, *, budget=37, tokenizer_cache=None):
    inputs = load_project_inputs(frozen_root, authentic_root)
    replay = replay_dataset(inputs.frozen)
    if replay["status"] != "PASS":
        raise ValueError("Frozen replay differs; pilot preparation stopped")
    counter = _local_counter(tokenizer_cache)
    compatibility = historical_compatibility()
    output = _safe_path(Path(output_dir))
    if output.exists():
        raise FileExistsError("Offline output exists; keep the prior artifacts")
    runs = {router: run_offline(inputs.pairs, budget, router, LexicalFixtureVerifier())
            for router in ("r0", "semantic")}
    blind, comparison = {}, {}
    for pair in inputs.pairs:
        blind[pair.node_id], comparison[pair.node_id] = pair_inputs(pair)
    plans = {}
    for cohort in ("primary", "sensitivity"):
        for loss in ("ce", "wce"):
            plans[f"{cohort}_{loss}"] = {
                "comparison_role": "PRIMARY" if loss == "ce" else "SUPPLEMENTARY_PREVIOUSLY_SELECTED",
                "baselines": baseline_plans(inputs.frozen, cohort, loss, "both"),
                "fixture_sara_not_measured": plan_from_frozen(inputs.frozen, cohort, loss,
                                                             accepted=runs["semantic"]["decisions"]),
                "future_live_output": "REPLACE_FIXTURES_ONLY_AFTER_APPROVED_VERIFICATION_AND_FROZEN_OUTPUT_ADMISSION"}
    # All source validation and dry-runs precede the first output write.
    output.mkdir(parents=True, exist_ok=False)
    pilot = seal_pilot(inputs.pairs, blind, comparison, output / "pilot", token_counter=counter,
                       model="gpt-6-luna", provider="GapAPI", input_price_per_million=1,
                       output_price_per_million=4, source_provenance=dict(inputs.provenance))
    summary = {"status": "OFFLINE_FIXTURE_RUN_NOT_SCIENTIFIC_VERIFIER_RESULTS", "targets": len(inputs.pairs),
               "admission": {"texts": len(inputs.pairs), "recorded_neighborhoods": len(inputs.pairs),
                             "prompt_hashes_matched": 280, "sample_prompt_references_matched": 840,
                             "source_sha256": dict(inputs.provenance),
                             "canonical_graph_recomputed": False},
               "replay_matched": replay["predictions_matched"], "routers": {},
               "pilot": {k: pilot[k] for k in ("selection", "generation_call_cap", "manifest_sha256",
                         "total_input_tokens_estimate", "maximum_output_tokens_under_call_cap",
                         "estimated_max_cost_usd_under_assumptions", "cost_status", "live_readiness")},
               "cost_caveat": "Illustrative $1/$4 per million, NOT verified GapAPI pricing; cl100k surrogate+64 framing allowance is NOT provider tokenization",
               "provider_calls": 0, "training_runs": 0, "GT_decoded": False}
    contents = {}
    for router, result in runs.items():
        result["input_provenance"] = "AUTHENTIC_HASH_VERIFIED_PROJECT_INPUTS"
        result["verifier_output_provenance"] = "DETERMINISTIC_LEXICAL_FIXTURES_NOT_LLM_OUTPUTS"
        summary["routers"][router] = {key: result[key] for key in (
            "target_count", "review_count", "completed_review_count", "accepted_count", "abstention_count",
            "selected_node_ids", "coverage", "class_retention_counts", "mock_verifier_calls")}
        summary["routers"][router]["decision_reasons"] = dict(Counter(d["reason"] for d in result["decisions"]))
        summary["routers"][router]["failures"] = sum(d["reason"].startswith(("VERIFICATION_REJECTED", "TIMEOUT")) for d in result["decisions"])
        contents[f"dry_run_{router}.json"] = result
    contents["gcn_plans.json"] = plans
    for node in pilot["selection"]["selected_node_ids"]:
        contents[f"gapapi/blind-{node}.json"] = gapapi_body(blind[node])
        contents[f"gapapi/compare-template-{node}.json"] = gapapi_body(comparison[node])
    contents["provider_compatibility.json"] = {
        "provider": "GapAPI", "endpoint": "https://api.gapapi.com/v1/chat/completions", **GAPAPI,
        "static_historical_configuration": "MATCHES_PINNED_REQUEST_MODEL_N_TEMPERATURE_AND_RUNNER_ENDPOINT",
        **compatibility,
        "public_docs_check": "No usable current provider/model pricing documentation located; website fetch returned404",
        "retention_and_prices": "UNAPPROVED_UNKNOWN", "execution_enabled": False}
    contents["summary.json"] = summary
    for name, data in contents.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(canonical_bytes(data))
    files = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in output.rglob("*") if p.is_file()}
    with (output / "SHA256.json").open("xb") as stream:
        stream.write(canonical_bytes({"files": files}))
    return {**summary, "output_dir": str(output), "artifact_manifest_sha256": hashlib.sha256((output / "SHA256.json").read_bytes()).hexdigest()}
