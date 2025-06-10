"""Command-line interface for FoF."""
import argparse
import os
import sys
import logging
from .models.article_manager import ArticleManager
from .feed_manager import FeedManager
from .control_loop import ControlLoop
from .config_manager import ConfigManager

DEFAULT_CONFIG_PATH = "~/.config/fof/"

def print_feed_paths(feed_manager):
    """
    Recursively print all feed paths from the root, and the product of likelihoods for WeightedFeeds along each path.
    Weights are interpreted as percentages and converted to fractions.
    Uses FeedManager.perform_on_feeds with context for accumulation.
    """
    def print_feed(feed, ctx):
        # Only print at leaf feeds (no children)
        is_leaf = not (
            hasattr(feed, "feeds") or
            (hasattr(feed, "source_feed") and feed.source_feed is not None) or
            (hasattr(feed, "feed") and feed.feed is not None)
        )
        feedpath = getattr(feed, "feedpath", [])
        url = getattr(feed, "url", None)
        if is_leaf:
            print(" -> ".join(feedpath))
            print("  " + (url if url else "(no url)"))
            print("  Cumulative likelihood: {:.2f}%".format(ctx.get("likelihood", 1.0) * 100.0))

    if getattr(feed_manager, "root_feed", None):
        feed_manager.perform_on_feeds(
            feed_manager.root_feed,
            print_feed,
            context={"likelihood": 1.0}
        )
    else:
        print("No root feed loaded.")

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="FoF - Feed of Feeds")

    subparsers = parser.add_subparsers(dest="command")

    # Logs subcommand
    logs_parser = subparsers.add_parser("logs", help="Print the log file and exit")
    logs_parser.add_argument(
        "--config", "-c", 
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: ~/.config/fof)"
    )

    # Feeds subcommand
    feeds_parser = subparsers.add_parser("feeds", help="Feed tree utilities")
    feeds_subparsers = feeds_parser.add_subparsers(dest="feeds_command")

    feeds_list_parser = feeds_subparsers.add_parser("list", help="List all feed paths")
    feeds_list_parser.add_argument(
        "--config", "-c", 
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: ~/.config/fof)"
    )

    # Global arguments for default mode (control loop)
    parser.add_argument(
        "--config", "-c", 
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: ~/.config/fof)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    config_path = os.path.expanduser(getattr(args, "config", DEFAULT_CONFIG_PATH))
    log_file = os.path.join(config_path, "fof.log")
    os.makedirs(config_path, exist_ok=True)

    if args.command == "logs":
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                print(f.read())
        else:
            print(f"Log file does not exist at {log_file}")
        sys.exit(0)

    # Set up root logger
    handlers = []
    file_handler = logging.FileHandler(log_file, mode="a")
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    ))
    handlers.append(file_handler)

    if getattr(args, "verbose", False):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        ))
        handlers.append(console_handler)

    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        handlers=handlers
    )
    logging.info("Logging started.")

    # Initialize article manager and feed manager
    config_manager = ConfigManager(config_path=config_path)
    article_manager = ArticleManager(config_manager=config_manager)
    feed_manager = FeedManager(article_manager=article_manager, config_manager=config_manager)

    # Handle subcommands
    if args.command == "feeds" and getattr(args, "feeds_command", None) == "list":
        print_feed_paths(feed_manager)
        sys.exit(0)
    
    # Initialize control loop to handle interactions
    ControlLoop(feed_manager, article_manager).start()
    feed_manager.save_config()

if __name__ == "__main__":
    main()
