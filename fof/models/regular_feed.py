from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import feedparser
import time
from .base_feed import BaseFeed
from .article import Article
from .enums import FeedType
from .article_manager import ArticleManager

@dataclass
class RegularFeed(BaseFeed):
    """A standard feed that fetches articles from a URL."""
    url: Optional[str] = None  # Moved `url` here from `BaseFeed`
    article_manager: ArticleManager = ArticleManager()
    
    @property
    def feed_type(self) -> FeedType:
        return FeedType.REGULAR

    def fetch(self) -> Optional[Article]:
        """Fetch the first unread article from the feed URL."""
        try:
            parsed = feedparser.parse(self.url)
            
            if not parsed.entries:
                return None
            
            for entry in parsed.entries:
                title = entry.get('title', 'No Title')
                content = entry.get('summary', '')
                
                # Check if the article is already read
                if not self.article_manager.is_read(title, content):
                    article_id = entry.get('id', entry.get('link', ''))
                    link = entry.get('link', '')
                    author = entry.get('author', 'Unknown')

                    # Handle published date conversion using time.mktime
                    published_date = None
                    if entry.get('published_parsed'):
                        published_date = datetime.fromtimestamp(
                            time.mktime(entry.published_parsed)
                        )

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
            
            return None  # No unread articles found
        
        except Exception as e:
            # Log the error and return None
            print(f"Error fetching articles for feed {self.id}: {e}")
            return None
