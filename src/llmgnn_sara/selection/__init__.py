"""GT-free graph adapters; frozen FeatProp IDs remain the reconstruction baseline."""
from .neighbors import build_undirected_neighbors, semantic_topk_1hop

__all__ = ["build_undirected_neighbors", "semantic_topk_1hop"]
