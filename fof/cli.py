"""Command-line interface for FoF."""
import argparse
import os
import sys
from .feed_manager import FeedManager
from .control_loop import ControlLoop

DEFAULT_CONFIG_PATH = "~/.config/fof/"

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="FoF - Feed of Feeds")
    
    parser.add_argument(
        "--config", "-c", 
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: ~/.config/fof)"
    )
    
    args = parser.parse_args()
    
    # Initialize feed manager
    feed_manager = FeedManager(args.config)
    
    # Fetch and display the first article
    article = feed_manager.next_article()
    
    # Ensure article is initialized
    if not article:
        print("No unread articles found! Exiting...")
        sys.exit(0)

    # Initialize control loop to handle interactions
    ControlLoop(feed_manager).start()

if __name__ == "__main__":
    main()
