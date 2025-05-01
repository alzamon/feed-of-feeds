from enum import Enum

class FeedType(Enum):
    """Types of feeds in the system."""
    REGULAR = "regular"
    UNION = "union"
    FILTER = "filter"

class FilterType(Enum):
    """Types of filters that can be applied to feeds."""
    TITLE_REGEX = "title_regex"
    CONTENT_REGEX = "content_regex"
    AUTHOR = "author"
    LINK_REGEX = "link_regex"
