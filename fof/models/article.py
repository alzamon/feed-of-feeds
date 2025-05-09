from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class Article:
    """Represents a single article from a feed."""
    id: str
    title: str
    content: str
    link: str
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    feed_id: Optional[str] = None
    feedpath: List[str] = None  # Changed from Optional[str] to List[str]
    read: bool = False
    score: Optional[int] = None
