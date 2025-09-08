# Backward compatibility - import from new structure
from .union_feed import UnionFeed, WeightedFeed
from .union_feed.models import WEIGHT_PERCENTAGE_BASE

__all__ = ['UnionFeed', 'WeightedFeed', 'WEIGHT_PERCENTAGE_BASE']
