"""Syndication feed serialization functionality."""
import json
import os

from .models import SyndicationFeed


def serialize_syndication_feed_to_directory(feed: SyndicationFeed, path: str, serializer):
    """Serialize a syndication feed to a directory structure."""
    os.makedirs(path, exist_ok=True)
    feed_path = os.path.join(path, "feed.json")
    with open(feed_path, "w", encoding="utf-8") as f:
        json.dump(serializer.serialize_feed(feed), f,
                  indent=2, ensure_ascii=False)


def serialize_syndication_feed_to_dict(feed: SyndicationFeed, serializer) -> dict:
    """Serialize a syndication feed object to a dictionary."""
    result = serializer._get_base_feed_dict(feed)
    result["url"] = feed.url
    serializer._add_purge_age_if_present(result, feed)
    return result
