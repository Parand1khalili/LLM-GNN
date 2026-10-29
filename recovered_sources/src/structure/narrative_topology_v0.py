"""Offline Narrative Consensus v0; historical Consensus is never rewritten.

Supply ``structure.prompt_builder.count_tokens`` explicitly. This module does
not import the historical builder, initialize a tokenizer, or read any files.
Adjacency must use the original graph's node numbering and undirected semantics,
for example the lists returned by ``selector.build_undirected_neighbors``.
"""

from json import dumps
from operator import index
from typing import (
    Callable, Collection, Dict, Mapping, Optional, Sequence, Tuple, TypedDict, Union,
)


HISTORICAL_STRUCTURAL_CAP = 256
NARRATIVE_STRUCTURAL_CAP = 320

Adjacency = Union[Mapping[int, Collection[int]], Sequence[Collection[int]]]
NodePairs = Tuple[Tuple[int, int], ...]
IdentifierPairs = Tuple[Tuple[str, str], ...]


class Diagnostics(TypedDict):
    """Counts and exact pair identities; pair order follows identifier order."""

    target_id: int
    selected_neighbor_count: int
    possible_neighbor_pairs: int
    connected_neighbor_pairs: int
    representative_connected_neighbor_count: int
    original_structural_tokens: int
    new_structural_tokens: int
    narrative_text: str
    inserted_block: str
    insertion_offset: int
    original_prompt_preserved: bool
    identifier_mapping: Dict[str, int]
    node_identifier_mapping: Dict[int, str]
    descriptors_by_identifier: Dict[str, str]
    connected_node_pairs: NodePairs
    disconnected_node_pairs: NodePairs
    connected_identifier_pairs: IdentifierPairs
    disconnected_identifier_pairs: IdentifierPairs


def _nonnegative_integer(value: int, description: str) -> int:
    """Accept integer IDs/counts without silently rounding floats."""
    if isinstance(value, bool):
        raise ValueError(f"{description} must be a nonnegative integer.")
    try:
        normalized = index(value)
    except TypeError as exc:
        raise ValueError(
            f"{description} must be a nonnegative integer."
        ) from exc
    if normalized < 0:
        raise ValueError(f"{description} must be a nonnegative integer.")
    return normalized


def _join_names(names: Sequence[str], conjunction: str = "and") -> str:
    """Join a nonempty ordered sequence using ordinary English punctuation."""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} {conjunction} {names[1]}"
    return ", ".join(names[:-1]) + f", {conjunction} {names[-1]}"


def _describe_connectivity(
    target: int,
    identifier_mapping: Mapping[str, int],
    descriptors: Mapping[str, str],
    connected_pairs: IdentifierPairs,
    disconnected_pairs: IdentifierPairs,
) -> str:
    """Define every identity and describe every pair without semantic claims."""
    definitions = []
    for identifier, node_id in identifier_mapping.items():
        definition = f"{identifier}={node_id}"
        details = []
        if identifier == "N1":
            details.append("representative")
        if identifier in descriptors:
            # Quote caller-verified text as data; never invent or shorten it.
            details.append(dumps(descriptors[identifier], ensure_ascii=False))
        if details:
            definition += " (" + ", ".join(details) + ")"
        definitions.append(definition)

    selected_count = len(definitions)
    if selected_count == 1:
        return (
            f"Target {target}'s selected direct neighbor is {definitions[0]}. "
            "No selected pair exists."
        )

    sentences = [
        f"Target {target}'s selected direct neighbors are {_join_names(definitions)}.",
    ]
    if selected_count == 3 and len(connected_pairs) == 1:
        left, right = connected_pairs[0]
        isolated = next(
            name for name in identifier_mapping if name not in (left, right)
        )
        sentences.append(
            f"Among them, {left} connects directly to {right}; "
            f"{isolated} has no edge to "
            f"{left} or {right}."
        )
    else:
        # Each unordered pair appears exactly once in one of these groups.
        # Group by the first endpoint to reduce repetition while naming both
        # endpoints of every present or absent connection.
        clauses = []
        for left in identifier_mapping:
            connected = [right for a, right in connected_pairs if a == left]
            disconnected = [right for a, right in disconnected_pairs if a == left]
            if connected:
                clauses.append(
                    f"{left} connects directly to {_join_names(connected)}"
                )
            if disconnected:
                clauses.append(
                    f"{left} has no edge to "
                    f"{_join_names(disconnected, 'or')}"
                )
        sentences.append("Among them, " + "; ".join(clauses) + ".")
    return " ".join(sentences)


