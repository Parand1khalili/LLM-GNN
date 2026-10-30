"""GT-free matched GCN contracts; training is explicitly gated and never automatic."""
from .plan import GCNConfig, PseudoLabel, confidence_weights, gcn_demo_plan, gcn_plan, reduce_loss

__all__ = ["GCNConfig", "PseudoLabel", "confidence_weights", "gcn_demo_plan", "gcn_plan", "reduce_loss"]
