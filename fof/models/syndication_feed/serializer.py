"""Syndication feed serialization functionality.

NOTE: Symlinked directories are treated as static, curated subtrees and are never modified or serialized into by this program.
"""
import json
import os
import logging

from .models import SyndicationFeed

logger = logging.getLogger(__name__)

def serialize_syndication_feed_to_directory(feed: SyndicationFeed, path: str, serializer):
    """Serialize a syndication feed to a directory structure.

    If the target directory is a symlink, skip serialization and log info.
    """
    if os.path.islink(path):
        logger.info(f"Skipping serialization for symlinked syndication feed directory: {path}")
        return
    os.makedirs(path, exist_ok=True)
    feed_path = os.path.join(path, "feed.fof")
    with open(feed_path, "w", encoding="utf-8") as f:
        json.dump(serializer.serialize_feed(feed), f,
                  indent=2, ensure_ascii=False)


def serialize_syndication_feed_to_dict(feed: SyndicationFeed, serializer) -> dict:
    """Serialize a syndication feed object to a dictionary."""
    result = serializer._get_base_feed_dict(feed)
    result["url"] = feed.url
    serializer._add_purge_age_if_present(result, feed)
    return result
