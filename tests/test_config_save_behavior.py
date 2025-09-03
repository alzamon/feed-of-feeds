import tempfile
import os
import json
from datetime import datetime, timedelta

from fof.feed_manager import FeedManager
from fof.config_manager import ConfigManager


class DummyArticleManager:
    """Dummy article manager for testing."""

    def fetch_article(self, **kwargs):
        return None


def test_config_not_rewritten_when_no_changes():
    """Test that config is not rewritten when no actual changes are made."""

    # Create a temporary config directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        tree_dir = os.path.join(temp_dir, "tree")
        os.makedirs(tree_dir)

        # Create a simple syndication feed config
        now = datetime.now()
        feed_config = {
            "id": "test_feed",
            "title": "Test Feed",
            "description": "A test feed",
            "last_updated": now.isoformat(),
            "url": "http://example.com/feed.xml",
            "max_age": "7d"
        }

        feed_json_path = os.path.join(tree_dir, "feed.json")
        with open(feed_json_path, "w") as f:
            json.dump(feed_config, f, indent=2)

        # Create config and feed managers
        config_manager = ConfigManager(temp_dir)
        article_manager = DummyArticleManager()
        feed_manager = FeedManager(article_manager, config_manager)

        # Get the original modification time of the config file
        original_mtime = os.path.getmtime(feed_json_path)

        # Wait a bit to ensure any file change would have a different timestamp
        import time
        time.sleep(0.01)

        # Save config without making any changes
        feed_manager.save_config()

        # Check if the config file was rewritten by comparing timestamps
        new_mtime = os.path.getmtime(feed_json_path)

        # The file should not have been rewritten since no changes were made
        # But currently this will fail because config is always rewritten
        assert original_mtime == new_mtime, "Config was rewritten even though no changes were made"


def test_config_rewritten_when_changes_made():
    """Test that config IS rewritten when actual changes are made."""

    # Create a temporary config directory structure with a union feed
    with tempfile.TemporaryDirectory() as temp_dir:
        tree_dir = os.path.join(temp_dir, "tree")
        os.makedirs(tree_dir)

        # Create union feed structure
        now = datetime.now()
        union_config = {
            "id": "test_union",
            "title": "Test Union",
            "description": "A test union",
            "last_updated": now.isoformat(),
            "max_age": "7d",
            "weights": {"feed1": 60, "feed2": 40}
        }

        # Create the union.json file
        union_json_path = os.path.join(tree_dir, "union.json")
        with open(union_json_path, "w") as f:
            json.dump(union_config, f, indent=2)

        # Create subdirectory and feed configs
        feed1_dir = os.path.join(tree_dir, "feed1")
        os.makedirs(feed1_dir)
        feed1_config = {
            "id": "feed1",
            "title": "Feed 1",
            "description": "First feed",
            "url": "http://example.com/feed1.xml",
            "max_age": "7d"
        }
        with open(os.path.join(feed1_dir, "feed.json"), "w") as f:
            json.dump(feed1_config, f, indent=2)

        feed2_dir = os.path.join(tree_dir, "feed2")
        os.makedirs(feed2_dir)
        feed2_config = {
            "id": "feed2",
            "title": "Feed 2",
            "description": "Second feed",
            "url": "http://example.com/feed2.xml",
            "max_age": "7d"
        }
        with open(os.path.join(feed2_dir, "feed.json"), "w") as f:
            json.dump(feed2_config, f, indent=2)

        # Create config and feed managers
        config_manager = ConfigManager(temp_dir)
        article_manager = DummyArticleManager()
        feed_manager = FeedManager(article_manager, config_manager)

        # Get the original modification time
        original_mtime = os.path.getmtime(union_json_path)

        # Wait a bit to ensure file change would have different timestamp
        import time
        time.sleep(0.01)

        # Make an actual change - update weights
        feed_manager.update_weights(["feed1"], 10)

        # Save config after making changes
        feed_manager.save_config()

        # Check if the config file was rewritten
        new_mtime = os.path.getmtime(union_json_path)

        # The file should have been rewritten since changes were made
        assert new_mtime > original_mtime, "Config was not rewritten despite making changes"


