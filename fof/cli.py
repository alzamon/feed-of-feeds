"""Command-line interface for FoF."""
import argparse
import os
import sys
import logging
from .models.article_manager import ArticleManager
from .feed_manager import FeedManager
from .control_loop import ControlLoop
from .config_manager import ConfigManager
from .time_period import parse_time_period

try:
    import argcomplete
except ImportError:
    argcomplete = None

try:
    from colorama import init, Fore, Style
    # Initialize colorama for cross-platform color support
    init()
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False

DEFAULT_CONFIG_PATH = "~/.config/fof/"

# Constants for percentage calculations
PERCENTAGE_MULTIPLIER = 100.0


def _should_use_color():
    """Check if we should use colors for output."""
    return (
        COLORS_AVAILABLE
        and hasattr(sys.stdout, 'isatty')
        and sys.stdout.isatty()
        and os.getenv('NO_COLOR') is None
    )


def _colorize(text, color_code, style_code=''):
    """Apply color to text if colors are available and appropriate."""
    if _should_use_color():
        return f"{style_code}{color_code}{text}{Style.RESET_ALL}"
    return text


def print_feed_paths(feed_manager, base_feed=None):
    """
    Recursively print all feed paths from the given base feed, and the
    product of likelihoods for WeightedFeeds along each path.
    """
    def print_feed(feed, ctx):
        # Only print at leaf feeds (no children)
        is_leaf = not (
            hasattr(feed, "feeds") or (
                hasattr(feed, "source_feed") and
                feed.source_feed is not None
            ) or (
                hasattr(feed, "feed") and feed.feed is not None
            )
        )
        feedpath = getattr(feed, "feedpath", [])
        url = getattr(feed, "url", None)
        if is_leaf:
            # Color the feed path in bold cyan
            feed_path_text = " -> ".join(feedpath)
            colored_feed_path = _colorize(
                feed_path_text, Fore.CYAN, Style.BRIGHT
            )
            print(colored_feed_path)

            # Color the URL in green
            url_text = url if url else "(no url)"
            colored_url = _colorize(url_text, Fore.GREEN)
            print("  " + colored_url)

            # Color the likelihood percentage in yellow
            likelihood_pct = (
                ctx.get("likelihood", 1.0) * PERCENTAGE_MULTIPLIER
            )
            likelihood_text = "Cumulative likelihood: {:.2f}%".format(
                likelihood_pct
            )
            colored_likelihood = _colorize(likelihood_text, Fore.YELLOW)
            print("  " + colored_likelihood)

    root = (
        base_feed if base_feed is not None
        else getattr(feed_manager, "root_feed", None)
    )
    if root:
        feed_manager.perform_on_feeds(
            root,
            print_feed,
            context={"likelihood": 1.0}
        )
    else:
        no_feed_text = "No root feed loaded."
        colored_no_feed = _colorize(no_feed_text, Fore.RED)
        print(colored_no_feed)


