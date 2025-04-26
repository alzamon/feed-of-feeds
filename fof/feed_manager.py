"""Core FoF feed management functionality."""
import random
import yaml
import os
from datetime import datetime
from typing import Dict, List, Optional
import logging
import feedparser
from pathlib import Path

from .models import BaseFeed, RegularFeed, UnionFeed, FilterFeed, Article, FeedType, FilterType

logger = logging.getLogger(__name__)


class FeedManager:
    """Main class for managing feeds and articles."""
    
    def __init__(self, config_path: str):
        """Initialize the feed manager with the given config file.
        
        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = os.path.expanduser(config_path)
        self.feeds: Dict[str, BaseFeed] = {}
        self.articles: Dict[str, Article] = {}
        self.current_article_id: Optional[str] = None
        self.db_path = os.path.join(os.path.dirname(self.config_path), "fof.db")
        
        # Create directory if it doesn't exist
        config_dir = os.path.dirname(self.config_path)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        # Load or create config
        if os.path.exists(self.config_path):
            self.load_config()
        else:
            self.create_default_config()
            
        # Initialize database
        self._init_db()

    def load_config(self):
        """Load the configuration from the YAML file."""
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Process the feeds
        for feed_id, feed_data in config.get('feeds', {}).items():
            self._load_feed(feed_id, feed_data)
    
    def _load_feed(self, feed_id: str, feed_data: dict) -> BaseFeed:
        """Recursively load a feed from config data."""
        if feed_id in self.feeds:
            return self.feeds[feed_id]
            
        feed_type = FeedType(feed_data.get('type', 'regular'))
        
        if feed_type == FeedType.REGULAR:
            feed = RegularFeed(
                id=feed_id,
                title=feed_data.get('title', feed_id),
                url=feed_data['url'],
                description=feed_data.get('description'),
                weight=float(feed_data.get('weight', 1.0))
            )
            
        elif feed_type == FeedType.UNION:
            feed = UnionFeed(
                id=feed_id,
                title=feed_data.get('title', feed_id),
                url=f"union://{feed_id}",
                description=feed_data.get('description'),
                weight=float(feed_data.get('weight', 1.0)),
                feeds=[]
            )
            
            # Recursively load child feeds
            for child_id, child_weight in feed_data.get('feeds', {}).items():
                if isinstance(child_weight, dict):
                    # Complex format with full feed definition
                    child_feed = self._load_feed(child_id, child_weight)
                else:
                    # Simple format referencing existing feed
                    if child_id not in self.feeds:
                        raise ValueError(f"Feed {child_id} referenced but not defined")
                    child_feed = self.feeds[child_id]
                    child_feed.weight = float(child_weight)
                
                feed.feeds.append(child_feed)
                
        elif feed_type == FeedType.FILTER:
            # Get source feed
            source_id = feed_data.get('source_feed')
            if not source_id:
                raise ValueError(f"Filter feed {feed_id} missing source_feed")
                
            # Load source feed if not already loaded
            if source_id not in self.feeds:
                # Check if source feed is defined in config
                config = yaml.safe_load(open(self.config_path, 'r'))
                if source_id not in config.get('feeds', {}):
                    raise ValueError(f"Source feed {source_id} not defined")
                source_feed = self._load_feed(source_id, config['feeds'][source_id])
            else:
                source_feed = self.feeds[source_id]
                
            feed = FilterFeed(
                id=feed_id,
                title=feed_data.get('title', feed_id),
                url=f"filter://{feed_id}",
                description=feed_data.get('description'),
                weight=float(feed_data.get('weight', 1.0)),
                source_feed=source_feed,
                filters=[]
            )
            
            # Add filters
            for filter_data in feed_data.get('filters', []):
                filter_type = FilterType(filter_data['type'])
                pattern = filter_data['pattern']
                is_inclusion = filter_data.get('include', True)
                feed.add_filter(filter_type, pattern, is_inclusion)
        
        # Store the feed
        self.feeds[feed_id] = feed
        return feed

    def create_default_config(self):
        """Create a default configuration file."""
        default_config = {
            'feeds': {
                'example_feed': {
                    'type': 'regular',
                    'title': 'Example Feed',
                    'url': 'https://example.com/feed.xml',
                    'weight': 1.0
                }
            },
            'last_updated': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            'created_by': 'alzamon'
        }
        
        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
    
    def _init_db(self):
        """Initialize the database for storing articles and user preferences."""
        # This would normally set up SQLite, but simplified for this example
        pass
    
    def next_article(self) -> Optional[Article]:
        """Get the next article based on weighted sampling."""
        # Sample a feed based on weights
        root_feed = self._sample_feed(list(self.feeds.values()))
        
        # Fetch articles from the feed
        articles = root_feed.fetch()
        
        # Filter to unread articles
        unread = [a for a in articles if not self._is_read(a)]
        
        if not unread:
            return None
            
        # For now, just return a random article
        article = random.choice(unread)
        self.current_article_id = article.id
        return article
    
    def _sample_feed(self, feeds: List[BaseFeed]) -> BaseFeed:
        """Sample a feed based on weights."""
        if not feeds:
            raise ValueError("No feeds to sample from")
            
        # Calculate total weight
        total_weight = sum(feed.weight for feed in feeds)
        
        # Sample based on weights
        r = random.random() * total_weight
        current = 0
        for feed in feeds:
            current += feed.weight
            if r <= current:
                # If this is a union feed, recursively sample from it
                if isinstance(feed, UnionFeed):
                    return self._sample_feed(feed.feeds)
                return feed
                
        # Should never get here, but just in case
        return feeds[-1]
    
    def score_article(self, article_id: str, score: int):
        """Score the current article."""
        if score < 0 or score > 100:
            raise ValueError("Score must be between 0 and 100")
            
        # TODO In a real implementation, this would update the database
        # For now, just print
        print(f"Article {article_id} scored {score}")
        
        # Mark as read
        self._mark_as_read(article_id)
        
        # Update feed weight based on score
        article = self.articles.get(article_id)
        if article and article.feed_id:
            feed = self.feeds.get(article.feed_id)
            if feed:
                # Simple exponential moving average
                alpha = 0.2
                if feed.last_score is None:
                    feed.last_score = score
                else:
                    feed.last_score = alpha * score + (1 - alpha) * feed.last_score
    
    def _is_read(self, article: Article) -> bool:
        """Check if an article has been read."""
        # In a real implementation, this would query the database
        return article.read
    
    def _mark_as_read(self, article_id: str):
        """Mark an article as read."""
        # In a real implementation, this would update the database
        if article_id in self.articles:
            self.articles[article_id].read = True

    def refresh_feeds(self):
        """Refresh all feeds to fetch new articles."""
        for feed_id, feed in self.feeds.items():
            if isinstance(feed, RegularFeed):
                self._refresh_feed(feed)
    
    def _refresh_feed(self, feed: RegularFeed):
        """Refresh a single feed."""
        try:
            parsed = feedparser.parse(feed.url)
            
            # Update feed metadata
            if 'title' in parsed.feed:
                feed.title = parsed.feed.title
            
            # Process entries
            for entry in parsed.entries:
                article_id = entry.id if 'id' in entry else entry.link
                
                # Skip if we already have this article
                if article_id in self.articles:
                    continue
                    
                # Create new article
                article = Article(
                    id=article_id,
                    title=entry.title,
                    content=entry.get('description', ''),
                    link=entry.link,
                    author=entry.get('author'),
                    published_date=datetime.fromtimestamp(
                        entry.get('published_parsed', entry.get('updated_parsed')).timestamp()
                    ) if entry.get('published_parsed') or entry.get('updated_parsed') else None,
                    feed_id=feed.id
                )
                
                self.articles[article_id] = article
                
            # Update last_updated
            feed.last_updated = datetime.now()
            
        except Exception as e:
            logger.error(f"Error refreshing feed {feed.id}: {e}")
