"""Core FoF feed management functionality."""
import random
import json
import os
from typing import Dict, Optional, List
from datetime import timedelta, datetime
import logging

from .models.article import Article
from .models.base_feed import BaseFeed
from .models.union_feed import UnionFeed
from .models.regular_feed import RegularFeed
from .models.filter_feed import FilterFeed, Filter
from .models.enums import FeedType, FilterType
from .error_logger import log_error_with_readkey
from .models.article_manager import ArticleManager

from .time_period import parse_time_period, timedelta_to_period_str


logger = logging.getLogger(__name__)

class FeedManager:
    """Main class for managing feeds and articles."""

    def __init__(self, config_path: str = "~/.config/fof"):
        """Initialize the FeedManager.

        Args:
            config_path (str): Path to the configuration directory. Defaults to "~/.config/fof/".
        """
        self.config_path = os.path.expanduser(config_path)
        self.article_manager = ArticleManager(db_path=self.config_path)
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

                # Now expect a single "defaultRootFeed" property for the root feed config
                root_feed_config = config_data.get("defaultRootFeed")
                if not root_feed_config:
                    raise ValueError("Configuration must include a 'defaultRootFeed' property.")

                # "max_age" for the root feed must be set in the union feed config
                if "max_age" not in root_feed_config:
                    raise ValueError("Root feed must have a max_age defined in the configuration under 'defaultRootFeed'.")

                root_max_age = parse_time_period(root_feed_config["max_age"])
                self.root_feed = self._create_feed(root_feed_config, parent_max_age=root_max_age, parent_feedpath=[])
        except Exception as e:
            log_error_with_readkey(f"Failed to load config file at {config_file_path}: {e}")
            self.root_feed = None

    def _create_feed(self, feed_config: Dict, parent_max_age: timedelta, parent_feedpath: List[str]) -> BaseFeed:
        """
        Create a feed object from the configuration.

        Args:
            feed_config (Dict): Feed configuration dictionary.
            parent_max_age (timedelta): The max_age value inherited from the parent feed.
            parent_feedpath (List[str]): The feedpath inherited from the parent feed.

        Returns:
            BaseFeed: The initialized feed object.
        """
        feed_type = FeedType(feed_config["feed_type"])
        # Parse max_age as period string (if present), else inherit from parent
        feed_max_age = parse_time_period(feed_config["max_age"]) if "max_age" in feed_config else parent_max_age

        feedpath = (parent_feedpath if parent_feedpath != ["root"] else []) + [feed_config["id"]]
        description = feed_config.get("description", "No description provided")
        last_updated = datetime.now()
        weight = feed_config.get("weight", 10.0)

        # For regular feeds
        if feed_type == FeedType.REGULAR:
            return RegularFeed(
                id=feed_config["id"],
                url=feed_config["url"],
                title=feed_config.get("title"),
                description=description,
                last_updated=last_updated,
                weight=weight,
                max_age=feed_max_age,
                article_manager=self.article_manager,
                feedpath=feedpath
            )
        # For union feeds
        elif feed_type == FeedType.UNION:
            # Recursively create child feeds with inherited max_age and feedpath
            member_feeds = [
                self._create_feed(member_feed, parent_max_age=feed_max_age, parent_feedpath=feedpath)
                for member_feed in feed_config.get("feeds", [])
            ]
            member_feeds = [feed for feed in member_feeds if feed is not None]

            return UnionFeed(
                id=feed_config["id"],
                feeds=member_feeds,
                title=feed_config.get("title"),
                description=description,
                last_updated=last_updated,
                weight=weight,
                max_age=feed_max_age,
                feedpath=feedpath
            )
        # For filter feeds
        elif feed_type == FeedType.FILTER:
            # Create the source feed inline
            source_feed_config = feed_config["feed"]
            source_feed = self._create_feed(source_feed_config, parent_max_age=feed_max_age, parent_feedpath=feedpath)
            if not source_feed:
                logger.warning(
                    f"Failed to create source feed for filter feed: {feed_config['id']}"
                )
                return None

            # Create FilterFeed and add filters
            filter_feed = FilterFeed(
                source_feed=source_feed,
                id=feed_config["id"],
                title=feed_config.get("title"),
                description=description,
                last_updated=last_updated,
                weight=weight,
                max_age=feed_max_age,
                filters=[],
                feedpath=feedpath
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

        while self.root_feed.effective_weight() > 0:
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

        for feed_id in feedpath:
            logger.debug(f"Looking for feed ID '{feed_id}' in current feed '{current_feed.id}'")

            if isinstance(current_feed, UnionFeed):
                sub_feed = next((feed for feed in current_feed.feeds if feed.id == feed_id), None)
            elif isinstance(current_feed, FilterFeed):
                sub_feed = current_feed.source_feed if current_feed.source_feed.id == feed_id else None
            else:
                sub_feed = None

            if not sub_feed:
                logger.error(f"Feed with ID '{feed_id}' not found in the feedpath at feed '{current_feed.id}'")
                raise ValueError(f"Feed with ID '{feed_id}' not found in the feedpath.")

            current_feed = sub_feed
            # Update the weight of each feed in the path except root
            current_feed.weight += increment
            logger.info(f"Updated weight of feed '{current_feed.id}' to {current_feed.weight}.")

    def save_config(self):
        """
        Save the current feed configuration to the configuration file.

        Normalizes weights so every union feed's subfeeds sum to 100, and filter/regular feeds have weight 100.

        Raises:
            IOError: If unable to write to the configuration file.
        """
        if not self.root_feed:
            raise ValueError("Root feed is not initialized.")

        config_file_path = os.path.join(self.config_path, "config.json")

        # Normalize weights in-place before serialization
        self._normalize_feed_weights(self.root_feed)

        # Serialize the root feed under the "defaultRootFeed" property
        config_data = {
            "defaultRootFeed": self._serialize_feed(self.root_feed)
        }

        try:
            with open(config_file_path, "w") as config_file:
                json.dump(config_data, config_file, indent=4)
            logger.info(f"Configuration saved to {config_file_path}.")
        except IOError as e:
            log_error_with_readkey(f"Failed to save configuration to {config_file_path}: {e}")
            raise

     
     
    def _normalize_feed_weights(self, feed: BaseFeed):
        """
        Only normalize:
        - The direct subfeeds of each UnionFeed so their weights sum to 100 (preserving ratios).
        - The source_feed of FilterFeed to 100.
        Never change weights of any other feeds.
        """
        from .models.union_feed import UnionFeed
        from .models.filter_feed import FilterFeed

        if isinstance(feed, UnionFeed):
            subfeeds = feed.feeds
            total_weight = sum(f.weight for f in subfeeds)
            if total_weight > 0:
                for subfeed in subfeeds:
                    subfeed.weight = 100.0 * (subfeed.weight / total_weight)
            else:
                n = len(subfeeds)
                for subfeed in subfeeds:
                    subfeed.weight = 100.0 / n if n > 0 else 0.0
            # Recurse into each subfeed (do NOT normalize their weights, just apply normalization at their union/filter layer if any)
            for subfeed in subfeeds:
                self._normalize_feed_weights(subfeed)

        elif isinstance(feed, FilterFeed):
            # Only normalize the direct source_feed to weight 100
            if hasattr(feed, "source_feed") and feed.source_feed is not None:
                feed.source_feed.weight = 100.0
                self._normalize_feed_weights(feed.source_feed)

    def _serialize_feed(self, feed: BaseFeed) -> Dict:
        """
        Recursively serialize a feed object into a dictionary.

        Args:
            feed (BaseFeed): The feed object to serialize.

        Returns:
            Dict: The serialized feed configuration.
        """
        feed_data = {
            "id": feed.id,
            "feed_type": feed.feed_type.value,
            "weight": feed.weight,
            "max_age": timedelta_to_period_str(feed.max_age),
            "description": feed.description,
        }

        if isinstance(feed, RegularFeed):
            feed_data["url"] = feed.url
            feed_data["title"] = feed.title
        elif isinstance(feed, UnionFeed):
            feed_data["feeds"] = [self._serialize_feed(sub_feed) for sub_feed in feed.feeds]
            feed_data["title"] = feed.title
        elif isinstance(feed, FilterFeed):
            feed_data["feed"] = self._serialize_feed(feed.source_feed)
            feed_data["criteria"] = [
                {
                    "filter_type": filter_obj.filter_type.value,
                    "pattern": filter_obj.pattern,
                    "is_inclusion": filter_obj.is_inclusion,
                }
                for filter_obj in feed.filters
            ]
            feed_data["title"] = feed.title

        return feed_data
