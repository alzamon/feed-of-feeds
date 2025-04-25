"""
FoF - Feed of Feeds
A hierarchical feed reader with weighted sampling based on user preferences.
"""

__version__ = "0.1.0"

from .feed_manager import FeedManager
from .models import Feed, UnionFeed, FilterFeed, Article

__all__ = ['FeedManager', 'Feed', 'UnionFeed', 'FilterFeed', 'Article']
