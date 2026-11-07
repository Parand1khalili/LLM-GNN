"""Reviewed GCN reuse, lazy optional backend, and explicit training permission gate.

GCN class copied from recovered src/models/nn.py (lines 158-198), SHA-256
5d00c347e5a6aa504de9bf8c5abbd6e084efa1302e004c142567b9dc364b4b9b.
Only its class is reused; the legacy module and its imports are never executed.
"""
from dataclasses import dataclass
import importlib.util
import random
from types import SimpleNamespace

from .plan import GCNConfig, PseudoLabel, gcn_plan


@dataclass(frozen=True, slots=True)
class GraphInputs:
    """Explicit feature/edge boundary. There is deliberately no label field."""
    x: object
    edge_index: object
    edge_weight: object = None


def backend_status() -> dict:
    missing = [name for name in ("torch", "torch_geometric", "numpy")
               if importlib.util.find_spec(name) is None]
    return {"status": "AVAILABLE" if not missing else "MISSING_OPTIONAL_DEPENDENCIES",
            "missing": missing, "installed_automatically": False}


def build_gcn(input_dim: int, config: GCNConfig = GCNConfig()):
    if type(input_dim) is not int or input_dim <= 0 or not isinstance(config, GCNConfig):
        raise ValueError("Invalid model dimensions/configuration")
    import torch
    import torch.nn.functional as F
    from torch_geometric.nn import GCNConv

    # Reviewed historical class; dropout-before-each-layer and normalization preserved.
    class GCN(torch.nn.Module):
        def __init__(self, num_layers, input_dim, hidden_dimension, num_classes, dropout, norm=None) -> None:
            super().__init__()
            self.convs = torch.nn.ModuleList()
            self.norms = torch.nn.ModuleList()
            self.num_layers = num_layers
            self.dropout = dropout
            if num_layers == 1:
                self.convs.append(GCNConv(input_dim, num_classes, cached=False,
                                 normalize=True))
            else:
                self.convs.append(GCNConv(input_dim, hidden_dimension, cached=False,
                                 normalize=True))
                if norm:
                    self.norms.append(torch.nn.BatchNorm1d(hidden_dimension))
                else:
                    self.norms.append(torch.nn.Identity())

                for _ in range(num_layers - 2):
                    self.convs.append(GCNConv(hidden_dimension, hidden_dimension, cached=False,
                                 normalize=True))
                    if norm:
                        self.norms.append(torch.nn.BatchNorm1d(hidden_dimension))
                    else:
                        self.norms.append(torch.nn.Identity())

                self.convs.append(GCNConv(hidden_dimension, num_classes, cached=False, normalize=True))

        def forward(self, data):
            x, edge_index, edge_weight= data.x, data.edge_index, data.edge_weight
            for i in range(self.num_layers):
                x = F.dropout(x, p=self.dropout, training=self.training)
                if edge_weight != None:
                    x = self.convs[i](x, edge_index, edge_weight)
                else:
                    x = self.convs[i](x, edge_index)
                if i != self.num_layers - 1:
                    x = self.norms[i](x)
                    x = F.relu(x)
            return x

    return GCN(config.num_layers, input_dim, config.hidden_dimension,
               config.num_classes, config.dropout, norm=None)


def _validate_graph(graph: GraphInputs, node_count: int):
    if type(graph) is not GraphInputs:
        raise ValueError("Only explicit GT-free GraphInputs are accepted")
    import torch
    x, edges, weights = graph.x, graph.edge_index, graph.edge_weight
    if (not isinstance(x, torch.Tensor) or x.ndim != 2 or x.shape[0] != node_count
            or x.shape[1] == 0 or not x.is_floating_point() or not torch.isfinite(x).all().item()):
        raise ValueError("Invalid graph features")
    if (not isinstance(edges, torch.Tensor) or edges.ndim != 2 or edges.shape[0] != 2
            or edges.dtype != torch.long or edges.device != x.device):
        raise ValueError("Invalid graph edges")
    if edges.numel() and (edges.min().item() < 0 or edges.max().item() >= node_count):
        raise ValueError("Graph edge ID out of bounds")
    if weights is not None and (
        not isinstance(weights, torch.Tensor) or weights.ndim != 1
        or weights.numel() != edges.shape[1] or not weights.is_floating_point()
        or weights.device != x.device or not torch.isfinite(weights).all().item()
        or (weights < 0).any().item()
    ):
        raise ValueError("Invalid graph edge weights")
    return graph


def synthetic_forward() -> dict:
    """One tiny synthetic forward only: no optimizer, backward, dataset or GT."""
    status = backend_status()
    if status["missing"]:
        return {**status, "forward": "NOT_RUN", "training_runs": 0}
    import torch
    torch.manual_seed(0)
    config = GCNConfig(node_count=4, num_classes=2, strict_historical=False)
    graph = GraphInputs(torch.ones((4, 3)), torch.tensor([[0, 1, 2, 3], [1, 2, 3, 0]]))
    _validate_graph(graph, 4)
    model = build_gcn(3, config)
    model.eval()
    with torch.no_grad():
        logits = model(graph)
    if logits.shape != (4, 2) or not torch.isfinite(logits).all().item():
        raise ValueError("Synthetic forward contract failed")
    return {"forward": "PASS", "shape": [4, 2], "training_runs": 0, "GT_accessed": False}


