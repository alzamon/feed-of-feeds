import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, TYPE_CHECKING
from random import choices
from datetime import timedelta, datetime
from .base_feed import BaseFeed
from .article import Article
from .enums import FeedType
from ..error_logger import log_error_with_readkey
from ..time_period import parse_time_period

if TYPE_CHECKING:
    from .regular_feed import RegularFeed
    from .filter_feed import FilterFeed

# Configure the logger
logger = logging.getLogger(__name__)

@dataclass
class UnionFeed(BaseFeed):
    """A feed that combines multiple other feeds with weights."""
    feeds: List[BaseFeed] = field(default_factory=list)
    max_age: Optional[timedelta] = None  # Optional max age for filtering articles
    
    @property
    def feed_type(self) -> FeedType:
        return FeedType.UNION

    def __init__(self, id: str, title: str, description: str, last_updated: datetime, weight: float, 
                 feeds: List[BaseFeed], max_age: Optional[timedelta], feedpath: List[str]):
        super().__init__(id, title, description, last_updated, weight, feedpath, fetch_failed=False)
        self.feeds = feeds
        self.max_age = max_age

    def add_feed(self, feed: BaseFeed):
        """Add a feed to this union feed."""
        self.feeds.append(feed)

    def fetch(self) -> Optional[Article]:
        """Fetch one article from a randomly selected feed, based on weights."""
        if not self.feeds:
            logger.debug("No feeds available in this UnionFeed.")
            self.fetch_failed = True
            return None
        
        weights = [feed.effective_weight() for feed in self.feeds]
        for feed, weight in zip(self.feeds, weights):
            if weight == 0:
                logger.debug(f"Feed {feed.id} ignored because weight is 0.")
        if sum(weights) <= 0:
            self.fetch_failed = True
            return None

        selected_feed = choices(self.feeds, weights=weights, k=1)[0]
        logger.debug(f"Selected feed: {selected_feed.id} with weight: {getattr(selected_feed, 'weight', 10.0)}")
        try:
            article = selected_feed.fetch()
            if article:
                if self.max_age and article.published_date:
                    if datetime.now() - article.published_date > self.max_age:
                        logger.debug(f"Article {article.id} is too old and ignored due to max_age.")
                        return None
                logger.debug(f"Fetched article: {article.id} from feed {selected_feed.id}")
            else:
                logger.debug(f"No article fetched from selected feed: {selected_feed.id}")
            return article
        except Exception as e:
            log_error_with_readkey(f"Error fetching from feed {selected_feed.id}: {e}")
            return None

    @classmethod
    def from_config_dict(cls, config: Dict, article_manager: "ArticleManager", parent_max_age: timedelta, parent_feedpath: List[str]) -> "UnionFeed":
        from .regular_feed import RegularFeed
        from .filter_feed import FilterFeed

        feed_max_age = parse_time_period(config["max_age"]) if "max_age" in config else parent_max_age
        feedpath = (parent_feedpath if parent_feedpath != ["root"] else []) + [config["id"]]
        member_feeds = []
        for member_config in config.get("feeds", []):
            ft = FeedType(member_config["feed_type"])
            if ft == FeedType.REGULAR:
                member_feeds.append(
                    RegularFeed.from_config_dict(member_config, article_manager, feed_max_age, feedpath)
                )
            elif ft == FeedType.UNION:
                member_feeds.append(
                    UnionFeed.from_config_dict(member_config, article_manager, feed_max_age, feedpath)
                )
            elif ft == FeedType.FILTER:
                member_feeds.append(
                    FilterFeed.from_config_dict(member_config, article_manager, feed_max_age, feedpath)
                )
            else:
                logger.warning(f"Unknown feed type {ft} for id {member_config.get('id')}")
        return cls(
            id=config["id"],
            title=config.get("title"),
            description=config.get("description", "No description provided"),
            last_updated=datetime.now(),
            weight=config.get("weight", 10.0),
            feeds=member_feeds,
            max_age=feed_max_age,
            feedpath=feedpath
        )