def parse_session_timeout(timeout_value):
    """Parse session timeout value. Returns seconds or raises ValueError."""
    if timeout_value == 0 or timeout_value == "0":
        return 0  # Disabled
    
    try:
        # Support both time period strings ("5m", "1h") and plain numbers
        if (isinstance(timeout_value, str) and
                any(c in timeout_value for c in 'dhms')):
            return int(parse_time_period(timeout_value).total_seconds())
        else:
            # Legacy support: plain number assumed to be minutes
            minutes = int(timeout_value)
            if minutes < 0:
                raise ValueError("Session timeout cannot be negative")
            return minutes * 60
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid session timeout value: {timeout_value}")


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="FoF - Feed of Feeds")

    subparsers = parser.add_subparsers(dest="command")

    # Logs subcommand
    logs_parser = subparsers.add_parser(
        "logs", help="Print the log file and exit"
    )
    logs_parser.add_argument(
        "--config", "-c",
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: ~/.config/fof)"
    )

    # Feeds subcommand
    feeds_parser = subparsers.add_parser(
        "feeds", help="Feed tree utilities"
    )
    feeds_subparsers = feeds_parser.add_subparsers(dest="feeds_command")

    feeds_list_parser = feeds_subparsers.add_parser(
        "list", help="List all feed paths"
    )
    feeds_list_parser.add_argument(
        "--config", "-c",
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: ~/.config/fof)"
    )
    feeds_list_parser.add_argument(
        "--feed",
        default=None,
        help="Only show feeds under the selected feed id"
    )

    # Cache subcommand
    cache_parser = subparsers.add_parser(
        "cache", help="Cache management utilities"
    )
    cache_subparsers = cache_parser.add_subparsers(dest="cache_command")

    cache_clear_parser = cache_subparsers.add_parser(
        "clear",
        help="Clear the article cache for all syndication feeds under a feed"
    )
    cache_clear_parser.add_argument(
        "--config", "-c",
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: ~/.config/fof)"
    )
    cache_clear_parser.add_argument(
        "--feed",
        required=True,
        help=("Feed ID under which to clear the cache for "
              "all syndication feeds")
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
    parser.add_argument(
        "--feed",
        default=None,
        help="Scope down to the selected feed and its descendants"
    )
    parser.add_argument(
        "--session-timeout",
        default=None,
        help=("Session timeout (e.g., '5m', '1h', '30s', or plain number "
              "in minutes; 0 to disable, default: 5m)")
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help=(
            "Use the classic terminal (curses) UI "
            "instead of the web UI"
        )
    )

    # Enable tab-completion if argcomplete is installed
    if argcomplete:
        argcomplete.autocomplete(parser)

    args = parser.parse_args()

    # Get config path - prefer command-specific config if provided,
    # otherwise use global
    config_path = os.path.expanduser(
        getattr(args, "config", DEFAULT_CONFIG_PATH)
    )
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
        level=(
            logging.DEBUG if getattr(args, "verbose", False)
            else logging.INFO
        ),
        handlers=handlers
    )
    logging.info("Logging started.")

    # Initialize managers
    config_manager = ConfigManager(config_path=config_path)
    article_manager = ArticleManager(config_manager=config_manager)
    feed_manager = FeedManager(
        article_manager=article_manager,
        config_manager=config_manager,
        feed_id=getattr(args, "feed", None)
    )

    # Handle session timeout configuration
    session_timeout_arg = getattr(args, "session_timeout", None)
    if session_timeout_arg is not None:
        try:
            session_timeout_seconds = parse_session_timeout(session_timeout_arg)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        # Use timeout from config file (defaults to 5m if not set)
        session_timeout_seconds = config_manager.get_session_timeout_seconds()

    # Handle subcommands
    if (args.command == "feeds" and
            getattr(args, "feeds_command", None) == "list"):
        feed_id = getattr(args, "feed", None)
        base_feed = None
        if feed_id:
            base_feed = feed_manager.get_feed_by_id(feed_id)
            if base_feed is None:
                print(f"Feed with id '{feed_id}' not found.")
                sys.exit(1)
        print_feed_paths(feed_manager, base_feed=base_feed)
        sys.exit(0)

    if (args.command == "cache" and
            getattr(args, "cache_command", None) == "clear"):
        # Find the feed by id (any type)
        feed_id = getattr(args, "feed", None)
        if feed_id is None:
            print(
                "Error: --feed argument is required for cache clear command."
            )
            sys.exit(1)
        selected_feed = feed_manager.get_feed_by_id(feed_id)
        if selected_feed is None:
            print(f"Feed with id '{feed_id}' not found.")
            sys.exit(1)

        from .models.syndication_feed.models import SyndicationFeed

        total_deleted = 0

        def clear_if_syndication(feed, ctx):
            nonlocal total_deleted
            if isinstance(feed, SyndicationFeed):
                deleted = article_manager.clear_cache(feed)
                print(
                    f"Cleared {deleted} articles from cache for "
                    f"syndication feed '{feed.id}'."
                )
                total_deleted += deleted

        feed_manager.perform_on_feeds(selected_feed, clear_if_syndication)
        print(f"Total articles cleared: {total_deleted}")
        sys.exit(0)

    # Initialize UI to handle interactions
    if getattr(args, "tui", False):
        control_loop = ControlLoop(
            feed_manager, article_manager,
            session_timeout=session_timeout_seconds
        )
        control_loop.start()

        # Purge old articles before saving config and exiting
        feed_manager.purge_old_articles()

        feed_manager.save_config()
    else:
        from .web_ui import WebUI
        web_ui = WebUI(
            feed_manager, article_manager,
            session_timeout=session_timeout_seconds
        )
        web_ui.start()
        # purge_old_articles and save_config are called
        # inside WebUI._shutdown()


if __name__ == "__main__":
    main()
