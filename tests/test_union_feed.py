from datetime import datetime, timedelta

from fof.models.union_feed.models import UnionFeed, WeightedFeed
from fof.models.base_feed import BaseFeed


class DummyFeed(BaseFeed):
    def __init__(
            self,
            id,
            disabled_in_session=False,
            article=None,
            raise_on_fetch=False):
        # Create feedpath with the id as the last component
        feedpath = [id] if id != "root" else []
        super().__init__(
            title=f"Title for {id}",
            description="",
            last_updated=datetime.now(),
            feedpath=feedpath,
            disabled_in_session=disabled_in_session)
        self._article = article
        self._raise_on_fetch = raise_on_fetch

    @property
    def feed_type(self):
        return "dummy"

    def fetch(self):
        if self._raise_on_fetch:
            raise RuntimeError("Fetch failed")
        return self._article


def test_normalize_weights_basic():
    feeds = [
        WeightedFeed(DummyFeed("a"), 20),
        WeightedFeed(DummyFeed("b"), 30),
        WeightedFeed(DummyFeed("c"), 50),
    ]
    uf = UnionFeed(
        title=None,
        description="",
        last_updated=datetime.now(),
        feeds=feeds,
        max_age=None,
        feedpath=[],
    )
    weights = [wf.weight for wf in uf.feeds]
    assert abs(sum(weights) - 100.0) < 1e-6
    assert [round(wf.weight, 1) for wf in uf.feeds] == [20.0, 30.0, 50.0]


def test_normalize_weights_zero_total():
    feeds = [
        WeightedFeed(DummyFeed("a"), 0),
        WeightedFeed(DummyFeed("b"), 0),
        WeightedFeed(DummyFeed("c"), 0),
        WeightedFeed(DummyFeed("d"), 0),
    ]
    uf = UnionFeed(
        title=None,
        description="",
        last_updated=datetime.now(),
        feeds=feeds,
        max_age=None,
        feedpath=[],
    )
    weights = [wf.weight for wf in uf.feeds]
    assert abs(sum(weights) - 100.0) < 1e-6
    for wf in uf.feeds:
        assert abs(wf.weight - 25.0) < 1e-6


def test_normalize_weights_after_add_feed():
    feeds = [
        WeightedFeed(DummyFeed("a"), 60),
        WeightedFeed(DummyFeed("b"), 40),
    ]
    uf = UnionFeed(
        title=None,
        description="",
        last_updated=datetime.now(),
        feeds=feeds,
        max_age=None,
        feedpath=[],
    )
    uf.add_feed(DummyFeed("c"), 100)
    weights = [wf.weight for wf in uf.feeds]
    assert abs(sum(weights) - 100.0) < 1e-6
    # All weights should now be normalized to sum to 100
    # Original weights: 60, 40, 100 -> sum = 200
    # Normalized: 30, 20, 50
    assert [round(wf.weight, 1) for wf in uf.feeds] == [30.0, 20.0, 50.0]


def test_normalize_weights_empty_union():
    uf = UnionFeed(
        title=None,
        description="",
        last_updated=datetime.now(),
        feeds=[],
        max_age=None,
        feedpath=[],
    )
    assert uf.feeds == []  # Should not crash or raise


def test_normalize_weights_large_numbers():
    feeds = [
        WeightedFeed(DummyFeed("a"), 1000),
        WeightedFeed(DummyFeed("b"), 4000),
    ]
    uf = UnionFeed(
        title=None,
        description="",
        last_updated=datetime.now(),
        feeds=feeds,
        max_age=None,
        feedpath=[],
    )
    weights = [wf.weight for wf in uf.feeds]
    assert abs(sum(weights) - 100.0) < 1e-6
    assert [round(wf.weight, 1) for wf in uf.feeds] == [20.0, 80.0]


def test_fetch_returns_none_and_sets_disabled_in_session_when_no_feeds():
    uf = UnionFeed(
        title=None,
        description="",
        last_updated=datetime.now(),
        feeds=[],
        max_age=None,
        feedpath=[],
    )
    result = uf.fetch()
    assert result is None
    assert uf.disabled_in_session


def test_fetch_skips_failed_feeds_and_picks_working():
    # One feed always fails, one feed returns article
    class Article:
        pass
    article = Article()
    article.published_date = datetime.now()
    article.id = "ok-article"
    feeds = [
        WeightedFeed(
            DummyFeed(
                "fail",
                disabled_in_session=True),
            50),
        WeightedFeed(
            DummyFeed(
                "ok",
                disabled_in_session=False,
                article=article),
            50),
    ]
    uf = UnionFeed(
        title=None,
        description="",
        last_updated=datetime.now(),
        feeds=feeds,
        max_age=None,
        feedpath=[],
    )
    result = uf.fetch()
    assert result is article
    assert not uf.disabled_in_session


def test_fetch_respects_max_age_and_skips_old_articles():
    class Article:
        pass
    old_article = Article()
    old_article.published_date = datetime.now() - timedelta(days=100)
    old_article.id = "old"
    feeds = [
        WeightedFeed(
            DummyFeed(
                "oldfeed",
                disabled_in_session=False,
                article=old_article),
            100)]
    uf = UnionFeed(
        title=None,
        description="",
        last_updated=datetime.now(),
        feeds=feeds,
        max_age=timedelta(days=7),
        feedpath=[],
    )
    result = uf.fetch()
    assert result is None
    assert uf.disabled_in_session


def test_add_feed_with_zero_weight_and_normalization():
    feeds = [
        WeightedFeed(DummyFeed("a"), 50),
        WeightedFeed(DummyFeed("b"), 50),
    ]
    uf = UnionFeed(
        title=None,
        description="",
        last_updated=datetime.now(),
        feeds=feeds,
        max_age=None,
        feedpath=[],
    )
    uf.add_feed(DummyFeed("c"), 0)
    weights = [wf.weight for wf in uf.feeds]
    assert abs(sum(weights) - 100.0) < 1e-6
    # All should be non-negative and sum to 100
    for w in weights:
        assert w >= 0
    # Proportions: 50, 50, 0 -> normalized to 50, 50, 0
    assert [round(w, 1) for w in weights] == [50.0, 50.0, 0.0]
