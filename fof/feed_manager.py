"""Core FoF feed management functionality."""
import random
import json
import os
from typing import Dict, Optional, List, Callable, Any
from datetime import timedelta, datetime
import logging

from .models.article import Article
from .models.base_feed import BaseFeed
from .models.union_feed import UnionFeed, WeightedFeed
from .models.syndication_feed import SyndicationFeed
from .models.filter_feed import FilterFeed, Filter
from .models.enums import FeedType, FilterType
from .models.article_manager import ArticleManager
from .config_manager import ConfigManager

from .time_period import parse_time_period, timedelta_to_period_str

logger = logging.getLogger(__name__)

class FeedManager:
    """Main class for managing feeds """

    def __init__(self, article_manager: ArticleManager, config_manager: ConfigManager, feed_id: Optional[str] = None):
        """Initialize the FeedManager.

        Args:
            article_manager (ArticleManager): The article manager instance to use.
            config_manager: The configuration manager instance to use.
            feed_id (Optional[str]): If set, disables all feeds except the specified feed and its descendants after loading.
        """
        self.config_manager = config_manager
        self.config_path = self.config_manager.config_path
        self.article_manager = article_manager
        self.feed_id = feed_id
        self._load_config()
        if self.feed_id:
            self._set_disabled_in_session_for_feeds(self.feed_id)

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
        union_path = os.path.join(path, "union.json")
        filter_path = os.path.join(path, "filter.json")
        feed_path = os.path.join(path, "feed.json")
        if os.path.isfile(union_path):
            with open(union_path, "r", encoding="utf-8") as f:
                union_info = json.load(f)
            weights = union_info.get("weights", {})
            subfeeds = []
            union_id = union_info.get("id") if "id" in union_info else os.path.basename(path)
            union_feedpath = feedpath + [union_id] if not is_root else []
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
            with open(feed_path, "r", encoding="utf-8") as f:
                feed_data = json.load(f)
            feed_id = feed_data.get("id")
            max_age_str = feed_data.get("max_age")
            my_max_age = parse_time_period(max_age_str) if isinstance(max_age_str, str) and max_age_str else parent_max_age
            if not my_max_age:
                raise ValueError("Root feed must have a max_age defined")
            syndication_feedpath =  feedpath + [feed_id] if not is_root else []
            return SyndicationFeed(
                id=feed_data["id"],
                title=feed_data.get("title"),
                description=feed_data.get("description", "No description provided"),
                last_updated=datetime.now(),
                url=feed_data["url"],
                max_age=my_max_age,
                article_manager=self.article_manager,
                feedpath=syndication_feedpath,
            )
        elif os.path.isfile(filter_path):
            with open(filter_path, "r", encoding="utf-8") as f:
                filter_data = json.load(f)
            filter_id = filter_data["id"]
            max_age_str = filter_data.get("max_age")
            my_max_age = parse_time_period(max_age_str) if isinstance(max_age_str, str) and max_age_str else parent_max_age
            if not my_max_age:
                raise ValueError("Root feed must have a max_age defined (inherited)")
            filter_feedpath = feedpath + [filter_id] if not is_root else []
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

    def get_feed_by_id(self, feed_id: str):
        """
        Recursively search for a feed with the given id in the entire feed tree.
        Returns the feed object if found, else None.
        """
        found_feed = None

        def finder(feed, ctx):
            nonlocal found_feed
            if getattr(feed, "id", None) == feed_id:
                found_feed = feed

        if getattr(self, "root_feed", None):
            self.perform_on_feeds(self.root_feed, finder)
        return found_feed

    def _try_load_union_info(self, path: str):
        union_path = os.path.join(path, "union.json")
        if os.path.isfile(union_path):
            with open(union_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def serialize_to_directory(self, feed: BaseFeed, path: str):
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
        if feed.feed_type == FeedType.UNION or feed.feed_type == FeedType.FILTER:
            name = feed.title or feed.id or "union"
            return self.config_manager.sanitize_filename(name)
        elif feed.feed_type == FeedType.SYNDICATION:
            return self.config_manager.sanitize_filename(feed.title or feed.id or "feed")
        else:
            return self.config_manager.sanitize_filename(feed.title or feed.id or "feed")

    def serialize_feed(self, feed: BaseFeed) -> dict:
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

    def save_config(self):
        """
        Atomically save the current root_feed to the new directory-based format.
        Write to an 'update' directory first, then move to 'tree' on success via config_manager.
        All chdir and delete logic is handled by config_manager.persist_update.
        Assumes update dir does not exist before serialization.
        """
        update_dir = self.config_manager.get_update_dir
        self.serialize_to_directory(self.root_feed, update_dir)
        self.config_manager.persist_update(update_dir)

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

    def perform_on_feeds(
        self,
        base_feed: BaseFeed,
        performer: Callable[[BaseFeed, dict], None],
        context: Optional[dict] = None
    ):
        """
        Recursively apply the performer to the base_feed and all its descendants,
        passing a user-supplied context dict which can be used for state accumulation (e.g., likelihood).

        The performer is a callable with signature (feed, context).
        If you need to update the context for a descendant (e.g., multiply likelihood for WeightedFeed),
        copy the context first.

        Example:
            def print_feed(feed, ctx):
                ...

            fm.perform_on_feeds(fm.root_feed, print_feed, {"likelihood": 1.0})
        """
        if context is None:
            context = {}

        performer(base_feed, context)

        # WeightedFeed: has .feed (compose likelihood if present)
        if hasattr(base_feed, "weight") and hasattr(base_feed, "feed"):
            new_context = context.copy()
            if "likelihood" in new_context:
                new_context["likelihood"] *= (base_feed.weight / 100.0)
            else:
                new_context["likelihood"] = (base_feed.weight / 100.0)
            self.perform_on_feeds(base_feed.feed, performer, new_context)
        # UnionFeed: has .feeds (list of WeightedFeed)
        elif hasattr(base_feed, "feeds"):
            for subfeed in getattr(base_feed, "feeds", []):
                self.perform_on_feeds(subfeed, performer, context.copy())
        # FilterFeed: has .source_feed
        elif hasattr(base_feed, "source_feed"):
            self.perform_on_feeds(base_feed.source_feed, performer, context.copy())
        # SyndicationFeed: no children, done

    def _set_disabled_in_session_for_feeds(self, active_feed_id: str):
        """
        Disables all feeds except:
          * feeds in the selected feed's feedpath (ancestors and itself), and
          * the selected feed and all its descendants.
        """
        if not self.root_feed:
            return

        # Find the selected feed object by id
        selected_feed = None
        def find_feed(feed: BaseFeed, ctx: dict):
            nonlocal selected_feed
            if getattr(feed, 'id', None) == active_feed_id:
                selected_feed = feed
        self.perform_on_feeds(self.root_feed, find_feed)
        if not selected_feed:
            logger.warning(f"Feed with id '{active_feed_id}' not found for disabling in session.")
            return

        # Ancestors: all ids in the feedpath of the selected feed
        allowed_ids = set(getattr(selected_feed, 'feedpath', []))
        # Include the selected feed itself
        allowed_ids.add(getattr(selected_feed, 'id', None))

        # Descendants: recursively collect all feed ids under the selected feed (including itself)
        def collect_descendants(feed: BaseFeed):
            feed_id = getattr(feed, 'id', None)
            if feed_id is not None:
                allowed_ids.add(feed_id)
            # UnionFeed: has .feeds (list of WeightedFeed)
            if hasattr(feed, "feeds"):
                for wf in getattr(feed, "feeds", []):
                    collect_descendants(wf.feed)
            # FilterFeed: has .source_feed
            elif hasattr(feed, "source_feed"):
                collect_descendants(feed.source_feed)
            # SyndicationFeed: just itself

        collect_descendants(selected_feed)

        # Now disable all feeds not in allowed_ids
        def disable_unless_allowed(feed: BaseFeed, ctx: dict):
            feed_id = getattr(feed, 'id', None)
            feed.disabled_in_session = (feed_id not in allowed_ids)

        self.perform_on_feeds(self.root_feed, disable_unless_allowed)

