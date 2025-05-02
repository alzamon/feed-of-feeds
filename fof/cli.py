"""Command-line interface for FoF."""
import argparse
import os
import sys
from datetime import datetime
from .feed_manager import FeedManager
from .models.enums import FeedType

DEFAULT_CONFIG_PATH = "~/.config/fof/config.yaml"

def display_feed_tree(feed, indent=0, max_depth=None):
    """Recursively display feed information as a tree."""
    if max_depth is not None and indent // 4 >= max_depth:
        return

    prefix = " " * indent
    feed_type_str = feed.feed_type.value.capitalize()
    print(f"{prefix}- {feed.id}: {feed.title} ({feed_type_str}, weight: {feed.weight})")
    
    if feed.feed_type == FeedType.REGULAR:
        print(f"{prefix}  URL: {feed.url}")
        if feed.last_updated:
            print(f"{prefix}  Last updated: {feed.last_updated}")
    
    elif feed.feed_type == FeedType.UNION and (max_depth is None or indent // 4 + 1 < max_depth):
        for sub_feed in feed.feeds:
            display_feed_tree(sub_feed, indent + 4, max_depth)
    
    elif feed.feed_type == FeedType.FILTER:
        print(f"{prefix}  Source Feed:")
        display_feed_tree(feed.source_feed, indent + 4, max_depth)
        if feed.filters:
            print(f"{prefix}  Filters:")
            for f in feed.filters:
                inclusion_str = "Include" if f.is_inclusion else "Exclude"
                print(f"{prefix}    - {inclusion_str} {f.filter_type.value}: {f.pattern}")

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="FoF - Feed of Feeds")
    
    parser.add_argument(
        "--config", "-c", 
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: ~/.config/fof/config.yaml)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # next command
    next_parser = subparsers.add_parser("next", help="Get next article")
    
    # refresh command
    refresh_parser = subparsers.add_parser("refresh", help="Refresh feeds")
    
    # add command
    add_parser = subparsers.add_parser("add", help="Add a new feed")
    add_parser.add_argument("url", help="URL of the feed")
    add_parser.add_argument("--id", help="ID for the feed (default: auto-generated)")
    add_parser.add_argument("--title", help="Title for the feed (default: from feed)")
    add_parser.add_argument("--weight", type=float, default=1.0, help="Weight for the feed")
    
    # list command
    list_parser = subparsers.add_parser("list", help="List feeds")
    list_parser.add_argument(
        "--depth", "-d", type=int, default=None,
        help="Maximum depth to display (default: unlimited)"
    )
    
    args = parser.parse_args()
    
    # Initialize feed manager
    manager = FeedManager(args.config)
    
    # Handle commands
    if args.command == "next":
        article = manager.next_article()
        if article:
            print(f"Title: {article.title}")
            print(f"Link: {article.link}")
            print(f"Author: {article.author or 'Unknown'}")
            print(f"Published: {article.published_date or 'Unknown date'}")
            print("\nContent Preview:")
            print("---------------")
            preview = article.content[:200] + "..." if len(article.content) > 200 else article.content
            print(preview)
            
        else:
            print("No unread articles found!")
            
    elif args.command == "refresh":
        print("Refreshing feeds...")
        manager.refresh_feeds()
        print("Done!")
        
    elif args.command == "add":
        print(f"Adding feed: {args.url}")
        # manager.add_feed(args.id, args.url, args.title, args.weight)
        
    elif args.command == "list":
        print("Available feeds (Tree View):")
        print("===========================")
        display_feed_tree(manager.root_feed, max_depth=args.depth)
    
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
