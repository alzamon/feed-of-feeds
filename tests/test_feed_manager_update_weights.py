import pytest
from datetime import datetime
from fof.feed_manager import FeedManager
from fof.models.union_feed import UnionFeed, WeightedFeed
from fof.models.syndication_feed import SyndicationFeed

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
def simple_union_feed():
    # Create two dummy RegularFeed children
    article_manager = DummyArticleManager()
    feed1 = SyndicationFeed(
        id="feed1",
        title="Feed One",
        description="desc1",
        last_updated=datetime.now(),
        url="http://example.com/1",
        max_age=None,
        article_manager=article_manager,
        feedpath=["feed1"],
    )
    feed2 = SyndicationFeed(
        id="feed2",
        title="Feed Two",
        description="desc2",
        last_updated=datetime.now(),
        url="http://example.com/2",
        max_age=None,
        article_manager=article_manager,
        feedpath=["feed2"],
    )
    # Wrap each in WeightedFeed
    wf1 = WeightedFeed(feed=feed1, weight=60)
    wf2 = WeightedFeed(feed=feed2, weight=40)
    # Create a UnionFeed root
    union_feed = UnionFeed(
        id="union",
        title="A Union",
        description="A union feed",
        last_updated=datetime.now(),
        feeds=[wf1, wf2],
        max_age=None,
        feedpath=[],
    )
    return union_feed, wf1, wf2


def test_update_weights_on_union_feed(simple_union_feed):
    union_feed, wf1, wf2 = simple_union_feed
    # Patch FeedManager so it uses our union_feed as root_feed
    fm = FeedManager(DummyArticleManager(), DummyConfigManager())
    fm.root_feed = union_feed

    # Initial weights
    assert wf1.weight == 60
    assert wf2.weight == 40

    # Update weight of feed2 by +10 using the correct feedpath
    fm.update_weights(feedpath=["feed2"], increment=10)

    # After update: wf2 should be 50, wf1 should remain 60
    assert wf1.weight == 60
    assert wf2.weight == 50

    # Now try updating feed1 by -20
    fm.update_weights(feedpath=["feed1"], increment=-20)
    assert wf1.weight == 40
    assert wf2.weight == 50

    # If we use a bad feedpath, should raise
    with pytest.raises(ValueError):
        fm.update_weights(feedpath=["nonexistent"], increment=5)
