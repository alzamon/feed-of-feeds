import logging
from dataclasses import dataclass, field
from typing import List, Optional
from random import choices
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
    
    @property
    def feed_type(self) -> FeedType:
        return FeedType.UNION

    def add_feed(self, feed: BaseFeed, weight: Optional[float] = None):
        """Add a feed to this union feed."""
        if weight is not None:
            feed.weight = weight
        else:
            feed.weight = 1.0  # Default weight if not provided
        self.feeds.append(feed)

    def fetch(self) -> Optional[Article]:
        """Fetch one article from a randomly selected feed, based on weights."""
        if not self.feeds:
            logger.warning("No feeds available in this UnionFeed.")
            return None
        
        # Collect weights and feeds
        weights = [getattr(feed, 'weight', 1.0) for feed in self.feeds]
        selected_feed = choices(self.feeds, weights=weights, k=1)[0]
        
        # Log the selected feed
        logger.debug(f"Selected feed: {selected_feed.id} with weight: {getattr(selected_feed, 'weight', 1.0)}")
        
        # Fetch one article from the selected feed
        try:
            article = selected_feed.fetch()
            if article:
                logger.debug(f"Fetched article: {article.id} from feed {selected_feed.id}")
            else:
                logger.warning(f"No article fetched from selected feed: {selected_feed.id}")
            return article
        except Exception as e:
            logger.error(f"Error fetching from feed {selected_feed.id}: {e}")
            return None
