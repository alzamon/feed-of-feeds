"""Syndication feed loading functionality."""
import json
import os
import logging
from typing import Optional
from datetime import datetime

from ..base_feed import BaseFeed
from .models import SyndicationFeed
from ...time_period import parse_time_period

logger = logging.getLogger(__name__)


def load_syndication_feed(
        feed_loader,
        path: str,
        feedpath: list,
        parent_max_age=None,
        is_root=False) -> Optional[BaseFeed]:
    """Load a syndication feed from a directory structure."""
    feed_path = os.path.join(path, "feed.json")
    with open(feed_path, "r", encoding="utf-8") as f:
        feed_data = json.load(f)
    feed_id = feed_data.get("id")
    max_age_str = feed_data.get("max_age")
    my_max_age = parse_time_period(max_age_str) if isinstance(
        max_age_str, str) and max_age_str else parent_max_age
    if not my_max_age:
        raise ValueError("Root feed must have a max_age defined")

    # Handle purge_age - only set if explicitly specified in config
    purge_age_str = feed_data.get("purge_age")
    my_purge_age = parse_time_period(
        purge_age_str) if purge_age_str else None
    syndication_feedpath = feedpath + [feed_id] if not is_root else []
    feed_last_updated = (
        datetime.fromisoformat(feed_data["last_updated"])
        if "last_updated" in feed_data
        else datetime.now())
    return SyndicationFeed(
        title=feed_data.get("title"),
        description=feed_data.get(
            "description",
            "No description provided"),
        last_updated=feed_last_updated,
        url=feed_data["url"],
        max_age=my_max_age,
        article_manager=feed_loader.article_manager,
        feedpath=syndication_feedpath,
        purge_age=my_purge_age,
    )