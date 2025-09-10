"""
feed_flag.py

Handles logic related to the global --feed <feed_id> flag for Feed of Feeds (FoF).
Provides validation, error feedback, and session restriction utilities for feed selection.
"""

import logging

logger = logging.getLogger(__name__)

def validate_feed_id(feed_manager, feed_id):
    """
    Checks if feed_id exists in the feed_manager's config.
    Raises ValueError with a clear message if not found.
    Returns the feed object if found.
    """
    feed = feed_manager.get_feed_by_id(feed_id)
    if not feed:
        logger.error(
            f"Feed with ID '{feed_id}' not found in configuration. "
            "Failing fast. Please check your --feed argument and config files."
        )
        raise ValueError(
            f"Feed with ID '{feed_id}' not found. "
            "Troubleshooting: Verify the feed ID exists in your config tree. "
            "Use 'fof feeds list' to see available feeds."
        )
    return feed

def restrict_to_feed(feed_manager, feed_id):
    """
    Restricts the session to the selected feed and its descendants.
    Validates feed_id first, then disables all other feeds in the session.
    """
    validate_feed_id(feed_manager, feed_id)
    feed_manager._set_disabled_in_session_for_feeds(feed_id)
