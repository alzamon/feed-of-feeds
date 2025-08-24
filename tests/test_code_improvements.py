"""Tests for code improvement changes."""
import pytest
import tempfile
import os
import re
from datetime import datetime, timedelta

from fof.config_manager import ConfigManager
from fof.models.filter_feed import Filter
from fof.models.enums import FilterType
from fof.feed_serializer import FeedSerializer
from fof.models.syndication_feed import SyndicationFeed
from fof.models.article_manager import ArticleManager


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


def test_filter_invalid_regex_handling():
    """Test that Filter handles invalid regex gracefully."""
    # Valid regex should work
    valid_filter = Filter(FilterType.TITLE_REGEX, "test.*", True)
    assert valid_filter.compiled_pattern is not None
    
    # Invalid regex should not crash but log error and set pattern to None
    invalid_filter = Filter(FilterType.TITLE_REGEX, "[invalid", True)
    assert invalid_filter.compiled_pattern is None


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


def test_feed_serializer_reduced_repetition():
    """Test that the FeedSerializer refactoring works correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = ConfigManager(temp_dir)
        serializer = FeedSerializer(config_manager)
        
        # Create a mock ArticleManager
        class MockArticleManager:
            pass
        
        # Create a syndication feed
        feed = SyndicationFeed(
            id="test_feed",
            title="Test Feed",
            description="A test feed",
            last_updated=datetime.now(),
            url="http://example.com/feed.xml",
            max_age=timedelta(days=7),
            article_manager=MockArticleManager(),
            feedpath=["root"],
            purge_age=timedelta(days=30)
        )
        
        result = serializer.serialize_feed(feed)
        
        # Check that all expected fields are present
        assert result["id"] == "test_feed"
        assert result["title"] == "Test Feed"
        assert result["description"] == "A test feed"
        assert result["url"] == "http://example.com/feed.xml"
        assert result["max_age"] == "7d"
        assert result["purge_age"] == "30d"
        assert "last_updated" in result