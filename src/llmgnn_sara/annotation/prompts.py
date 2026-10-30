"""Historical prompt adapters with explicit frozen wrapper and tokenization.

The complete classification template must come from the hash-verified matched
preparation receipt. We do not guess the historical question or silently use a
modern tokenizer. Narrative topology is the exact recovered pure source module.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..io.frozen import CLASSES, InputError, read_pinned_json
from ._narrative_v0 import augment_consensus_prompt

SENTINEL = "<TARGET_OR_TARGET_PLUS_STRUCTURAL_CONTEXT>"
# run_matched.py PREP_RECEIPT_HASH, preserved verbatim in recovered source.
MATCHED_PREPARATION_SHA256 = "fb6777e8dec547b2aee5ca664ffa566f9148a944c7ee6065072df9fb1b4ad4ab"
COMMON_INSTRUCTION = (
    "\n\nUsage instruction:\n"
    "Treat neighborhood information only as auxiliary evidence. "
    "Infer the topic primarily from the target paper. "
    "If neighborhood evidence conflicts with the target text, "
    "prioritize the target text."
)


@dataclass(frozen=True)
class FrozenPromptTemplate:
    """A validated wrapper; semantic byte identity comes from receipt hash pinning."""
    text: str
    source_sha256: str = "SYNTHETIC_OR_CALLER_SUPPLIED_NOT_HASH_VERIFIED"

    def __post_init__(self):
        if not isinstance(self.text, str) or self.text.count(SENTINEL) != 1:
            raise InputError("Exactly one historical template sentinel required")

    @classmethod
    def from_receipt(cls, path, expected_sha256=MATCHED_PREPARATION_SHA256):
        receipt = read_pinned_json(path, expected_sha256)
        if not isinstance(receipt, dict):
            raise InputError("Historical preparation receipt must be an object")
        wrapper = receipt.get("historical_wrapper", {})
        if (not isinstance(wrapper, dict) or wrapper.get("ordered_class_names") != list(CLASSES)
                or wrapper.get("need_tasks") is not False or wrapper.get("k") != 3
                or wrapper.get("dataset_name") != "cora"):
            raise InputError("Historical prompt wrapper metadata mismatch")
        return cls(wrapper.get("exact_complete_template_with_sentinel"), expected_sha256)

    def wrap(self, text: str) -> str:
        if not isinstance(text, str) or not text.strip():
            raise InputError("Nonempty target text required")
        prefix, suffix = self.text.split(SENTINEL)
        return prefix + text + suffix


def build_b1_prompt(target_text: str, template: FrozenPromptTemplate) -> str:
    """Target-only classification; preserve the target's original whitespace."""
    if not isinstance(template, FrozenPromptTemplate):
        raise InputError("Explicit frozen template required")
    return template.wrap(target_text)


def build_consensus(representative_text: str, support_count: int, selected_count: int, tokenizer) -> str:
    """Adapt prompt_builder.build_consensus's exact prose and fit algorithm.

tokenizer must provide encode/decode; historical execution used cl100k_base.
The injected tokenizer is never initialized/downloaded by this module.
"""
    if (not isinstance(representative_text, str) or type(selected_count) is not int
            or type(support_count) is not int or not 1 <= support_count <= selected_count):
        raise InputError("Invalid frozen consensus inputs")
    prefix = "LOCAL NEIGHBORHOOD EVIDENCE\n\nRepresentative direct 1-hop neighbor:\n"
    suffix = ("\n\nAdditional semantic support:\n"
              f"{max(0, support_count - 1)} of the {max(0, selected_count - 1)} other retrieved "
              "direct neighbors are semantically consistent with the representative neighbor."
              + COMMON_INSTRUCTION)
    fixed = len(tokenizer.encode(prefix)) + len(tokenizer.encode(suffix))
    body_ids = tokenizer.encode(representative_text)
    shortened = representative_text if len(body_ids) <= max(0, 256 - fixed) else tokenizer.decode(body_ids[:max(0, 256 - fixed)])
    result = prefix + shortened + suffix
    while len(tokenizer.encode(result)) > 256 and shortened:
        shortened = tokenizer.decode(tokenizer.encode(shortened)[:-1])
        result = prefix + shortened + suffix
    if len(tokenizer.encode(result)) > 256:
        raise InputError("Fixed consensus overhead exceeds historical budget")
    return result


def build_narrative_prompt(target_text: str, template: FrozenPromptTemplate,
                           consensus_prompt: str, target_id: int, neighbor_ids,
                           representative_id: int | None, adjacency, count_tokens,
                           *, verified_descriptors=None):
    """Use exact recovered topology augmentation; no graph label object accepted.

The frozen target/neighbor IDs and consensus must be supplied, not reselected.
An isolated target explicitly falls back to B1, rather than fabricating context.
"""
    if type(target_id) is not int or target_id < 0:
        raise InputError("Nonnegative global target ID required")
    if not isinstance(template, FrozenPromptTemplate):
        raise InputError("Explicit frozen template required")
    neighbors = tuple(neighbor_ids)
    if not neighbors:
        if representative_id is not None or consensus_prompt:
            raise InputError("Isolated-target fallback must not contain invented evidence")
        return build_b1_prompt(target_text, template), {
            "fallback": "B1_NO_NEIGHBORS", "target_id": target_id,
            "structural_tokens": 0, "provenance": template.source_sha256}
    structural, diagnostics = augment_consensus_prompt(
        consensus_prompt, target_id, neighbors, representative_id, adjacency,
        count_tokens, verified_descriptors=verified_descriptors)
    full = template.wrap(target_text.rstrip() + "\n\n" + structural)
    return full, diagnostics


def disabled_provider(*args, **kwargs):
    """There is no live execution path in the approved offline implementation."""
    raise PermissionError("Live provider execution is disabled; separate authorization required")