def test_multiple_saves_without_changes():
    """Test that multiple saves without changes never rewrite config."""

    # Create a temporary config directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        tree_dir = os.path.join(temp_dir, "tree")
        os.makedirs(tree_dir)

        # Create a simple syndication feed config
        now = datetime.now()
        feed_config = {
            "id": "test_feed",
            "title": "Test Feed",
            "description": "A test feed",
            "last_updated": now.isoformat(),
            "url": "http://example.com/feed.xml",
            "max_age": "7d"
        }

        feed_json_path = os.path.join(tree_dir, "feed.json")
        with open(feed_json_path, "w") as f:
            json.dump(feed_config, f, indent=2)

        # Create config and feed managers
        config_manager = ConfigManager(temp_dir)
        article_manager = DummyArticleManager()
        feed_manager = FeedManager(article_manager, config_manager)

        # Get the original modification time
        original_mtime = os.path.getmtime(feed_json_path)

        # Wait a bit to ensure any file change would have different timestamp
        import time
        time.sleep(0.01)

        # Save config multiple times without making changes
        for i in range(3):
            feed_manager.save_config()
            current_mtime = os.path.getmtime(feed_json_path)
            assert current_mtime == original_mtime, f"Config was rewritten on save #{
                i + 1} despite no changes"
            time.sleep(0.01)  # Small delay between saves


def test_config_rewritten_after_weight_change():
    """Test that config is rewritten when weights are changed."""

    # Create a temporary config directory structure with a union feed
    with tempfile.TemporaryDirectory() as temp_dir:
        tree_dir = os.path.join(temp_dir, "tree")
        os.makedirs(tree_dir)

        # Create union feed structure
        now = datetime.now()
        union_config = {
            "id": "test_union",
            "title": "Test Union",
            "description": "A test union",
            "last_updated": now.isoformat(),
            "max_age": "7d",
            "weights": {"Feed 1": 60, "Feed 2": 40}
        }

        # Create the union.json file
        union_json_path = os.path.join(tree_dir, "union.json")
        with open(union_json_path, "w") as f:
            json.dump(union_config, f, indent=2)

        # Create subdirectory and feed configs - use same names as weights
        feed1_dir = os.path.join(tree_dir, "Feed 1")
        os.makedirs(feed1_dir)
        feed1_config = {
            "id": "feed1",
            "title": "Feed 1",
            "description": "First feed",
            "last_updated": now.isoformat(),
            "url": "http://example.com/feed1.xml",
            "max_age": "7d"
        }
        with open(os.path.join(feed1_dir, "feed.json"), "w") as f:
            json.dump(feed1_config, f, indent=2)

        feed2_dir = os.path.join(tree_dir, "Feed 2")
        os.makedirs(feed2_dir)
        feed2_config = {
            "id": "feed2",
            "title": "Feed 2",
            "description": "Second feed",
            "last_updated": now.isoformat(),
            "url": "http://example.com/feed2.xml",
            "max_age": "7d"
        }
        with open(os.path.join(feed2_dir, "feed.json"), "w") as f:
            json.dump(feed2_config, f, indent=2)

        # Create config and feed managers
        config_manager = ConfigManager(temp_dir)
        article_manager = DummyArticleManager()
        feed_manager = FeedManager(article_manager, config_manager)

        # Save config without changes first - should not rewrite
        original_mtime = os.path.getmtime(union_json_path)

        import time
        time.sleep(0.01)

        feed_manager.save_config()
        no_change_mtime = os.path.getmtime(union_json_path)
        assert no_change_mtime == original_mtime, "Config was rewritten despite no changes"

        time.sleep(0.01)

        # Make an actual change - update weights
        feed_manager.update_weights(["feed1"], 10)

        # Save config after making changes - should rewrite
        feed_manager.save_config()
        changed_mtime = os.path.getmtime(union_json_path)
        assert changed_mtime > no_change_mtime, "Config was not rewritten despite making weight changes"


