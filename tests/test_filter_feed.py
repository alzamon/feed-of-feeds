import pytest
from datetime import datetime, timedelta

from fof.models.filter_feed import FilterFeed, Filter
from fof.models.enums import FilterType, FeedType
from fof.models.base_feed import BaseFeed

class DummyArticle:
    def __init__(self, title=None, content=None, link=None):
        self.title = title
        self.content = content
        self.link = link
        self.published_date = datetime.now()
        self.id = "dummy"

class DummyFeed(BaseFeed):
    def __init__(self, article=None, fetch_failed=False):
        super().__init__("dummy", title=None, description="", last_updated=datetime.now(), feedpath=[], fetch_failed=fetch_failed)
        self._article = article
        self._fetch_failed = fetch_failed
    @property
    def feed_type(self):
        return FeedType.REGULAR
    def fetch(self):
        if self._fetch_failed:
            return None
        return self._article

def test_filterfeed_no_filters_passes_article():
    art = DummyArticle(title="foo", content="bar", link="baz")
    dummy_feed = DummyFeed(article=art)
    ff = FilterFeed(
        id="f",
        title="t",
        description="d",
        last_updated=datetime.now(),
        source_feed=dummy_feed,
        filters=[],
        max_age=None,
        feedpath=[],
    )
    result = ff.fetch()
    assert result is art

def test_filterfeed_title_regex_inclusion_pass():
    art = DummyArticle(title="hello world", content="body", link="url")
    dummy_feed = DummyFeed(article=art)
    filt = Filter(FilterType.TITLE_REGEX, "hello")
    ff = FilterFeed(
        id="f",
        title="t",
        description="d",
        last_updated=datetime.now(),
        source_feed=dummy_feed,
        filters=[filt],
        max_age=None,
        feedpath=[],
    )
    result = ff.fetch()
    assert result is art

def test_filterfeed_title_regex_inclusion_fail():
    art = DummyArticle(title="goodbye", content="body", link="url")
    dummy_feed = DummyFeed(article=art)
    filt = Filter(FilterType.TITLE_REGEX, "hello")
    ff = FilterFeed(
        id="f",
        title="t",
        description="d",
        last_updated=datetime.now(),
        source_feed=dummy_feed,
        filters=[filt],
        max_age=None,
        feedpath=[],
    )
    result = ff.fetch()
    assert result is None

def test_filterfeed_content_regex_exclusion():
    art = DummyArticle(title="foo", content="forbidden", link="baz")
    dummy_feed = DummyFeed(article=art)
    filt = Filter(FilterType.CONTENT_REGEX, "forbidden", is_inclusion=False)
    ff = FilterFeed(
        id="f",
        title="t",
        description="d",
        last_updated=datetime.now(),
        source_feed=dummy_feed,
        filters=[filt],
        max_age=None,
        feedpath=[],
    )
    result = ff.fetch()
    assert result is None

def test_filterfeed_link_regex_inclusion():
    art = DummyArticle(title="foo", content="bar", link="baz.com/article/123")
    dummy_feed = DummyFeed(article=art)
    filt = Filter(FilterType.LINK_REGEX, r"article/\d+")
    ff = FilterFeed(
        id="f",
        title="t",
        description="d",
        last_updated=datetime.now(),
        source_feed=dummy_feed,
        filters=[filt],
        max_age=None,
        feedpath=[],
    )
    result = ff.fetch()
    assert result is art

def test_filterfeed_multiple_filters_all_must_pass():
    art = DummyArticle(title="Special Title", content="Special Content", link="https://x.com/42")
    dummy_feed = DummyFeed(article=art)
    filters = [
        Filter(FilterType.TITLE_REGEX, "Special"),
        Filter(FilterType.CONTENT_REGEX, "Content"),
        Filter(FilterType.LINK_REGEX, r"x\.com"),
    ]
    ff = FilterFeed(
        id="f",
        title="t",
        description="d",
        last_updated=datetime.now(),
        source_feed=dummy_feed,
        filters=filters,
        max_age=None,
        feedpath=[],
    )
    result = ff.fetch()
    assert result is art

def test_filterfeed_fetch_failed_propagation():
    dummy_feed = DummyFeed(article=None, fetch_failed=True)
    ff = FilterFeed(
        id="f",
        title="t",
        description="d",
        last_updated=datetime.now(),
        source_feed=dummy_feed,
        filters=[],
        max_age=None,
        feedpath=[],
    )
    result = ff.fetch()
    assert result is None
    assert ff.fetch_failed

def test_filterfeed_add_filter_method():
    art = DummyArticle(title="xyzz", content="abcd", link="test")
    dummy_feed = DummyFeed(article=art)
    ff = FilterFeed(
        id="f",
        title="t",
        description="d",
        last_updated=datetime.now(),
        source_feed=dummy_feed,
        filters=[],
        max_age=None,
        feedpath=[],
    )
    ff.add_filter(FilterType.TITLE_REGEX, "xyz")
    assert len(ff.filters) == 1
    result = ff.fetch()
    assert result is art

