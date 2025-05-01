"""
FoF - Feed of Feeds
A hierarchical feed reader with weighted sampling based on user preferences.

Last updated: 2025-04-25 21:02:06
Author: alzamon
"""

__version__ = "0.1.0"

from .feed_manager import FeedManager
from .models.feed import BaseFeed, RegularFeed, UnionFeed
from .models.filter import FilterFeed
from .models.article import Article

__all__ = ['FeedManager', 'BaseFeed', 'RegularFeed', 'UnionFeed', 'FilterFeed', 'Article']
