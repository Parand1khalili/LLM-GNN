"""Pure plans reconstructed from the frozen pre-Codex downstream protocol.

Only node IDs, pseudo-labels and voted confidence are accepted. No graph, GT,
diagnostic outcome or evaluator object enters training-label construction.
"""
from dataclasses import asdict, dataclass
import math
from typing import Iterable


def _integer(value, lower, upper, field):
    if type(value) is not int or not lower <= value < upper:
        raise ValueError(f"Invalid {field}")
    return value


def _finite(value, lower, upper, field):
    if type(value) not in (int, float) or not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError(f"Invalid {field}")
    return float(value)


@dataclass(frozen=True, slots=True)
class PseudoLabel:
    node_id: int
    class_index: int
    confidence_percent: float

    def __post_init__(self):
        _integer(self.node_id, 0, 2**63, "node ID")
        _integer(self.class_index, 0, 2**31, "class index")
        _finite(self.confidence_percent, 0, 100, "confidence")


@dataclass(frozen=True, slots=True)
class GCNConfig:
    loss: str = "ce"
    node_count: int = 2708
    num_classes: int = 7
    epochs: int = 30
    hidden_dimension: int = 64
    num_layers: int = 2
    dropout: float = 0.5
    learning_rate: float = 0.01
    weight_decay: float = 0.0005
    seeds: tuple[int, ...] = tuple(range(10))
    strict_historical: bool = True

    def __post_init__(self):
        if self.loss not in ("ce", "wce"):
            raise ValueError("Loss must be ce or wce")
        for field in ("node_count", "num_classes", "hidden_dimension", "num_layers", "epochs"):
            _integer(getattr(self, field), 1, 2**31, field)
        _finite(self.dropout, 0, 1, "dropout")
        _finite(self.learning_rate, 0, 1, "learning rate")
        _finite(self.weight_decay, 0, 1, "weight decay")
        if not self.learning_rate or self.dropout == 1:
            raise ValueError("Invalid optimizer/dropout configuration")
        if type(self.strict_historical) is not bool or type(self.seeds) is not tuple or not self.seeds:
            raise ValueError("Seeds must be a nonempty immutable tuple")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Duplicate seeds")
        for seed in self.seeds:
            _integer(seed, 0, 2**32, "seed")
        if self.strict_historical and (
            self.node_count != 2708 or self.num_classes != 7 or self.epochs != 30
            or self.hidden_dimension != 64 or self.num_layers != 2 or self.dropout != 0.5
            or self.learning_rate != 0.01 or self.weight_decay != 0.0005
            or self.seeds != tuple(range(10))
        ):
            raise ValueError("Historical protocol must not change silently")


def confidence_weights(confidences: Iterable[float]) -> tuple[float, ...]:
    """Frozen min-max weights; constant confidence means all ones (CE fallback)."""
    values = tuple(_finite(c, 0, 100, "confidence") for c in confidences)
    if not values:
        raise ValueError("Empty confidence set")
    low, high = min(values), max(values)
    return (1.0,) * len(values) if high == low else tuple((c - low) / (high - low) for c in values)


def reduce_loss(losses: Iterable[float], weights: Iterable[float] | None = None) -> float:
    """mean(CE_i * w_i), deliberately NOT sum(CE_i*w_i)/sum(w_i)."""
    values = tuple(_finite(v, 0, float("inf"), "loss") for v in losses)
    if not values:
        raise ValueError("Empty loss set")
    if weights is None:
        return math.fsum(values) / len(values)
    factors = tuple(_finite(w, 0, 1, "weight") for w in weights)
    if len(factors) != len(values):
        raise ValueError("Weight/loss alignment differs")
    return math.fsum(v * w for v, w in zip(values, factors)) / len(values)


