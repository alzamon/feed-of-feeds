"""Core FoF feed management functionality."""
import shutil
from typing import Optional, List, Callable
from datetime import datetime
import logging

from .models.article import Article
from .models.base_feed import BaseFeed
from .models.union_feed import UnionFeed
from .models.filter_feed import FilterFeed
from .models.article_manager import ArticleManager
from .config_manager import ConfigManager
from .feed_serializer import FeedSerializer
from .config_comparator import ConfigComparator
from .feed_loader import FeedLoader


# Constants for weight calculations
WEIGHT_PERCENTAGE_BASE = 100.0

logger = logging.getLogger(__name__)


class FeedManager:
    """Main class for managing feeds """

    def __init__(
            self,
            article_manager: ArticleManager,
            config_manager: ConfigManager,
            feed_id: Optional[str] = None):
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

        # Initialize helper classes
        self.feed_serializer = FeedSerializer(self.config_manager)
        self.config_comparator = ConfigComparator(self.feed_serializer)
        self.feed_loader = FeedLoader(self.article_manager)

        self._load_config()
        if self.feed_id:
            self._set_disabled_in_session_for_feeds(self.feed_id)

    def _load_config(self):
        """Load the configuration from the 'tree' directory and initialize feeds."""
        config_dir = self.config_manager.get_tree_dir
        try:
            feed = self.feed_loader.load_feed_from_directory(
                config_dir, feedpath=[], parent_max_age=None, is_root=True)
            if feed is None:
                logger.error(
                    f"No valid feed found in config directory {config_dir}. Skipping load.")
                self.root_feed = None
            else:
                self.root_feed = feed
        except Exception as e:
            logger.error(
                f"Failed to load config from directory at {config_dir}: {e}")
            self.root_feed = None

    def get_feed_by_id(self, feed_id: str):
        """
        Recursively search for a feed with the given id in the entire feed tree.
        Supports both local IDs (e.g., 'cicd') and qualified IDs (e.g., 'work/da/cicd').
        Returns the feed object if found, else None.
        """
        found_feed = None

        def finder(feed, ctx):
            nonlocal found_feed
            # Skip WeightedFeed wrappers - they don't have id or qualified_id
            if hasattr(feed, "weight") and hasattr(feed, "feed"):
                return
            # Match by local ID or qualified ID
            if (getattr(feed, "id", None) == feed_id or 
                getattr(feed, "qualified_id", None) == feed_id):
                found_feed = feed

        if getattr(self, "root_feed", None):
            self.perform_on_feeds(self.root_feed, finder)
        return found_feed

    def save_config(self):
        """
        Atomically save the current root_feed to the new directory-based format.
        Write to an 'update' directory first, then move to 'tree' on success via config_manager.
        All chdir and delete logic is handled by config_manager.persist_update.
        Assumes update dir does not exist before serialization.
        Only saves if there are actual changes to avoid unnecessary config rewrites.
        Updates last_updated timestamp for feeds that have changes.
        """
        update_dir = self.config_manager.get_update_dir
        tree_dir = self.config_manager.get_tree_dir

        # Serialize to update directory
        self.feed_serializer.serialize_to_directory(self.root_feed, update_dir)

        # Check if the new configuration is different from the existing one
        if self.config_comparator.config_directories_equal(
                tree_dir, update_dir):
            # No changes detected, clean up update directory and skip persist
            shutil.rmtree(update_dir)
            logger.info("No configuration changes detected, skipping save.")
            return

        # Changes detected, identify which feeds have changed and update their
        # timestamps
        changed_feeds = self.config_comparator.identify_changed_feeds(
            self.root_feed, tree_dir, update_dir)
        current_time = datetime.now()

        # Update timestamps for changed feeds
        for feed in changed_feeds:
            feed.last_updated = current_time
            logger.debug(f"Updated timestamp for changed feed: {feed.id}")

        # Re-serialize with updated timestamps
        shutil.rmtree(update_dir)
        self.feed_serializer.serialize_to_directory(self.root_feed, update_dir)

        # Proceed with persist
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
        logger.debug(
            f"Starting feed traversal. Root feed ID: {
                current_feed.id}")
        parent_weighted_feed = None
        for feed_id in feedpath:
            logger.debug(
                f"Looking for feed ID '{feed_id}' in current feed '{
                    current_feed.id}'")
            wf = None
            if isinstance(current_feed, UnionFeed):
                wf = next(
                    (wf for wf in current_feed.feeds if wf.feed.id == feed_id), None)
                sub_feed = wf.feed if wf else None
            elif isinstance(current_feed, FilterFeed):
                sub_feed = current_feed.source_feed if current_feed.source_feed.id == feed_id else None
            else:
                sub_feed = None
            if not sub_feed:
                logger.error(
                    f"Feed with ID '{feed_id}' not found in the feedpath at feed '{
                        current_feed.id}'")
                raise ValueError(
                    f"Feed with ID '{feed_id}' not found in the feedpath.")
            if wf is not None:
                wf.weight += increment
                logger.info(
                    f"Updated weight of feed '{
                        sub_feed.id}' to {
                        wf.weight}.")
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

        # Navigate the feed hierarchy using duck typing to avoid tight coupling
        # This approach allows for extensibility but could be improved with
        # polymorphism

        # WeightedFeed: has .feed (compose likelihood if present)
        if hasattr(base_feed, "weight") and hasattr(base_feed, "feed"):
            new_context = context.copy()
            if "likelihood" in new_context:
                new_context["likelihood"] *= (base_feed.weight /
                                              WEIGHT_PERCENTAGE_BASE)
            else:
                new_context["likelihood"] = (
                    base_feed.weight / WEIGHT_PERCENTAGE_BASE)
            self.perform_on_feeds(base_feed.feed, performer, new_context)
        # UnionFeed: has .feeds (list of WeightedFeed)
        elif hasattr(base_feed, "feeds"):
            for subfeed in getattr(base_feed, "feeds", []):
                self.perform_on_feeds(subfeed, performer, context.copy())
        # FilterFeed: has .source_feed
        elif hasattr(base_feed, "source_feed"):
            self.perform_on_feeds(
                base_feed.source_feed,
                performer,
                context.copy())
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
            # Skip WeightedFeed wrappers
            if hasattr(feed, "weight") and hasattr(feed, "feed"):
                return
            # Support both local and qualified ID lookup
            if (getattr(feed, 'id', None) == active_feed_id or
                getattr(feed, 'qualified_id', None) == active_feed_id):
                selected_feed = feed
        self.perform_on_feeds(self.root_feed, find_feed)
        if not selected_feed:
            logger.warning(
                f"Feed with id '{active_feed_id}' not found for disabling in session.")
            return

        # Ancestors: all ids in the feedpath of the selected feed
        allowed_ids = set(getattr(selected_feed, 'feedpath', []))
        # Include the selected feed itself
        allowed_ids.add(getattr(selected_feed, 'id', None))

        # Descendants: recursively collect all feed ids under the selected feed
        # (including itself)
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
            # Skip WeightedFeed wrappers
            if hasattr(feed, "weight") and hasattr(feed, "feed"):
                return
            feed_id = getattr(feed, 'id', None)
            feed.disabled_in_session = (feed_id not in allowed_ids)

        self.perform_on_feeds(self.root_feed, disable_unless_allowed)

    def purge_old_articles(self) -> int:
        """
        Purge old articles from all feeds based on their purge_age settings.
        Returns the total number of articles purged.
        """
        total_purged = 0

        def purge_feed_articles(feed: BaseFeed, ctx: dict):
            nonlocal total_purged
            # Check if feed has purge_age set or can compute it from max_age
            purge_age = getattr(feed, 'purge_age', None)
            max_age = getattr(feed, 'max_age', None)
            if purge_age or max_age:
                purged = self.article_manager.purge_old_articles(feed)
                total_purged += purged
                if purged > 0:
                    logger.info(
                        f"Purged {purged} old articles from feed '{
                            feed.id}'")

        if self.root_feed:
            self.perform_on_feeds(self.root_feed, purge_feed_articles)
            logger.info(f"Total articles purged: {total_purged}")

        return total_purged
