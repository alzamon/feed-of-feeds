from dataclasses import dataclass, field
from typing import List, Optional, Pattern
import re
from datetime import timedelta
from .article import Article
from .enums import FilterType
from .base_feed import BaseFeed
from .enums import FeedType

@dataclass
class Filter:
    """A filter to include or exclude articles."""
    filter_type: FilterType
    pattern: str
    is_inclusion: bool = True  # True = keep matches, False = exclude matches
    compiled_pattern: Optional[Pattern] = None

    def __post_init__(self):
        if self.filter_type in (FilterType.TITLE_REGEX, 
                               FilterType.CONTENT_REGEX, 
                               FilterType.LINK_REGEX):
            self.compiled_pattern = re.compile(self.pattern)

    def matches(self, article: Article) -> bool:
        """Check if article matches this filter."""
        matchers = {
            FilterType.TITLE_REGEX: lambda: self.compiled_pattern.search(article.title),
            FilterType.CONTENT_REGEX: lambda: self.compiled_pattern.search(article.content),
            FilterType.AUTHOR: lambda: self.pattern == article.author,
            FilterType.LINK_REGEX: lambda: self.compiled_pattern.search(article.link),
        }
        matcher = matchers.get(self.filter_type)
        return bool(matcher()) if matcher else False


@dataclass
class FilterFeed(BaseFeed):
    """A feed that filters articles from another feed."""
    source_feed: BaseFeed = field(default=None)
    filters: List[Filter] = field(default_factory=list)
    max_age: Optional[timedelta] = None  # Optional max age for filtering articles

    @property
    def feed_type(self) -> FeedType:
        return FeedType.FILTER

    def add_filter(self, filter_type: FilterType, pattern: str, is_inclusion: bool = True):
        """Add a filter to this filter feed."""
        self.filters.append(Filter(filter_type, pattern, is_inclusion))

    def fetch(self) -> Optional[Article]:
        """Fetch and filter a single article from source feed."""
        while True:
            article = self.source_feed.fetch()
            if not article:  # If no article is returned, stop fetching
                return None
            
            # Check if the article is too old
            if self.max_age and article.published_date:
                if datetime.now() - article.published_date > self.max_age:
                    continue

            # Check if the article matches all filters
            should_include = all(
                f.is_inclusion == f.matches(article) for f in self.filters
            )
            
            if should_include:
                return article  # Return the first matching article
