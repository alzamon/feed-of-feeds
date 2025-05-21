"""Command-line interface for FoF."""
import argparse
import os
import sys
import logging
from .models.article_manager import ArticleManager
from .feed_manager import FeedManager
from .control_loop import ControlLoop

DEFAULT_CONFIG_PATH = "~/.config/fof/"

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

    config_path = os.path.expanduser(args.config)
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
    article_manager = ArticleManager(db_path=config_path)
    feed_manager = FeedManager(args.config, article_manager=article_manager)
    
    # Initialize control loop to handle interactions
    ControlLoop(feed_manager, article_manager).start()
    feed_manager.save_config()

if __name__ == "__main__":
    main()
