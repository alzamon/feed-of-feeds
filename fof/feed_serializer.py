"""Feed serialization functionality."""
import json
import os
from typing import Dict, Any

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
                "id": getattr(feed, "id", None),
                "title": getattr(feed, "title", None),
                "description": getattr(feed, "description", ""),
                "last_updated": feed.last_updated.isoformat() if getattr(feed, "last_updated", None) else None,
                "max_age": timedelta_to_period_str(feed.max_age) if getattr(feed, "max_age", None) else None,
                "weights": weights,
            }
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
                json.dump(self.serialize_feed(feed), f, indent=2, ensure_ascii=False)

        elif feed.feed_type == FeedType.FILTER:
            filter_dir = path
            os.makedirs(filter_dir, exist_ok=True)
            filter_config_path = os.path.join(filter_dir, "filter.json")
            config = {
                "id": feed.id,
                "title": feed.title,
                "description": feed.description,
                "last_updated": feed.last_updated.isoformat(),
                "max_age": timedelta_to_period_str(feed.max_age) if feed.max_age else None,
                "criteria": [
                    {
                        "filter_type": f.filter_type.value,
                        "pattern": f.pattern,
                        "is_inclusion": f.is_inclusion
                    } for f in feed.filters
                ]
            }
            with open(filter_config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.serialize_to_directory(feed.source_feed, os.path.join(filter_dir, "source"))
        else:
            raise ValueError(f"Unknown feed type: {feed.feed_type}")

    def get_feed_folder_or_filename(self, feed: BaseFeed) -> str:
        """Get the folder or filename for a feed based on its type and properties."""
        if feed.feed_type == FeedType.UNION or feed.feed_type == FeedType.FILTER:
            name = feed.title or feed.id or "union"
            return self.config_manager.sanitize_filename(name)
        elif feed.feed_type == FeedType.SYNDICATION:
            return self.config_manager.sanitize_filename(feed.title or feed.id or "feed")
        else:
            return self.config_manager.sanitize_filename(feed.title or feed.id or "feed")

    def serialize_feed(self, feed: BaseFeed) -> dict:
        """Serialize a feed object to a dictionary."""
        if feed.feed_type == FeedType.SYNDICATION:
            return {
                "id": feed.id,
                "title": feed.title,
                "description": feed.description,
                "last_updated": feed.last_updated.isoformat(),
                "url": feed.url,
                "max_age": timedelta_to_period_str(feed.max_age) if feed.max_age else None,
            }
        elif feed.feed_type == FeedType.FILTER:
            return {
                "id": feed.id,
                "title": feed.title,
                "description": feed.description,
                "last_updated": feed.last_updated.isoformat(),
                "max_age": timedelta_to_period_str(feed.max_age) if feed.max_age else None,
                "criteria": [
                    {
                        "filter_type": f.filter_type.value,
                        "pattern": f.pattern,
                        "is_inclusion": f.is_inclusion
                    } for f in feed.filters
                ],
                "feed": self.serialize_feed(feed.source_feed)
            }
        elif feed.feed_type == FeedType.UNION:
            return {
                "id": feed.id,
                "title": feed.title,
                "description": feed.description,
                "last_updated": feed.last_updated.isoformat(),
                "max_age": timedelta_to_period_str(feed.max_age) if feed.max_age else None,
                "feeds": [
                    {
                        "weight": wf.weight,
                        "feed": self.serialize_feed(wf.feed)
                    } for wf in feed.feeds
                ]
            }
        raise ValueError(f"Unknown feed type: {feed.feed_type}")