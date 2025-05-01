from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
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
    last_score: Optional[int] = None

    @property
    @abstractmethod
    def feed_type(self) -> FeedType:
        """Return the type of this feed."""
        pass

    @abstractmethod
    def fetch(self) -> Optional[Article]:
        """Fetch a single article from this feed."""
        pass
