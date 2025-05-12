import curses
import os
import textwrap


class ControlLoop:
    """Manages display and keyboard interactions for navigating articles in a feed."""

    def __init__(self, feed_manager):
        """
        Initialize the ControlLoop.

        Args:
            feed_manager (FeedManager): The feed manager responsible for fetching articles.
        """
        self.feed_manager = feed_manager
        self.current_article = None

    def _display_article(self, stdscr):
        """Display the current article on the screen with word wrapping."""
        max_y, max_x = stdscr.getmaxyx()
        stdscr.clear()
        if self.current_article:
            # Prepare the article details
            lines = [
                f"Title: {self.current_article.title}",
                f"Link: {self.current_article.link}",
                f"Author: {self.current_article.author or 'Unknown'}",
                f"Published: {self.current_article.published_date or 'Unknown date'}",
                "",
                "Feed Path:",
                " -> ".join(self.current_article.feedpath) if self.current_article.feedpath else "Unknown",
                "",
                "Content Preview:",
                "---------------",
            ]
            
            # Wrap the content preview to fit the terminal width
            preview = self.current_article.content[:200] + "..." if len(self.current_article.content) > 200 else self.current_article.content
            wrapped_preview = textwrap.wrap(preview, width=max_x)  # Wrap content preview
            lines.extend(wrapped_preview)

            # Add lines to the screen with wrapping
            row = 0
            for line in lines:
                wrapped_lines = textwrap.wrap(line, width=max_x)  # Wrap each line
                for wrapped_line in wrapped_lines:
                    if row < max_y - 3:  # Leave space for the prompt
                        stdscr.addstr(row, 0, wrapped_line)
                        row += 1
                    else:
                        break  # Stop if there's no space left
        else:
            stdscr.addstr(0, 0, "No unread articles found!")

    def _display_prompt(self, stdscr):
        """Display the navigation prompt at the bottom of the screen."""
        max_y, max_x = stdscr.getmaxyx()
        prompt = "\n[n] Next | [o] Open | [+] Increase Weight | [-] Reduce Weight | [q] Quit"
        prompt_lines = prompt.split("\n")
        for i, line in enumerate(prompt_lines):
            stdscr.addstr(max_y - len(prompt_lines) + i - 1, 0, line[:max_x])

    def _handle_key_input(self, stdscr):
        """Main curses loop to handle user key inputs."""
        # Hide the cursor
        curses.curs_set(0)
        stdscr.nodelay(True)  # Make getch() non-blocking
        stdscr.timeout(100)  # Timeout for getch()

        max_y, max_x = stdscr.getmaxyx()

        # Display the first article
        self.current_article = self.feed_manager.next_article()
        self._display_article(stdscr)
        self._display_prompt(stdscr)

        while True:
            key = stdscr.getch()
            if key == ord("n"):
                self.current_article = self.feed_manager.next_article()
                self._display_article(stdscr)
                self._display_prompt(stdscr)

            elif key == ord("o"):
                try:
                    if self.current_article and self.current_article.link:
                        stdscr.addstr(max_y - 2, 0, f"Opening URL: {self.current_article.link}...".ljust(max_x))
                        os.system(f"xdg-open {self.current_article.link}")
                        stdscr.addstr(max_y - 2, 0, "Opened link in browser.".ljust(max_x))
                    else:
                        stdscr.addstr(max_y - 2, 0, "No valid link to open.".ljust(max_x))
                except Exception as e:
                    stdscr.addstr(max_y - 2, 0, f"Failed to open browser: {e}".ljust(max_x))
                self._display_prompt(stdscr)

            elif key == ord("+"):
                if self.current_article and self.current_article.feedpath:
                    try:
                        
                        self.feed_manager.update_weights(self.current_article.feedpath, increment=1)
                        self.feed_manager.save_config()
                        stdscr.addstr(max_y - 3, 0, "Increased weights along feedpath and saved configuration.".ljust(max_x))
                    except ValueError as e:
                        stdscr.addstr(max_y - 3, 0, f"Error: {e}".ljust(max_x))
                else:
                    stdscr.addstr(max_y - 3, 0, "No feed associated with this article.".ljust(max_x))
                self._display_prompt(stdscr)

            elif key == ord("-"):
                if self.current_article and self.current_article.feedpath:
                    try:
                        self.feed_manager.update_weights(self.current_article.feedpath, increment=-1)
                        self.feed_manager.save_config()
                        stdscr.addstr(max_y - 3, 0, "Decreased weights along feedpath and saved configuration.".ljust(max_x))
                    except ValueError as e:
                        stdscr.addstr(max_y - 3, 0, f"Error: {e}".ljust(max_x))
                else:
                    stdscr.addstr(max_y - 3, 0, "No feed associated with this article.".ljust(max_x))
                self._display_prompt(stdscr)

            elif key == ord("q"):
                stdscr.addstr(max_y - 2, 0, "Exiting...".ljust(max_x))
                stdscr.refresh()
                curses.napms(1000)
                break

            stdscr.refresh()

    def start(self):
        """Start the display and keyboard interaction interface."""
        curses.wrapper(self._handle_key_input)
