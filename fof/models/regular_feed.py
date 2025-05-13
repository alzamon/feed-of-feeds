from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, timedelta
import feedparser
import time
import requests
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
        """Fetch the first unread article from the feed URL."""
        try:
            # Fetch feed data with a timeout
            response = requests.get(self.url, timeout=5)  # Set timeout to 5 seconds
            response.raise_for_status()  # Raise an HTTPError if the HTTP request returned an unsuccessful status code

            # Parse the feed
            parsed = feedparser.parse(response.text)
            
            if not parsed.entries:
                self.fetch_failed = True
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
                elif entry.get('updated_parsed'):
                    published_date = datetime.fromtimestamp(
                        time.mktime(entry.updated_parsed)
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
                        feed_id=self.id,
                        feedpath=self.feedpath,  # Updated name
                    )

                    # Mark the article as read
                    self.article_manager.mark_as_read(title, content)

                    return article
            
            self.fetch_failed = True
            return None
        
        except requests.exceptions.RequestException as e:
            print(f"Request error for feed {self.id}: {e}")
            self.fetch_failed = True
            return None
        
        except Exception as e:
            # Log the error and set fetch_failed to True
            print(f"Error fetching articles for feed {self.id}: {e}")
            self.fetch_failed = True
            return None

    def __init__(self, id: str, title: str, description: str, last_updated: datetime, weight: float, 
                 url: str, max_age: Optional[timedelta], article_manager: ArticleManager, feedpath: List[str]):
        super().__init__(id, title, description, last_updated, weight, feedpath, fetch_failed=False)
        self.url = url
        self.max_age = max_age
        self.article_manager = article_manager  # Pass ArticleManager from FeedManager
