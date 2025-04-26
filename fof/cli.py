"""Command-line interface for FoF."""
import argparse
import os
import sys
from datetime import datetime
from .feed_manager import FeedManager

DEFAULT_CONFIG_PATH = "~/.config/fof/config.yaml"

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
    
    # List command
    list_parser = subparsers.add_parser("list", help="List feeds")
    
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
            
            # Prompt for score
            try:
                score = input("\nEnter score (0-100, default 0): ")
                if score.strip():
                    score = int(score.strip())
                    manager.score_article(article.id, score)
                else:
                    manager.score_article(article.id, 0)
            except ValueError:
                print("Invalid score, using 0")
                manager.score_article(article.id, 0)
        else:
            print("No unread articles found!")
            
    elif args.command == "refresh":
        print("Refreshing feeds...")
        manager.refresh_feeds()
        print("Done!")
        
    elif args.command == "add":
        # TODO: Implement add command
        print(f"Adding feed: {args.url}")
        # manager.add_feed(args.id, args.url, args.title, args.weight)
        
    elif args.command == "list":
        print("Available feeds:")
        print("================")
        for feed_id, feed in manager.feeds.items():
            feed_type_str = feed.feed_type.value.capitalize()
            print(f"- {feed_id}: {feed.title} ({feed_type_str}, weight: {feed.weight})")
            print(f"  URL: {feed.url}")
            if feed.last_updated:
                print(f"  Last updated: {feed.last_updated}")
    
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
