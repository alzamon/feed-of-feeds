"""Feed loading functionality."""
import json
import os
import logging
from typing import Optional, List
from datetime import datetime, timedelta

from .models.base_feed import BaseFeed
from .models.union_feed import UnionFeed, WeightedFeed
from .models.syndication_feed import SyndicationFeed
from .models.filter_feed import FilterFeed, Filter
from .models.enums import FilterType
from .time_period import parse_time_period

logger = logging.getLogger(__name__)


class FeedLoader:
    """Handles loading feeds from directory structures and configuration files."""
    
    def __init__(self, article_manager):
        """Initialize with article manager for syndication feeds."""
        self.article_manager = article_manager
    
    def load_feed_from_directory(self, path: str, feedpath: list, parent_max_age=None, is_root=False) -> Optional[BaseFeed]:
        """Load a feed from a directory structure."""
        union_path = os.path.join(path, "union.json")
        filter_path = os.path.join(path, "filter.json")
        feed_path = os.path.join(path, "feed.json")
        
        if os.path.isfile(union_path):
            with open(union_path, "r", encoding="utf-8") as f:
                union_info = json.load(f)
            weights = union_info.get("weights", {})
            subfeeds = []
            union_id = union_info.get("id") if "id" in union_info else os.path.basename(path)
            union_feedpath = feedpath + [union_id] if not is_root else []
            max_age_str = union_info.get("max_age") if "max_age" in union_info else None
            my_max_age = parse_time_period(max_age_str) if isinstance(max_age_str, str) and max_age_str else parent_max_age
            
            # Handle purge_age - only set if explicitly specified in config
            purge_age_str = union_info.get("purge_age")
            my_purge_age = parse_time_period(purge_age_str) if purge_age_str else None
            for sub_name, weight in weights.items():
                sub_path = os.path.join(path, sub_name)
                sub_feed = self.load_feed_from_directory(sub_path, feedpath=union_feedpath, parent_max_age=my_max_age)
                if sub_feed is not None:
                    subfeeds.append(WeightedFeed(feed=sub_feed, weight=weight))
                else:
                    logger.warning(f"Failed to load subfeed {sub_name} in {path}")
            return UnionFeed(
                id=union_id,
                title=union_info.get("title") if "title" in union_info else os.path.basename(path),
                description=union_info.get("description") if "description" in union_info else "",
                feeds=subfeeds,
                last_updated=datetime.fromisoformat(union_info["last_updated"]) if "last_updated" in union_info else datetime.now(),
                max_age=my_max_age,
                feedpath=feedpath,
                purge_age=my_purge_age
            )
        elif os.path.isfile(feed_path):
            with open(feed_path, "r", encoding="utf-8") as f:
                feed_data = json.load(f)
            feed_id = feed_data.get("id")
            max_age_str = feed_data.get("max_age")
            my_max_age = parse_time_period(max_age_str) if isinstance(max_age_str, str) and max_age_str else parent_max_age
            if not my_max_age:
                raise ValueError("Root feed must have a max_age defined")
                
            # Handle purge_age - only set if explicitly specified in config
            purge_age_str = feed_data.get("purge_age")
            my_purge_age = parse_time_period(purge_age_str) if purge_age_str else None
            syndication_feedpath =  feedpath + [feed_id] if not is_root else []
            return SyndicationFeed(
                id=feed_data["id"],
                title=feed_data.get("title"),
                description=feed_data.get("description", "No description provided"),
                last_updated=datetime.fromisoformat(feed_data["last_updated"]) if "last_updated" in feed_data else datetime.now(),
                url=feed_data["url"],
                max_age=my_max_age,
                article_manager=self.article_manager,
                feedpath=syndication_feedpath,
                purge_age=my_purge_age,
            )
        elif os.path.isfile(filter_path):
            with open(filter_path, "r", encoding="utf-8") as f:
                filter_data = json.load(f)
            filter_id = filter_data["id"]
            max_age_str = filter_data.get("max_age")
            my_max_age = parse_time_period(max_age_str) if isinstance(max_age_str, str) and max_age_str else parent_max_age
            if not my_max_age:
                raise ValueError("Root feed must have a max_age defined (inherited)")
                
            # Handle purge_age - only set if explicitly specified in config
            purge_age_str = filter_data.get("purge_age")
            my_purge_age = parse_time_period(purge_age_str) if purge_age_str else None
            filter_feedpath = feedpath + [filter_id] if not is_root else []
            source_path = os.path.join(path, "source")
            source_feed = self.load_feed_from_directory(source_path, feedpath=filter_feedpath, parent_max_age=my_max_age)
            filters = [
                Filter(
                    filter_type=FilterType(c["filter_type"]),
                    pattern=c["pattern"],
                    is_inclusion=c["is_inclusion"]
                ) for c in filter_data["criteria"]
            ]
            return FilterFeed(
                id=filter_id,
                title=filter_data.get("title"),
                description=filter_data.get("description"),
                filters=filters,
                source_feed=source_feed,
                last_updated=datetime.fromisoformat(filter_data["last_updated"]) if "last_updated" in filter_data else datetime.now(),
                max_age=my_max_age,
                feedpath=filter_feedpath,
                purge_age=my_purge_age
            )
        else:
            logger.error(f"Unknown feed directory structure at {path}")
            return None

    def try_load_union_info(self, path: str):
        """Try to load union info from a path."""
        union_path = os.path.join(path, "union.json")
        if os.path.isfile(union_path):
            with open(union_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None