import logging
from dataclasses import dataclass, field
from typing import List, Optional, Pattern, Dict, TYPE_CHECKING
import re
from datetime import timedelta, datetime
from .article import Article
from .enums import FilterType, FeedType
from .base_feed import BaseFeed
from ..time_period import parse_time_period

if TYPE_CHECKING:
    from .regular_feed import RegularFeed
    from .union_feed import UnionFeed
    from .article_manager import ArticleManager

logger = logging.getLogger(__name__)

@dataclass
class Filter:
    """A filter to include or exclude articles."""
    filter_type: FilterType
    pattern: str
    is_inclusion: bool = True  # True = keep matches, False = exclude matches
    compiled_pattern: Optional[Pattern] = None

    def __post_init__(self):
        if self.filter_type in (FilterType.TITLE_REGEX, 
                               FilterType.CONTENT_REGEX, 
                               FilterType.LINK_REGEX):
            self.compiled_pattern = re.compile(self.pattern)

    def matches(self, article: Article) -> bool:
        matchers = {
            FilterType.TITLE_REGEX: lambda: self.compiled_pattern.search(article.title),
            FilterType.CONTENT_REGEX: lambda: self.compiled_pattern.search(article.content),
            FilterType.AUTHOR: lambda: self.pattern == article.author,
            FilterType.LINK_REGEX: lambda: self.compiled_pattern.search(article.link),
        }
        matcher = matchers.get(self.filter_type)
        return bool(matcher()) if matcher else False

@dataclass
class FilterFeed(BaseFeed):
    """A feed that filters articles from another feed."""
    source_feed: BaseFeed
    filters: List[Filter] = field(default_factory=list)
    max_age: Optional[timedelta] = None  # Optional max age for filtering articles

    def __init__(self, id: str, title: str, description: str, last_updated: datetime, weight: float, 
                 source_feed: BaseFeed, filters: List[Filter], max_age: Optional[timedelta], feedpath: List[str]):
        super().__init__(id, title, description, last_updated, weight, feedpath, fetch_failed=False)
        self.source_feed = source_feed
        self.filters = filters or []
        self.max_age = max_age

    @property
    def feed_type(self) -> FeedType:
        return FeedType.FILTER

    def add_filter(self, filter_type: FilterType, pattern: str, is_inclusion: bool = True):
        self.filters.append(Filter(filter_type, pattern, is_inclusion))

    def fetch(self) -> Optional[Article]:
        """
        Fetches the next unfetched, unread article from the source feed that passes all filters.
        The fetched article is marked as fetched by the underlying RegularFeed/ArticleManager.
        Only articles not yet fetched (and not read) are considered.
        """
        if self.source_feed.effective_weight() == 0:
            self.fetch_failed = True
            return None
        while True:
            article = self.source_feed.fetch()
            if not article:
                self.fetch_failed = True
                return None
            if self.max_age and article.published_date:
                if datetime.now() - article.published_date > self.max_age:
                    continue
            logger.debug(f"Filtering article: {article}")
            should_include = all(
                f.is_inclusion == f.matches(article) for f in self.filters
            )
            if should_include:
                return article
            # If article does not pass, continue to fetch the next unfetched article

    @classmethod
    def from_config_dict(cls, config: Dict, article_manager: "ArticleManager", parent_max_age: timedelta, parent_feedpath: List[str]) -> "FilterFeed":
        from .regular_feed import RegularFeed
        from .union_feed import UnionFeed

        feed_max_age = parse_time_period(config["max_age"]) if "max_age" in config else parent_max_age
        feedpath = (parent_feedpath if parent_feedpath != ["root"] else []) + [config["id"]]
        # Construct the source feed first
        source_config = config["feed"]
        ft = FeedType(source_config["feed_type"])
        if ft == FeedType.REGULAR:
            source_feed = RegularFeed.from_config_dict(source_config, article_manager, feed_max_age, feedpath)
        elif ft == FeedType.UNION:
            source_feed = UnionFeed.from_config_dict(source_config, article_manager, feed_max_age, feedpath)
        elif ft == FeedType.FILTER:
            source_feed = FilterFeed.from_config_dict(source_config, article_manager, feed_max_age, feedpath)
        else:
            logger.warning(f"Unknown feed type {ft} for id {source_config.get('id')}")
            source_feed = None

        filters = []
        for criterion in config.get("criteria", []):
            filters.append(
                Filter(
                    filter_type=FilterType(criterion["filter_type"]),
                    pattern=criterion["pattern"],
                    is_inclusion=criterion.get("is_inclusion", True)
                )
            )
        return cls(
            id=config["id"],
            title=config.get("title"),
            description=config.get("description", "No description provided"),
            last_updated=datetime.now(),
            weight=config.get("weight", 10.0),
            source_feed=source_feed,
            filters=filters,
            max_age=feed_max_age,
            feedpath=feedpath
        )