def test_only_changed_feeds_get_timestamp_updates():
    """Test that only feeds with actual changes get their timestamps updated."""

    with tempfile.TemporaryDirectory() as temp_dir:
        tree_dir = os.path.join(temp_dir, "tree")
        os.makedirs(tree_dir)

        # Create root union
        base_time = datetime.now() - timedelta(hours=1)
        root_config = {
            "id": "root",
            "title": None,
            "description": "root union",
            "last_updated": base_time.isoformat(),
            "max_age": "7d",
            "weights": {"Feed 1": 60, "Feed 2": 40}
        }

        root_json_path = os.path.join(tree_dir, "union.json")
        with open(root_json_path, "w") as f:
            json.dump(root_config, f, indent=2)

        # Create Feed 1
        feed1_dir = os.path.join(tree_dir, "Feed 1")
        os.makedirs(feed1_dir)
        feed1_config = {
            "id": "feed1",
            "title": "Feed 1",
            "description": "First feed",
            "last_updated": base_time.isoformat(),
            "url": "http://example.com/feed1.xml",
            "max_age": "7d"
        }
        feed1_json_path = os.path.join(feed1_dir, "feed.json")
        with open(feed1_json_path, "w") as f:
            json.dump(feed1_config, f, indent=2)

        # Create Feed 2
        feed2_dir = os.path.join(tree_dir, "Feed 2")
        os.makedirs(feed2_dir)
        feed2_config = {
            "id": "feed2",
            "title": "Feed 2",
            "description": "Second feed",
            "last_updated": base_time.isoformat(),
            "url": "http://example.com/feed2.xml",
            "max_age": "7d"
        }
        feed2_json_path = os.path.join(feed2_dir, "feed.json")
        with open(feed2_json_path, "w") as f:
            json.dump(feed2_config, f, indent=2)

        # Create feed manager
        config_manager = ConfigManager(temp_dir)
        article_manager = DummyArticleManager()
        feed_manager = FeedManager(article_manager, config_manager)

        # Update weights - this should trigger changes to root feed only
        feed_manager.update_weights(["feed1"], 10)

        # Save config
        import time
        time.sleep(0.01)
        feed_manager.save_config()

        # Read updated configs
        with open(root_json_path, "r") as f:
            updated_root = json.load(f)
        with open(feed1_json_path, "r") as f:
            updated_feed1 = json.load(f)
        with open(feed2_json_path, "r") as f:
            updated_feed2 = json.load(f)

        # Parse timestamps
        root_timestamp = datetime.fromisoformat(updated_root["last_updated"])
        feed1_timestamp = datetime.fromisoformat(updated_feed1["last_updated"])
        feed2_timestamp = datetime.fromisoformat(updated_feed2["last_updated"])

        # Root should be updated (has weight changes)
        assert root_timestamp > base_time, "Root feed timestamp should be updated when weights change"

        # Feed1 and Feed2 should NOT be updated (they didn't change themselves)
        assert feed1_timestamp == base_time, "Feed1 timestamp should remain unchanged when feed itself is not modified"
        assert feed2_timestamp == base_time, "Feed2 timestamp should remain unchanged when feed itself is not modified"

        # Check that weight was actually updated
        assert updated_root["weights"]["Feed 1"] == 70, "Feed 1 weight should have increased by 10"


def test_config_manager_persist_update_atomic():
    """Test that persist_update works atomically with proper error handling."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = ConfigManager(temp_dir)

        # Create tree directory
        tree_dir = os.path.join(temp_dir, "tree")
        os.makedirs(tree_dir)

        # Create a test file in tree
        test_file = os.path.join(tree_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("original content")

        # Create update directory
        update_dir = os.path.join(temp_dir, "update")
        os.makedirs(update_dir)
        update_file = os.path.join(update_dir, "test.txt")
        with open(update_file, "w") as f:
            f.write("updated content")

        # Persist update should work
        config_manager.persist_update(update_dir)

        # Check that tree directory now has the updated content
        with open(test_file, "r") as f:
            assert f.read() == "updated content"

        # Update directory should be gone
        assert not os.path.exists(update_dir)


def test_config_manager_persist_update_empty_directory():
    """Test that persist_update skips empty update directories."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = ConfigManager(temp_dir)

        # Create tree directory
        tree_dir = os.path.join(temp_dir, "tree")
        os.makedirs(tree_dir)
        test_file = os.path.join(tree_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("original content")

        # Create empty update directory
        update_dir = os.path.join(temp_dir, "update")
        os.makedirs(update_dir)

        # Should skip persist
        config_manager.persist_update(update_dir)

        # Original content should be unchanged
        with open(test_file, "r") as f:
            assert f.read() == "original content"
