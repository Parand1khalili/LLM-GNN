"""Offline Narrative Consensus v1: unchanged v0 plus genuine opening excerpts.

No dataset, manifest, tokenizer, or label is loaded here. The caller supplies
node-indexed paper texts and the project's existing token counter. V0 owns all
topology generation, identity assignment, adjacency checks, historical prompt
preservation, and the original 256/320-token checks. V1 enforces a 416-token cap.
"""

from json import dumps
from operator import index
from typing import Callable, Dict, Mapping, Optional, Sequence, Tuple, TypedDict, Union

from .narrative_topology_v0 import (
    Adjacency,
    Diagnostics as V0Diagnostics,
    augment_consensus_prompt as _augment_v0,
)


EXCERPT_WORD_LIMIT = 15
NARRATIVE_V1_STRUCTURAL_CAP = 416
RawPaperTexts = Union[Mapping[int, str], Sequence[str]]


class ExcerptRecord(TypedDict):
    """An exact normalized opening excerpt tied to its source global node ID."""

    identifier: str
    node_id: int
    excerpt: str
    word_count: int


class Diagnostics(TypedDict):
    """V1 measurements plus the complete unchanged diagnostics returned by v0."""

    target_id: int
    identifier_mapping: Dict[str, int]
    non_representative_node_ids: Dict[str, int]
    excerpts: Dict[str, str]
    excerpt_word_counts: Dict[str, int]
    excerpt_records: Tuple[ExcerptRecord, ...]
    original_structural_tokens: int
    v0_structural_tokens: int
    v1_structural_tokens: int
    additional_structural_tokens: int
    excerpt_block: str
    excerpt_insertion_offset: int
    v0_prompt_preserved: bool
    original_prompt_preserved: bool
    v0_diagnostics: V0Diagnostics


def _opening_excerpt(raw_text: str, target: int, identifier: str, node_id: int) -> Tuple[str, int]:
    """Keep the first 15 whitespace-delimited words, changing only whitespace."""
    if not isinstance(raw_text, str):
        raise ValueError(
            f"Target {target}: raw paper text for {identifier} (node {node_id}) "
            "must be a string."
        )
    words = raw_text.split()[:EXCERPT_WORD_LIMIT]
    if not words:
        raise ValueError(
            f"Target {target}: raw paper text for {identifier} (node {node_id}) "
            "is empty or whitespace-only."
        )
    excerpt = " ".join(words)
    try:
        excerpt.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(
            f"Target {target}: opening text for {identifier} (node {node_id}) "
            "is not valid UTF-8 text."
        ) from exc
    if excerpt.split() != words:
        raise RuntimeError(
            f"Target {target}: excerpt normalization changed source words "
            f"for {identifier} (node {node_id})."
        )
    return excerpt, len(words)


