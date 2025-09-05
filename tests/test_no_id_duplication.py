"""Test to ensure no ID duplication in configuration files."""
import tempfile
import os
import json
from datetime import datetime, timedelta

from fof.config_manager import ConfigManager
from fof.feed_serializer import FeedSerializer
from fof.feed_loader import FeedLoader
from fof.models.syndication_feed import SyndicationFeed
from fof.models.union_feed import UnionFeed, WeightedFeed
from fof.models.filter_feed import FilterFeed, Filter
from fof.models.enums import FilterType
from fof.models.article_manager import ArticleManager


def test_no_id_duplication_in_serialization():
    """Test that feed serialization does not include ID fields."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = ConfigManager(temp_dir)
        serializer = FeedSerializer(config_manager)
        article_manager = ArticleManager(config_manager)
        
        # Test syndication feed
        syndication_feed = SyndicationFeed(
            id="test_feed",
            title="Test Feed",
            description="A test feed",
            last_updated=datetime.now(),
            url="http://example.com/feed.xml",
            max_age=timedelta(days=7),
            article_manager=article_manager,
            feedpath=["test_feed"],
        )
        
        # Serialize to directory
        feed_dir = os.path.join(temp_dir, "test_feed")
        serializer.serialize_to_directory(syndication_feed, feed_dir)
        
        # Check that feed.json does NOT contain ID field
        feed_json_path = os.path.join(feed_dir, "feed.json")
        with open(feed_json_path, 'r') as f:
            feed_config = json.load(f)
        
        assert "id" not in feed_config, "feed.json should not contain 'id' field"
        
        # Test union feed
        union_feed = UnionFeed(
            id="my_union",
            title="My Union Feed",
            description="A union of feeds",
            last_updated=datetime.now(),
            feeds=[],
            max_age=timedelta(days=7),
            feedpath=["my_union"],
        )
        
        # Serialize to directory
        union_dir = os.path.join(temp_dir, "my_union")
        serializer.serialize_to_directory(union_feed, union_dir)
        
        # Check that union.json does NOT contain ID field
        union_json_path = os.path.join(union_dir, "union.json")
        with open(union_json_path, 'r') as f:
            union_config = json.load(f)
        
        assert "id" not in union_config, "union.json should not contain 'id' field"
        
        # Test filter feed
        source_feed = SyndicationFeed(
            id="source",
            title="Source Feed",
            description="Source for filtering",
            last_updated=datetime.now(),
            url="http://example.com/source.xml",
            max_age=timedelta(days=7),
            article_manager=article_manager,
            feedpath=["filter_feed", "source"],
        )
        
        filter_feed = FilterFeed(
            id="filter_feed",
            title="Filter Feed",
            description="A filtered feed",
            last_updated=datetime.now(),
            source_feed=source_feed,
            filters=[Filter(FilterType.TITLE_REGEX, "test", True)],
            max_age=timedelta(days=7),
            feedpath=["filter_feed"],
        )
        
        # Serialize to directory
        filter_dir = os.path.join(temp_dir, "filter_feed")
        serializer.serialize_to_directory(filter_feed, filter_dir)
        
        # Check that filter.json does NOT contain ID field
        filter_json_path = os.path.join(filter_dir, "filter.json")
        with open(filter_json_path, 'r') as f:
            filter_config = json.load(f)
        
        assert "id" not in filter_config, "filter.json should not contain 'id' field"


def test_directory_names_used_for_feed_ids():
    """Test that feed IDs are derived from directory names during deserialization."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = ConfigManager(temp_dir)
        article_manager = ArticleManager(config_manager)
        loader = FeedLoader(article_manager)
        
        # Create a test configuration without ID fields
        feed_dir = os.path.join(temp_dir, "my_test_feed")
        os.makedirs(feed_dir)
        
        feed_config = {
            "title": "Test Feed",
            "description": "A test feed",
            "last_updated": datetime.now().isoformat(),
            "url": "http://example.com/feed.xml",
            "max_age": "7d"
        }
        
        feed_json_path = os.path.join(feed_dir, "feed.json")
        with open(feed_json_path, "w") as f:
            json.dump(feed_config, f, indent=2)
        
        # Load the feed
        loaded_feed = loader.load_feed_from_directory(feed_dir, feedpath=[])
        
        # Verify the feed ID comes from directory name
        assert loaded_feed is not None
        assert loaded_feed.id == "my_test_feed", f"Expected 'my_test_feed', got '{loaded_feed.id}'"
        assert loaded_feed.title == "Test Feed"


def test_root_feed_special_case():
    """Test that root feeds get 'root' as their ID regardless of directory name."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = ConfigManager(temp_dir)
        article_manager = ArticleManager(config_manager)
        loader = FeedLoader(article_manager)
        
        # Create a root feed configuration (directory name is 'tree')
        tree_dir = os.path.join(temp_dir, "tree")
        os.makedirs(tree_dir)
        
        union_config = {
            "title": "Root Feed",
            "description": "Root union feed",
            "last_updated": datetime.now().isoformat(),
            "max_age": "7d",
            "weights": {}
        }
        
        union_json_path = os.path.join(tree_dir, "union.json")
        with open(union_json_path, "w") as f:
            json.dump(union_config, f, indent=2)
        
        # Load as root feed (is_root=True)
        loaded_feed = loader.load_feed_from_directory(tree_dir, feedpath=[], is_root=True)
        
        # Verify the root feed gets 'root' as ID, not 'tree'
        assert loaded_feed is not None
        assert loaded_feed.id == "root", f"Root feed should have ID 'root', got '{loaded_feed.id}'"
        assert loaded_feed.title == "Root Feed"