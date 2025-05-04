"""Command-line interface for FoF."""
import argparse
import os
import sys
import curses
from .feed_manager import FeedManager
from .models.enums import FeedType

DEFAULT_CONFIG_PATH = "~/.config/fof/config.yaml"

def display_article(article):
    """Return article details as a string."""
    if article:
        result = []
        result.append(f"Title: {article.title}")
        result.append(f"Link: {article.link}")
        result.append(f"Author: {article.author or 'Unknown'}")
        result.append(f"Published: {article.published_date or 'Unknown date'}")
        result.append("")
        result.append("Content Preview:")
        result.append("---------------")
        preview = article.content[:200] + "..." if len(article.content) > 200 else article.content
        result.append(preview)
        return "\n".join(result)
    else:
        return "No unread articles found!"

def handle_key_input(manager, article):
    """Handle user key inputs for article actions using curses."""
    def main(stdscr):
        # Hide the cursor
        curses.curs_set(0)
        stdscr.nodelay(True)  # Make getch() non-blocking
        stdscr.timeout(100)  # Timeout for getch()

        # Calculate the terminal height for proper placement of the prompt
        max_y, max_x = stdscr.getmaxyx()

        # Helper to display the article
        def display_article_on_screen(article):
            stdscr.clear()
            if article:
                lines = [
                    f"Title: {article.title}",
                    f"Link: {article.link}",
                    f"Author: {article.author or 'Unknown'}",
                    f"Published: {article.published_date or 'Unknown date'}",
                    "",
                    "Content Preview:",
                    "---------------",
                ]
                preview = article.content[:200] + "..." if len(article.content) > 200 else article.content
                lines.append(preview)

                # Add lines to the screen
                for i, line in enumerate(lines):
                    if i < max_y - 3:  # Leave space for the prompt
                        stdscr.addstr(i, 0, line[:max_x])  # Truncate to terminal width

            else:
                stdscr.addstr(0, 0, "No unread articles found!")

        # Display the first article
        article = manager.next_article()
        display_article_on_screen(article)

        # Display the prompt
        def display_prompt():
            prompt = "\n[n] Next | [o] Open | [+] Increase Weight | [-] Reduce Weight | [q] Quit"
            prompt_lines = prompt.split("\n")
            for i, line in enumerate(prompt_lines):
                stdscr.addstr(max_y - len(prompt_lines) + i - 1, 0, line[:max_x])

        display_prompt()

        while True:
            key = stdscr.getch()

            if key == ord("n"):
                article = manager.next_article()
                display_article_on_screen(article)
                display_prompt()

            elif key == ord("o"):
                try:
                    if article and article.link:
                        stdscr.addstr(max_y - 2, 0, f"Opening URL: {article.link}...".ljust(max_x))
                        os.system(f"termux-open-url {article.link}")
                        stdscr.addstr(max_y - 2, 0, "Opened link in browser.".ljust(max_x))
                    else:
                        stdscr.addstr(max_y - 2, 0, "No valid link to open.".ljust(max_x))
                except Exception as e:
                    stdscr.addstr(max_y - 2, 0, f"Failed to open browser: {e}".ljust(max_x))
                display_prompt()

            elif key == ord("+"):
                stdscr.addstr(max_y - 4, 0, "TODO: Increase weight of feed providing this article.".ljust(max_x))

            elif key == ord("-"):
                stdscr.addstr(max_y - 4, 0, "TODO: Decrease weight of feed providing this article.".ljust(max_x))


            elif key == ord("q"):
                stdscr.addstr(max_y - 2, 0, "Exiting...".ljust(max_x))
                stdscr.refresh()
                curses.napms(1000)
                break

            stdscr.refresh()

    curses.wrapper(main)

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="FoF - Feed of Feeds")
    
    parser.add_argument(
        "--config", "-c", 
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: ~/.config/fof/config.yaml)"
    )
    
    args = parser.parse_args()
    
    # Initialize feed manager
    manager = FeedManager(args.config)
    
    # Fetch and display the first article
    article = manager.next_article()
    
    # Ensure article is initialized
    if not article:
        print("No unread articles found! Exiting...")
        sys.exit(0)

    # Handle key-based interactions
    handle_key_input(manager, article)

if __name__ == "__main__":
    main()
