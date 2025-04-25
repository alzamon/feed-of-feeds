"""Core data models for FoF."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Pattern, Union
import re


class FeedType(Enum):
    """Types of feeds in the system."""
    REGULAR = "regular"
    UNION = "union"
    FILTER = "filter"


@dataclass
class Article:
    """Represents a single article from a feed."""
    id: str
    title: str
    content: str
    link: str
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    feed_id: Optional[str] = None
    read: bool = False
    score: Optional[int] = None


@dataclass
class Feed:
    """Base feed class for all feed types."""
    id: str
    title: str
    url: str
    feed_type: FeedType = FeedType.REGULAR
    description: Optional[str] = None
    last_updated: Optional[datetime] = None
    weight: float = 1.0
    last_score: Optional[int] = None

    def fetch(self) -> List[Article]:
        """Fetch articles from this feed."""
        raise NotImplementedError("Subclasses must implement this")


@dataclass
class UnionFeed(Feed):
    """A feed that combines multiple other feeds with weights."""
    feeds: List[Feed] = field(default_factory=list)
    
    def __post_init__(self):
        self.feed_type = FeedType.UNION
    
    def add_feed(self, feed: Feed, weight: Optional[float] = None):
        """Add a feed to this union feed."""
        if weight is not None:
            feed.weight = weight
        self.feeds.append(feed)

    def fetch(self) -> List[Article]:
        """Fetch articles from all child feeds based on weighting."""
        # Implementation will sample from child feeds based on weights
        pass


class FilterType(Enum):
    """Types of filters that can be applied to feeds."""
    TITLE_REGEX = "title_regex"
    CONTENT_REGEX = "content_regex"
    AUTHOR = "author"
    LINK_REGEX = "link_regex"


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
        if self.filter_type == FilterType.TITLE_REGEX:
            return bool(self.compiled_pattern.search(article.title))
        elif self.filter_type == FilterType.CONTENT_REGEX:
            return bool(self.compiled_pattern.search(article.content))
        elif self.filter_type == FilterType.AUTHOR:
            return self.pattern == article.author
        elif self.filter_type == FilterType.LINK_REGEX:
            return bool(self.compiled_pattern.search(article.link))
        return False


    
@dataclass
class FilterFeed(Feed):
    """A feed that filters articles from another feed."""
    source_feed: Feed = field(default=None)  # Field with no default, but technicallyy has one
    filters: List[Filter] = field(default_factory=list)

    def __post_init__(self):
        self.feed_type = FeedType.FILTER
        if self.source_feed is None:
            raise ValueError("FilterFeed requires a source_feed")
    def add_filter(self, filter_type: FilterType, pattern: str, is_inclusion: bool = True):
        """Add a filter to this filter feed."""
        self.filters.append(Filter(filter_type, pattern, is_inclusion))

    def fetch(self) -> List[Article]:
        """Fetch and filter articles from source feed."""
        articles = self.source_feed.fetch()
        filtered_articles = []
        
        for article in articles:
            should_include = True
            for f in self.filters:
                matches = f.matches(article)
                if (f.is_inclusion and not matches) or (not f.is_inclusion and matches):
                    should_include = False
                    break
            if should_include:
                filtered_articles.append(article)
                
        return filtered_articles