def train_gcn(graph: GraphInputs, plan: dict, seed: int, *, allow_training: bool = False):
    """Prepared future training function; never called by offline commands.

    A caller must have separate user authorization before setting allow_training.
    No file loading/saving or evaluation happens here. This backend is untested
    until optional Torch/PyG are available and authorized execution is reviewed.
    """
    if allow_training is not True:
        raise PermissionError("Real training requires separate explicit user authorization")
    if type(graph) is not GraphInputs or not isinstance(plan, dict):
        raise ValueError("Invalid graph/plan boundary")
    settings = dict(plan["config"])
    settings["seeds"] = tuple(settings["seeds"])
    config = GCNConfig(**settings)
    if type(seed) is not int or seed not in config.seeds:
        raise ValueError("Seed is not in the matched protocol")
    labels = tuple(PseudoLabel(i, plan["pseudo_y"][i], confidence)
                   for i, confidence in zip(plan["train_ids"], plan["confidence_percent"]))
    verified = gcn_plan(plan["selected_ids"], labels, cohort=plan["cohort"],
                        excluded_ids=plan["excluded_ids"], config=config, pipeline=plan["pipeline"],
                        allow_abstention=bool(plan["abstained_ids"]))
    for field in ("train_ids", "test_ids", "pseudo_y", "weights", "confidence_percent", "PS"):
        if plan.get(field) != verified[field]:
            raise ValueError(f"Plan integrity differs: {field}")
    return _fit(graph, verified, config, seed)


def train_matrix_fit(graph, package, fit_sha256, seed, *, allow_training=False):
    """Separately gated explicit loss-weight extension; never imputes confidence.

    The runner must first authenticate the full matrix against frozen inputs and
    validate independent owner admission/training approval. Old train_gcn stays
    restricted to its original confidence-derived weight contract.
    """
    if allow_training is not True:
        raise PermissionError("Real training requires separate explicit user authorization")
    from .full_matrix import VERSION, CONTRACT, reject_controls
    from ..sara3.experiment import digest
    from ..sara3.correction_features import require
    from ..io.project import GRAPH_SHA256
    reject_controls(package)
    require(package["schema"] == VERSION and package["contract"] == CONTRACT
            and package["rule_sha256"] == digest(CONTRACT))
    spec = package["fits"][fit_sha256]["spec"]
    require(digest(spec) == fit_sha256 and spec["graph_sha256"] == GRAPH_SHA256)
    settings = dict(spec["config"]); settings["seeds"] = tuple(settings["seeds"])
    config = GCNConfig(**settings)
    ids, classes, weights = spec["train_ids"], spec["class_indices"], spec["weights"]
    require(type(seed) is int and seed in config.seeds and len(ids) == len(set(ids)) > 0
            and len(ids) == len(classes) == len(weights)
            and all(type(i) is int and 0 <= i < 2708 for i in ids)
            and all(type(c) is int and 0 <= c < 7 for c in classes)
            and all(type(w) in (int, float) and 0 <= w <= 1 for w in weights)
            and (config.loss != "ce" or all(w == 1 for w in weights)))
    selected = package["selected_ids"]
    test = [i for i in range(2708) if i not in set(selected)]
    require(len(selected) == len(set(selected)) == 140 and len(test) == 2568
            and all(type(i) is int and 0 <= i < 2708 for i in selected)
            and package["test_ids"] == test and spec["test_ids_sha256"] == digest(test)
            and set(ids) <= set(selected))
    labels = dict(zip(ids, classes))
    return _fit(graph, {"train_ids": ids, "pseudo_y": [labels.get(i, -1) for i in range(2708)],
                        "weights": weights}, config, seed)


def _parameter_hash(model):
    import hashlib
    h = hashlib.sha256()
    for name, tensor in model.state_dict().items():
        array = tensor.detach().cpu().numpy()
        h.update(name.encode("utf-8")); h.update(str(array.dtype).encode("ascii"))
        h.update(str(array.shape).encode("ascii")); h.update(array.tobytes())
    return h.hexdigest()


def _fit(graph, verified, config, seed):
    """Shared historical optimization loop; callers validate their own contracts."""
    import numpy as np
    import torch
    import torch.nn.functional as F
    _validate_graph(graph, config.node_count)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    # Clone allowed fields only. No y/fixed_y/diagnostic object is accessed.
    data = SimpleNamespace(x=graph.x.detach().clone(), edge_index=graph.edge_index.detach().clone(),
                           edge_weight=None if graph.edge_weight is None else graph.edge_weight.detach().clone())
    model = build_gcn(data.x.shape[1], config).to(data.x.device)
    initial_sha = _parameter_hash(model)
    indices = torch.tensor(verified["train_ids"], dtype=torch.long, device=data.x.device)
    pseudo = torch.tensor(verified["pseudo_y"], dtype=torch.long, device=data.x.device)
    weights = torch.tensor(verified["weights"], dtype=data.x.dtype, device=data.x.device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    losses = []
    for _ in range(config.epochs):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        logits = model(data)
        per_node = F.cross_entropy(logits[indices], pseudo[indices], reduction="none", label_smoothing=0.0)
        loss = (per_node * weights).mean()
        if not torch.isfinite(loss).item():
            raise ValueError("Nonfinite training loss")
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach().cpu()))
    model.eval()
    with torch.no_grad():
        logits = model(data)
    if not torch.isfinite(logits).all().item():
        raise ValueError("Nonfinite final predictions")
    return {"model": model, "logits": logits, "losses": losses, "seed": seed,
            "initial_parameter_sha256": initial_sha, "final_parameter_sha256": _parameter_hash(model),
            "GT_accessed": False, "evaluation_performed": False}
