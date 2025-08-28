"""Command-line interface for FoF."""
import argparse
import os
import sys
import logging
from .models.article_manager import ArticleManager
from .feed_manager import FeedManager
from .control_loop import ControlLoop
from .config_manager import ConfigManager
from .sync import SyncManager, DevicePreparationManager

try:
    import argcomplete
except ImportError:
    argcomplete = None

try:
    from colorama import init, Fore, Back, Style
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
        COLORS_AVAILABLE and 
        hasattr(sys.stdout, 'isatty') and 
        sys.stdout.isatty() and
        os.getenv('NO_COLOR') is None
    )

def _colorize(text, color_code, style_code=''):
    """Apply color to text if colors are available and appropriate."""
    if _should_use_color():
        return f"{style_code}{color_code}{text}{Style.RESET_ALL}"
    return text

def print_feed_paths(feed_manager, base_feed=None):
    """
    Recursively print all feed paths from the given base feed, and the product of
    likelihoods for WeightedFeeds along each path.
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
            # Color the feed path in bold cyan
            feed_path_text = " -> ".join(feedpath)
            colored_feed_path = _colorize(feed_path_text, Fore.CYAN, Style.BRIGHT)
            print(colored_feed_path)
            
            # Color the URL in green
            url_text = url if url else "(no url)"
            colored_url = _colorize(url_text, Fore.GREEN)
            print("  " + colored_url)
            
            # Color the likelihood percentage in yellow
            likelihood_pct = ctx.get("likelihood", 1.0) * PERCENTAGE_MULTIPLIER
            likelihood_text = "Cumulative likelihood: {:.2f}%".format(likelihood_pct)
            colored_likelihood = _colorize(likelihood_text, Fore.YELLOW)
            print("  " + colored_likelihood)

    root = base_feed if base_feed is not None else getattr(feed_manager, "root_feed", None)
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
    feeds_list_parser.add_argument(
        "--feed",
        default=None,
        help="Only show feeds under the selected feed id"
    )

    # Cache subcommand
    cache_parser = subparsers.add_parser("cache", help="Cache management utilities")
    cache_subparsers = cache_parser.add_subparsers(dest="cache_command")

    cache_clear_parser = cache_subparsers.add_parser("clear", help="Clear the article cache for all syndication feeds under a feed")
    cache_clear_parser.add_argument(
        "--config", "-c", 
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: ~/.config/fof)"
    )
    cache_clear_parser.add_argument(
        "--feed",
        required=True,
        help="Feed ID under which to clear the cache for all syndication feeds"
    )

    # Sync subcommand
    sync_parser = subparsers.add_parser("sync", help="Multi-device synchronization utilities")
    sync_subparsers = sync_parser.add_subparsers(dest="sync_command")

    # Sync status
    sync_status_parser = sync_subparsers.add_parser("status", help="Show sync status and peer connectivity")
    sync_status_parser.add_argument(
        "--config", "-c", 
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: ~/.config/fof)"
    )

    # Sync now (manual sync)
    sync_now_parser = sync_subparsers.add_parser("now", help="Perform manual sync with all peers")
    sync_now_parser.add_argument(
        "--config", "-c", 
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: ~/.config/fof)"
    )

    # Peer management
    peer_parser = sync_subparsers.add_parser("peer", help="Manage sync peers")
    peer_subparsers = peer_parser.add_subparsers(dest="peer_command")

    # Add peer
    peer_add_parser = peer_subparsers.add_parser("add", help="Add a new sync peer")
    peer_add_parser.add_argument("device_name", help="Name for the peer device")
    peer_add_parser.add_argument("host", help="Hostname or IP address")
    peer_add_parser.add_argument("user", help="Username for SSH connection")
    peer_add_parser.add_argument("--port", type=int, default=22, help="SSH port (default: 22)")
    peer_add_parser.add_argument(
        "--config", "-c", 
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: ~/.config/fof)"
    )

    # Remove peer
    peer_remove_parser = peer_subparsers.add_parser("remove", help="Remove a sync peer")
    peer_remove_parser.add_argument("device_name", help="Name of the peer device to remove")
    peer_remove_parser.add_argument(
        "--config", "-c", 
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: ~/.config/fof)"
    )

    # List peers
    peer_list_parser = peer_subparsers.add_parser("list", help="List all configured peers")
    peer_list_parser.add_argument(
        "--config", "-c", 
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: ~/.config/fof)"
    )

    # Device management
    device_parser = sync_subparsers.add_parser("device", help="Manage device settings")
    device_subparsers = device_parser.add_subparsers(dest="device_command")

    # Set device name
    device_name_parser = device_subparsers.add_parser("name", help="Get or set device name")
    device_name_parser.add_argument("name", nargs="?", help="New device name (if not provided, shows current name)")
    device_name_parser.add_argument(
        "--config", "-c", 
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: ~/.config/fof)"
    )

    # Device preparation
    device_prep_parser = device_subparsers.add_parser("prepare", help="Prepare device for syncing (SSH setup)")
    device_prep_parser.add_argument(
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
    parser.add_argument(
        "--feed",
        default=None,
        help="Scope down to the selected feed and its descendants"
    )

    # Enable tab-completion if argcomplete is installed
    if argcomplete:
        argcomplete.autocomplete(parser)

    args = parser.parse_args()

    # Get config path - prefer command-specific config if provided, otherwise use global
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
    feed_manager = FeedManager(
        article_manager=article_manager,
        config_manager=config_manager,
        feed_id=getattr(args, "feed", None)
    )

    # Handle subcommands
    if args.command == "feeds" and getattr(args, "feeds_command", None) == "list":
        feed_id = getattr(args, "feed", None)
        base_feed = None
        if feed_id:
            base_feed = feed_manager.get_feed_by_id(feed_id)
            if base_feed is None:
                print(f"Feed with id '{feed_id}' not found.")
                sys.exit(1)
        print_feed_paths(feed_manager, base_feed=base_feed)
        sys.exit(0)

    if args.command == "cache" and getattr(args, "cache_command", None) == "clear":
        # Find the feed by id (any type)
        feed_id = getattr(args, "feed", None)
        selected_feed = feed_manager.get_feed_by_id(feed_id)
        if selected_feed is None:
            print(f"Feed with id '{feed_id}' not found.")
            sys.exit(1)

        from .models.syndication_feed import SyndicationFeed

        total_deleted = 0

        def clear_if_syndication(feed, ctx):
            nonlocal total_deleted
            if isinstance(feed, SyndicationFeed):
                deleted = article_manager.clear_cache(feed)
                print(f"Cleared {deleted} articles from cache for syndication feed '{feed.id}'.")
                total_deleted += deleted

        feed_manager.perform_on_feeds(selected_feed, clear_if_syndication)
        print(f"Total articles cleared: {total_deleted}")
        sys.exit(0)

    # Handle sync subcommands
    if args.command == "sync":
        sync_manager = SyncManager(article_manager, config_path)
        
        if getattr(args, "sync_command", None) == "status":
            status = sync_manager.get_sync_status()
            print(f"Device name: {status['device_name']}")
            print(f"Config path: {status['config_path']}")
            print(f"Configured peers: {status.get('peer_count', 0)}")
            
            if 'peers' in status:
                print("\nPeer status:")
                for device_name, peer_info in status['peers'].items():
                    reachable = "✓" if peer_info['reachable'] else "✗"
                    print(f"  {reachable} {device_name}: {peer_info['user']}@{peer_info['host']}:{peer_info['port']}")
            
            if 'error' in status:
                print(f"Error: {status['error']}")
            sys.exit(0)
            
        elif getattr(args, "sync_command", None) == "now":
            print("Starting manual sync...")
            stats = sync_manager.manual_sync()
            print(f"Sync completed:")
            print(f"  - Pulled from {stats['pulled_peers']} peers")
            print(f"  - Merged {stats['merged_articles']} articles")
            print(f"  - Pushed to {stats['pushed_peers']} peers")
            sys.exit(0)
            
        elif getattr(args, "sync_command", None) == "peer":
            peer_command = getattr(args, "peer_command", None)
            
            if peer_command == "add":
                sync_manager.add_peer(args.device_name, args.host, args.user, args.port)
                print(f"Added peer: {args.device_name}")
                sys.exit(0)
                
            elif peer_command == "remove":
                if sync_manager.remove_peer(args.device_name):
                    print(f"Removed peer: {args.device_name}")
                else:
                    print(f"Peer not found: {args.device_name}")
                    sys.exit(1)
                sys.exit(0)
                
            elif peer_command == "list":
                peers = sync_manager.list_peers()
                if peers:
                    print("Configured peers:")
                    for device_name, peer in peers.items():
                        print(f"  {device_name}: {peer.user}@{peer.host}:{peer.port}")
                else:
                    print("No peers configured.")
                sys.exit(0)
                
        elif getattr(args, "sync_command", None) == "device":
            device_command = getattr(args, "device_command", None)
            
            if device_command == "name":
                if hasattr(args, 'name') and args.name:
                    sync_manager.set_device_name(args.name)
                    print(f"Device name set to: {args.name}")
                else:
                    current_name = sync_manager.get_device_name()
                    print(f"Current device name: {current_name}")
                sys.exit(0)
                
            elif device_command == "prepare":
                prep_manager = DevicePreparationManager()
                peers = list(sync_manager.list_peers().values())
                
                print("Preparing device for multi-device sync...")
                success = prep_manager.prepare_device_interactive(peers)
                
                if success:
                    print("Device preparation completed successfully!")
                    sys.exit(0)
                else:
                    print("Device preparation failed.")
                    sys.exit(1)
    
    # Initialize sync manager for startup sync
    sync_manager = SyncManager(article_manager, config_path)
    sync_manager.sync_on_startup()
    
    # Initialize control loop to handle interactions
    ControlLoop(feed_manager, article_manager).start()
    
    # Perform exit sync
    sync_manager.sync_on_exit()
    
    # Purge old articles before saving config and exiting
    feed_manager.purge_old_articles()
    
    feed_manager.save_config()

if __name__ == "__main__":
    main()
