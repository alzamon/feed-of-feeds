import pytest
from datetime import datetime
from fof.feed_manager import FeedManager
from fof.models.union_feed import UnionFeed, WeightedFeed
from fof.models.filter_feed import FilterFeed, Filter
from fof.models.syndication_feed import SyndicationFeed
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
    # Root: UnionFeed (id="root_union")
    #   - Child 1: UnionFeed (id="sub_union")
    #       - Grandchild: RegularFeed (id="regular1")
    #   - Child 2: FilterFeed (id="filter1") wrapping RegularFeed (id="regular2")
    now = datetime.now()
    article_manager = DummyArticleManager()

    # Grandchild under sub_union
    regular1 = SyndicationFeed(
        id="regular1",
        title="Regular 1",
        description="desc1",
        last_updated=now,
        url="http://example.com/1",
        max_age=None,
        article_manager=article_manager,
        feedpath=["root_union", "sub_union", "regular1"],
    )

    sub_union = UnionFeed(
        id="sub_union",
        title="Sub Union",
        description="A sub-union",
        last_updated=now,
        feeds=[WeightedFeed(feed=regular1, weight=100)],
        max_age=None,
        feedpath=["root_union", "sub_union"],
    )

    # Filter branch
    regular2 = SyndicationFeed(
        id="regular2",
        title="Regular 2",
        description="desc2",
        last_updated=now,
        url="http://example.com/2",
        max_age=None,
        article_manager=article_manager,
        feedpath=["root_union", "filter1", "regular2"],
    )
    filt = Filter(FilterType.TITLE_REGEX, "Python", is_inclusion=True)
    filter1 = FilterFeed(
        id="filter1",
        title="Filter 1",
        description="filters on title",
        last_updated=now,
        source_feed=regular2,
        filters=[filt],
        max_age=None,
        feedpath=["root_union", "filter1"],
    )

    # Root union
    root_union = UnionFeed(
        id="root_union",
        title="Root Union",
        description="top-level union",
        last_updated=now,
        feeds=[
            WeightedFeed(feed=sub_union, weight=60),
            WeightedFeed(feed=filter1, weight=40)
        ],
        max_age=None,
        feedpath=["root_union"],
    )

    return root_union, sub_union, regular1, filter1, regular2

def test_set_disabled_in_session_for_feeds(complex_feed_tree):
    root_union, sub_union, regular1, filter1, regular2 = complex_feed_tree
    fm = FeedManager(DummyArticleManager(), DummyConfigManager())
    fm.root_feed = root_union

    # Call: select regular1 (grandchild of sub_union)
    fm._set_disabled_in_session_for_feeds("regular1")
    # Only root_union, sub_union, and regular1 enabled; filter1 and regular2 disabled
    assert not root_union.disabled_in_session
    assert not sub_union.disabled_in_session
    assert not regular1.disabled_in_session
    assert filter1.disabled_in_session
    assert regular2.disabled_in_session

    # Call: select filter1 (should enable root_union, filter1, regular2; sub_union/regular1 disabled)
    fm._set_disabled_in_session_for_feeds("filter1")
    assert not root_union.disabled_in_session
    assert sub_union.disabled_in_session
    assert regular1.disabled_in_session
    assert not filter1.disabled_in_session
    assert not regular2.disabled_in_session

    # Call: select root_union (all enabled)
    fm._set_disabled_in_session_for_feeds("root_union")
    assert not root_union.disabled_in_session
    assert not sub_union.disabled_in_session
    assert not regular1.disabled_in_session
    assert not filter1.disabled_in_session
    assert not regular2.disabled_in_session

    # Call: select regular2 (should enable root_union, filter1, regular2 only)
    fm._set_disabled_in_session_for_feeds("regular2")
    assert not root_union.disabled_in_session
    assert filter1.disabled_in_session == False
    assert regular2.disabled_in_session == False
    assert sub_union.disabled_in_session
    assert regular1.disabled_in_session
