from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import feedparser
import time
from .article import Article
from .enums import FeedType

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
    @abstractmethod
    def feed_type(self) -> FeedType:
        """Return the type of this feed."""
        pass

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
        try:
            parsed = feedparser.parse(self.url)
            articles = []
            
            for entry in parsed.entries:
                article_id = entry.get('id', entry.get('link', ''))  # Fallback to 'link' if 'id' is missing
                title = entry.get('title', 'No Title')
                content = entry.get('summary', '')
                link = entry.get('link', '')
                author = entry.get('author', 'Unknown')

                # Handle published date conversion using time.mktime
                published_date = None
                if entry.get('published_parsed'):
                    published_date = datetime.fromtimestamp(
                        time.mktime(entry.published_parsed)
                    )

                articles.append(Article(
                    id=article_id,
                    title=title,
                    content=content,
                    link=link,
                    author=author,
                    published_date=published_date,
                    feed_id=self.id
                ))
            return articles
        
        except Exception as e:
            # Log the error and return an empty list
            print(f"Error fetching articles for feed {self.id}: {e}")
            return []


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
        """Fetch articles from all child feeds based on weights."""
        all_articles = []
        for feed in self.feeds:
            articles = feed.fetch()
            all_articles.extend(articles)
        return all_articles  # Basic implementation, weighting can be added later
