"""Core data models for FoF."""
from abc import ABC, abstractmethod
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
class BaseFeed(ABC):
    """Abstract base feed class for all feed types."""
    id: str
    title: str
    url: str
    description: Optional[str] = None
    last_updated: Optional[datetime] = None
    weight: float = 1.0
    last_score: Optional[int] = None

    @property
    def feed_type(self) -> FeedType:
        """Return the type of this feed."""
        return NotImplementedError("Subclasses must implement this")

    @abstractmethod
    def fetch(self) -> List[Article]:
        """Fetch articles from this feed."""
        pass


@dataclass
class RegularFeed(BaseFeed):
    """A standard feed that fetches articles from a URL."""
    
    @property
    def feed_type(self) -> FeedType:
        return FeedType.REGULAR
    
    def fetch(self) -> List[Article]:
        """Fetch articles from the feed URL."""
        # Implementation for fetching RSS/Atom feeds goes here
        # This will use feedparser or similar library
        pass


@dataclass
class UnionFeed(BaseFeed):
    """A feed that combines multiple other feeds with weights."""
    feeds: List[BaseFeed] = field(default_factory=list)
    
    @property
    def feed_type(self) -> FeedType:
        return FeedType.UNION
    
    def add_feed(self, feed: BaseFeed, weight: Optional[float] = None):
        """Add a feed to this union feed."""
        if weight is not None:
            feed.weight = weight
        self.feeds.append(feed)

    def fetch(self) -> List[Article]:
        """Fetch articles from all child feeds based on weighting."""
        # Implementation will sample from child feeds based on weights
        all_articles = []
        for feed in self.feeds:
            articles = feed.fetch()
            all_articles.extend(articles)
        return all_articles  # Basic implementation, needs proper weighting


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
class FilterFeed(BaseFeed):
    """A feed that filters articles from another feed."""
    source_feed: BaseFeed = field(default=None)
    filters: List[Filter] = field(default_factory=list)

    def __post_init__(self):
        if self.source_feed is None:
            raise ValueError("FilterFeed requires a source_feed")
    
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
            should_include = True
            for f in self.filters:
                matches = f.matches(article)
                if (f.is_inclusion and not matches) or (not f.is_inclusion and matches):
                    should_include = False
                    break
            if should_include:
                filtered_articles.append(article)
                
        return filtered_articles
