import pytest
from datetime import datetime, timedelta

from fof.models.regular_feed import RegularFeed
from fof.models.base_feed import BaseFeed
from fof.models.enums import FeedType

class DummyArticle:
    def __init__(self, title="title", published_date=None, id="id"):
        self.title = title
        self.published_date = published_date or datetime.now()
        self.id = id

class DummyArticleManager:
    def __init__(self, article=None):
        self._article = article
        self.called_with = {}

    def fetch_article(self, feedpath, url, feed_id, max_age):
        # Store the arguments to verify them in tests if needed
        self.called_with = {
            "feedpath": feedpath,
            "url": url,
            "feed_id": feed_id,
            "max_age": max_age
        }
        return self._article

def test_regular_feed_fetch_returns_article():
    article = DummyArticle()
    manager = DummyArticleManager(article=article)
    rf = RegularFeed(
        id="feed1",
        title="Feed 1",
        description="desc",
        last_updated=datetime.now(),
        url="http://example.com/feed",
        max_age=timedelta(days=2),
        article_manager=manager,
        feedpath=["root", "feed1"],
    )
    result = rf.fetch()
    assert result is article
    assert not rf.fetch_failed
    # Check that the ArticleManager was called with correct arguments
    assert manager.called_with["url"] == "http://example.com/feed"
    assert manager.called_with["feed_id"] == "feed1"
    assert manager.called_with["feedpath"] == ["root", "feed1"]
    assert manager.called_with["max_age"] == timedelta(days=2)

def test_regular_feed_fetch_returns_none_and_sets_fetch_failed():
    manager = DummyArticleManager(article=None)
    rf = RegularFeed(
        id="feed2",
        title="Feed 2",
        description="desc",
        last_updated=datetime.now(),
        url="http://example.com/feed2",
        max_age=None,
        article_manager=manager,
        feedpath=["root", "feed2"],
    )
    result = rf.fetch()
    assert result is None
    assert rf.fetch_failed

def test_regular_feed_feed_type_property():
    manager = DummyArticleManager()
    rf = RegularFeed(
        id="feed3",
        title="Feed 3",
        description="desc",
        last_updated=datetime.now(),
        url="http://example.com/feed3",
        max_age=None,
        article_manager=manager,
        feedpath=["root", "feed3"],
    )
    assert rf.feed_type == FeedType.REGULAR

def test_regular_feed_from_config_dict_uses_defaults(monkeypatch):
    class DummyManager(DummyArticleManager): pass
    config = {
        "id": "feed4",
        "url": "http://example.com/feed4"
    }
    # Patch parse_time_period to return a known value if needed
    monkeypatch.setattr("fof.models.regular_feed.parse_time_period", lambda x: timedelta(days=3))
    rf = RegularFeed.from_config_dict(
        config=config,
        article_manager=DummyManager(),
        parent_max_age=timedelta(days=3),
        parent_feedpath=["root"]
    )
    assert isinstance(rf, RegularFeed)
    assert rf.id == "feed4"
    assert rf.url == "http://example.com/feed4"
    assert rf.max_age == timedelta(days=3)
    assert rf.feedpath == ["feed4"]  # parent_feedpath was ["root"], so ["feed4"]

def test_regular_feed_from_config_dict_merges_feedpath(monkeypatch):
    class DummyManager(DummyArticleManager): pass
    config = {
        "id": "feed5",
        "url": "http://example.com/feed5"
    }
    monkeypatch.setattr("fof.models.regular_feed.parse_time_period", lambda x: timedelta(days=7))
    rf = RegularFeed.from_config_dict(
        config=config,
        article_manager=DummyManager(),
        parent_max_age=timedelta(days=7),
        parent_feedpath=["root", "section"],
    )
    assert rf.feedpath == ["root", "section", "feed5"]
