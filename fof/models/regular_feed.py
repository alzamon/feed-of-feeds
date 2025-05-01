from dataclasses import dataclass
from typing import List
from datetime import datetime
import feedparser
import time
from .base_feed import BaseFeed
from .article import Article
from .enums import FeedType

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
