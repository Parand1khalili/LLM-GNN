"""Explicit-array evaluation boundary; no graph or dataset loading occurs here."""
import math
import statistics


def evaluate_frozen(predictions, labels, *, decisions_frozen: bool, num_classes: int = 7) -> dict:
    """Only the evaluator receives externally supplied labels after a freeze.

    No automatic data access or GT decoding is implemented. Tests use synthetic
    labels only. This function must run separately from the decision pipeline.
    """
    if decisions_frozen is not True:
        raise PermissionError("Evaluation requires frozen decisions")
    if type(num_classes) is not int or num_classes <= 0:
        raise ValueError("Invalid class count")
    predictions, labels = tuple(predictions), tuple(labels)
    if not predictions or len(predictions) != len(labels):
        raise ValueError("Prediction/label alignment differs")
    for value in predictions + labels:
        if type(value) is not int or not 0 <= value < num_classes:
            raise ValueError("Invalid class index")
    correct = sum(p == y for p, y in zip(predictions, labels))
    return {"count": len(labels), "correct": correct, "accuracy_percent": 100 * correct / len(labels)}


def matched_summary(b1_by_seed: dict, narrative_by_seed: dict) -> dict:
    """Population SD of matched training seeds, not LLM annotation uncertainty."""
    if not b1_by_seed or set(b1_by_seed) != set(narrative_by_seed):
        raise ValueError("Matched seed sets differ")
    if any(type(s) is not int or s < 0 for s in b1_by_seed):
        raise ValueError("Invalid seed")
    for value in (*b1_by_seed.values(), *narrative_by_seed.values()):
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError("Invalid accuracy")
    seeds = sorted(b1_by_seed)
    b1, narrative = [b1_by_seed[s] for s in seeds], [narrative_by_seed[s] for s in seeds]
    delta = [v - b for b, v in zip(b1, narrative)]
    summary = lambda values: {"mean": statistics.mean(values), "population_sd": statistics.pstdev(values)}
    return {"seeds": seeds, "b1_accuracy_percent": summary(b1),
            "narrative_accuracy_percent": summary(narrative), "paired_delta_pp": summary(delta),
            "per_seed_delta_pp": dict(zip(seeds, delta)),
            "uncertainty_scope": "training-seed variability; not independent annotation replicates"}