def gcn_plan(selected_ids: Iterable[int], pseudo_labels: Iterable[PseudoLabel],
             cohort: str = "sensitivity", *, excluded_ids: Iterable[int] = (),
             config: GCNConfig = GCNConfig(), pipeline: str | None = None,
             allow_abstention: bool = False) -> dict:
    """Validate matched masks and construct only accepted pseudo-training labels.

    selected_ids always describes the full selected pool, including the five
    Primary exclusions and any prospective SARA abstentions. Those nodes never
    become test nodes. train_ids preserve selection-manifest order.
    """
    if not isinstance(config, GCNConfig) or cohort not in ("primary", "sensitivity"):
        raise ValueError("Invalid GCN plan configuration")
    if pipeline is None:
        pipeline = "ce" if config.loss == "ce" else "weighted_ce"
    if pipeline not in ("ce", "weighted_ce") or type(allow_abstention) is not bool:
        raise ValueError("Only declared CE/WCE without PS is supported here")
    if pipeline != ("ce" if config.loss == "ce" else "weighted_ce"):
        raise ValueError("Pipeline and loss configuration disagree")
    selected, excluded, labels = tuple(selected_ids), tuple(excluded_ids), tuple(pseudo_labels)
    for value in selected + excluded:
        _integer(value, 0, config.node_count, "node ID")
    if not selected or len(set(selected)) != len(selected) or len(set(excluded)) != len(excluded):
        raise ValueError("Empty or duplicate node IDs")
    if not set(excluded) <= set(selected):
        raise ValueError("Excluded IDs must belong to the selected pool")
    if cohort == "sensitivity" and excluded:
        raise ValueError("Sensitivity has no Primary exclusions")
    if config.strict_historical and (len(selected) != 140 or (cohort == "primary" and len(excluded) != 5)):
        raise ValueError("Historical cohort count differs")
    by_id = {}
    for label in labels:
        if type(label) is not PseudoLabel:
            raise ValueError("Only explicit PseudoLabel records are accepted")
        _integer(label.class_index, 0, config.num_classes, "class index")
        if label.node_id not in selected or label.node_id in excluded or label.node_id in by_id:
            raise ValueError("Pseudo-label node is duplicate or outside the training cohort")
        by_id[label.node_id] = label
    eligible = tuple(i for i in selected if i not in set(excluded))
    if not by_id or (not allow_abstention and set(by_id) != set(eligible)):
        raise ValueError("Missing pseudo-labels; abstention must be declared")
    train_ids = tuple(i for i in eligible if i in by_id)
    test_ids = tuple(i for i in range(config.node_count) if i not in set(selected))
    pseudo_y = tuple(by_id[i].class_index if i in by_id else -1 for i in range(config.node_count))
    confidences = tuple(by_id[i].confidence_percent for i in train_ids)
    weights = confidence_weights(confidences) if pipeline == "weighted_ce" else (1.0,) * len(train_ids)
    if config.strict_historical and len(test_ids) != 2568:
        raise ValueError("Common test complement differs")
    return {
        "schema": "sara.gcn_plan.v1", "status": "PLANNED_NOT_TRAINED",
        "protocol_status": "HISTORICAL_CONTRACT" if config.strict_historical else "SYNTHETIC",
        "config": asdict(config), "cohort": cohort, "pipeline": pipeline, "PS": False,
        "selected_ids": list(selected), "train_ids": list(train_ids), "test_ids": list(test_ids),
        "excluded_ids": list(excluded), "abstained_ids": [i for i in eligible if i not in by_id],
        "pseudo_y": list(pseudo_y), "confidence_percent": list(confidences), "weights": list(weights),
        "train_count": len(train_ids), "common_test_count": len(test_ids),
        "retention": len(train_ids) / len(eligible),
        "class_coverage": len({by_id[i].class_index for i in train_ids}) / config.num_classes,
        "loss_reduction": "mean(CE_i * w_i)" if pipeline == "weighted_ce" else "mean(CE_i)",
        "checkpoint_selection": "last epoch", "early_stopping": False, "validation": None,
        "feature_l2_normalization": False, "train_mode_each_epoch": True,
        "training_runs": 0, "GT_accessed": False,
        "authorization": "Separate explicit authorization is required before real training",
    }


def gcn_demo_plan() -> dict:
    config = GCNConfig(loss="wce", node_count=6, num_classes=2, strict_historical=False)
    return gcn_plan((0, 2, 4), (PseudoLabel(0, 0, 50), PseudoLabel(2, 1, 75),
                              PseudoLabel(4, 0, 100)), config=config, pipeline="weighted_ce")
