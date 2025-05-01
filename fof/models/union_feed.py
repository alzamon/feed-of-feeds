from dataclasses import dataclass, field
from typing import List, Optional
from .base_feed import BaseFeed
from .article import Article
from .enums import FeedType

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
