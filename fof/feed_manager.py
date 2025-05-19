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
from .error_logger import log_error_with_readkey
from .models.article_manager import ArticleManager

from .time_period import parse_time_period, timedelta_to_period_str

logger = logging.getLogger(__name__)

class FeedManager:
    """Main class for managing feeds and articles."""

    def __init__(self, config_path: str = "~/.config/fof", article_manager: ArticleManager = None):
        """Initialize the FeedManager.

        Args:
            config_path (str): Path to the configuration directory. Defaults to "~/.config/fof/".
            article_manager (ArticleManager): The article manager instance to use.
        """
        self.config_path = os.path.expanduser(config_path)
        if article_manager is None:
            self.article_manager = ArticleManager(db_path=self.config_path)
        else:
            self.article_manager = article_manager
        self._load_config()

    def _load_config(self):
        """Load the configuration file and initialize feeds."""
        config_file_path = os.path.join(self.config_path, "config.json")
        if not os.path.exists(config_file_path):
            logger.warning(f"Config file not found at {config_file_path}. Using empty configuration.")
            self.root_feed = None
            return

        try:
            with open(config_file_path, "r") as config_file:
                config_data = json.load(config_file)

                root_feed_config = config_data.get("defaultRootFeed")
                if not root_feed_config:
                    raise ValueError("Configuration must include a 'defaultRootFeed' property.")

                if "max_age" not in root_feed_config:
                    raise ValueError("Root feed must have a max_age defined in the configuration under 'defaultRootFeed'.")

                root_max_age = parse_time_period(root_feed_config["max_age"])
                # Use the from_config_dict classmethod for full recursive construction
                feed_type = FeedType(root_feed_config["feed_type"])
                if feed_type == FeedType.REGULAR:
                    self.root_feed = RegularFeed.from_config_dict(
                        root_feed_config,
                        self.article_manager,
                        parent_max_age=root_max_age,
                        parent_feedpath=[]
                    )
                elif feed_type == FeedType.UNION:
                    self.root_feed = UnionFeed.from_config_dict(
                        root_feed_config,
                        self.article_manager,
                        parent_max_age=root_max_age,
                        parent_feedpath=[]
                    )
                elif feed_type == FeedType.FILTER:
                    self.root_feed = FilterFeed.from_config_dict(
                        root_feed_config,
                        self.article_manager,
                        parent_max_age=root_max_age,
                        parent_feedpath=[]
                    )
                else:
                    raise ValueError(f"Unknown feed_type in root config: {feed_type}")
        except Exception as e:
            log_error_with_readkey(f"Failed to load config file at {config_file_path}: {e}")
            self.root_feed = None

    def serialize_feed(self, feed: BaseFeed) -> dict:
        """Recursively serialize a feed to a dict suitable for saving as JSON config."""
        if feed.feed_type == FeedType.REGULAR:
            return {
                "id": feed.id,
                "title": feed.title,
                "description": feed.description,
                "feed_type": "regular",
                "last_updated": feed.last_updated.isoformat(),
                "url": feed.url,
                "max_age": timedelta_to_period_str(feed.max_age) if feed.max_age else None,
            }
        elif feed.feed_type == FeedType.FILTER:
            return {
                "id": feed.id,
                "title": feed.title,
                "description": feed.description,
                "feed_type": "filter",
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
                "feed_type": "union",
                "last_updated": feed.last_updated.isoformat(),
                "max_age": timedelta_to_period_str(feed.max_age) if feed.max_age else None,
                "feeds": [
                    {
                        "weight": wf.weight,
                        "feed": self.serialize_feed(wf.feed)
                    } for wf in feed.feeds
                ]
            }
        else:
            raise ValueError(f"Unknown feed type: {feed.feed_type}")

    def save_config(self):
        """Serialize the root_feed and save to the config file."""
        config_file_path = os.path.join(self.config_path, "config.json")
        config_data = {
            "defaultRootFeed": self.serialize_feed(self.root_feed)
        }
        with open(config_file_path, "w") as config_file:
            json.dump(config_data, config_file, indent=2)

    def next_article(self) -> Optional[Article]:
        """Fetch the next article by sampling feeds until an article is retrieved or root feed fails.

        Returns:
            The fetched article, or None if no matching articles are available.
        """
        if not self.root_feed:
            logger.warning("No root feed available to fetch articles.")
            return None

        # This could have more logic for sampling/selection
        return self.root_feed.fetch()

    def update_weights(self, feedpath: List[str], increment: int):
        """
        Update the weights of feeds along the given feedpath, except the root.

        Args:
            feedpath (List[str]): The path of feeds in the tree (excluding the root).
            increment (int): The value to increment or decrement the weight by.

        Raises:
            ValueError: If the feedpath is invalid or does not exist.
        """
        if not self.root_feed:
            raise ValueError("Root feed is not initialized.")

        current_feed = self.root_feed
        logger.debug(f"Starting feed traversal. Root feed ID: {current_feed.id}")

        # The parent WeightedFeed object for the current feed if traversing a union
        parent_weighted_feed = None

        for feed_id in feedpath:
            logger.debug(f"Looking for feed ID '{feed_id}' in current feed '{current_feed.id}'")

            wf = None  # WeightedFeed containing the subfeed, if traversing a union
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

            # Update the weight on the WeightedFeed if we are traversing through a union
            if wf is not None:
                wf.weight += increment
                logger.info(f"Updated weight of feed '{sub_feed.id}' to {wf.weight}.")

            current_feed = sub_feed

