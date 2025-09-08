import logging
from dataclasses import dataclass, field
from typing import List, Optional, Pattern, TYPE_CHECKING
import re
from datetime import timedelta, datetime
from ..article import Article
from ..enums import FilterType, FeedType
from ..base_feed import BaseFeed

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class Filter:
    filter_type: FilterType
    pattern: str
    is_inclusion: bool = True
    compiled_pattern: Optional[Pattern] = None

    def __post_init__(self):
        if self.filter_type in {
                FilterType.TITLE_REGEX,
                FilterType.CONTENT_REGEX,
                FilterType.LINK_REGEX}:
            try:
                self.compiled_pattern = re.compile(self.pattern)
            except re.error as e:
                logger.error(
                    f"Invalid regex pattern '{
                        self.pattern}' for filter {
                        self.filter_type}: {e}")
                # Set to None to disable this filter rather than crash
                self.compiled_pattern = None


@dataclass
class FilterFeed(BaseFeed):
    """A feed that filters articles from another feed."""
    source_feed: BaseFeed
    filters: List[Filter] = field(default_factory=list)
    # Optional max age for filtering articles
    max_age: Optional[timedelta] = None
    # Optional age after which articles are purged from cache
    purge_age: Optional[timedelta] = None

    def __init__(
        self,
        title: str,
        description: str,
        last_updated: datetime,
        source_feed: BaseFeed,
        filters: List[Filter],
        max_age: Optional[timedelta],
        feedpath: List[str],
        purge_age: Optional[timedelta] = None,
    ):
        super().__init__(
            title,
            description,
            last_updated,
            feedpath,
            disabled_in_session=False)
        self.source_feed = source_feed
        self.filters = filters or []
        self.max_age = max_age
        # Only set purge_age if explicitly provided
        self.purge_age = purge_age

    @property
    def feed_type(self) -> FeedType:
        return FeedType.FILTER

    def add_filter(
            self,
            filter_type: FilterType,
            pattern: str,
            is_inclusion: bool = True):
        self.filters.append(Filter(filter_type, pattern, is_inclusion))

    def fetch(self) -> Optional[Article]:
        # Keep fetching until we get an article that passes all filters, or
        # source is exhausted
        while True:
            article = self.source_feed.fetch()
            if not article:
                self.disabled_in_session = True
                return None

            passed = True
            for f in self.filters:
                match = False
                if f.filter_type == FilterType.TITLE_REGEX:
                    if f.compiled_pattern and article.title is not None:
                        match = f.compiled_pattern.search(
                            article.title) is not None
                elif f.filter_type == FilterType.CONTENT_REGEX:
                    if f.compiled_pattern and article.content is not None:
                        match = f.compiled_pattern.search(
                            article.content) is not None
                elif f.filter_type == FilterType.LINK_REGEX:
                    if f.compiled_pattern and article.link is not None:
                        match = f.compiled_pattern.search(
                            article.link) is not None

                # Inclusion filter: skip if not matched
                if f.is_inclusion and not match:
                    passed = False
                    break
                # Exclusion filter: skip if matched
                if not f.is_inclusion and match:
                    passed = False
                    break

            if passed:
                return article
            # Otherwise, loop and fetch next candidate