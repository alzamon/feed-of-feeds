import pytest
from datetime import datetime, timedelta

from fof.models.union_feed import UnionFeed, WeightedFeed
from fof.models.base_feed import BaseFeed

class DummyFeed(BaseFeed):
    def __init__(self, id, fetch_failed=False, article=None, raise_on_fetch=False):
        super().__init__(id, title=None, description="", last_updated=datetime.now(), feedpath=[], fetch_failed=fetch_failed)
        self.id = id
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
        id="test",
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
        id="test",
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
        id="test",
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
        id="test",
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
        id="test",
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

# --------------------------- New tests below ---------------------------

def test_fetch_returns_none_and_sets_fetch_failed_when_no_feeds():
    uf = UnionFeed(
        id="test",
        title=None,
        description="",
        last_updated=datetime.now(),
        feeds=[],
        max_age=None,
        feedpath=[],
    )
    result = uf.fetch()
    assert result is None
    assert uf.fetch_failed

def test_fetch_skips_failed_feeds_and_picks_working():
    # One feed always fails, one feed returns article
    class Article: pass
    article = Article()
    article.published_date = datetime.now()
    article.id = "ok-article"
    feeds = [
        WeightedFeed(DummyFeed("fail", fetch_failed=True), 50),
        WeightedFeed(DummyFeed("ok", fetch_failed=False, article=article), 50),
    ]
    uf = UnionFeed(
        id="union",
        title=None,
        description="",
        last_updated=datetime.now(),
        feeds=feeds,
        max_age=None,
        feedpath=[],
    )
    result = uf.fetch()
    assert result is article
    assert not uf.fetch_failed

def test_fetch_respects_max_age_and_skips_old_articles():
    class Article: pass
    old_article = Article()
    old_article.published_date = datetime.now() - timedelta(days=100)
    old_article.id = "old"
    feeds = [
        WeightedFeed(DummyFeed("oldfeed", fetch_failed=False, article=old_article), 100)
    ]
    uf = UnionFeed(
        id="test",
        title=None,
        description="",
        last_updated=datetime.now(),
        feeds=feeds,
        max_age=timedelta(days=7),
        feedpath=[],
    )
    result = uf.fetch()
    assert result is None
    assert uf.fetch_failed

def test_add_feed_with_zero_weight_and_normalization():
    feeds = [
        WeightedFeed(DummyFeed("a"), 50),
        WeightedFeed(DummyFeed("b"), 50),
    ]
    uf = UnionFeed(
        id="test",
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


def test_from_config_dict_nested_union_and_filter(monkeypatch):
    dummy_manager = object()
    monkeypatch.setattr(
        "fof.models.regular_feed.RegularFeed",
        type("RegularFeed", (), {
            "from_config_dict": staticmethod(lambda cfg, am, ma, fp: DummyFeed(cfg["id"] + "-regular"))
        }),
    )
    monkeypatch.setattr(
        "fof.models.filter_feed.FilterFeed",
        type("FilterFeed", (), {
            "from_config_dict": staticmethod(lambda cfg, am, ma, fp: DummyFeed(cfg["id"] + "-filter"))
        }),
    )
    config = {
        "id": "union1",
        "description": "desc",
        "feeds": [
            {"weight": 70, "feed": {"id": "r1", "feed_type": "regular"}},
            {"weight": 30, "feed": {
                "id": "subunion",
                "feed_type": "union",
                "feeds": [
                    {"weight": 100, "feed": {"id": "f1", "feed_type": "filter"}}
                ]
            }},
        ],
    }
    uf = UnionFeed.from_config_dict(config, dummy_manager, timedelta(days=10), ["root"])
    assert isinstance(uf, UnionFeed)
    assert len(uf.feeds) == 2
    assert any(isinstance(wf.feed, DummyFeed) and wf.feed.id == "r1-regular" for wf in uf.feeds)
    subunion = [wf.feed for wf in uf.feeds if isinstance(wf.feed, UnionFeed)]
    assert subunion and isinstance(subunion[0], UnionFeed)
    assert any(isinstance(wf.feed, DummyFeed) and wf.feed.id == "f1-filter" for wf in subunion[0].feeds)
