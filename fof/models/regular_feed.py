from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, timedelta
from .base_feed import BaseFeed
from .article import Article
from .enums import FeedType
from .article_manager import ArticleManager

@dataclass
class RegularFeed(BaseFeed):
    """A standard feed that fetches articles from a URL."""
    url: str
    max_age: Optional[timedelta]  # Optional max age for filtering articles
    article_manager: ArticleManager  # Removed initialization here
    
    @property
    def feed_type(self) -> FeedType:
        return FeedType.REGULAR
     
    def fetch(self) -> Optional[Article]:
        """Fetch the first unread article using the ArticleManager."""
        article = self.article_manager.fetch_article(
            url=self.url,
            max_age=self.max_age,
            feed_id=self.id,
            feedpath=self.feedpath,
        )
        self.fetch_failed = article is None
        return article

    def __init__(self, id: str, title: str, description: str, last_updated: datetime, weight: float, 
                 url: str, max_age: Optional[timedelta], article_manager: ArticleManager, feedpath: List[str]):
        super().__init__(id, title, description, last_updated, weight, feedpath, fetch_failed=False)
        self.url = url
        self.max_age = max_age
        self.article_manager = article_manager  # Pass ArticleManager from FeedManager
