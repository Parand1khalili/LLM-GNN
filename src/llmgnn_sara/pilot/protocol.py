"""Pure scientific-pilot preparation. There is deliberately no provider client.

Blind requests can be frozen exactly now. Comparison requests depend on the
future validated blind result, so only a conditional template can be frozen now.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Callable, Mapping

from ..io.frozen import reject_gt
from ..sara2.policy import CLASSES, validated_pairs, route_r0
from ..sara3.atlas import ATLAS, route_semantic

BLIND_CLASS_SLOT = "$BLIND_CLASS_INDEX"
_SHA = re.compile(r"[0-9a-f]{64}")
_BASE_FIELDS = {"phase", "node_id", "target", "neighborhood", "class_atlas",
                "instructions", "response_schema"}
_NEIGHBOR_FIELDS = {"neighbor_ids", "representative_id", "degree", "connected_pairs",
                    "disconnected_pairs", "context", "graph_sha256", "source_sha256",
                    "verification_level"}
_HISTORY = {"b1", "narrative_v0", "votes", "vote", "predictions", "prediction",
            "prior_labels", "historical_candidates", "confidence", "confidence_percent",
            "confidence_percent_before_tensor_cast", "blind_class_index"}
_CREDENTIALS = {"api_key", "apikey", "authorization", "password", "secret", "access_token",
                "refresh_token", "credentials", "credential"}


@dataclass(frozen=True, slots=True)
class PilotConfig:
    """Predeclared feasibility scope, not a post-GT threshold optimization."""
    per_router: int = 3
    max_generation_calls: int = 12
    max_input_tokens_per_call: int = 16384
    max_output_tokens_per_call: int = 512
    timeout_seconds: int = 120
    retries: int = 0

    def __post_init__(self):
        if (type(self.per_router) is not int or self.per_router != 3
                or type(self.max_generation_calls) is not int or self.max_generation_calls != 12
                or type(self.retries) is not int or self.retries != 0):
            raise ValueError("Pilot is fixed at six cases, twelve calls and zero retries")
        for name in ("max_input_tokens_per_call", "max_output_tokens_per_call", "timeout_seconds"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError("Invalid pilot resource bound")


def _encoded(value) -> bytes:
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError, RecursionError):
        raise ValueError("Pilot data is not finite JSON") from None


def _digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _safe_path(path: Path) -> Path:
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError("Symlink output path rejected")
    resolved = path.resolve()
    forbidden = {"prnd-project", "llmgnn_reference", "mydrive", "recovered_sources"}
    if forbidden.intersection(p.casefold() for p in resolved.parts):
        raise ValueError("Historical or mounted Drive output rejected")
    if str(resolved).replace("\\", "/").startswith(("/content/drive/", "/content/gdrive/")):
        raise ValueError("Mounted Drive output rejected")
    return resolved


def _inspect_keys(value, *, blind: bool, depth: int = 0):
    if depth > 24:
        raise ValueError("Pilot input nesting limit exceeded")
    if isinstance(value, dict):
        for key, item in value.items():
            if type(key) is not str or key.casefold() in _CREDENTIALS:
                raise ValueError("Sensitive pilot field rejected")
            if blind and key.casefold() in _HISTORY:
                raise ValueError("Blind-first request contains historical predictions")
            _inspect_keys(item, blind=blind, depth=depth + 1)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _inspect_keys(item, blind=blind, depth=depth + 1)


def _index(value):
    if type(value) is not int or not 0 <= value < len(CLASSES):
        raise ValueError("Invalid blind class index")
    return value


def _request(value: dict, node: int, *, comparison: bool, conditional: bool = True) -> dict:
    # Copy through canonical finite JSON before inspection/sealing: caller mutation
    # cannot alter bytes after validation. No raw graph/GT object is accepted.
    if type(value) is not dict:
        raise ValueError("Pilot requests must be explicit JSON objects")
    value = json.loads(_encoded(value))
    reject_gt(value)
    _inspect_keys(value, blind=not comparison)
    fields = _BASE_FIELDS | ({"historical_candidates", "blind_class_index"} if comparison else set())
    if set(value) != fields or type(value["node_id"]) is not int or value["node_id"] != node:
        raise ValueError("Pilot request fields or node identity differ")
    if value["phase"] not in (("compare", "comparison") if comparison else ("blind",)):
        raise ValueError("Pilot request phase differs")
    target, neighbors = value["target"], value["neighborhood"]
    if (type(target) is not dict or set(target) != {"text", "source_sha256"}
            or type(target["text"]) is not str or not target["text"].strip()
            or not isinstance(target["source_sha256"], str) or not _SHA.fullmatch(target["source_sha256"])):
        raise ValueError("Invalid target evidence or provenance")
    if type(neighbors) is not dict or set(neighbors) != _NEIGHBOR_FIELDS:
        raise ValueError("Invalid neighborhood evidence fields")
    ids = neighbors["neighbor_ids"]
    if (type(ids) is not list or any(type(i) is not int or not 0 <= i < 2708 or i == node for i in ids)
            or len(set(ids)) != len(ids) or type(neighbors["degree"]) is not int
            or neighbors["degree"] < len(ids)
            or (neighbors["representative_id"] is not None and neighbors["representative_id"] not in ids)
            or type(neighbors["context"]) is not str
            or type(neighbors["verification_level"]) is not str or not neighbors["verification_level"]):
        raise ValueError("Invalid neighborhood identity")
    for name in ("graph_sha256", "source_sha256"):
        if type(neighbors[name]) is not str or not _SHA.fullmatch(neighbors[name]):
            raise ValueError("Invalid neighborhood provenance hash")
    pairs = []
    for name in ("connected_pairs", "disconnected_pairs"):
        items = neighbors[name]
        if type(items) is not list:
            raise ValueError("Invalid neighbor pair evidence")
        normalized = []
        for pair in items:
            if (type(pair) is not list or len(pair) != 2 or any(type(i) is not int or i not in ids for i in pair)
                    or pair[0] == pair[1]):
                raise ValueError("Invalid neighbor pair evidence")
            normalized.append(tuple(sorted(pair)))
        if len(set(normalized)) != len(normalized):
            raise ValueError("Duplicate neighbor pair evidence")
        pairs.append(set(normalized))
    if pairs[0] & pairs[1]:
        raise ValueError("Conflicting neighbor pair evidence")
    expected_atlas = [{"name": entry.name, "definition": entry.definition} for entry in ATLAS]
    if value["class_atlas"] != expected_atlas:
        raise ValueError("Public class atlas order or definitions differ")
    if type(value["instructions"]) is not str or not value["instructions"].strip():
        raise ValueError("Explicit verifier instructions required")
    if type(value["response_schema"]) is not dict or not value["response_schema"]:
        raise ValueError("Explicit verifier schema required")
    if comparison:
        candidates = value["historical_candidates"]
        if type(candidates) is not list or not 1 <= len(candidates) <= 2:
            raise ValueError("One or two original candidate classes required")
        for index in candidates:
            _index(index)
        if len(set(candidates)) != len(candidates):
            raise ValueError("Duplicate historical candidates")
        if conditional:
            if value["blind_class_index"] != BLIND_CLASS_SLOT:
                raise ValueError("Future comparison must preserve the blind-result slot")
        else:
            _index(value["blind_class_index"])
    blob = _encoded(value)
    if len(blob) > 256 * 1024:
        raise ValueError("Pilot request byte limit exceeded")
    return value


def materialize_comparison(template: dict, blind_class_index: int) -> dict:
    """Bind a validated future class without changing any frozen evidence/template.

    Callers must record the template hash, validated blind-response hash and final
    payload hash in the execution ledger. This helper never dispatches a request.
    """
    if type(template) is not dict or type(template.get("node_id")) is not int:
        raise ValueError("Comparison template identity required")
    result = _request(template, template["node_id"], comparison=True)
    result["blind_class_index"] = _index(blind_class_index)
    return _request(result, result["node_id"], comparison=True, conditional=False)


def select_pilot(pairs, config: PilotConfig = PilotConfig()) -> dict:
    rows = validated_pairs(pairs)
    if len(rows) < 2 * config.per_router:
        raise ValueError("At least six distinct eligible targets required")
    baseline = route_r0(rows, len(rows))
    semantic = route_semantic(rows, len(rows))
    first = baseline[:config.per_router]
    second = tuple(node for node in semantic if node not in first)[:config.per_router]
    return {"rule": "top3_reconstructed_R0_then_top3_distinct_semantic_rank; node-ID ties",
            "selected_node_ids": list(first + second), "baseline_stratum": list(first),
            "semantic_unique_stratum": list(second),
            "top3_router_overlap_count": len(set(first) & set(semantic[:config.per_router])),
            "cohort_size": len(rows), "replacement_after_outputs": False,
            "sampling_scope": "PURPOSIVE_FEASIBILITY_NOT_UNBIASED_COHORT_ACCURACY",
            "historical_policy_002_equivalence": False}


def _price(value):
    if value is None:
        return None
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("Invalid price assumption")
    return float(value)


def seal_pilot(pairs, blind_inputs: Mapping[int, dict], comparison_templates: Mapping[int, dict],
               output_dir: Path, *, token_counter: Callable[[str], int] | None = None,
               model: str | None = None, provider: str | None = None,
               input_price_per_million: float | None = None,
               output_price_per_million: float | None = None,
               source_provenance: Mapping[str, str] | None = None,
               config: PilotConfig = PilotConfig()) -> dict:
    """Create a new immutable-by-contract request bundle; never execute it.

    A local token counter must be explicitly provisioned by the caller. The
    default estimate is character-based and never downloads tokenizer files.
    """
    rows = validated_pairs(pairs)
    selection = select_pilot(rows, config)
    output = _safe_path(Path(output_dir))
    if output.exists():
        raise FileExistsError("Pilot output already exists; never overwrite a seal")
    prices = _price(input_price_per_million), _price(output_price_per_million)
    for value in (model, provider):
        if value is not None and (type(value) is not str or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}", value)):
            raise ValueError("Invalid non-secret provider/model identifier")
    provenance = dict(source_provenance or {})
    if any(type(k) is not str or type(v) is not str or not _SHA.fullmatch(v) for k, v in provenance.items()):
        raise ValueError("Source provenance must contain SHA-256 values only")
    contents, token_rows = {}, []
    by_id = {row.node_id: row for row in rows}

    def count(value):
        text = _encoded(value).decode("utf-8")
        estimate = token_counter(text) if token_counter is not None else math.ceil(len(text) / 4)
        if type(estimate) is not int or not 0 < estimate <= config.max_input_tokens_per_call:
            raise ValueError("Pilot input token estimate exceeds the configured limit")
        return estimate

    for node in selection["selected_node_ids"]:
        if node not in blind_inputs or node not in comparison_templates:
            raise ValueError("Required pilot node evidence unavailable")
        blind = _request(blind_inputs[node], node, comparison=False)
        compare = _request(comparison_templates[node], node, comparison=True)
        if blind["target"] != compare["target"] or blind["neighborhood"] != compare["neighborhood"]:
            raise ValueError("Blind/comparison source evidence differs")
        if compare["historical_candidates"] != sorted({by_id[node].b1.class_index, by_id[node].narrative_v0.class_index}):
            raise ValueError("Comparison candidates differ from frozen annotations")
        if blind["target"]["text"] != by_id[node].text:
            raise ValueError("Pilot text differs from routing evidence")
        contents[f"requests/blind-{node}.json"] = _encoded(blind)
        contents[f"templates/compare-{node}.json"] = _encoded(compare)
        bound = max(count(materialize_comparison(compare, index)) for index in range(7))
        token_rows.append({"node_id": node, "blind_input_tokens_estimate": count(blind),
                           "comparison_input_tokens_max_over_7_bindings": bound})
    input_tokens = sum(row["blind_input_tokens_estimate"] + row["comparison_input_tokens_max_over_7_bindings"]
                       for row in token_rows)
    output_tokens = config.max_generation_calls * config.max_output_tokens_per_call
    cost = None if None in prices else (input_tokens * prices[0] + output_tokens * prices[1]) / 1_000_000
    report = {
        "schema": "sara.pilot_protocol.v1", "status": "SEALED_OFFLINE_NOT_EXECUTED",
        "live_readiness": "NO_GO_PENDING_SEPARATE_OWNER_APPROVAL_AND_PROVIDER_PREFLIGHT",
        "selection": selection, "config": asdict(config), "model": model, "provider": provider,
        "source_provenance": provenance,
        "input_token_estimates": token_rows, "total_input_tokens_estimate": input_tokens,
        "maximum_output_tokens_under_call_cap": output_tokens,
        "token_estimate_method": "EXPLICIT_LOCAL_COUNTER_NOT_PROVIDER_TOKEN_COUNT" if token_counter else "CHARACTER_COUNT_DIVIDED_BY_4_HEURISTIC",
        "normalized_cost_coefficients_per_million": {"input": input_tokens / 1_000_000,
                                                      "output": output_tokens / 1_000_000},
        "price_assumptions_usd_per_million": {"input": prices[0], "output": prices[1]},
        "estimated_max_cost_usd_under_assumptions": cost,
        "cost_status": "UNKNOWN_NO_PRICE_ASSUMPTIONS" if cost is None else "SCENARIO_NOT_VERIFIED_VENDOR_PRICE_OR_BILLING_CAP",
        "generation_call_cap": 12, "token_count_api_calls_planned": 0, "automatic_retries": 0,
        "comparison_binding": "Validate blind class0..6, bind only blind_class_index; record template/response/final-payload hashes before dispatch",
        "comparison_future_exact_bytes": "CONDITIONAL_NOT_YET_KNOWN",
        "timeout_policy": "UNCERTAIN_INTENT_COUNTS_AGAINST_BUDGET_NO_AUTOMATIC_RETRY",
        "retention_policy": "UNAPPROVED; store=false alone does not establish Zero Data Retention",
        "credentials": "USER_APPROVED_ENVIRONMENT_MECHANISM_REQUIRED_NEVER_STORED_IN_BUNDLE",
        "failure_policy": "Malformed schema/evidence, conflict, missing data or uncertain timeout abstains; no substitute labels",
        "third_class_training_allowed": False,
        "evaluation": {"scope": "Purposive feasibility, schema/evidence/coverage/failure/resource checks",
                       "accuracy_and_corrections": "Future isolated GT evaluation only after decisions freeze and separate authorization",
                       "downstream_primary": "CE/noPS matched baselines versus future accepted SARA output",
                       "downstream_supplementary": "WCE/noPS, chosen after prior exploratory results",
                       "paired_seeds": list(range(10)), "epochs": 30, "training": "NOT_RUN"},
        "required_before_live": ["owner spending and data-sharing approval", "provider/model compatibility and pricing verification",
                                 "credentials/account mechanism", "retention policy approval", "sealed manifest SHA review",
                                 "durable intent ledger reviewed and bound to this seal"],
        "provider_calls": 0, "training_runs": 0, "GT_decoded": False,
    }
    contents["pilot_protocol.json"] = _encoded(report)
    manifest = {"schema": "sara.pilot_seal.v1", "files": {name: _digest(blob) for name, blob in sorted(contents.items())}}
    manifest_blob = _encoded(manifest)
    # Everything validates before the first write. Exclusive writes prevent even
    # accidental replacement of previously frozen requests or protocol records.
    output.mkdir(parents=True, exist_ok=False)
    for name, blob in contents.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(blob)
    with (output / "SHA256.json").open("xb") as stream:
        stream.write(manifest_blob)
    digest = _digest(manifest_blob)
    verify_pilot(output, digest)
    return {**report, "output_dir": str(output), "manifest_sha256": digest}


def verify_pilot(output_dir: Path, expected_manifest_sha256: str) -> dict:
    """Readback against an externally recorded seal digest, not bundle claims."""
    root = _safe_path(Path(output_dir))
    if type(expected_manifest_sha256) is not str or not _SHA.fullmatch(expected_manifest_sha256):
        raise ValueError("Expected manifest SHA-256 required")
    blob = (root / "SHA256.json").read_bytes()
    if _digest(blob) != expected_manifest_sha256:
        raise ValueError("Pilot seal hash conflict")
    manifest = json.loads(blob)
    files = manifest.get("files")
    if manifest.get("schema") != "sara.pilot_seal.v1" or type(files) is not dict:
        raise ValueError("Invalid pilot seal schema")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual != set(files) | {"SHA256.json"}:
        raise ValueError("Pilot seal inventory differs")
    for name, digest in files.items():
        parts = name.split("/")
        if (not parts or any(part in ("", ".", "..") for part in parts) or "\\" in name or ":" in name
                or name.startswith("/") or type(digest) is not str or not _SHA.fullmatch(digest)):
            raise ValueError("Unsafe pilot seal member")
        path = _safe_path(root / name)
        if not path.is_relative_to(root) or _digest(path.read_bytes()) != digest:
            raise ValueError("Pilot member hash conflict")
    return {"status": "PASS", "manifest_sha256": expected_manifest_sha256, "verified_files": len(files)}
