"""Feed serialization functionality."""
import os
from typing import Set, Optional

from .models.base_feed import BaseFeed
from .models.enums import FeedType
from .models.union_feed.serializer import serialize_union_feed_to_directory, serialize_union_feed_to_dict
from .models.filter_feed.serializer import serialize_filter_feed_to_directory, serialize_filter_feed_to_dict
from .models.syndication_feed.serializer import serialize_syndication_feed_to_directory, serialize_syndication_feed_to_dict
from .time_period import timedelta_to_period_str
from .symlink_utils import is_path_symlinked


class FeedSerializer:
    """Handles serialization of feed objects to JSON and directory structures."""

    def __init__(self, config_manager):
        """Initialize with config manager for filename sanitization."""
        self.config_manager = config_manager
        self.preserved_symlinks: Optional[Set[str]] = None
        self.update_dir: Optional[str] = None

    def set_symlink_context(self, preserved_symlinks: Set[str], update_dir: str):
        """Set symlink preservation context for this serialization session."""
        self.preserved_symlinks = preserved_symlinks
        self.update_dir = update_dir

    def clear_symlink_context(self):
        """Clear symlink preservation context."""
        self.preserved_symlinks = None
        self.update_dir = None

    def is_path_preserved_symlink(self, path: str) -> bool:
        """Check if a path is already preserved as a symlink."""
        if self.preserved_symlinks is None or self.update_dir is None:
            return False
        return is_path_symlinked(path, self.update_dir, self.preserved_symlinks)

    def serialize_to_directory(self, feed: BaseFeed, path: str):
        """Serialize a feed and its children to a directory structure."""
        # Skip serialization if this path is already preserved as a symlink
        if self.is_path_preserved_symlink(path):
            return

        os.makedirs(path, exist_ok=True)
        if feed.feed_type == FeedType.UNION:
            serialize_union_feed_to_directory(feed, path, self)
        elif feed.feed_type == FeedType.SYNDICATION:
            serialize_syndication_feed_to_directory(feed, path, self)
        elif feed.feed_type == FeedType.FILTER:
            serialize_filter_feed_to_directory(feed, path, self)
        else:
            raise ValueError(f"Unknown feed type: {feed.feed_type}")

    def get_feed_folder_or_filename(self, feed: BaseFeed) -> str:
        """Get the folder or filename for a feed based on its type and properties."""
        if not feed.local_id:
            raise ValueError(f"Feed must have a local_id for directory naming: {feed}")
        return self.config_manager.sanitize_filename(feed.local_id)

    def _get_base_feed_dict(self, feed: BaseFeed) -> dict:
        """Get the common fields for all feed types."""
        return {
            "id": feed.local_id,
            "title": feed.title,
            "description": feed.description,
            "last_updated": feed.last_updated.isoformat(),
            "max_age": timedelta_to_period_str(
                feed.max_age) if hasattr(
                feed,
                'max_age') and feed.max_age else None,
        }

    def _add_purge_age_if_present(self, result: dict, feed: BaseFeed) -> None:
        """Add purge_age to result if it exists and is not None."""
        if hasattr(feed, 'purge_age') and feed.purge_age is not None:
            result["purge_age"] = timedelta_to_period_str(feed.purge_age)

    def serialize_feed(self, feed: BaseFeed) -> dict:
        """Serialize a feed object to a dictionary."""
        if feed.feed_type == FeedType.SYNDICATION:
            return serialize_syndication_feed_to_dict(feed, self)
        elif feed.feed_type == FeedType.FILTER:
            return serialize_filter_feed_to_dict(feed, self)
        elif feed.feed_type == FeedType.UNION:
            return serialize_union_feed_to_dict(feed, self)
        raise ValueError(f"Unknown feed type: {feed.feed_type}")
