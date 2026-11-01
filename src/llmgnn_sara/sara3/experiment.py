"""Pinned draft routing contract and offline-only request identity rules."""
from dataclasses import asdict, dataclass
import hashlib
import json
import re

from ..annotation.prompts import MATCHED_PREPARATION_SHA256
from ..io.frozen import PINS as FROZEN_PINS, read_pinned_json, reject_gt
from ..io.project import PINS as PROJECT_PINS
from ..sara2.policy import CLASSES, PolicyConfig, route_r0, validated_pairs
from .atlas import route_semantic
from .inputs import canonical_bytes, pair_inputs
from .r1_candidate import VERSION as R1_V1, route_r1_candidate
from .r1_coverage import VERSION as R1_V2, route_r1_candidate_v2
from .r2_candidate import VERSION as R2_V1, route_r2_candidate

VERSION = "sara.routing.experiment.draft.v1"
MANIFEST_SHA256 = "dd2cd784e58cbb905ffa6c337782ef67073960a11ca32d07e8f9991dcc71387b"
LEGACY_SCHEMA = "sara.verifier.legacy.v1"  # New explicit identifier for the unchanged legacy schema.
FIXTURE_VERSION = "sara.routing.synthetic.v1"
SOURCES = {**FROZEN_PINS, **PROJECT_PINS, "preparation": MATCHED_PREPARATION_SHA256}
MODEL_PLACEHOLDERS = dict.fromkeys(("provider", "endpoint", "api_style", "model", "temperature",
    "seed", "max_output_tokens", "tools", "retention", "reasoning", "service_tier"))


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def request_identity(payload, context, *, blind_response_sha256=None):
    """Complete effective request/context identity; unresolved comparison is not reusable."""
    reject_gt(payload)
    reject_gt(context)
    if (type(context) is not dict or set(context) != {"mode", "fixture_version", "experiment_version",
            "cohort_sha256", "protocol_sha256", "model_settings"}
            or context["mode"] != "OFFLINE_SYNTHETIC_ONLY"
            or type(context["model_settings"]) is not dict
            or set(context["model_settings"]) != set(MODEL_PLACEHOLDERS)):
        raise ValueError("Explicit offline execution context required")
    if payload.get("phase") == "compare":
        if (type(payload.get("blind_class_index")) is not int or not 0 <= payload["blind_class_index"] < 7
                or not re.fullmatch(r"[0-9a-f]{64}", blind_response_sha256 or "")):
            raise ValueError("Comparison dependency not materialized")
    elif payload.get("phase") != "blind" or blind_response_sha256 is not None:
        raise ValueError("Invalid request phase/dependency")
    return digest({"identity_version": "sara.request.identity.v1", "effective_request": payload,
                   "execution_context": context, "blind_response_sha256": blind_response_sha256})


