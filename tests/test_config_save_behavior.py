import pytest
import tempfile
import os
import json
import shutil
from datetime import datetime
from unittest.mock import patch

from fof.feed_manager import FeedManager
from fof.config_manager import ConfigManager
from fof.models.article_manager import ArticleManager
from fof.models.syndication_feed import SyndicationFeed


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