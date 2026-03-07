"""Integration test for symlink preservation during configuration updates."""
import os
import tempfile
import shutil
import unittest
import json
from datetime import datetime

from fof.config_manager import ConfigManager
from fof.feed_manager import FeedManager
from fof.feed_serializer import FeedSerializer
from fof.feed_loader import FeedLoader
from fof.models.article_manager import ArticleManager
from fof.models.union_feed.models import UnionFeed, WeightedFeed
from fof.models.syndication_feed.models import SyndicationFeed


class TestSymlinkIntegration(unittest.TestCase):
    """Test symlink preservation during real configuration updates."""

    def setUp(self):
        """Set up test environment with feeds and symlinks."""
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.test_dir, "config")
        self.tree_dir = os.path.join(self.config_dir, "tree")
        self.external_dir = os.path.join(self.test_dir, "external")

        # Create directory structure
        os.makedirs(self.tree_dir)
        os.makedirs(self.external_dir)

        # Create external curated feed
        self.create_external_curated_feed()

        # Create main tree with symlink
        self.create_main_tree_with_symlink()

        # Initialize FoF components
        self.config_manager = ConfigManager(self.config_dir)
        self.article_manager = ArticleManager(self.config_manager)
        self.feed_loader = FeedLoader(self.article_manager)
        self.feed_serializer = FeedSerializer(self.config_manager)

    def tearDown(self):
        """Clean up test directories."""
        shutil.rmtree(self.test_dir)

    def create_external_curated_feed(self):
        """Create an external curated feed to symlink to."""
        curated_dir = os.path.join(self.external_dir, "curated_news")
        os.makedirs(curated_dir)

        # Create a simple syndication feed
        feed_config = {
            "id": "tech_news",
            "title": "Tech News",
            "description": "Technology news feed",
            "url": "https://example.com/tech.rss",
            "last_updated": datetime.now().isoformat(),
            "max_age": "7d"
        }

        with open(os.path.join(curated_dir, "feed.fof"), "w") as f:
            json.dump(feed_config, f, indent=2)

    def create_main_tree_with_symlink(self):
        """Create main tree with regular feeds and a symlink."""
        # Create union feed config
        union_config = {
            "id": "root",
            "title": "Root Feed",
            "description": "Main aggregation feed",
            "last_updated": datetime.now().isoformat(),
            "max_age": "7d",
            "weights": {
                "personal": 1.0,
                "tech_news": 2.0
            }
        }

        with open(os.path.join(self.tree_dir, "union.fof"), "w") as f:
            json.dump(union_config, f, indent=2)

        # Create personal feed directory
        personal_dir = os.path.join(self.tree_dir, "personal")
        os.makedirs(personal_dir)

        personal_config = {
            "id": "personal",
            "title": "Personal Feed",
            "description": "My personal syndication feed",
            "url": "https://example.com/personal.rss",
            "last_updated": datetime.now().isoformat(),
            "max_age": "7d"
        }

        with open(os.path.join(personal_dir, "feed.fof"), "w") as f:
            json.dump(personal_config, f, indent=2)

        # Create symlink to external curated feed
        curated_symlink = os.path.join(self.tree_dir, "tech_news")
        curated_target = os.path.join(self.external_dir, "curated_news")
        os.symlink(curated_target, curated_symlink)

    def test_symlink_preservation_during_save(self):
        """Test that symlinks are preserved during configuration save."""
        # Load the configuration
        feed_manager = FeedManager(
            self.article_manager,
            self.config_manager
        )

        # Verify symlink exists before save
        curated_symlink = os.path.join(self.tree_dir, "tech_news")
        self.assertTrue(os.path.islink(curated_symlink))
        original_target = os.readlink(curated_symlink)

        # Modify a feed to trigger a save
        root_feed = feed_manager.root_feed
        self.assertIsInstance(root_feed, UnionFeed)

        # Find and modify the personal feed weight
        for weighted_feed in root_feed.feeds:
            if weighted_feed.feed.local_id == "personal":
                weighted_feed.weight = 3.0
                break

        # Save configuration
        feed_manager.save_config()



        # Verify symlink still exists and points to same target
        self.assertTrue(os.path.exists(curated_symlink))
        self.assertTrue(os.path.islink(curated_symlink))
        new_target = os.readlink(curated_symlink)
        self.assertEqual(original_target, new_target)

        # Verify the symlinked feed is still loadable
        feed_manager_after_save = FeedManager(
            self.article_manager,
            self.config_manager
        )

        root_feed_after = feed_manager_after_save.root_feed
        self.assertIsNotNone(root_feed_after)

        # Find the curated feed and verify it loaded correctly
        curated_feed = None
        for weighted_feed in root_feed_after.feeds:
            if weighted_feed.feed.local_id == "tech_news":
                curated_feed = weighted_feed.feed
                break

        self.assertIsNotNone(curated_feed)
        self.assertIsInstance(curated_feed, SyndicationFeed)
        self.assertEqual(curated_feed.title, "Tech News")

    def test_symlink_discovery_and_validation(self):
        """Test symlink discovery and validation functionality."""
        from fof.symlink_utils import discover_symlinks, validate_symlink_integrity

        # Discover symlinks
        symlinks = discover_symlinks(self.tree_dir)
        self.assertEqual(len(symlinks), 1)
        self.assertIn("tech_news", symlinks)

        # Validate symlink integrity
        is_valid = validate_symlink_integrity(self.tree_dir)
        self.assertTrue(is_valid)

    def test_nested_symlinks(self):
        """Test handling of symlinks in nested directories."""
        # Create nested directory structure
        nested_dir = os.path.join(self.tree_dir, "categories", "tech")
        os.makedirs(nested_dir)

        # Create another external target
        external_tech = os.path.join(self.external_dir, "tech_feeds")
        os.makedirs(external_tech)

        tech_config = {
            "id": "hacker_news",
            "title": "Hacker News",
            "description": "Tech news from HN",
            "url": "https://hnrss.org/frontpage",
            "last_updated": datetime.now().isoformat(),
            "max_age": "7d"
        }

        with open(os.path.join(external_tech, "feed.fof"), "w") as f:
            json.dump(tech_config, f, indent=2)

        # Create symlink in nested location
        nested_symlink = os.path.join(nested_dir, "hacker_news")
        os.symlink(external_tech, nested_symlink)

        # Update the union config to include nested structure
        categories_dir = os.path.join(self.tree_dir, "categories")
        categories_union_config = {
            "id": "categories",
            "title": "Categorized Feeds",
            "description": "Feeds organized by category",
            "last_updated": datetime.now().isoformat(),
            "max_age": "7d",
            "weights": {
                "tech": 1.0
            }
        }

        with open(os.path.join(categories_dir, "union.fof"), "w") as f:
            json.dump(categories_union_config, f, indent=2)

        tech_union_config = {
            "id": "tech",
            "title": "Technology",
            "description": "Technology-related feeds",
            "last_updated": datetime.now().isoformat(),
            "max_age": "7d",
            "weights": {
                "hacker_news": 1.0
            }
        }

        with open(os.path.join(nested_dir, "union.fof"), "w") as f:
            json.dump(tech_union_config, f, indent=2)

        # Update root union to include categories
        root_union_config = {
            "id": "root",
            "title": "Root Feed",
            "description": "Main aggregation feed",
            "last_updated": datetime.now().isoformat(),
            "max_age": "7d",
            "weights": {
                "personal": 1.0,
                "tech_news": 2.0,
                "categories": 1.5
            }
        }

        with open(os.path.join(self.tree_dir, "union.fof"), "w") as f:
            json.dump(root_union_config, f, indent=2)

        # Test that nested symlinks are preserved
        feed_manager = FeedManager(
            self.article_manager,
            self.config_manager
        )

        # Verify nested symlink exists
        self.assertTrue(os.path.islink(nested_symlink))
        original_target = os.readlink(nested_symlink)

        # Save configuration
        feed_manager.save_config()

        # Verify nested symlink is preserved
        self.assertTrue(os.path.exists(nested_symlink))
        self.assertTrue(os.path.islink(nested_symlink))
        new_target = os.readlink(nested_symlink)
        self.assertEqual(original_target, new_target)

        # Verify the nested feed hierarchy loads correctly
        from fof.symlink_utils import discover_symlinks
        symlinks = discover_symlinks(self.tree_dir)
        self.assertEqual(len(symlinks), 2)  # tech_news + nested hacker_news
        self.assertIn("tech_news", symlinks)
        self.assertIn("categories/tech/hacker_news", symlinks)


if __name__ == "__main__":
    unittest.main()
