import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, TYPE_CHECKING
from random import choices
from datetime import timedelta, datetime
from .base_feed import BaseFeed
from .article import Article
from .enums import FeedType
from ..time_period import parse_time_period

if TYPE_CHECKING:
    from .syndication_feed import SyndicationFeed
    from .filter_feed import FilterFeed

logger = logging.getLogger(__name__)

@dataclass
class WeightedFeed:
    feed: BaseFeed
    weight: float

    @property
    def effective_weight(self) -> float:
        return self.weight if not self.feed.disabled_in_session else 0.0

@dataclass
class UnionFeed(BaseFeed):
    feeds: List[WeightedFeed] = field(default_factory=list)
    max_age: Optional[timedelta] = None
    purge_age: Optional[timedelta] = None  # Optional age after which articles are purged from cache

    @property
    def feed_type(self) -> FeedType:
        return FeedType.UNION

    def __init__(
        self,
        id: str,
        title: Optional[str],
        description: str,
        last_updated: datetime,
        feeds: List[WeightedFeed],
        max_age: Optional[timedelta],
        feedpath: List[str],
        purge_age: Optional[timedelta] = None,
    ):
        super().__init__(id, title, description, last_updated, feedpath, disabled_in_session=False)
        self.feeds = feeds
        self.max_age = max_age
        # Only set purge_age if explicitly provided
        self.purge_age = purge_age
        self.normalize_weights()

    def add_feed(self, feed: BaseFeed, weight: float):
        self.feeds.append(WeightedFeed(feed, weight))
        self.normalize_weights()

    def normalize_weights(self):
        """
        Normalize the persisted weights of subfeeds so that their sum is 100.
        This does NOT consider effective_weight (which is session-only).
        """
        total = sum(wf.weight for wf in self.feeds)
        if total == 0:
            if self.feeds:
                for wf in self.feeds:
                    wf.weight = 100.0 / len(self.feeds)
        else:
            for wf in self.feeds:
                wf.weight = (wf.weight / total) * 100.0

    def fetch(self) -> Optional[Article]:
        """
        Fetch one article from a randomly selected feed, using effective_weight to avoid failing feeds.
        """
        if not self.feeds:
            logger.debug("No feeds available in this UnionFeed.")
            self.disabled_in_session = True
            return None

        effective_weights = [wf.effective_weight for wf in self.feeds]
        if sum(effective_weights) <= 0:
            logger.debug("All subfeeds failed or have zero weight.")
            self.disabled_in_session = True
            return None

        sampled_indices = list(range(len(self.feeds)))
        first_idx = choices(sampled_indices, weights=effective_weights, k=1)[0]
        try_indices = [first_idx] + [i for i in sampled_indices if i != first_idx]

        for i in try_indices:
            wf = self.feeds[i]
            if wf.effective_weight == 0:
                logger.debug(f"Skipping feed {wf.feed.id} due to disabled_in_session or zero weight.")
                continue
            selected_feed = wf.feed
            logger.debug(f"Trying feed: {selected_feed.id} with effective weight: {wf.effective_weight}")
            try:
                article = selected_feed.fetch()
                if article:
                    if self.max_age and article.published_date:
                        if datetime.now() - article.published_date > self.max_age:
                            logger.debug(f"Article {article.id} is too old and ignored due to max_age.")
                            continue
                    logger.debug(f"Fetched article: {article.id} from feed {selected_feed.id}")
                    self.disabled_in_session = False
                    return article
                else:
                    logger.debug(f"No article fetched from feed: {selected_feed.id}")
            except Exception as e:
                logger.error(f"Error fetching from feed {selected_feed.id}: {e}")
                continue
        self.disabled_in_session = True
        return None
