from dataclasses import dataclass, field
from typing import List, Optional, Pattern
import re
from .article import Article
from .enums import FilterType
from .feed import BaseFeed
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

    @property
    def feed_type(self) -> FeedType:
        return FeedType.FILTER

    def add_filter(self, filter_type: FilterType, pattern: str, is_inclusion: bool = True):
        """Add a filter to this filter feed."""
        self.filters.append(Filter(filter_type, pattern, is_inclusion))

    def fetch(self) -> List[Article]:
        """Fetch and filter articles from source feed."""
        articles = self.source_feed.fetch()
        filtered_articles = []
        
        for article in articles:
            should_include = all(
                f.is_inclusion == f.matches(article) for f in self.filters
            )
            if should_include:
                filtered_articles.append(article)
                
        return filtered_articles
