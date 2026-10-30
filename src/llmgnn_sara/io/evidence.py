"""Explicit graph-derived evidence; never accepts a graph or diagnostic labels."""
from dataclasses import dataclass
from itertools import combinations
import re


@dataclass(frozen=True, slots=True)
class NeighborhoodEvidence:
    target_id: int
    neighbor_ids: tuple[int, ...]
    representative_id: int | None
    degree: int
    connected_pairs: tuple[tuple[int, int], ...]
    disconnected_pairs: tuple[tuple[int, int], ...]
    context: str
    graph_sha256: str
    source_sha256: str
    verification_level: str = "HASH_ANCHORED_FROZEN_NEIGHBORHOOD_NOT_RECOMPUTED"

    def __post_init__(self):
        ids = self.neighbor_ids
        if (type(self.target_id) is not int or not 0 <= self.target_id < 2708
                or type(ids) is not tuple or len(ids) != len(set(ids))
                or any(type(i) is not int or not 0 <= i < 2708 or i == self.target_id for i in ids)
                or type(self.degree) is not int or self.degree < len(ids)
                or (self.representative_id is not None and
                    (type(self.representative_id) is not int or self.representative_id not in ids))
                or type(self.context) is not str):
            raise ValueError("Invalid neighborhood identity")
        sets = []
        for pairs in (self.connected_pairs, self.disconnected_pairs):
            if type(pairs) is not tuple or any(type(p) is not tuple or len(p) != 2
                    or any(type(i) is not int or i not in ids for i in p) or p[0] >= p[1] for p in pairs):
                raise ValueError("Invalid canonical neighborhood pairs")
            if len(set(pairs)) != len(pairs):
                raise ValueError("Duplicate neighborhood pair")
            sets.append(set(pairs))
        if sets[0] & sets[1] or sets[0] | sets[1] != set(combinations(sorted(ids), 2)):
            raise ValueError("Incomplete/conflicting neighborhood pairs")
        if any(type(pin) is not str or not re.fullmatch(r"[0-9a-f]{64}", pin)
               for pin in (self.graph_sha256, self.source_sha256)):
            raise ValueError("Invalid evidence hash")
        if self.verification_level != "HASH_ANCHORED_FROZEN_NEIGHBORHOOD_NOT_RECOMPUTED":
            raise ValueError("Independent canonical graph recomputation is not established")
