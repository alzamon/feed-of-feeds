"""Filter feed loading functionality."""
import json
import os
import logging
from typing import Optional
from datetime import datetime

from ..base_feed import BaseFeed
from .models import FilterFeed, Filter
from ..enums import FilterType
from ...time_period import parse_time_period

logger = logging.getLogger(__name__)


def load_filter_feed(
        feed_loader,
        path: str,
        feedpath: list,
        parent_max_age=None,
        is_root=False) -> Optional[BaseFeed]:
    """Load a filter feed from a directory structure."""
    filter_path = os.path.join(path, "filter.json")
    with open(filter_path, "r", encoding="utf-8") as f:
        filter_data = json.load(f)
    filter_id = filter_data["id"]
    max_age_str = filter_data.get("max_age")
    my_max_age = parse_time_period(max_age_str) if isinstance(
        max_age_str, str) and max_age_str else parent_max_age
    if not my_max_age:
        raise ValueError(
            "Root feed must have a max_age defined (inherited)")

    # Handle purge_age - only set if explicitly specified in config
    purge_age_str = filter_data.get("purge_age")
    my_purge_age = parse_time_period(
        purge_age_str) if purge_age_str else None
    filter_feedpath = feedpath + [filter_id] if not is_root else []
    source_path = os.path.join(path, "source")
    source_feed = feed_loader.load_feed_from_directory(
        source_path, feedpath=filter_feedpath, parent_max_age=my_max_age)
    filters = [
        Filter(
            filter_type=FilterType(c["filter_type"]),
            pattern=c["pattern"],
            is_inclusion=c["is_inclusion"]
        ) for c in filter_data["criteria"]
    ]
    filter_last_updated = (
        datetime.fromisoformat(filter_data["last_updated"])
        if "last_updated" in filter_data
        else datetime.now())
    return FilterFeed(
        title=filter_data.get("title"),
        description=filter_data.get("description"),
        filters=filters,
        source_feed=source_feed,
        last_updated=filter_last_updated,
        max_age=my_max_age,
        feedpath=filter_feedpath,
        purge_age=my_purge_age)