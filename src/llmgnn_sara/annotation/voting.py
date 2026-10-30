"""Pure reconstruction of llm.py::eval_result's consistency prediction loop.

Source SHA-256: 483e7a1b7d445801edf1ee5e8251187807663e47dac940e4b24efcf06250ecce.
The GT lookup, tensor cast, scoring, saving and provider imports are excluded.
The original denominator includes invalid samples. Ties use first appearance.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math

from ..io.frozen import CLASSES, InputError


@dataclass(frozen=True)
class VoteResult:
    class_index: int
    prediction: str
    confidence_percent: float
    fallback_count: int


def _distance(left: str, right: str) -> int:
    """Unit-cost Levenshtein, equivalent to editdistance.eval for strings."""
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def vote_parsed_samples(samples, classes=CLASSES) -> VoteResult:
    """Vote exactly three stored parsed samples; do not parse/recreate raw text.

For all-invalid classes, historical behavior chooses the nearest class to the
last sample's first answer, halves that sample's confidence, and records1fallback.
Nonfinite, out-of-range, empty or malformed samples fail closed rather than
inventing labels. This input boundary rejects abnormal legacy parser outputs;
it never clips or repairs confidence, and leaves valid frozen voting unchanged.
"""
    classes = tuple(classes)
    if not classes or len(set(classes)) != len(classes) or not all(isinstance(c, str) for c in classes):
        raise InputError("Invalid class vocabulary")
    if not isinstance(samples, (list, tuple)) or len(samples) != 3:
        raise InputError("Historical vote requires exactly three samples")
    first_answers = []
    for sample in samples:
        if not isinstance(sample, (list, tuple)) or not sample:
            raise InputError("Empty/malformed parsed sample")
        answer = sample[0]
        if (not isinstance(answer, (list, tuple)) or len(answer) != 2 or not isinstance(answer[0], str)
                or type(answer[1]) not in (int, float) or not math.isfinite(answer[1])
                or not 0 <= answer[1] <= 100):
            raise InputError("Invalid first answer/confidence")
        first_answers.append((answer[0], answer[1]))
    valid = [(classes.index(a), c) for a, c in first_answers if a in classes]
    if not valid:
        answer, confidence = first_answers[-1]
        index = min(range(len(classes)), key=lambda i: _distance(answer, classes[i]))
        return VoteResult(index, classes[index], confidence / 2, 1)
    winner = Counter(i for i, _ in valid).most_common(1)[0][0]
    original = next(c for i, c in valid if i == winner)
    confidence = 0
    for index, sample_confidence in valid:
        confidence += (original + sample_confidence) / 2 if index == winner else 100 - sample_confidence
    confidence /= len(samples)
    return VoteResult(winner, classes[winner], confidence, 0)