def _manifest(pairs):
    rows = validated_pairs(pairs)
    if len(rows) != 140:
        raise ValueError("Draft requires the frozen140 cohort")
    cohort = digest([asdict(p) for p in rows])
    first_blind, first_compare = pair_inputs(rows[0])
    protocol = {"schema_version": LEGACY_SCHEMA, "pipeline_response_version": None,
        "response_schema": first_blind["response_schema"], "class_order": list(CLASSES),
        "class_atlas_sha256": digest(first_blind["class_atlas"]),
        "blind_instructions_sha256": digest(first_blind["instructions"]),
        "comparison_instructions_sha256": digest(first_compare["instructions"]),
        "comparison_rule": "ONLY_AFTER_VALID_NON_ABSTAINING_BLIND; STOP_ON_FAILURE; NO_AUTOMATIC_RETRY",
        "dispatch_order": "FROZEN_COHORT_ORDER", "policy": asdict(PolicyConfig()),
        "l2_status": "NOT_ASSESSED", "third_class_training_allowed": False}
    context = {"mode": "OFFLINE_SYNTHETIC_ONLY", "fixture_version": FIXTURE_VERSION,
        "experiment_version": VERSION, "cohort_sha256": cohort, "protocol_sha256": digest(protocol),
        "model_settings": dict(MODEL_PLACEHOLDERS)}
    selectors = {"r0": ("CONTROL", "r0_current@dc08852ce918c9ac8ed91f97d6dcded2ed351e11", route_r0(rows, 37)),
        "r1_v2": ("PRIMARY_CANDIDATE", R1_V2, route_r1_candidate_v2(rows)),
        "r2_v1": ("PRIMARY_CANDIDATE", R2_V1, route_r2_candidate(rows)),
        "semantic_v0": ("OPTIONAL_EXPLORATORY", "semantic_v0@dc08852ce918c9ac8ed91f97d6dcded2ed351e11", route_semantic(rows, 37)),
        "r1_v1": ("OPTIONAL_EXPLORATORY", R1_V1, route_r1_candidate(rows))}
    arms = {name: {"role": role, "router_version": version, "selected_ids": list(ids),
                   "selection_sha256": digest(list(ids)), "budget": 37}
            for name, (role, version, ids) in selectors.items()}
    requests = {}
    for p in rows:
        blind, comparison = pair_inputs(p)
        requests[str(p.node_id)] = {"target_sha256": blind["target"]["source_sha256"],
            "neighborhood_sha256": digest(blind["neighborhood"]), "blind_payload_sha256": digest(blind),
            "comparison_template_sha256": digest(comparison),
            "blind_identity": request_identity(blind, context), "comparison_identity": None}
    primary = ("r0", "r1_v2", "r2_v1")
    union = {n for name in primary for n in arms[name]["selected_ids"]}
    return {"schema_version": VERSION, "status": "DRAFT", "live_execution": "NOT_AUTHORIZED_FOR_LIVE_EXECUTION",
        "cohort_ids_in_order": [p.node_id for p in rows], "cohort_sha256": cohort,
        "source_hashes": dict(SOURCES), "budget": 37, "primary_arms": list(primary), "arms": arms,
        "r2": {"seed": "primary", "hash_domain": R2_V1 + ":explore:<node ID>",
               "stage_order": ["unknown_exploration", "observed_risk", "candidate_risk"],
               "allocation": [4, 17, 16], "backfill": "GLOBAL_R0_LAST"},
        "protocol": protocol, "execution_context": context, "requests_by_node": requests,
        "accounting": {"standalone_per_arm": {name: {"selected": 37, "blind_identities": 37,
            "potential_conditional_comparisons": 37, "maximum_generation_calls": 74} for name in arms},
            "primary_standalone_sum_maximum_calls": 222, "primary_union_selected_nodes": len(union),
            "primary_union_blind_identities": len({requests[str(n)]["blind_identity"] for n in union}),
            "primary_union_potential_conditional_comparisons": len(union),
            "primary_union_maximum_generation_calls": 2 * len(union),
            "bound_assumption": "ONE_BOUND_BLIND_RESULT_PER_IDENTITY; NO_RETRY; COMPARISON_ONLY_IF_ELIGIBLE",
            "provider_token_counts": None, "prices": None, "costs": None, "actual_response_dependent_calls": None}}


def build_manifest(inputs):
    if dict(inputs.provenance) != SOURCES:
        raise ValueError("Authenticated source pins differ")
    return _manifest(inputs.pairs)


@dataclass(frozen=True)
class VerifiedSelection:
    manifest_bytes: bytes
    arm: str

    def resolve(self, pairs, budget, response_version, config):
        if (type(self.manifest_bytes) is not bytes
                or hashlib.sha256(self.manifest_bytes).hexdigest() != MANIFEST_SHA256):
            raise ValueError("Unverified experiment manifest")
        manifest = json.loads(self.manifest_bytes)
        if (manifest != _manifest(pairs) or self.arm not in manifest["arms"] or budget != 37
                or response_version is not None or config != PolicyConfig()):
            raise ValueError("Experiment inputs/protocol/selection differ")
        return tuple(manifest["arms"][self.arm]["selected_ids"])


def load_selection(path, expected_sha256, arm, inputs):
    if expected_sha256 != MANIFEST_SHA256:
        raise ValueError("Draft manifest pin differs")
    manifest = read_pinned_json(path, expected_sha256)
    if manifest != build_manifest(inputs) or arm not in manifest["arms"]:
        raise ValueError("Experiment contract differs")
    blob = (json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    selection = VerifiedSelection(blob, arm)
    selection.resolve(inputs.pairs, 37, None, PolicyConfig())
    return selection