def augment_consensus_prompt(
    consensus_prompt: str,
    target_id: int,
    neighbor_ids: Sequence[int],
    representative_id: int,
    adjacency: Adjacency,
    count_tokens: Callable[[str], int],
    raw_texts: RawPaperTexts,
    *,
    verified_descriptors: Optional[Mapping[int, str]] = None,
) -> Tuple[str, Diagnostics]:
    """Return v0's prompt plus opening excerpts and measured token diagnostics.

    Pass the original frozen Consensus prompt, not an already augmented prompt.
    All original arguments and optional verified descriptors are forwarded to
    v0 without changing its topology prose or its 256/320-token checks.

    ``raw_texts`` must be a node-indexed sequence or integer-keyed mapping of
    actual paper strings, aligned with the original graph's global node IDs.
    Only non-representative entries identified by v0 are retrieved. N1 is never
    retrieved or replaced; N2/N3 retain v0's frozen ordering. If a future input
    has additional selected neighbors, all its non-representatives are included.
    Missing rows, non-string text, and empty text are explicit errors. The caller
    is responsible for upstream graph/text alignment: source identity is checked
    by lookup using v0's IDs, not by semantic inference or external metadata.

    Each excerpt is exactly the first min(15, word_count) whitespace-delimited
    words with whitespace normalized to single spaces. No ellipsis, title,
    summary, or invented completion is added. Display quotes use JSON escaping
    so embedded quotes/control characters remain data; ``excerpts`` contains
    the exact unescaped normalized strings. No label fields are accessed.

    The excerpt block is inserted immediately before the historical usage block.
    Removing it by ``excerpt_insertion_offset`` and ``len(excerpt_block)`` must
    recover the complete v0 prompt as UTF-8 bytes. Together with v0's existing
    preservation check, this also preserves the original Consensus bytes. Use
    the nested ``v0_diagnostics`` insertion offset/block for the second removal.
    With only a representative, no excerpt block is added and v1 equals v0.

    Count the complete v1 string with the same supplied counter. The additional
    token count is v1 minus v0, including token-boundary effects, not a separate
    count of the inserted block. V1 raises ValueError above 416 tokens without
    shortening historical Consensus text, v0 topology, or opening excerpts.
    Inputs are not mutated and no I/O occurs. Supplied collections and callable
    are assumed to have no side effects. Import this as a package module, e.g.
    ``structure.narrative_topology_v1``; it is not a standalone script.
    """
    v0_prompt, v0_diagnostics = _augment_v0(
        consensus_prompt=consensus_prompt,
        target_id=target_id,
        neighbor_ids=neighbor_ids,
        representative_id=representative_id,
        adjacency=adjacency,
        count_tokens=count_tokens,
        verified_descriptors=verified_descriptors,
    )
    target = v0_diagnostics["target_id"]
    if not v0_diagnostics["original_prompt_preserved"]:
        raise RuntimeError(f"Target {target}: v0 did not confirm historical preservation.")
    if isinstance(raw_texts, (str, bytes)) or not isinstance(raw_texts, (Mapping, Sequence)):
        raise ValueError(
            f"Target {target}: raw_texts must be a node-indexed sequence "
            "or an integer-keyed mapping of paper strings."
        )

    identifier_mapping = dict(v0_diagnostics["identifier_mapping"])
    non_representatives = {
        identifier: node_id
        for identifier, node_id in identifier_mapping.items()
        if identifier != "N1"
    }
    records = []
    lines = []
    for identifier, node_id in non_representatives.items():
        # Lookup uses v0's exact global ID, never the identifier's ordinal or a
        # position in a newly selected subset. No dataset attributes are read.
        try:
            if isinstance(raw_texts, Mapping) and node_id not in raw_texts:
                raise KeyError(node_id)
            raw_text = raw_texts[node_id]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(
                f"Target {target}: missing raw paper text for "
                f"{identifier} (node {node_id})."
            ) from exc
        excerpt, word_count = _opening_excerpt(raw_text, target, identifier, node_id)
        record: ExcerptRecord = {
            "identifier": identifier,
            "node_id": node_id,
            "excerpt": excerpt,
            "word_count": word_count,
        }
        records.append(record)
        lines.append(
            f"{identifier} (node {node_id}) \u2014 Opening text excerpt: "
            + dumps(excerpt, ensure_ascii=False)
        )

    usage_marker = "\n\nUsage instruction:\n"
    insertion_offset = v0_prompt.index(usage_marker)
    excerpt_block = ""
    if lines:
        excerpt_block = (
            "\n\nOpening text excerpts from other selected neighbors:\n"
            + "\n".join(lines)
        )
    augmented = (
        v0_prompt[:insertion_offset]
        + excerpt_block
        + v0_prompt[insertion_offset:]
    )
    recovered_v0 = (
        augmented[:insertion_offset]
        + augmented[insertion_offset + len(excerpt_block):]
    )
    if recovered_v0.encode("utf-8") != v0_prompt.encode("utf-8"):
        raise RuntimeError(
            f"Target {target}: excerpt insertion changed the original v0 UTF-8 prompt."
        )

    measured_tokens = count_tokens(augmented)
    try:
        if isinstance(measured_tokens, bool):
            raise TypeError("Boolean token count")
        v1_tokens = index(measured_tokens)
    except TypeError as exc:
        raise ValueError(
            f"Target {target}: v1 token count must be a nonnegative integer."
        ) from exc
    if v1_tokens < 0:
        raise ValueError(f"Target {target}: v1 token count must be nonnegative.")
    if v1_tokens > NARRATIVE_V1_STRUCTURAL_CAP:
        raise ValueError(
            f"Target {target}: augmented v1 structural prompt has {v1_tokens} "
            f"tokens; cap is {NARRATIVE_V1_STRUCTURAL_CAP}. "
            "Historical Consensus text, v0 topology, and opening excerpts "
            "were not truncated."
        )
    v0_tokens = v0_diagnostics["new_structural_tokens"]

    diagnostics: Diagnostics = {
        "target_id": target,
        "identifier_mapping": identifier_mapping,
        "non_representative_node_ids": non_representatives,
        "excerpts": {record["identifier"]: record["excerpt"] for record in records},
        "excerpt_word_counts": {
            record["identifier"]: record["word_count"] for record in records
        },
        "excerpt_records": tuple(records),
        "original_structural_tokens": v0_diagnostics["original_structural_tokens"],
        "v0_structural_tokens": v0_tokens,
        "v1_structural_tokens": v1_tokens,
        "additional_structural_tokens": v1_tokens - v0_tokens,
        "excerpt_block": excerpt_block,
        "excerpt_insertion_offset": insertion_offset,
        "v0_prompt_preserved": True,
        "original_prompt_preserved": True,
        "v0_diagnostics": v0_diagnostics,
    }
    return augmented, diagnostics
