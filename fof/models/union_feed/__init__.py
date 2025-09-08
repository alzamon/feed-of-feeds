"""Union feed module with backward compatibility."""

from .models import UnionFeed, WeightedFeed, WEIGHT_PERCENTAGE_BASE
from .loader import load_union_feed
from .serializer import (serialize_union_feed_to_directory,
                         serialize_union_feed_to_dict)

__all__ = ['UnionFeed', 'WeightedFeed', 'WEIGHT_PERCENTAGE_BASE',
           'load_union_feed', 'serialize_union_feed_to_directory',
           'serialize_union_feed_to_dict']
