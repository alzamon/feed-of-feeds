import logging
from dataclasses import dataclass, field
from typing import List, Optional
from random import choices
from datetime import timedelta, datetime
from .base_feed import BaseFeed
from .article import Article
from .enums import FeedType

# Configure the logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@dataclass
class UnionFeed(BaseFeed):
    """A feed that combines multiple other feeds with weights."""
    feeds: List[BaseFeed] = field(default_factory=list)
    max_age: Optional[timedelta] = None  # Optional max age for filtering articles
    
    @property
    def feed_type(self) -> FeedType:
        return FeedType.UNION

    def add_feed(self, feed: BaseFeed):
        """Add a feed to this union feed."""
        self.feeds.append(feed)

    def fetch(self) -> Optional[Article]:
        """Fetch one article from a randomly selected feed, based on weights."""
        if not self.feeds:
            logger.warning("No feeds available in this UnionFeed.")
            self.weight = 0  # Set weight to 0 if no subfeeds are available
            return None
        
        # Collect weights and feeds
        weights = [getattr(feed, 'weight', 1.0) for feed in self.feeds]
        
        # Log feeds with weight 0
        for feed, weight in zip(self.feeds, weights):
            if weight == 0:
                logger.debug(f"Feed {feed.id} ignored because weight is 0.")
        
        if all(weight == 0 for weight in weights):
            self.weight = 0  # Set weight to 0 if all subfeeds have weight 0
            return None

        selected_feed = choices(self.feeds, weights=weights, k=1)[0]
        
        # Log the selected feed
        logger.debug(f"Selected feed: {selected_feed.id} with weight: {getattr(selected_feed, 'weight', 1.0)}")
        
        # Fetch one article from the selected feed
        try:
            article = selected_feed.fetch()
            if article:
                # Check if the article is too old
                if self.max_age and article.published_date:
                    if datetime.now() - article.published_date > self.max_age:
                        logger.debug(f"Article {article.id} is too old and ignored due to max_age.")
                        return None
                
                logger.debug(f"Fetched article: {article.id} from feed {selected_feed.id}")
            else:
                logger.warning(f"No article fetched from selected feed: {selected_feed.id}")
            return article
        except Exception as e:
            logger.error(f"Error fetching from feed {selected_feed.id}: {e}")
            return None
