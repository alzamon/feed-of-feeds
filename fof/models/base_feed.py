from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List
from .article import Article
from .enums import FeedType

@dataclass
class BaseFeed(ABC):
    """Abstract base feed class for all feed types."""
    id: str
    title: str
    description: str
    last_updated: datetime
    weight: float
    feedpath: List[str]  # Required parameter to track the path from the root feed to this feed

    @property
    @abstractmethod
    def feed_type(self) -> FeedType:
        """Return the type of this feed."""
        pass

    @abstractmethod
    def fetch(self, max_age: Optional[timedelta] = None) -> Optional[Article]:
        """
        Fetch a single article from this feed.

        Args:
            max_age (Optional[timedelta]): Ignore articles older than this age.

        Returns:
            Optional[Article]: The fetched article, or None if no suitable article is found.
        """
        pass
