"""Configuration comparison and change detection functionality."""
import json
import os
import filecmp
import logging
from typing import List

from .models.base_feed import BaseFeed
from .models.enums import FeedType

logger = logging.getLogger(__name__)


class ConfigComparator:
    """Handles comparison of configurations and detection of changes."""

    def __init__(self, feed_serializer):
        """Initialize with feed serializer for getting folder names."""
        self.feed_serializer = feed_serializer

    def config_directories_equal(self, dir1: str, dir2: str) -> bool:
        """
        Compare two directory structures to see if they contain identical
        files. Returns True if the directories have the same structure and
        file contents. Handles JSON files with special comparison to account
        for equivalent values (e.g., 60 vs 60.0).
        """
        def json_files_equal(file1_path: str, file2_path: str) -> bool:
            """Compare two JSON files, treating equivalent values as equal."""
            try:
                with open(file1_path, 'r') as f1, open(file2_path, 'r') as f2:
                    data1 = json.load(f1)
                    data2 = json.load(f2)
                    return data1 == data2
            except (json.JSONDecodeError, OSError):
                # Fall back to binary comparison if JSON parsing fails
                return filecmp.cmp(file1_path, file2_path, shallow=False)

        def compare_dirs(dcmp):
            """Recursively compare directory structures."""
            # Check if there are files only in one directory or the other
            if dcmp.left_only or dcmp.right_only:
                return False

            # Check files with different contents
            for file_name in dcmp.diff_files:
                file1_path = os.path.join(dcmp.left, file_name)
                file2_path = os.path.join(dcmp.right, file_name)

                # Special handling for JSON files
                if file_name.endswith('.json'):
                    if not json_files_equal(file1_path, file2_path):
                        return False
                else:
                    # For non-JSON files, they are already identified as
                    # different
                    return False

            # Recursively check subdirectories
            for sub_dcmp in dcmp.subdirs.values():
                if not compare_dirs(sub_dcmp):
                    return False

            return True
        try:
            # Use filecmp to compare directory structures
            dcmp = filecmp.dircmp(dir1, dir2)
            return compare_dirs(dcmp)
        except (OSError, FileNotFoundError):
            # If either directory doesn't exist or there's an error,
            # consider them different
            return False

    def identify_changed_feeds(self, root_feed: BaseFeed, old_dir: str,
                               new_dir: str) -> List[BaseFeed]:
        """
        Identify which feeds have actually changed by comparing their
        serialized configurations. Returns a list of BaseFeed objects that
        have changes.
        """
        changed_feeds = []

        def collect_feeds_with_paths(feed: BaseFeed,
                                     current_path: str = "") -> List[tuple]:
            """Recursively collect all feeds with their actual file paths."""
            feeds_with_paths = []

            if feed.feed_type == FeedType.UNION:
                config_path = os.path.join(current_path, "union.json")
                feeds_with_paths.append((feed, config_path))

                for wf in feed.feeds:
                    folder_name = (
                        self.feed_serializer.get_feed_folder_or_filename(
                            wf.feed
                        )
                    )
                    child_path = os.path.join(current_path, folder_name)
                    feeds_with_paths.extend(
                        collect_feeds_with_paths(wf.feed, child_path)
                    )

            elif feed.feed_type == FeedType.FILTER:
                config_path = os.path.join(current_path, "filter.json")
                feeds_with_paths.append((feed, config_path))

                if feed.source_feed:
                    source_path = os.path.join(current_path, "source")
                    feeds_with_paths.extend(
                        collect_feeds_with_paths(feed.source_feed, source_path)
                    )

            elif feed.feed_type == FeedType.SYNDICATION:
                config_path = os.path.join(current_path, "feed.json")
                feeds_with_paths.append((feed, config_path))

            return feeds_with_paths

        def configs_equal(old_path: str, new_path: str) -> bool:
            """Compare two feed configuration files."""
            try:
                if (not os.path.exists(old_path)
                        or not os.path.exists(new_path)):
                    return False

                with open(old_path, 'r') as f1, open(new_path, 'r') as f2:
                    old_config = json.load(f1)
                    new_config = json.load(f2)

                    # Remove last_updated from comparison since we're
                    # checking for other changes
                    old_config_copy = old_config.copy()
                    new_config_copy = new_config.copy()
                    old_config_copy.pop('last_updated', None)
                    new_config_copy.pop('last_updated', None)

                    return old_config_copy == new_config_copy
            except (json.JSONDecodeError, OSError):
                return False

        # Get all feeds with their actual paths
        feeds_with_paths = collect_feeds_with_paths(root_feed)

        # Check each feed for changes
        for feed, relative_path in feeds_with_paths:
            try:
                old_config_path = os.path.join(old_dir, relative_path)
                new_config_path = os.path.join(new_dir, relative_path)

                if not configs_equal(old_config_path, new_config_path):
                    changed_feeds.append(feed)
                    logger.debug(f"Detected changes in feed: {feed.id}")
            except Exception as e:
                logger.debug(f"Error comparing feed {feed.id}: {e}")
                # If we can't compare, assume it changed to be safe
                changed_feeds.append(feed)

        return changed_feeds
