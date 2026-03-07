"""Feed loading functionality."""
import os
import logging
from typing import Optional

from .models.base_feed import BaseFeed
from .models.union_feed.loader import load_union_feed
from .models.filter_feed.loader import load_filter_feed
from .models.syndication_feed.loader import load_syndication_feed

logger = logging.getLogger(__name__)


class FeedLoader:
    """Handles loading feeds from directory structures and config files."""

    def __init__(self, article_manager):
        """Initialize with article manager for syndication feeds."""
        self.article_manager = article_manager

    def load_feed_from_directory(
            self,
            path: str,
            feedpath: list,
            parent_max_age=None,
            is_root=False) -> Optional[BaseFeed]:
        """Load a feed from a directory structure."""
        union_path = os.path.join(path, "union.fof")
        filter_path = os.path.join(path, "filter.fof")
        feed_path = os.path.join(path, "feed.fof")

        if os.path.isfile(union_path):
            return load_union_feed(
                self, path, feedpath, parent_max_age, is_root)
        elif os.path.isfile(feed_path):
            return load_syndication_feed(
                self, path, feedpath, parent_max_age, is_root)
        elif os.path.isfile(filter_path):
            return load_filter_feed(
                self, path, feedpath, parent_max_age, is_root)
        else:
            logger.error(f"Unknown feed directory structure at {path}")
            return None


