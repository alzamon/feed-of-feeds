"""Union feed loading functionality."""
import json
import os
import logging
from typing import Optional
from datetime import datetime

from ..base_feed import BaseFeed
from .models import UnionFeed, WeightedFeed
from ...time_period import parse_time_period

logger = logging.getLogger(__name__)


def load_union_feed(
        feed_loader,
        path: str,
        feedpath: list,
        parent_max_age=None,
        is_root=False) -> Optional[BaseFeed]:
    """Load a union feed from a directory structure."""
    union_path = os.path.join(path, "union.fof")
    try:
        with open(union_path, "r", encoding="utf-8") as f:
            union_info = json.load(f)
    except Exception as e:
        logger.error(
            f"Failed to load or parse JSON from {union_path}.\n"
            f"Error type: {type(e).__name__}\n"
            f"Error message: {e}\n"
        )
        raise
    weights = union_info.get("weights", {})
    subfeeds = []
    union_id = union_info.get(
        "id") if "id" in union_info else os.path.basename(path)
    union_feedpath = feedpath + [union_id] if not is_root else []
    max_age_str = union_info.get(
        "max_age") if "max_age" in union_info else None
    my_max_age = parse_time_period(max_age_str) if isinstance(
        max_age_str, str) and max_age_str else parent_max_age

    # Handle purge_age - only set if explicitly specified in config
    purge_age_str = union_info.get("purge_age")
    my_purge_age = parse_time_period(
        purge_age_str) if purge_age_str else None
    for sub_name, weight in weights.items():
        sub_path = os.path.join(path, sub_name)
        sub_feed = feed_loader.load_feed_from_directory(
            sub_path, feedpath=union_feedpath, parent_max_age=my_max_age)
        if sub_feed is not None:
            subfeeds.append(WeightedFeed(feed=sub_feed, weight=weight))
        else:
            logger.warning(
                f"Failed to load subfeed {sub_name} in {path}")
    union_feedpath_for_self = feedpath + [union_id] if not is_root else []
    union_title = (union_info.get("title") if "title" in union_info
                   else os.path.basename(path))
    union_description = (union_info.get("description")
                         if "description" in union_info else "")
    union_last_updated = (
        datetime.fromisoformat(union_info["last_updated"])
        if "last_updated" in union_info
        else datetime.now())
    return UnionFeed(
        title=union_title,
        description=union_description,
        feeds=subfeeds,
        last_updated=union_last_updated,
        max_age=my_max_age,
        feedpath=union_feedpath_for_self,
        purge_age=my_purge_age)
