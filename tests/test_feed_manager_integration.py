import pytest
from datetime import datetime
from unittest.mock import patch, mock_open
import json

from fof.feed_manager import FeedManager
from fof.models.union_feed import UnionFeed
from fof.models.filter_feed import FilterFeed
from fof.models.syndication_feed import SyndicationFeed
from fof.models.enums import FilterType

# Dummy managers to use for FeedManager initialization


class DummyArticleManager:
    pass


class DummyConfigManager:
    config_path = "dummy_path"

    @property
    def get_tree_dir(self):
        return "tree_dir"

    def sanitize_filename(self, name):
        # mimic the real one
        return name.replace(" ", "_")

    @property
    def get_update_dir(self):
        return "update_dir"

    def persist_update(self, dir):
        pass


@pytest.fixture
def mock_files_structure():
    """
    Sets up a fake nested feed config, as described:
    tree_dir/
      union.json  (union of "syndication1" and "filter1")
      syndication1/feed.json
      filter1/filter.json
      filter1/source/feed.json
    """
    now = datetime.now()
    # All the config file contents, keyed by their full paths
    files = {
        "tree_dir/union.json": {
            "title": "Root Union",
            "description": "A union of feeds",
            "last_updated": now.isoformat(),
            "max_age": "7d",
            "weights": {"syndication1": 60, "filter1": 40}
        },
        "tree_dir/syndication1/feed.json": {
            "title": "Syndication Feed 1",
            "description": "Syndication feed description",
            "last_updated": now.isoformat(),
            "url": "http://example.com/feed1",
            "max_age": "7d"
        },
        "tree_dir/filter1/filter.json": {
            "title": "Filter Feed 1",
            "description": "Filters by title",
            "last_updated": now.isoformat(),
            "max_age": "3d",
            "criteria": [{
                "filter_type": FilterType.TITLE_REGEX.value,
                "pattern": "Python",
                "is_inclusion": True
            }]
        },
        "tree_dir/filter1/source/feed.json": {
            "title": "Syndication Feed 2",
            "description": "Another syndication feed",
            "last_updated": now.isoformat(),
            "url": "http://example.com/feed2",
            "max_age": "3d"
        },
    }
    return files


@pytest.fixture
def patch_fs(mock_files_structure):
    # Patch os.path.isfile to return True for our mock files
    def isfile(path):
        return path in mock_files_structure

    # Patch open to serve our mock files
    def my_open(path, mode="r", encoding=None):
        if path in mock_files_structure:
            # Return a mock file object
            data = json.dumps(mock_files_structure[path])
            m = mock_open(read_data=data)()
            m.__enter__.return_value = m
            return m
        raise FileNotFoundError(f"No such file: {path}")

    # Patch os.path.join to behave simply (for this test)
    def join(*args):
        return "/".join(args)

    with patch("os.path.isfile", side_effect=isfile), \
            patch("builtins.open", side_effect=my_open), \
            patch("os.path.join", side_effect=join):
        yield


def test_nested_feed_hierarchy_load(patch_fs):
    article_manager = DummyArticleManager()
    config_manager = DummyConfigManager()
    fm = FeedManager(article_manager, config_manager)
    root = fm.root_feed
    assert isinstance(root, UnionFeed)
    assert root.id == "root"
    assert root.title == "Root Union"
    assert len(root.feeds) == 2

    feed_types = {type(wf.feed) for wf in root.feeds}
    assert SyndicationFeed in feed_types
    assert FilterFeed in feed_types

    # Find the filter feed and check its internals
    filter_feed = next(
        (wf.feed for wf in root.feeds if isinstance(
            wf.feed, FilterFeed)), None)
    assert filter_feed is not None
    assert filter_feed.id == "filter1"
    assert filter_feed.filters
    assert filter_feed.filters[0].filter_type == FilterType.TITLE_REGEX
    assert filter_feed.filters[0].pattern == "Python"
    # Its source_feed should be a SyndicationFeed
    assert isinstance(filter_feed.source_feed, SyndicationFeed)
    assert filter_feed.source_feed.id == "source"
