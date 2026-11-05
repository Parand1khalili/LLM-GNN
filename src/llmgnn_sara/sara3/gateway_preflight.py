"""Read-only bounded preflight for GapGPT Rich Prompt V2.

Validates our pinned wire/budget assumptions for every routed node. This
cannot prove the third-party provider actually accepts the request, nor that
Rich JSON fits the historical output limit. Never dispatches HTTP.
"""
from decimal import Decimal

from .gapgpt_live import contract_from_dict, wire_for, worst_call_cost
from .rich_evidence import rich_verifier_input_v2
from .selection import select_router

VERSION = "sara.gapgpt.wire_preflight.v1"

# These require *external* evidence / owner approval, not a synthetic API call.
EXTERNAL_UNVERIFIED = [
    "GAPGPT_CURRENT_MODEL_AND_RETURNED_IDENTIFIER",
    "GAPGPT_CURRENT_PARAMETERS_AND_RESPONSE_FORMAT",
    "RICH_JSON_COMPLETENESS_WITH_MAX_TOKENS",
    "GAPGPT_ACCOUNT_RATES_QUOTA_AND_FINAL_BILLING",
    "GAPGPT_DATA_RETENTION_AND_SHARING_TERMS",
]


def validate_batch_wire(inputs, router, budget, config):
    """Fail before journal creation if local wire/cost caps cannot cover batch."""
    cfg = contract_from_dict(config)
    selected = select_router(inputs.pairs, budget, router)
    if not selected or cfg["max_calls"] > 2 * len(selected):
        raise ValueError("Selected cohort and declared call cap are inconsistent")
    by_id = {pair.node_id: pair for pair in inputs.pairs}
    blind_sizes = []
    comparison_upper_sizes = []
    for node_id in selected:
        pair = by_id[node_id]
        blind = rich_verifier_input_v2(node_id, pair.text, pair.neighborhood)
        blind_sizes.append(len(wire_for(blind, cfg)))
        candidates = tuple(sorted((pair.b1.class_index,
                                    pair.narrative_v0.class_index)))
        # Comparison happens only after a persisted valid Blind; its class is
        # unknown during preflight. Enumerate all 7 legal Blind classes.
        comparison_upper_sizes.append(max(len(wire_for(
            rich_verifier_input_v2(node_id, pair.text, pair.neighborhood,
                                   candidates=candidates, blind_class=class_index), cfg))
            for class_index in range(7)))
    largest = max(blind_sizes + comparison_upper_sizes)
    if largest > cfg["max_input_tokens"]:
        raise ValueError("Possible request exceeds conservative byte-size input cap")
    worst = worst_call_cost(cfg) * cfg["max_calls"]
    if worst > Decimal(cfg["max_spend_usd"]):
        raise ValueError("Worst-case declared reservation exceeds declared spending cap")
    return {
        "version": VERSION,
        "status": "LOCAL_WIRE_AND_RESERVATION_PASS_PROVIDER_UNVERIFIED",
        "router": router, "budget": budget, "denominator": len(inputs.pairs),
        "selected_count": len(selected),
        "selected_node_ids": list(selected),
        "maximum_conditional_calls": 2 * len(selected),
        "call_cap": cfg["max_calls"],
        "blind_wire_bytes_total": sum(blind_sizes),
        "blind_wire_bytes_max": max(blind_sizes),
        "comparison_wire_bytes_max": max(comparison_upper_sizes),
        "largest_possible_wire_bytes": largest,
        "declared_input_cap": cfg["max_input_tokens"],
        "input_size_contract": "WIRE_UTF8_BYTES_NOT_TOKENIZER_OR_PROVIDER_TOKEN_PROOF",
        "max_tokens_requested": cfg["max_tokens"],
        "output_contract": "HISTORICAL_LIMIT_RICH_JSON_FIT_NOT_MEASURED",
        "requested_model": cfg["model"],
        "allowed_returned_models": list(cfg["allowed_returned_models"]),
        "endpoint": cfg["endpoint"],
        "temperature": cfg["temperature"],
        "n": cfg["n"],
        "declared_input_usd_per_million": cfg["input_usd_per_million"],
        "declared_output_usd_per_million": cfg["output_usd_per_million"],
        "max_spend_usd": cfg["max_spend_usd"],
        "declared_maximum_reservation_usd": str(worst),
        "money_status": "USER_DECLARED_RATE_NOT_PROVIDER_INVOICE_CAP",
        "provider_calls": 0,
        "GT_accessed": False,
        "training_runs": 0,
        "external_checks_not_verified": list(EXTERNAL_UNVERIFIED),
    }
