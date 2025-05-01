"""Core FoF feed management functionality."""
import random
import yaml
import os
from datetime import datetime
from typing import Dict, Optional
import logging
from pathlib import Path

from .models.article import Article
from .models.base_feed import BaseFeed
from .models.regular_feed import RegularFeed
from .models.union_feed import UnionFeed
from .models.filter import FilterFeed
from .models.enums import FeedType, FilterType

logger = logging.getLogger(__name__)

class FeedManager:
    """Main class for managing feeds and articles."""

    def __init__(self, config_path: str):
        """Initialize the FeedManager.

        Args:
            config_path (str): Path to the configuration file.
        """
        self.config_path = os.path.expanduser(config_path)
        self.feeds: Dict[str, BaseFeed] = {}
        self._load_config()

    def _load_config(self):
        """Load the configuration file and initialize feeds."""
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file not found at {self.config_path}. Using empty configuration.")
            return

        try:
            with open(self.config_path, "r") as config_file:
                config_data = yaml.safe_load(config_file)
                self._initialize_feeds(config_data.get("feeds", []))
        except Exception as e:
            logger.error(f"Failed to load config file at {self.config_path}: {e}")

    def _initialize_feeds(self, feeds_config: list[Dict]):
        """Initialize feeds from the configuration data.

        Args:
            feeds_config (List[Dict]): List of feed configuration dictionaries.
        """
        for feed_config in feeds_config:
            try:
                feed = self._create_feed(feed_config)
                if feed:
                    self.feeds[feed.id] = feed
                    logger.info(f"Loaded feed: {feed.id} ({feed.title})")
            except Exception as e:
                logger.error(f"Failed to initialize feed from config: {feed_config}. Error: {e}")

    def _create_feed(self, feed_config: Dict) -> Optional[BaseFeed]:
        """Create a feed object from the configuration.

        Args:
            feed_config (Dict): Feed configuration dictionary.

        Returns:
            BaseFeed: The initialized feed object or None if creation fails.
        """
        feed_type = FeedType(feed_config["type"])

        if feed_type == FeedType.REGULAR:
            return RegularFeed(
                id=feed_config["id"],
                url=feed_config["url"],
                title=feed_config.get("title"),
                weight=feed_config.get("weight", 1.0)
            )
        elif feed_type == FeedType.UNION:
            # Recursively create feeds within the UnionFeed
            member_feeds = [
                self._create_feed(member_feed) for member_feed in feed_config["feeds"]
            ]
            # Filter out None values in case of errors during recursion
            member_feeds = [feed for feed in member_feeds if feed is not None]

            return UnionFeed(
                id=feed_config["id"],
                feeds=member_feeds,
                title=feed_config.get("title"),
                weight=feed_config.get("weight", 1.0)
            )
        elif feed_type == FeedType.FILTER:
            return FilterFeed(
                id=feed_config["id"],
                feed=feed_config["feed"],
                filter_type=FilterType(feed_config["filter_type"]),
                criteria=feed_config["criteria"],
                title=feed_config.get("title"),
                weight=feed_config.get("weight", 1.0)
            )
        else:
            logger.warning(f"Unknown feed type: {feed_type}")
            return None

    def next_article(self) -> Optional[Article]:
        """Fetch the next article by sampling a feed based on weights.

        Returns:
            The fetched article, or None if no feeds are available or fetch fails.
        """
        if not self.feeds:
            logger.warning("No feeds available to fetch articles.")
            return None

        # Prepare weights for sampling
        feeds = list(self.feeds.values())
        weights = [feed.weight for feed in feeds]

        # Sample a feed based on weights
        chosen_feed = random.choices(feeds, weights=weights, k=1)[0]

        logger.info(f"Selected feed: {chosen_feed.id} ({chosen_feed.title})")

        # Fetch a single article from the chosen feed
        try:
            article = chosen_feed.fetch()
            if article:  # Ensure an article is returned
                logger.info(f"Fetched article: {article.id} ({article.title})")
                return article
            else:
                logger.warning(f"No article fetched from feed: {chosen_feed.id}")
        except Exception as e:
            logger.error(f"Error while fetching from feed {chosen_feed.id}: {e}")

        return None
