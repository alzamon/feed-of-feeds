import pytest
from datetime import datetime
from fof.feed_manager import FeedManager
from fof.models.union_feed.models import UnionFeed, WeightedFeed
from fof.models.syndication_feed.models import SyndicationFeed

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
        title="Feed One",
        description="desc1",
        last_updated=datetime.now(),
        url="http://example.com/1",
        max_age=None,
        article_manager=article_manager,
        feedpath=["feed1"],
    )
    feed2 = SyndicationFeed(
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


def test_update_weights_on_filter_feed():
    """Test that update_weights works with FilterFeed using global ID matching."""
    from fof.models.filter_feed.models import FilterFeed, Filter
    from fof.models.enums import FilterType

    # Create a syndication feed as the source
    article_manager = DummyArticleManager()
    source_feed = SyndicationFeed(
        title="Source Feed",
        description="source desc",
        last_updated=datetime.now(),
        url="http://example.com/source",
        max_age=None,
        article_manager=article_manager,
        feedpath=["tech"],  # This gives it global_id "tech"
    )

    # Create a filter feed that wraps the source
    filt = Filter(FilterType.TITLE_REGEX, "python", is_inclusion=True)
    filter_feed = FilterFeed(
        title="Tech Filter",
        description="filters tech news",
        last_updated=datetime.now(),
        source_feed=source_feed,
        filters=[filt],
        max_age=None,
        feedpath=[],  # This gives it global_id "root" when used as root
    )

    # Set up FeedManager with the filter feed as root
    fm = FeedManager(DummyArticleManager(), DummyConfigManager())
    fm.root_feed = filter_feed

    # This should work - we're looking for the source feed with global_id "tech"
    # The feedpath ["tech"] should match source_feed.id == "tech"
    try:
        fm.update_weights(feedpath=["tech"], increment=5)
        # If we get here without exception, the fix is working
        assert True
    except ValueError as e:
        # This would happen if global ID matching is broken
        pytest.fail(f"update_weights failed with global ID matching: {e}")

    # This should fail - no feed with global_id "nonexistent"
    with pytest.raises(ValueError):
        fm.update_weights(feedpath=["nonexistent"], increment=5)


def test_update_weights_prevents_duplicate_local_id_confusion():
    """Test that duplicate local IDs in different parts of tree don't cause confusion."""
    article_manager = DummyArticleManager()

    # Create feeds with duplicate local IDs in different branches
    news_nrk = SyndicationFeed(
        title="NRK News",
        description="Norwegian news",
        last_updated=datetime.now(),
        url="http://example.com/news-nrk",
        max_age=None,
        article_manager=article_manager,
        feedpath=["news", "nrk"],  # global_id: "news/nrk"
    )

    sports_nrk = SyndicationFeed(
        title="NRK Sports",
        description="Norwegian sports",
        last_updated=datetime.now(),
        url="http://example.com/sports-nrk",
        max_age=None,
        article_manager=article_manager,
        feedpath=["sports", "nrk"],  # global_id: "sports/nrk"
    )

    # Create category feeds
    news_feed = UnionFeed(
        title="News",
        description="News feeds",
        last_updated=datetime.now(),
        feeds=[WeightedFeed(feed=news_nrk, weight=100)],  # Will be normalized to 100
        max_age=None,
        feedpath=["news"],
    )

    sports_feed = UnionFeed(
        title="Sports",
        description="Sports feeds",
        last_updated=datetime.now(),
        feeds=[WeightedFeed(feed=sports_nrk, weight=100)],  # Will be normalized to 100
        max_age=None,
        feedpath=["sports"],
    )

    # Create root feed
    root_feed = UnionFeed(
        title="Root",
        description="Root feed",
        last_updated=datetime.now(),
        feeds=[
            WeightedFeed(feed=news_feed, weight=50),
            WeightedFeed(feed=sports_feed, weight=50)
        ],  # Will be normalized to 50/50
        max_age=None,
        feedpath=[],
    )

    fm = FeedManager(DummyArticleManager(), DummyConfigManager())
    fm.root_feed = root_feed

    # Get initial weights (after normalization)
    news_nrk_weight = root_feed.feeds[0].feed.feeds[0].weight  # Should be 100 (only feed in its parent)
    sports_nrk_weight = root_feed.feeds[1].feed.feeds[0].weight  # Should be 100 (only feed in its parent)

    assert news_nrk_weight == 100.0
    assert sports_nrk_weight == 100.0

    # Update weight for news/nrk - should only affect news NRK, not sports NRK
    fm.update_weights(feedpath=["news", "nrk"], increment=20)

    # Verify only news/nrk was updated
    new_news_nrk_weight = root_feed.feeds[0].feed.feeds[0].weight  # Should be 120
    new_sports_nrk_weight = root_feed.feeds[1].feed.feeds[0].weight  # Should still be 100

    assert new_news_nrk_weight == 120.0
    assert new_sports_nrk_weight == 100.0  # This should be unchanged!

    # Update weight for sports/nrk - should only affect sports NRK
    fm.update_weights(feedpath=["sports", "nrk"], increment=10)

    # Verify only sports/nrk was updated this time
    final_news_nrk_weight = root_feed.feeds[0].feed.feeds[0].weight  # Should still be 120
    final_sports_nrk_weight = root_feed.feeds[1].feed.feeds[0].weight  # Should be 110

    assert final_news_nrk_weight == 120.0  # This should be unchanged!
    assert final_sports_nrk_weight == 110.0
