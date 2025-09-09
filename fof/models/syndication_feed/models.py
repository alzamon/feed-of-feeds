from dataclasses import dataclass
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timedelta
from ..base_feed import BaseFeed
from ..article import Article
from ..enums import FeedType
from ..article_manager import ArticleManager

if TYPE_CHECKING:
    pass


@dataclass
class SyndicationFeed(BaseFeed):
    """A feed that fetches articles from a syndication source (e.g., RSS/Atom)."""
    url: str
    max_age: Optional[timedelta]  # Optional max age for filtering articles
    article_manager: ArticleManager  # ArticleManager instance
    # Optional age after which articles are purged from cache
    purge_age: Optional[timedelta] = None

    @property
    def feed_type(self) -> FeedType:
        return FeedType.SYNDICATION

    def fetch(self) -> Optional[Article]:
        """
        Fetch the first unfetched and unread article using the ArticleManager.
        The fetched article is immediately marked as fetched (not read).
        The article will be marked as read only when displayed.
        """
        article = self.article_manager.fetch_article(
            feedpath=self.feedpath,
            url=self.url,
            feed_id=self.id,
            max_age=self.max_age,
        )
        self.disabled_in_session = article is None
        return article

    def __init__(
        self,
        title: str,
        description: str,
        last_updated: datetime,
        url: str,
        max_age: Optional[timedelta],
        article_manager: ArticleManager,
        feedpath: List[str],
        purge_age: Optional[timedelta] = None,
    ):
        super().__init__(
            title,
            description,
            last_updated,
            feedpath,
            disabled_in_session=False,
        )
        self.url = url
        self.max_age = max_age
        self.article_manager = article_manager
        # Only set purge_age if explicitly provided
        self.purge_age = purge_age