def augment_consensus_prompt(
    consensus_prompt: str,
    target_id: int,
    neighbor_ids: Sequence[int],
    representative_id: int,
    adjacency: Adjacency,
    count_tokens: Callable[[str], int],
    *,
    verified_descriptors: Optional[Mapping[int, str]] = None,
) -> Tuple[str, Diagnostics]:
    """Insert actual local connectivity into a frozen Consensus prompt.

    Return ``(augmented_prompt, diagnostics)`` without mutating any input.
    ``neighbor_ids`` must be the frozen, ordered, nonempty selection, with no
    duplicates; the representative must belong to it. No selection or semantic
    scoring is performed. IDs refer to the caller's original graph numbering.

    N1 always names the representative. N2 onward name the remaining selected
    neighbors in their original frozen order; the supplied sequence is unchanged.
    Every identifier is explicitly mapped to its global node ID in the prose.
    All pair endpoints in diagnostics follow this identifier order, not numeric
    node-ID order. Disconnected pairs mean absent direct edges in the selected
    induced subgraph, not absence of paths through other nodes.

    The frozen M1 selection manifest contains only degree and neighbor records
    with node_id/similarity, not verified article titles. ``verified_descriptors``
    optionally supplies short, caller-verified titles/descriptors keyed by global
    node ID. Missing entries are omitted; unrelated entries are ignored. Selected
    entries must be nonempty single-line strings with no surrounding whitespace
    or control characters. They are quoted without truncation. The caller is
    responsible for provenance and for excluding labels or unsupported claims;
    the module neither reads metadata nor infers titles from paper text.

    Adjacency is an integer-keyed mapping or node-indexed sequence of reusable
    neighbor collections, not an edge-index tensor or dense adjacency matrix.
    Rows for the target and selected neighbors must exist. Only these rows are
    copied; selected target edges and every distinct selected-neighbor pair are
    checked for symmetry. Missing edges are ordinary absent membership entries;
    missing rows, asymmetric queried edges, and non-neighbors are errors.

    The supplied token counter must be the project's existing implementation.
    Both original and augmented prompts are counted as complete strings, so
    token boundary effects are included. Caps are fixed at 256 and 320.

    Diagnostics include the exact inserted block and its character offset;
    deleting that slice recovers the original UTF-8 bytes. Invalid inputs and
    budget violations raise ValueError. A failed preservation check raises
    RuntimeError. The function performs no I/O; caller-supplied objects and the
    token counter are assumed to have no side effects.
    """
    target = _nonnegative_integer(target_id, "Target ID")
    if not isinstance(consensus_prompt, str):
        raise ValueError(f"Target {target}: Consensus prompt must be a string.")
    if not callable(count_tokens):
        raise ValueError(f"Target {target}: count_tokens must be callable.")

    neighbors = tuple(
        _nonnegative_integer(node_id, f"Target {target}: neighbor ID")
        for node_id in neighbor_ids
    )
    representative = _nonnegative_integer(
        representative_id, f"Target {target}: representative ID"
    )
    if not neighbors or len(set(neighbors)) != len(neighbors):
        raise ValueError(
            f"Target {target}: frozen neighbor_ids must be nonempty and unique."
        )
    if target in neighbors:
        raise ValueError(f"Target {target}: a selected neighbor cannot be itself.")
    if representative not in neighbors:
        raise ValueError(
            f"Target {target}: representative_id must be a selected neighbor."
        )

    identity_order = (representative,) + tuple(
        node_id for node_id in neighbors if node_id != representative
    )
    identifier_mapping = {
        f"N{position}": node_id
        for position, node_id in enumerate(identity_order, start=1)
    }
    node_identifier_mapping = {
        node_id: identifier for identifier, node_id in identifier_mapping.items()
    }
    descriptors = {}
    if verified_descriptors is not None:
        if not isinstance(verified_descriptors, Mapping):
            raise ValueError(
                f"Target {target}: verified_descriptors must be a node-ID mapping."
            )
        for identifier, node_id in identifier_mapping.items():
            if node_id not in verified_descriptors:
                continue
            descriptor = verified_descriptors[node_id]
            if (
                not isinstance(descriptor, str)
                or not descriptor
                or descriptor != descriptor.strip()
                or any(ord(character) < 32 or ord(character) == 127 for character in descriptor)
                or len(descriptor.splitlines()) != 1
            ):
                raise ValueError(
                    f"Target {target}: descriptor for node {node_id} must be "
                    "nonempty single-line text without surrounding whitespace "
                    "or control characters."
                )
            descriptors[identifier] = descriptor

    usage_marker = "\n\nUsage instruction:\n"
    support_marker = "\n\nAdditional semantic support:\n"
    narrative_marker = "\n\nLocal structural description:\n"
    prefix = (
        "LOCAL NEIGHBORHOOD EVIDENCE\n\n"
        "Representative direct 1-hop neighbor:\n"
    )
    if not consensus_prompt.startswith(prefix):
        raise ValueError(f"Target {target}: expected the historical Consensus prefix.")
    if consensus_prompt.count(usage_marker) != 1:
        raise ValueError(
            f"Target {target}: expected exactly one historical Usage instruction block."
        )
    insertion_offset = consensus_prompt.index(usage_marker)
    if support_marker not in consensus_prompt[:insertion_offset]:
        raise ValueError(f"Target {target}: Consensus semantic support block is missing.")
    if narrative_marker in consensus_prompt:
        raise ValueError(f"Target {target}: a local structural description already exists.")

    original_tokens = _nonnegative_integer(
        count_tokens(consensus_prompt), f"Target {target}: original token count"
    )
    if original_tokens > HISTORICAL_STRUCTURAL_CAP:
        raise ValueError(
            f"Target {target}: original structural prompt has {original_tokens} "
            f"tokens; historical cap is {HISTORICAL_STRUCTURAL_CAP}."
        )

    rows = {}
    for node_id in (target,) + neighbors:
        try:
            row = adjacency[node_id]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(
                f"Target {target}: adjacency row for node {node_id} is unavailable."
            ) from exc
        rows[node_id] = frozenset(
            _nonnegative_integer(value, f"Target {target}: adjacency node ID")
            for value in row
        )

    for neighbor in neighbors:
        if neighbor not in rows[target] or target not in rows[neighbor]:
            raise ValueError(
                f"Target {target}: selected node {neighbor} must be an "
                "undirected direct neighbor of the target."
            )

    connected_node_pairs = []
    disconnected_node_pairs = []
    representative_connections = 0
    for position, left in enumerate(identity_order):
        for right in identity_order[position + 1:]:
            forward = right in rows[left]
            reverse = left in rows[right]
            if forward != reverse:
                raise ValueError(
                    f"Target {target}: adjacency is asymmetric for "
                    f"selected pair ({left}, {right})."
                )
            if forward:
                connected_node_pairs.append((left, right))
                if representative in (left, right):
                    representative_connections += 1
            else:
                disconnected_node_pairs.append((left, right))

    selected_count = len(neighbors)
    possible_pairs = selected_count * (selected_count - 1) // 2
    connected_pairs = len(connected_node_pairs)
    connected_identifier_pairs = tuple(
        (node_identifier_mapping[left], node_identifier_mapping[right])
        for left, right in connected_node_pairs
    )
    disconnected_identifier_pairs = tuple(
        (node_identifier_mapping[left], node_identifier_mapping[right])
        for left, right in disconnected_node_pairs
    )
    narrative = _describe_connectivity(
        target, identifier_mapping, descriptors,
        connected_identifier_pairs, disconnected_identifier_pairs,
    )
    inserted_block = narrative_marker + narrative
    augmented = (
        consensus_prompt[:insertion_offset]
        + inserted_block
        + consensus_prompt[insertion_offset:]
    )
    restored = (
        augmented[:insertion_offset]
        + augmented[insertion_offset + len(inserted_block):]
    )
    if restored.encode("utf-8") != consensus_prompt.encode("utf-8"):
        raise RuntimeError(
            f"Target {target}: insertion failed to preserve the original UTF-8 prompt."
        )

    new_tokens = _nonnegative_integer(
        count_tokens(augmented), f"Target {target}: new token count"
    )
    if new_tokens > NARRATIVE_STRUCTURAL_CAP:
        raise ValueError(
            f"Target {target}: augmented structural prompt has {new_tokens} "
            f"tokens; Narrative Consensus v0 cap is {NARRATIVE_STRUCTURAL_CAP}. "
            "Historical text was not truncated."
        )

    diagnostics: Diagnostics = {
        "target_id": target,
        "selected_neighbor_count": selected_count,
        "possible_neighbor_pairs": possible_pairs,
        "connected_neighbor_pairs": connected_pairs,
        "representative_connected_neighbor_count": representative_connections,
        "original_structural_tokens": original_tokens,
        "new_structural_tokens": new_tokens,
        "narrative_text": narrative,
        "inserted_block": inserted_block,
        "insertion_offset": insertion_offset,
        "original_prompt_preserved": True,
        "identifier_mapping": identifier_mapping,
        "node_identifier_mapping": node_identifier_mapping,
        "descriptors_by_identifier": descriptors,
        "connected_node_pairs": tuple(connected_node_pairs),
        "disconnected_node_pairs": tuple(disconnected_node_pairs),
        "connected_identifier_pairs": connected_identifier_pairs,
        "disconnected_identifier_pairs": disconnected_identifier_pairs,
    }
    return augmented, diagnostics
