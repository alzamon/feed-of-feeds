"""Core FoF feed management functionality."""
from .config_comparator import ConfigComparator
from .config_manager import ConfigManager
from .feed_flag import restrict_to_feed
from .feed_loader import FeedLoader
from .feed_serializer import FeedSerializer
from .models.article import Article
from .models.article_manager import ArticleManager
from .models.base_feed import BaseFeed
from .models.union_feed.models import UnionFeed
from datetime import datetime
from typing import Optional, List, Callable
import logging
import shutil


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
            restrict_to_feed(self, self.feed_id)

    def _load_config(self):
        """Load the configuration from the 'tree' directory and initialize feeds."""
        config_dir = self.config_manager.get_tree_dir
        try:
            feed = self.feed_loader.load_feed_from_directory(
                config_dir, feedpath=[], parent_max_age=None, is_root=True)
            if feed is None:
                logger.error(
                    f"No valid feed found in config directory {config_dir}. "
                    "Check that your configuration files exist and are valid JSON. "
                    "See ~/.config/fof/tree for details."
                )
                self.root_feed = None
            else:
                self.root_feed = feed
        except Exception as e:
            import traceback
            logger.error(
                f"Failed to load config from directory at {config_dir}.\n"
                f"Error type: {type(e).__name__}\n"
                f"Error message: {e}\n"
                f"Traceback:\n{traceback.format_exc()}\n"
                "Troubleshooting: Check file permissions, JSON syntax, and required fields in your config files."
            )
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
            # Match by qualified ID or local ID
            if (getattr(feed, "id", None) == feed_id or
                    getattr(feed, "local_id", None) == feed_id):
                found_feed = feed

        if not self.root_feed:
            logger.warning(f"Cannot search for feed '{feed_id}': root_feed is not loaded")
            return None

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
        if not self.root_feed:
            logger.warning("Cannot save config: root_feed is not loaded")
            return

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

        # Build expected global IDs as we traverse
        current_path = []

        for feed_id in feedpath:
            current_path.append(feed_id)
            expected_global_id = '/'.join(current_path)

            logger.debug(
                f"Looking for feed with global ID '{expected_global_id}' in current feed '{
                    current_feed.id}'")
            
            # Use polymorphism instead of isinstance checks
            sub_feed = current_feed.find_child_feed_by_id(expected_global_id)
            wf = None
            
            # Special handling for UnionFeed to get the WeightedFeed for weight updates
            if isinstance(current_feed, UnionFeed):
                wf = current_feed.find_weighted_feed_by_id(expected_global_id)
                
            if not sub_feed:
                logger.error(
                    f"Feed with global ID '{expected_global_id}' not found in the feedpath at feed '{
                        current_feed.id}'")
                raise ValueError(
                    f"Feed with global ID '{expected_global_id}' not found in the feedpath.")
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

        # Use polymorphism for feed traversal instead of duck typing
        transformed_context = base_feed.apply_context_transform(context)
        
        # Special handling for UnionFeed to deal with WeightedFeed weights
        if isinstance(base_feed, UnionFeed):
            for weighted_feed in base_feed.get_weighted_child_feeds():
                # Apply weight transformation for WeightedFeed
                new_context = transformed_context.copy()
                if "likelihood" in new_context:
                    new_context["likelihood"] *= (weighted_feed.weight /
                                                  WEIGHT_PERCENTAGE_BASE)
                else:
                    new_context["likelihood"] = (
                        weighted_feed.weight / WEIGHT_PERCENTAGE_BASE)
                self.perform_on_feeds(weighted_feed.feed, performer, new_context)
        else:
            # Standard polymorphic traversal for other feed types
            for child_feed in base_feed.get_child_feeds():
                self.perform_on_feeds(child_feed, performer, transformed_context)

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
            # Support both local and qualified ID lookup
            if (getattr(feed, 'id', None) == active_feed_id or
                    getattr(feed, 'local_id', None) == active_feed_id):
                selected_feed = feed
        self.perform_on_feeds(self.root_feed, find_feed)
        if not selected_feed:
            logger.warning(
                f"Feed with id '{active_feed_id}' not found for disabling in session.")
            return

        # Build set of allowed qualified IDs
        allowed_ids = set()

        # Ancestors: construct qualified IDs for each prefix of the selected feed's path
        selected_feedpath = getattr(selected_feed, 'feedpath', [])
        for i in range(1, len(selected_feedpath) + 1):
            ancestor_id = '/'.join(selected_feedpath[:i])
            allowed_ids.add(ancestor_id)

        # Include root feed if it exists
        if not selected_feedpath:
            # Selected feed is root
            allowed_ids.add(getattr(selected_feed, 'id', None))
        else:
            # Add root feed to allowed (root has empty feedpath)
            allowed_ids.add("root")

        # Descendants: recursively collect all feed ids under the selected feed
        def collect_descendants(feed: BaseFeed):
            feed_id = getattr(feed, 'id', None)
            if feed_id is not None:
                allowed_ids.add(feed_id)
            # Use polymorphism instead of duck typing
            for child_feed in feed.get_child_feeds():
                collect_descendants(child_feed)

        collect_descendants(selected_feed)

        # Now disable all feeds not in allowed_ids
        def disable_unless_allowed(feed: BaseFeed, ctx: dict):
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
