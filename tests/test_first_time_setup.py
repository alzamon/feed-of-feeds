"""Test first-time setup handling when tree directory doesn't exist."""
import pytest
import os
import tempfile
import shutil
from fof.config_manager import ConfigManager
from fof.feed_manager import FeedManager
from fof.models.article_manager import ArticleManager


class DummyArticleManager:
    """Dummy article manager for testing."""
    pass


def _create_test_temp_dir():
    """Create a temporary directory inside the project for testing.
    This works around Termux/Android where /tmp is not accessible.
    """
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_temp_base = os.path.join(project_root, "test_temp")
    
    # Create unique temp directory
    import uuid
    temp_name = f"test_{uuid.uuid4().hex[:8]}"
    temp_dir = os.path.join(test_temp_base, temp_name)
    os.makedirs(temp_dir, exist_ok=True)
    
    return temp_dir


def test_feed_manager_handles_missing_tree_directory():
    """Test that FeedManager handles missing tree directory gracefully on first-time setup."""
    # Create a temporary directory for config inside the project
    temp_dir = _create_test_temp_dir()
    try:
        config_path = os.path.join(temp_dir, "fof_config")
        os.makedirs(config_path, exist_ok=True)
        
        # Create ConfigManager and ArticleManager
        config_manager = ConfigManager(config_path=config_path)
        article_manager = DummyArticleManager()
        
        # This should not raise an exception even though tree directory doesn't exist
        feed_manager = FeedManager(
            article_manager=article_manager,
            config_manager=config_manager
        )
        
        # Should have no root feed on first-time setup
        assert feed_manager.root_feed is None
    finally:
        # Clean up
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def test_config_manager_persist_update_handles_missing_tree():
    """Test that persist_update handles missing tree directory gracefully."""
    # Create temporary directories inside the project
    temp_dir = _create_test_temp_dir()
    try:
        config_path = os.path.join(temp_dir, "fof_config") 
        os.makedirs(config_path, exist_ok=True)
        
        update_dir = os.path.join(config_path, "update")
        os.makedirs(update_dir)
        
        # Create a dummy file in update directory
        with open(os.path.join(update_dir, "test.json"), "w") as f:
            f.write('{"test": "data"}')
        
        config_manager = ConfigManager(config_path=config_path)
        
        # This should not fail even though tree directory doesn't exist initially
        config_manager.persist_update(update_dir)
        
        # Tree directory should now exist
        tree_dir = os.path.join(config_path, "tree")
        assert os.path.exists(tree_dir)
        assert os.path.exists(os.path.join(tree_dir, "test.json"))
    finally:
        # Clean up
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def test_feed_manager_next_article_with_no_root_feed():
    """Test that next_article returns None gracefully when no root feed is configured."""
    temp_dir = _create_test_temp_dir()
    try:
        config_path = os.path.join(temp_dir, "fof_config")
        os.makedirs(config_path, exist_ok=True)
        
        config_manager = ConfigManager(config_path=config_path)
        article_manager = DummyArticleManager()
        
        feed_manager = FeedManager(
            article_manager=article_manager,
            config_manager=config_manager
        )
        
        # Should return None gracefully when no feeds are configured
        article = feed_manager.next_article()
        assert article is None
    finally:
        # Clean up
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)