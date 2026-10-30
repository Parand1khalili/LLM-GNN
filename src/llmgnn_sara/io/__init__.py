"""Hash-pinned, read-only research inputs. No binary deserialization."""
from .frozen import CLASSES, FrozenDataset, FrozenPrediction, FrozenSample, load_frozen

__all__ = ["CLASSES", "FrozenDataset", "FrozenPrediction", "FrozenSample", "load_frozen"]
