from datetime import datetime

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
    def __init__(self, article=None, disabled_in_session=False):
        super().__init__(
            title="dummy",
            description="",
            last_updated=datetime.now(),
            feedpath=["dummy"],
            disabled_in_session=disabled_in_session)
        self._article = article
        self._disabled_in_session = disabled_in_session
        self._fetched = False  # Simulate single-use feed

    @property
    def feed_type(self):
        return FeedType.REGULAR

    def fetch(self):
        if self._disabled_in_session:
            return None
        if self._fetched:
            return None
        self._fetched = True
        return self._article


def test_filterfeed_no_filters_passes_article():
    art = DummyArticle(title="foo", content="bar", link="baz")
    dummy_feed = DummyFeed(article=art)
    ff = FilterFeed(
        
        title="t",
        description="d",
        last_updated=datetime.now(),
        source_feed=dummy_feed,
        filters=[],
        max_age=None,
        feedpath=["f"],
    )
    result = ff.fetch()
    assert result is art


def test_filterfeed_title_regex_inclusion_pass():
    art = DummyArticle(title="hello world", content="body", link="url")
    dummy_feed = DummyFeed(article=art)
    filt = Filter(FilterType.TITLE_REGEX, "hello")
    ff = FilterFeed(
        
        title="t",
        description="d",
        last_updated=datetime.now(),
        source_feed=dummy_feed,
        filters=[filt],
        max_age=None,
        feedpath=["f"],
    )
    result = ff.fetch()
    assert result is art


def test_filterfeed_title_regex_inclusion_fail():
    art = DummyArticle(title="goodbye", content="body", link="url")
    dummy_feed = DummyFeed(article=art)
    filt = Filter(FilterType.TITLE_REGEX, "hello")
    ff = FilterFeed(
        
        title="t",
        description="d",
        last_updated=datetime.now(),
        source_feed=dummy_feed,
        filters=[filt],
        max_age=None,
        feedpath=["f"],
    )
    result = ff.fetch()
    assert result is None


def test_filterfeed_content_regex_exclusion():
    art = DummyArticle(title="foo", content="forbidden", link="baz")
    dummy_feed = DummyFeed(article=art)
    filt = Filter(FilterType.CONTENT_REGEX, "forbidden", is_inclusion=False)
    ff = FilterFeed(
        
        title="t",
        description="d",
        last_updated=datetime.now(),
        source_feed=dummy_feed,
        filters=[filt],
        max_age=None,
        feedpath=["f"],
    )
    result = ff.fetch()
    assert result is None


def test_filterfeed_link_regex_inclusion():
    art = DummyArticle(title="foo", content="bar", link="baz.com/article/123")
    dummy_feed = DummyFeed(article=art)
    filt = Filter(FilterType.LINK_REGEX, r"article/\d+")
    ff = FilterFeed(
        
        title="t",
        description="d",
        last_updated=datetime.now(),
        source_feed=dummy_feed,
        filters=[filt],
        max_age=None,
        feedpath=["f"],
    )
    result = ff.fetch()
    assert result is art


def test_filterfeed_multiple_filters_all_must_pass():
    art = DummyArticle(
        title="Special Title",
        content="Special Content",
        link="https://x.com/42")
    dummy_feed = DummyFeed(article=art)
    filters = [
        Filter(FilterType.TITLE_REGEX, "Special"),
        Filter(FilterType.CONTENT_REGEX, "Content"),
        Filter(FilterType.LINK_REGEX, r"x\.com"),
    ]
    ff = FilterFeed(
        
        title="t",
        description="d",
        last_updated=datetime.now(),
        source_feed=dummy_feed,
        filters=filters,
        max_age=None,
        feedpath=["f"],
    )
    result = ff.fetch()
    assert result is art


def test_filterfeed_disabled_in_session_propagation():
    dummy_feed = DummyFeed(article=None, disabled_in_session=True)
    ff = FilterFeed(
        
        title="t",
        description="d",
        last_updated=datetime.now(),
        source_feed=dummy_feed,
        filters=[],
        max_age=None,
        feedpath=["f"],
    )
    result = ff.fetch()
    assert result is None
    assert ff.disabled_in_session


def test_filterfeed_add_filter_method():
    art = DummyArticle(title="xyzz", content="abcd", link="test")
    dummy_feed = DummyFeed(article=art)
    ff = FilterFeed(
        
        title="t",
        description="d",
        last_updated=datetime.now(),
        source_feed=dummy_feed,
        filters=[],
        max_age=None,
        feedpath=["f"],
    )
    ff.add_filter(FilterType.TITLE_REGEX, "xyz")
    assert len(ff.filters) == 1
    result = ff.fetch()
    assert result is art


def test_filter_invalid_regex_handling():
    """Test that Filter handles invalid regex gracefully."""
    # Valid regex should work
    valid_filter = Filter(FilterType.TITLE_REGEX, "test.*", True)
    assert valid_filter.compiled_pattern is not None

    # Invalid regex should not crash but log error and set pattern to None
    invalid_filter = Filter(FilterType.TITLE_REGEX, "[invalid", True)
    assert invalid_filter.compiled_pattern is None
