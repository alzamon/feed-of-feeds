from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta
import feedparser
import time
from .base_feed import BaseFeed
from .article import Article
from .enums import FeedType
from .article_manager import ArticleManager

@dataclass
class RegularFeed(BaseFeed):
    """A standard feed that fetches articles from a URL."""
    url: Optional[str] = None  # URL of the feed
    max_age: Optional[timedelta] = None  # Optional max age for filtering articles
    article_manager: ArticleManager = ArticleManager()
    
    @property
    def feed_type(self) -> FeedType:
        return FeedType.REGULAR

    def fetch(self) -> Optional[Article]:
        """Fetch the first unread article from the feed URL."""
        try:
            parsed = feedparser.parse(self.url)
            
            if not parsed.entries:
                self.weight = 0  # Set weight to 0 if no articles are available
                return None
            
            for entry in parsed.entries:
                title = entry.get('title', 'No Title')
                content = entry.get('summary', '')

                # Handle published date conversion using time.mktime
                published_date = None
                if entry.get('published_parsed'):
                    published_date = datetime.fromtimestamp(
                        time.mktime(entry.published_parsed)
                    )
                
                # Check if the article is too old
                if self.max_age and published_date:
                    if datetime.now() - published_date > self.max_age:
                        continue

                # Check if the article is already read
                if not self.article_manager.is_read(title, content):
                    article_id = entry.get('id', entry.get('link', ''))
                    link = entry.get('link', '')
                    author = entry.get('author', 'Unknown')

                    # Create the article object
                    article = Article(
                        id=article_id,
                        title=title,
                        content=content,
                        link=link,
                        author=author,
                        published_date=published_date,
                        feed_id=self.id
                    )

                    # Mark the article as read
                    self.article_manager.mark_as_read(title, content)

                    return article
            
            self.weight = 0  # Set weight to 0 if no unread articles are found
            return None
        
        except Exception as e:
            # Log the error and set weight to 0
            print(f"Error fetching articles for feed {self.id}: {e}")
            self.weight = 0
            return None
