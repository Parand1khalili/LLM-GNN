"""Explicit reconstruction decisions, never a recovered Policy 002 replica.

Available historical reports establish confidence/agreement routing but do not
provide the complete threshold table. These defaults are prospective engineering
choices, not fitted to historical route counts or ground-truth diagnostics.
"""
from dataclasses import dataclass
import math
from typing import Iterable


CLASSES = ("rule_learning", "neural_networks", "case_based", "genetic_algorithms",
           "theory", "reinforcement_learning", "probabilistic_methods")


def integer(value: int, name: str, maximum: int | None = None) -> None:
    if type(value) is not int or value < 0 or (maximum is not None and value >= maximum):
        raise ValueError(f"Invalid {name}")


@dataclass(frozen=True)
class Annotation:
    """Pseudo-label only; confidence is historical percent in [0, 100]."""
    node_id: int
    class_index: int
    confidence: float

    def __post_init__(self):
        integer(self.node_id, "node ID")
        integer(self.class_index, "class index", len(CLASSES))
        if (type(self.confidence) not in (int, float) or not math.isfinite(self.confidence)
                or not 0 <= self.confidence <= 100):
            raise ValueError("Invalid confidence percent")


@dataclass(frozen=True)
class Pair:
    b1: Annotation
    narrative_v0: Annotation
    text: str = ""

    def __post_init__(self):
        if type(self.b1) is not Annotation or type(self.narrative_v0) is not Annotation:
            raise TypeError("Pair requires explicit GT-free annotations")
        if self.b1.node_id != self.narrative_v0.node_id:
            raise ValueError("Annotation node IDs differ")
        if type(self.text) is not str:
            raise TypeError("Text must be a string")

    @property
    def node_id(self):
        return self.b1.node_id

    @property
    def agrees(self):
        return self.b1.class_index == self.narrative_v0.class_index


@dataclass(frozen=True)
class PolicyConfig:
    """Uncalibrated, predeclared defaults; no historical equivalence claim."""
    agreement_acceptance_percent: float = 80.0
    provenance: str = "RECONSTRUCTED_POLICY_NOT_HISTORICAL_EQUIVALENT"

    def __post_init__(self):
        if (type(self.agreement_acceptance_percent) not in (int, float)
                or not math.isfinite(self.agreement_acceptance_percent)
                or not 0 <= self.agreement_acceptance_percent <= 100):
            raise ValueError("Invalid agreement acceptance threshold")
        if self.provenance != "RECONSTRUCTED_POLICY_NOT_HISTORICAL_EQUIVALENT":
            raise ValueError("Historical Policy 002 equivalence is not established")


def validated_pairs(pairs: Iterable[Pair]) -> tuple[Pair, ...]:
    rows = tuple(pairs)
    if any(type(pair) is not Pair for pair in rows):
        raise TypeError("Expected explicit GT-free Pair records")
    if len({pair.node_id for pair in rows}) != len(rows):
        raise ValueError("Duplicate node IDs")
    return rows


def risk(pair: Pair) -> float:
    """Disagreement first, then low minimum confidence; no GT inputs."""
    return (100.0 if not pair.agrees else 0.0) + 100.0 - min(
        pair.b1.confidence, pair.narrative_v0.confidence)


def route_r0(pairs: Iterable[Pair], budget: int) -> tuple[int, ...]:
    """Budgeted confidence/agreement baseline, not exact historical R0."""
    integer(budget, "review budget")
    rows = validated_pairs(pairs)
    return tuple(pair.node_id for pair in sorted(rows, key=lambda p: (-risk(p), p.node_id))[:budget])


def pair_from_frozen(node_id: int, b1: dict, narrative_v0: dict, text: str = "") -> Pair:
    """Allowlisted mapping adapter. Extra fields, including diagnostics, are unread.

    Prefer using typed FrozenPrediction records. This small adapter exists for
    external JSON adapters and deliberately never enumerates mapping contents.
    """
    return Pair(Annotation(node_id, b1["class_index"], b1["confidence_percent_before_tensor_cast"]),
                Annotation(node_id, narrative_v0["class_index"],
                           narrative_v0["confidence_percent_before_tensor_cast"]), text)
