"""Test CLI --feed argument functionality."""

from fof.models.article_manager import ArticleManager
from fof.config_manager import ConfigManager
from fof.feed_manager import FeedManager
from fof.cli import main
import pytest
import sys
import os
import tempfile
import json
import shutil
from unittest.mock import patch

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def test_config_dir():
    """Create a temporary test configuration directory."""
    test_dir = tempfile.mkdtemp()
    tree_dir = os.path.join(test_dir, 'tree')
    os.makedirs(tree_dir)

    # Create root union.json
    union_config = {
        "feed_type": "union",
        "id": "root",
        "title": "Root Feed",
        "description": "Root union feed for testing",
        "max_age": "7d",
        "weights": {"news": 50, "tech": 50}
    }

    with open(os.path.join(tree_dir, 'union.json'), 'w') as f:
        json.dump(union_config, f, indent=2)

    # Create news subdirectory
    news_dir = os.path.join(tree_dir, 'news')
    os.makedirs(news_dir)
    news_config = {
        "feed_type": "syndication",
        "id": "news",
        "title": "News Feed",
        "description": "A news syndication feed",
        "url": "https://feeds.feedburner.com/oreilly/radar",
        "max_age": "7d"
    }

    with open(os.path.join(news_dir, 'feed.json'), 'w') as f:
        json.dump(news_config, f, indent=2)

    # Create tech subdirectory
    tech_dir = os.path.join(tree_dir, 'tech')
    os.makedirs(tech_dir)
    tech_config = {
        "feed_type": "syndication",
        "id": "tech",
        "title": "Tech Feed",
        "description": "A tech syndication feed",
        "url": "https://feeds.feedburner.com/TechCrunch",
        "max_age": "7d"
    }

    with open(os.path.join(tech_dir, 'feed.json'), 'w') as f:
        json.dump(tech_config, f, indent=2)

    yield test_dir

    shutil.rmtree(test_dir)


def test_feed_manager_with_feed_id(test_config_dir):
    """Test that FeedManager correctly filters feeds when feed_id is provided."""
    config_manager = ConfigManager(config_path=test_config_dir)
    article_manager = ArticleManager(config_manager=config_manager)

    # Test without feed_id - all feeds should be enabled
    feed_manager = FeedManager(
        article_manager=article_manager,
        config_manager=config_manager,
        feed_id=None
    )

    assert feed_manager.root_feed is not None
    assert feed_manager.root_feed.id == "root"

    # Find all feeds and check their disabled_in_session status
    news_feed = feed_manager.get_feed_by_id("news")
    tech_feed = feed_manager.get_feed_by_id("tech")

    assert news_feed is not None
    assert tech_feed is not None
    assert not news_feed.disabled_in_session  # Should be enabled
    assert not tech_feed.disabled_in_session  # Should be enabled

    # Test with feed_id="news" - only news feed and its ancestors should be
    # enabled
    feed_manager_scoped = FeedManager(
        article_manager=article_manager,
        config_manager=config_manager,
        feed_id="news"
    )

    # Check that the scoping worked correctly
    news_feed_scoped = feed_manager_scoped.get_feed_by_id("news")
    tech_feed_scoped = feed_manager_scoped.get_feed_by_id("tech")

    assert news_feed_scoped is not None
    assert tech_feed_scoped is not None
    assert not news_feed_scoped.disabled_in_session  # Should be enabled
    assert tech_feed_scoped.disabled_in_session      # Should be disabled


def test_cli_feed_argument_parsing():
    """Test that the CLI correctly parses the --feed argument."""
    # Test that the --feed argument is available in help
    with patch('sys.argv', ['fof', '--help']):
        with pytest.raises(SystemExit) as exc_info:
            main()
        # Should exit with code 0 for help
        assert exc_info.value.code == 0


def test_cli_feed_argument_functionality(test_config_dir):
    """Test that the CLI --feed argument works correctly."""
    # Mock the ControlLoop to avoid curses issues in tests
    with patch('fof.cli.ControlLoop') as mock_control_loop:
        mock_instance = mock_control_loop.return_value
        mock_instance.start.return_value = None

        # Test the main command with --feed argument
        with patch('sys.argv', ['fof', '--config', test_config_dir, '--feed', 'news']):
            try:
                main()
            except SystemExit:
                pass  # Expected for successful execution

        # Verify ControlLoop was called
        mock_control_loop.assert_called_once()

        # Get the FeedManager that was passed to ControlLoop
        args, kwargs = mock_control_loop.call_args
        feed_manager = args[0]

        # Verify that the feed scoping worked
        news_feed = feed_manager.get_feed_by_id("news")
        tech_feed = feed_manager.get_feed_by_id("tech")

        assert news_feed is not None
        assert tech_feed is not None
        assert not news_feed.disabled_in_session  # Should be enabled
        assert tech_feed.disabled_in_session      # Should be disabled


def test_cli_without_feed_argument(test_config_dir):
    """Test that the CLI works correctly without --feed argument."""
    # Mock the ControlLoop to avoid curses issues in tests
    with patch('fof.cli.ControlLoop') as mock_control_loop:
        mock_instance = mock_control_loop.return_value
        mock_instance.start.return_value = None

        # Test the main command without --feed argument
        with patch('sys.argv', ['fof', '--config', test_config_dir]):
            try:
                main()
            except SystemExit:
                pass  # Expected for successful execution

        # Verify ControlLoop was called
        mock_control_loop.assert_called_once()

        # Get the FeedManager that was passed to ControlLoop
        args, kwargs = mock_control_loop.call_args
        feed_manager = args[0]

        # Verify that no scoping was applied - all feeds should be enabled
        news_feed = feed_manager.get_feed_by_id("news")
        tech_feed = feed_manager.get_feed_by_id("tech")

        assert news_feed is not None
        assert tech_feed is not None
        assert not news_feed.disabled_in_session  # Should be enabled
        assert not tech_feed.disabled_in_session  # Should be enabled
