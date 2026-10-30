"""Public class semantics only; keywords are an unvalidated research heuristic."""
from dataclasses import dataclass
import re

from ..sara2.policy import CLASSES, Pair, integer, risk, validated_pairs


@dataclass(frozen=True)
class ClassDefinition:
    name: str
    definition: str
    keywords: tuple[str, ...]


ATLAS = (
    ClassDefinition(CLASSES[0], "Learning explicit symbolic rules and logic-based induction.",
                    ("rule", "rules", "induction", "logic")),
    ClassDefinition(CLASSES[1], "Learning with artificial neural networks and their architectures.",
                    ("neural", "network", "networks", "backpropagation")),
    ClassDefinition(CLASSES[2], "Reasoning and learning by retrieving or adapting prior cases.",
                    ("case", "cases", "retrieval", "analogy")),
    ClassDefinition(CLASSES[3], "Evolutionary optimization using populations and genetic operators.",
                    ("genetic", "evolutionary", "mutation", "crossover")),
    ClassDefinition(CLASSES[4], "Theoretical properties, complexity and guarantees of learning.",
                    ("theorem", "bound", "bounds", "complexity")),
    ClassDefinition(CLASSES[5], "Learning actions or policies through rewards and interaction.",
                    ("reward", "policy", "reinforcement", "markov")),
    ClassDefinition(CLASSES[6], "Probabilistic modeling, inference and uncertainty in learning.",
                    ("bayesian", "probabilistic", "probability", "likelihood")),
)


def semantic_support(text: str) -> tuple[int, ...]:
    if type(text) is not str:
        raise TypeError("Text must be a string")
    tokens = set(re.findall(r"[a-z]+", text.lower()))
    return tuple(len(tokens.intersection(entry.keywords)) for entry in ATLAS)


def semantic_risk(pair: Pair) -> float:
    """Risk from unsupported predicted topics; no learned/GT-fitted weights."""
    scores = semantic_support(pair.text)
    if max(scores) == 0:
        return risk(pair)
    predicted_support = max(scores[pair.b1.class_index], scores[pair.narrative_v0.class_index])
    mismatch = (max(scores) - predicted_support) / max(scores)
    # Fixed prospective weight, explicitly uncalibrated. No historical R1 claim.
    return risk(pair) + 100.0 * mismatch


def route_semantic(pairs, budget: int) -> tuple[int, ...]:
    integer(budget, "review budget")
    rows = validated_pairs(pairs)
    return tuple(p.node_id for p in sorted(rows, key=lambda p: (-semantic_risk(p), p.node_id))[:budget])
