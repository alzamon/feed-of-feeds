"""Union feed serialization functionality.

NOTE: Symlinked directories are treated as static, curated subtrees and are never modified or serialized into by this program.
"""
import json
import os
import logging

from .models import UnionFeed
from ...time_period import timedelta_to_period_str

logger = logging.getLogger(__name__)


def serialize_union_feed_to_directory(feed: UnionFeed, path: str, serializer):
    """Serialize a union feed and its children to a directory structure.

    Symlinked directories are treated as static, curated subtrees and are never modified or serialized into.
    """
    if os.path.islink(path):
        logger.info(f"Skipping serialization for symlinked union feed directory: {path}")
        return
    os.makedirs(path, exist_ok=True)
    weights = {}
    for wf in feed.feeds:
        subfeed_name = serializer.get_feed_folder_or_filename(wf.feed)
        weights[subfeed_name] = wf.weight

    union_meta = {
        "id": getattr(feed, "local_id", None),
        "title": getattr(feed, "title", None),
        "description": getattr(feed, "description", ""),
        "last_updated": feed.last_updated.isoformat() if getattr(feed, "last_updated", None) else None,
        "max_age": timedelta_to_period_str(feed.max_age) if getattr(feed, "max_age", None) else None,
        "weights": weights,
    }
    # Only include purge_age if it's not None
    if getattr(feed, "purge_age", None) is not None:
        union_meta["purge_age"] = timedelta_to_period_str(feed.purge_age)
    union_meta_path = os.path.join(path, "union.fof")
    with open(union_meta_path, "w", encoding="utf-8") as f:
        json.dump(union_meta, f, indent=2, ensure_ascii=False)
    for wf in feed.feeds:
        subfeed_name = serializer.get_feed_folder_or_filename(wf.feed)
        child_path = os.path.join(path, subfeed_name)
        # Check if this path is preserved as a symlink (new symlink-aware check)
        if serializer.is_path_preserved_symlink(child_path):
            logger.info(f"Skipping serialization for preserved symlinked subfeed directory: {child_path}")
            continue
        # Legacy check for existing symlinks in the target location
        if os.path.islink(child_path):
            logger.info(f"Skipping serialization for symlinked subfeed directory: {child_path}")
            continue
        serializer.serialize_to_directory(wf.feed, child_path)


def serialize_union_feed_to_dict(feed: UnionFeed, serializer) -> dict:
    """Serialize a union feed object to a dictionary."""
    result = serializer._get_base_feed_dict(feed)
    result["feeds"] = [
        {
            "weight": wf.weight,
            "feed": serializer.serialize_feed(wf.feed)
        } for wf in feed.feeds
    ]
    serializer._add_purge_age_if_present(result, feed)
    return result
