"""Core FoF feed management functionality."""
import random
import yaml
import os
from typing import Dict, Optional
from datetime import timedelta
import logging
from .models.article import Article
from .models.base_feed import BaseFeed
from .models.union_feed import UnionFeed
from .models.regular_feed import RegularFeed
from .models.filter_feed import FilterFeed, Filter
from .models.enums import FeedType, FilterType
from .error_logger import log_error_with_readkey  # Importing the utility function

logger = logging.getLogger(__name__)

class FeedManager:
    """Main class for managing feeds and articles."""

    def __init__(self, config_path: str):
        """Initialize the FeedManager.

        Args:
            config_path (str): Path to the configuration file.
        """
        self.config_path = os.path.expanduser(config_path)
        self._load_config()

    def _load_config(self):
        """Load the configuration file and initialize feeds."""
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file not found at {self.config_path}. Using empty configuration.")
            return

        try:
            with open(self.config_path, "r") as config_file:
                config_data = yaml.safe_load(config_file)

                # Initialize root feed (UnionFeed)
                root_feed_config = {
                    "id": "root",
                    "type": "union",
                    "feeds": config_data.get("feeds", []),
                    "max_age": config_data.get("max_age"),  # Root feed must have max_age set in config
                }
                if "max_age" not in root_feed_config:
                    raise ValueError("Root feed must have a max_age defined in the configuration.")
                
                root_max_age = timedelta(seconds=root_feed_config["max_age"])
                self.root_feed = self._create_feed(root_feed_config, parent_max_age=root_max_age)
        except Exception as e:
            log_error_with_readkey(f"Failed to load config file at {self.config_path}: {e}")

    def _create_feed(self, feed_config: Dict, parent_max_age: timedelta) -> BaseFeed:
        """Create a feed object from the configuration.

        Args:
            feed_config (Dict): Feed configuration dictionary.
            parent_max_age (timedelta): The max_age value inherited from the parent feed.

        Returns:
            BaseFeed: The initialized feed object.
        """
        feed_type = FeedType(feed_config["type"])
        feed_max_age = timedelta(seconds=feed_config.get("max_age", parent_max_age.total_seconds()))

        if feed_type == FeedType.REGULAR:
            return RegularFeed(
                id=feed_config["id"],
                url=feed_config["url"],
                title=feed_config.get("title"),
                weight=feed_config.get("weight", 1.0),
                max_age=feed_max_age  # Explicit max_age passed
            )
        elif feed_type == FeedType.UNION:
            # Recursively create child feeds with inherited max_age
            member_feeds = [
                self._create_feed(member_feed, parent_max_age=feed_max_age) for member_feed in feed_config["feeds"]
            ]
            member_feeds = [feed for feed in member_feeds if feed is not None]

            return UnionFeed(
                id=feed_config["id"],
                feeds=member_feeds,
                title=feed_config.get("title"),
                weight=feed_config.get("weight", 1.0),
                max_age=feed_max_age  # Explicit max_age passed
            )
        elif feed_type == FeedType.FILTER:
            # Create the source feed inline
            source_feed_config = feed_config["feed"]
            source_feed = self._create_feed(source_feed_config, parent_max_age=feed_max_age)
            if not source_feed:
                logger.warning(
                    f"Failed to create source feed for filter feed: {feed_config['id']}"
                )
                return None

            # Create FilterFeed and add filters
            filter_feed = FilterFeed(
                source_feed=source_feed,
                id=feed_config["id"],
                title=feed_config.get("title"),  # Pass title here
                max_age=feed_max_age  # Explicit max_age passed
            )
            if "criteria" in feed_config:
                for criterion in feed_config["criteria"]:
                    try:
                        filter_type = FilterType(criterion["filter_type"])
                    except ValueError as e:
                        log_error_with_readkey(f"Invalid filter type: {criterion['filter_type']}. Error: {e}")
                        continue

                    filter_feed.add_filter(
                        filter_type=filter_type,
                        pattern=criterion["pattern"],
                        is_inclusion=criterion.get("is_inclusion", True),
                    )
            return filter_feed
        else:
            logger.warning(f"Unknown feed type: {feed_type}")
            return None

    def next_article(self) -> Optional[Article]:
        """Fetch the next article by sampling feeds until an article is retrieved or root feed weight is 0.

        Returns:
            The fetched article, or None if no matching articles are available.
        """
        if not self.root_feed:
            logger.warning("No root feed available to fetch articles.")
            return None

        while self.root_feed.weight > 0:
            try:
                article = self.root_feed.fetch()
                if article:
                    logger.info(f"Fetched article: {article.id} ({article.title})")
                    return article
                else:
                    logger.warning("No matching article fetched from the root feed.")
            except Exception as e:
                log_error_with_readkey(f"Error while fetching from the root feed: {e}")

        logger.info("All caught up")
        return None

