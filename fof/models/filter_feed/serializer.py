"""Filter feed serialization functionality."""
import json
import os

from .models import FilterFeed
from ...time_period import timedelta_to_period_str


def serialize_filter_feed_to_directory(feed: FilterFeed, path: str, serializer):
    """Serialize a filter feed and its children to a directory structure."""
    filter_dir = path
    os.makedirs(filter_dir, exist_ok=True)
    filter_config_path = os.path.join(filter_dir, "filter.json")
    config = {
        "id": feed.local_id,
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
    serializer.serialize_to_directory(
        feed.source_feed, os.path.join(
            filter_dir, "source"))


def serialize_filter_feed_to_dict(feed: FilterFeed, serializer) -> dict:
    """Serialize a filter feed object to a dictionary."""
    result = serializer._get_base_feed_dict(feed)
    result.update({
        "criteria": [
            {
                "filter_type": f.filter_type.value,
                "pattern": f.pattern,
                "is_inclusion": f.is_inclusion
            } for f in feed.filters
        ],
        "feed": serializer.serialize_feed(feed.source_feed)
    })
    serializer._add_purge_age_if_present(result, feed)
    return result