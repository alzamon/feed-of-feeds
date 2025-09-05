"""Tests for FeedSerializer functionality."""
import tempfile
from datetime import datetime, timedelta

from fof.config_manager import ConfigManager
from fof.feed_serializer import FeedSerializer
from fof.models.syndication_feed import SyndicationFeed


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

        # Check that all expected fields are present (but NOT id)
        assert "id" not in result  # ID should no longer be in serialized output
        assert result["title"] == "Test Feed"
        assert result["description"] == "A test feed"
        assert result["url"] == "http://example.com/feed.xml"
        assert result["max_age"] == "7d"
        assert result["purge_age"] == "30d"
        assert "last_updated" in result
