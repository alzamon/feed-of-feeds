import pytest
from datetime import datetime
from fof.feed_manager import FeedManager
from fof.models.union_feed.models import UnionFeed, WeightedFeed
from fof.models.filter_feed.models import FilterFeed, Filter
from fof.models.syndication_feed.models import SyndicationFeed
from fof.models.enums import FilterType

# Dummy managers for FeedManager


class DummyArticleManager:
    pass


class DummyConfigManager:
    config_path = "dummy_path"

    @property
    def get_tree_dir(self):
        return "tree_dir"

    def sanitize_filename(self, name):
        return name.replace(" ", "_")

    @property
    def get_update_dir(self):
        return "update_dir"

    def persist_update(self, dir):
        pass


@pytest.fixture
def complex_feed_tree():
    # Root: UnionFeed (id="root")
    #   - Child 1: UnionFeed (id="sub_union")
    #       - Grandchild: RegularFeed (id="sub_union/regular1")
    #   - Child 2: FilterFeed (id="filter1") wrapping RegularFeed (id="filter1/regular2")
    now = datetime.now()
    article_manager = DummyArticleManager()

    # Grandchild under sub_union
    regular1 = SyndicationFeed(
        title="Regular 1",
        description="desc1",
        last_updated=now,
        url="http://example.com/1",
        max_age=None,
        article_manager=article_manager,
        feedpath=["sub_union", "regular1"],
    )

    sub_union = UnionFeed(
        title="Sub Union",
        description="A sub-union",
        last_updated=now,
        feeds=[WeightedFeed(feed=regular1, weight=100)],
        max_age=None,
        feedpath=["sub_union"],
    )

    # Filter branch
    regular2 = SyndicationFeed(
        title="Regular 2",
        description="desc2",
        last_updated=now,
        url="http://example.com/2",
        max_age=None,
        article_manager=article_manager,
        feedpath=["filter1", "regular2"],
    )
    filt = Filter(FilterType.TITLE_REGEX, "Python", is_inclusion=True)
    filter1 = FilterFeed(
        title="Filter 1",
        description="filters on title",
        last_updated=now,
        source_feed=regular2,
        filters=[filt],
        max_age=None,
        feedpath=["filter1"],
    )

    # Root union
    root_union = UnionFeed(
        title="Root Union",
        description="top-level union",
        last_updated=now,
        feeds=[
            WeightedFeed(feed=sub_union, weight=60),
            WeightedFeed(feed=filter1, weight=40)
        ],
        max_age=None,
        feedpath=[],
    )

    return root_union, sub_union, regular1, filter1, regular2


def test_set_disabled_in_session_for_feeds(complex_feed_tree):
    root_union, sub_union, regular1, filter1, regular2 = complex_feed_tree
    fm = FeedManager(DummyArticleManager(), DummyConfigManager())
    fm.root_feed = root_union

    # Call: select regular1 (grandchild of sub_union)
    fm._set_disabled_in_session_for_feeds("sub_union/regular1")
    # Only root, sub_union, and regular1 enabled; filter1 and regular2
    # disabled
    assert not root_union.disabled_in_session
    assert not sub_union.disabled_in_session
    assert not regular1.disabled_in_session
    assert filter1.disabled_in_session
    assert regular2.disabled_in_session

    # Call: select filter1 (should enable root, filter1, regular2;
    # sub_union/regular1 disabled)
    fm._set_disabled_in_session_for_feeds("filter1")
    assert not root_union.disabled_in_session
    assert sub_union.disabled_in_session
    assert regular1.disabled_in_session
    assert not filter1.disabled_in_session
    assert not regular2.disabled_in_session

    # Call: select root (all enabled)
    fm._set_disabled_in_session_for_feeds("root")
    assert not root_union.disabled_in_session
    assert not sub_union.disabled_in_session
    assert not regular1.disabled_in_session
    assert not filter1.disabled_in_session
    assert not regular2.disabled_in_session

    # Call: select regular2 (should enable root, filter1, regular2 only)
    fm._set_disabled_in_session_for_feeds("filter1/regular2")
    assert not root_union.disabled_in_session
    assert filter1.disabled_in_session == False
    assert regular2.disabled_in_session == False
    assert sub_union.disabled_in_session
    assert regular1.disabled_in_session
