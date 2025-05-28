"""Core FoF feed management functionality."""
import random
import json
import os
from typing import Dict, Optional, List
from datetime import timedelta, datetime
import logging

from .models.article import Article
from .models.base_feed import BaseFeed
from .models.union_feed import UnionFeed, WeightedFeed
from .models.regular_feed import RegularFeed
from .models.filter_feed import FilterFeed, Filter
from .models.enums import FeedType, FilterType
from .models.article_manager import ArticleManager
from .config_manager import ConfigManager

from .time_period import parse_time_period, timedelta_to_period_str

logger = logging.getLogger(__name__)

class FeedManager:
    """Main class for managing feeds """

    def __init__(self, article_manager: ArticleManager, config_manager: ConfigManager):
        """Initialize the FeedManager.

        Args:
            article_manager (ArticleManager): The article manager instance to use.
            config_manager: The configuration manager instance to use.
        """
        self.config_manager = config_manager
        self.config_path = self.config_manager.config_path
        self.article_manager = article_manager
        self._load_config()

    def _load_config(self):
        """Load the configuration from the 'tree' directory and initialize feeds."""
        config_dir = self.config_manager.get_tree_dir
        try:
            feed = self._load_feed_from_directory(config_dir, feedpath=[], parent_max_age=None, is_root=True)
            if feed is None:
                logger.error(f"No valid feed found in config directory {config_dir}. Skipping load.")
                self.root_feed = None
            else:
                self.root_feed = feed
        except Exception as e:
            logger.error(f"Failed to load config from directory at {config_dir}: {e}")
            self.root_feed = None

    def _load_feed_from_directory(self, path: str, feedpath: list, parent_max_age=None, is_root=False) -> Optional[BaseFeed]:
        """
        Recursively load a feed from a directory structure.
        - UnionFeed: directory contains union.json and subdirs.
        - RegularFeed: directory contains feed.json.
        - FilterFeed: directory contains filter.json and 'source' subdir.
        feedpath is a list of IDs from the root to this feed (not including the root).
        parent_max_age is the inherited max_age from the parent feed.
        """
        union_path = os.path.join(path, "union.json")
        filter_path = os.path.join(path, "filter.json")
        feed_path = os.path.join(path, "feed.json")
        if os.path.isfile(union_path):
            # It's a union feed
            with open(union_path, "r", encoding="utf-8") as f:
                union_info = json.load(f)
            weights = union_info.get("weights", {})
            subfeeds = []
            union_id = union_info.get("id") if "id" in union_info else os.path.basename(path)
            union_feedpath = feedpath + [union_id] if not is_root else []
            # Inherit max_age if not explicitly set
            max_age_str = union_info.get("max_age") if "max_age" in union_info else None
            my_max_age = parse_time_period(max_age_str) if isinstance(max_age_str, str) and max_age_str else parent_max_age
            for sub_name, weight in weights.items():
                sub_path = os.path.join(path, sub_name)
                sub_feed = self._load_feed_from_directory(sub_path, feedpath=union_feedpath, parent_max_age=my_max_age)
                if sub_feed is not None:
                    subfeeds.append(WeightedFeed(feed=sub_feed, weight=weight))
                else:
                    logger.warning(f"Failed to load subfeed {sub_name} in {path}")
            return UnionFeed(
                id=union_id,
                title=union_info.get("title") if "title" in union_info else os.path.basename(path),
                description=union_info.get("description") if "description" in union_info else "",
                feeds=subfeeds,
                last_updated=datetime.fromisoformat(union_info["last_updated"]) if "last_updated" in union_info else datetime.now(),
                max_age=my_max_age,
                feedpath=feedpath
            )
        elif os.path.isfile(feed_path):
            # It's a regular feed
            with open(feed_path, "r", encoding="utf-8") as f:
                feed_data = json.load(f)
            feed_id = feed_data.get("id")
            max_age_str = feed_data.get("max_age")
            my_max_age = parse_time_period(max_age_str) if isinstance(max_age_str, str) and max_age_str else parent_max_age
            # Root must have max_age!
            if not my_max_age:
                raise ValueError("Root feed must have a max_age defined")
            
            regular_feedpath =  feedpath + [feed_id] if not is_root else []
            return RegularFeed(
                id=feed_data["id"],
                title=feed_data.get("title"),
                description=feed_data.get("description", "No description provided"),
                last_updated=datetime.now(),
                url=feed_data["url"],
                max_age=my_max_age,
                article_manager=self.article_manager,
                feedpath=regular_feedpath,
            )
        elif os.path.isfile(filter_path):
            # It's a filter feed
            with open(filter_path, "r", encoding="utf-8") as f:
                filter_data = json.load(f)
            filter_id = filter_data["id"]
            max_age_str = filter_data.get("max_age")
            my_max_age = parse_time_period(max_age_str) if isinstance(max_age_str, str) and max_age_str else parent_max_age
            if not my_max_age:
                raise ValueError("Root feed must have a max_age defined (inherited)")
            filter_feedpath = feedpath + [filter_id]
            source_path = os.path.join(path, "source")
            source_feed = self._load_feed_from_directory(source_path, feedpath=filter_feedpath, parent_max_age=my_max_age)
            filters = [
                Filter(
                    filter_type=FilterType(c["filter_type"]),
                    pattern=c["pattern"],
                    is_inclusion=c["is_inclusion"]
                ) for c in filter_data["criteria"]
            ]
            return FilterFeed(
                id=filter_id,
                title=filter_data.get("title"),
                description=filter_data.get("description"),
                filters=filters,
                source_feed=source_feed,
                last_updated=datetime.fromisoformat(filter_data["last_updated"]) if "last_updated" in filter_data else datetime.now(),
                max_age=my_max_age,
                feedpath=filter_feedpath
            )
        else:
            logger.error(f"Unknown feed directory structure at {path}")
            return None

    def _try_load_union_info(self, path: str):
        """
        Try to load union feed metadata (optional).
        Looks for 'union.json' or similar for union meta, e.g. id, title, description.
        """
        union_path = os.path.join(path, "union.json")
        if os.path.isfile(union_path):
            with open(union_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def serialize_to_directory(self, feed: BaseFeed, path: str):
        """
        Recursively serialize a feed tree to a directory structure inside `path`.
        - Each UnionFeed becomes a folder with union.json for weights and meta.
        - Each RegularFeed becomes a .json file with its configuration.
        - Each FilterFeed becomes a folder with filter config and a subfeed.
        """
        os.makedirs(path, exist_ok=True)
        if feed.feed_type == FeedType.UNION:
            weights = {}
            for wf in feed.feeds:
                subfeed_name = self.get_feed_folder_or_filename(wf.feed)
                weights[subfeed_name] = wf.weight

            # Save union feed meta (id, title, etc.) and weights into union.json
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

        elif feed.feed_type == FeedType.REGULAR:
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
        """
        Helper to get a folder or filename for a feed based on its type.
        """
        # Use the sanitize_filename method from ConfigManager
        if feed.feed_type == FeedType.UNION or feed.feed_type == FeedType.FILTER:
            name = feed.title or feed.id or "union"
            return self.config_manager.sanitize_filename(name)
        elif feed.feed_type == FeedType.REGULAR:
            return self.config_manager.sanitize_filename(feed.title or feed.id or "feed")
        else:
            return self.config_manager.sanitize_filename(feed.title or feed.id or "feed")

    def serialize_feed(self, feed: BaseFeed) -> dict:
        """Recursively serialize a feed to a dict suitable for saving as JSON config."""
        if feed.feed_type == FeedType.REGULAR:
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

    def save_config(self):
        """
        Save the current root_feed to the new directory-based format.
        """
        config_dir = self.config_manager.get_tree_dir
        import shutil
        shutil.rmtree(config_dir)
        self.serialize_to_directory(self.root_feed, config_dir)

    def next_article(self) -> Optional[Article]:
        if not self.root_feed:
            logger.warning("No root feed available to fetch articles.")
            return None
        return self.root_feed.fetch()

    def update_weights(self, feedpath: List[str], increment: int):
        if not self.root_feed:
            raise ValueError("Root feed is not initialized.")
        current_feed = self.root_feed
        logger.debug(f"Starting feed traversal. Root feed ID: {current_feed.id}")
        parent_weighted_feed = None
        for feed_id in feedpath:
            logger.debug(f"Looking for feed ID '{feed_id}' in current feed '{current_feed.id}'")
            wf = None
            if isinstance(current_feed, UnionFeed):
                wf = next((wf for wf in current_feed.feeds if wf.feed.id == feed_id), None)
                sub_feed = wf.feed if wf else None
            elif isinstance(current_feed, FilterFeed):
                sub_feed = current_feed.source_feed if current_feed.source_feed.id == feed_id else None
            else:
                sub_feed = None
            if not sub_feed:
                logger.error(f"Feed with ID '{feed_id}' not found in the feedpath at feed '{current_feed.id}'")
                raise ValueError(f"Feed with ID '{feed_id}' not found in the feedpath.")
            if wf is not None:
                wf.weight += increment
                logger.info(f"Updated weight of feed '{sub_feed.id}' to {wf.weight}.")
            current_feed = sub_feed

