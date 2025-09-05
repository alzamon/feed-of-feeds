"""Feed serialization functionality."""
import json
import os

from .models.base_feed import BaseFeed
from .models.enums import FeedType
from .time_period import timedelta_to_period_str


class FeedSerializer:
    """Handles serialization of feed objects to JSON and directory structures."""

    def __init__(self, config_manager):
        """Initialize with config manager for filename sanitization."""
        self.config_manager = config_manager

    def serialize_to_directory(self, feed: BaseFeed, path: str):
        """Serialize a feed and its children to a directory structure."""
        os.makedirs(path, exist_ok=True)
        if feed.feed_type == FeedType.UNION:
            weights = {}
            for wf in feed.feeds:
                subfeed_name = self.get_feed_folder_or_filename(wf.feed)
                weights[subfeed_name] = wf.weight

            union_meta = {
                "title": getattr(
                    feed, "title", None), "description": getattr(
                    feed, "description", ""), "last_updated": feed.last_updated.isoformat() if getattr(
                    feed, "last_updated", None) else None, "max_age": timedelta_to_period_str(
                        feed.max_age) if getattr(
                            feed, "max_age", None) else None, "weights": weights, }
            # Only include purge_age if it's not None
            if getattr(feed, "purge_age", None) is not None:
                union_meta["purge_age"] = timedelta_to_period_str(
                    feed.purge_age)
            union_meta_path = os.path.join(path, "union.json")
            with open(union_meta_path, "w", encoding="utf-8") as f:
                json.dump(union_meta, f, indent=2, ensure_ascii=False)
            for wf in feed.feeds:
                subfeed_name = self.get_feed_folder_or_filename(wf.feed)
                child_path = os.path.join(path, subfeed_name)
                self.serialize_to_directory(wf.feed, child_path)

        elif feed.feed_type == FeedType.SYNDICATION:
            feed_path = os.path.join(path, "feed.json")
            with open(feed_path, "w", encoding="utf-8") as f:
                json.dump(self.serialize_feed(feed), f,
                          indent=2, ensure_ascii=False)

        elif feed.feed_type == FeedType.FILTER:
            filter_dir = path
            os.makedirs(filter_dir, exist_ok=True)
            filter_config_path = os.path.join(filter_dir, "filter.json")
            config = {
                "title": feed.title,
                "description": feed.description,
                "last_updated": feed.last_updated.isoformat(),
                "max_age": timedelta_to_period_str(
                    feed.max_age) if feed.max_age else None,
                "criteria": [
                    {
                        "filter_type": f.filter_type.value,
                        "pattern": f.pattern,
                        "is_inclusion": f.is_inclusion} for f in feed.filters]}
            # Only include purge_age if it's not None
            if feed.purge_age is not None:
                config["purge_age"] = timedelta_to_period_str(feed.purge_age)
            with open(filter_config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.serialize_to_directory(
                feed.source_feed, os.path.join(
                    filter_dir, "source"))
        else:
            raise ValueError(f"Unknown feed type: {feed.feed_type}")

    def get_feed_folder_or_filename(self, feed: BaseFeed) -> str:
        """Get the folder or filename for a feed based on its type and properties."""
        if feed.feed_type == FeedType.UNION or feed.feed_type == FeedType.FILTER:
            name = feed.title or feed.id or "union"
            return self.config_manager.sanitize_filename(name)
        elif feed.feed_type == FeedType.SYNDICATION:
            return self.config_manager.sanitize_filename(
                feed.title or feed.id or "feed")
        else:
            return self.config_manager.sanitize_filename(
                feed.title or feed.id or "feed")

    def _get_base_feed_dict(self, feed: BaseFeed) -> dict:
        """Get the common fields for all feed types."""
        return {
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
            result = self._get_base_feed_dict(feed)
            result["url"] = feed.url
            self._add_purge_age_if_present(result, feed)
            return result
        elif feed.feed_type == FeedType.FILTER:
            result = self._get_base_feed_dict(feed)
            result.update({
                "criteria": [
                    {
                        "filter_type": f.filter_type.value,
                        "pattern": f.pattern,
                        "is_inclusion": f.is_inclusion
                    } for f in feed.filters
                ],
                "feed": self.serialize_feed(feed.source_feed)
            })
            self._add_purge_age_if_present(result, feed)
            return result
        elif feed.feed_type == FeedType.UNION:
            result = self._get_base_feed_dict(feed)
            result["feeds"] = [
                {
                    "weight": wf.weight,
                    "feed": self.serialize_feed(wf.feed)
                } for wf in feed.feeds
            ]
            self._add_purge_age_if_present(result, feed)
            return result
        raise ValueError(f"Unknown feed type: {feed.feed_type}")
