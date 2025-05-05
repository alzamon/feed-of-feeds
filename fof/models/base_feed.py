from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from .article import Article
from .enums import FeedType

@dataclass
class BaseFeed(ABC):
    """Abstract base feed class for all feed types."""
    id: str
    title: str
    description: Optional[str] = None
    last_updated: Optional[datetime] = None
    weight: float = 1.0

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
