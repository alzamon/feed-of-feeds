from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from .article import Article
from .enums import FeedType


@dataclass
class BaseFeed(ABC):
    """Abstract base feed class for all feed types."""
    title: str
    description: str
    last_updated: datetime
    # Required parameter to track the path from the root feed to this feed
    feedpath: List[str]
    disabled_in_session: bool

    @property
    def id(self) -> str:
        """
        Return the globally unique qualified ID for this feed.

        The qualified ID is constructed from the feedpath, which contains
        the complete path including this feed's ID. For example, a feed with
        feedpath ['work', 'da', 'cicd'] would have qualified ID
        'work/da/cicd'.

        Returns:
            str: The qualified feed ID from the feedpath
        """
        if not self.feedpath:
            # Root feed case - use a default identifier
            return "root"
        return '/'.join(self.feedpath)

    @property
    def local_id(self) -> str:
        """
        Return the local ID for this feed (last component of the path).

        Returns:
            str: The local feed ID used in configuration files
        """
        if not self.feedpath:
            return "root"
        return self.feedpath[-1]

    @property
    @abstractmethod
    def feed_type(self) -> FeedType:
        """Return the type of this feed."""

    @abstractmethod
    def fetch(self) -> Optional[Article]:
        """
        Fetch a single article from this feed.

        Returns:
            Optional[Article]: The fetched article, or None if no suitable
                article is found or something went wrong.
        """
