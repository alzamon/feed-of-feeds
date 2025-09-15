import curses
import textwrap
import time
from .platform_quirks import open_url_in_browser


class ControlLoop:
    """Manages display and keyboard interactions for navigating articles."""

    def __init__(self, feed_manager, article_manager, session_timeout=300):
        self.feed_manager = feed_manager
        self.article_manager = article_manager
        self.current_article = None
        self.browsing_read_history = False
        self.session_timeout = session_timeout
        self.last_activity_time = time.time()

    def _display_article(self, stdscr):
        max_y, max_x = stdscr.getmaxyx()
        stdscr.clear()
        if self.current_article:
            lines = [
                f"Title: {
                    self.current_article.title}", f"Link: {
                    self.current_article.link}", f"Author: {
                    self.current_article.author or 'Unknown'}", f"Published: {
                    self.current_article.published_date or 'Unknown date'}", ]
            if (hasattr(self.current_article, "tags")
               and self.current_article.tags):
                tag_str = ", ".join(self.current_article.tags)
                lines.append(f"Tags: {tag_str}")
            else:
                lines.append("Tags: None")
            lines.extend([
                "",
                "Feed Path:",
                (" -> ".join(self.current_article.feedpath)
                 if self.current_article.feedpath else "Unknown"),
                "",
                "Content Preview:",
                "---------------",
            ])
            preview = (
                self.current_article.content[:200] + "..."
                if len(self.current_article.content) > 200
                else self.current_article.content
            )
            wrapped_preview = textwrap.wrap(preview, width=max_x)
            lines.extend(wrapped_preview)
            row = 0
            for line in lines:
                wrapped_lines = textwrap.wrap(line, width=max_x)
                for wrapped_line in wrapped_lines:
                    if row < max_y - 3:
                        stdscr.addstr(row, 0, wrapped_line)
                        row += 1
                    else:
                        break
        else:
            stdscr.addstr(0, 0, "All caught up! No more articles to display.")

    def _display_prompt(self, stdscr):
        max_y, max_x = stdscr.getmaxyx()
        prompt = "[?] Show hotkeys"
        stdscr.addstr(max_y - 1, 0, prompt[:max_x])

    def _display_hotkeys(self, stdscr):
        max_y, max_x = stdscr.getmaxyx()
        hotkey_help = (
            "[n] Next article\n"
            "[p] Previous (read) article\n"
            "[o] Open article link in browser\n"
            "[+] Increase weight along feed path\n"
            "[-] Decrease weight along feed path\n"
            "[q] Quit\n"
            "[?] Show/hide this hotkey help\n"
        )
        # Display hotkeys, wrapped if necessary
        row = 0
        for line in hotkey_help.strip().split("\n"):
            wrapped = textwrap.wrap(line, width=max_x)
            for wline in wrapped:
                if row < max_y - 1:
                    stdscr.addstr(row, 0, wline)
                    row += 1
        # Add "Press any key to return..." at the bottom
        press_any_key = "-- press any key to return --"
        if row < max_y:
            stdscr.addstr(max_y - 1, 0, press_any_key[:max_x])
        stdscr.refresh()

    def _update_activity(self):
        """Update the last activity timestamp."""
        self.last_activity_time = time.time()

    def _check_session_timeout(self):
        """Check if session has timed out due to inactivity."""
        if self.session_timeout <= 0:
            return False  # Timeout disabled
        
        current_time = time.time()
        return (current_time - self.last_activity_time) >= self.session_timeout

    def _handle_session_timeout(self, stdscr):
        """Handle session timeout by showing message and exiting."""
        max_y, max_x = stdscr.getmaxyx()
        timeout_msg = f"Session timed out after {self.session_timeout // 60} minutes of inactivity. Exiting..."
        stdscr.addstr(max_y - 2, 0, timeout_msg[:max_x])
        stdscr.refresh()
        curses.napms(2000)  # Show message for 2 seconds
        return True  # Exit main loop

    def _update_display(self, stdscr):
        self._display_article(stdscr)
        self._display_prompt(stdscr)
        stdscr.refresh()

    def _show_status_message(self, stdscr, message):
        """Show a status message and update the display."""
        max_y, max_x = stdscr.getmaxyx()
        stdscr.addstr(max_y - 2, 0, message.ljust(max_x))
        self._display_prompt(stdscr)

    def _handle_help_key(self, stdscr):
        """Handle the ? key to show/hide help."""
        stdscr.clear()
        self._display_hotkeys(stdscr)
        stdscr.nodelay(False)
        stdscr.getch()  # Wait for any key
        stdscr.nodelay(True)
        self._update_display(stdscr)
        return False  # Continue main loop

    def _handle_next_article_key(self, stdscr):
        """Handle the 'n' key for next article navigation."""
        max_y, max_x = stdscr.getmaxyx()

        if self.browsing_read_history:
            if (self.current_article
               and getattr(self.current_article, "read", None)):
                next_article = (
                    self.article_manager.get_next_read_article(
                        self.current_article.read.isoformat()
                    )
                )
                if next_article:
                    self.current_article = next_article
                    self._show_status_message(
                        stdscr, "Moved to newer read article.")
                    self._update_display(stdscr)
                else:
                    # At most recent read article. Switch to unread mode.
                    self.browsing_read_history = False
                    self.current_article = (
                        self.feed_manager.next_article()
                    )
                    if self.current_article:
                        self.article_manager.mark_as_read(
                            self.current_article.id
                        )
                        message = ("Switched to unread. Showing next unread "
                                   "article.")
                        self._show_status_message(stdscr, message)
                    else:
                        stdscr.addstr(
                            0, 0,
                            "All caught up! No more articles to display."
                        )
                    self._update_display(stdscr)
            else:
                self._show_status_message(stdscr, "Not in read history.")
        else:
            # Get next unread article
            self.current_article = self.feed_manager.next_article()
            if self.current_article:
                self.article_manager.mark_as_read(
                    self.current_article.id
                )
            else:
                stdscr.addstr(
                    0, 0,
                    "All caught up! No more articles to display."
                )
            self._update_display(stdscr)
        return False  # Continue main loop

    def _handle_previous_article_key(self, stdscr):
        """Handle the 'p' key for previous article navigation."""
        max_y, max_x = stdscr.getmaxyx()

        prev_article = None
        if (self.current_article
                and getattr(self.current_article, "read", None)):
            prev_article = (
                self.article_manager.get_previous_read_article(
                    self.current_article.read.isoformat()
                )
            )
        else:
            most_recent = self.article_manager.get_previous_read_article()
            if (most_recent and self.current_article
                    and most_recent.id == self.current_article.id):
                prev_article = (
                    self.article_manager.get_previous_read_article(
                        most_recent.read.isoformat()
                    )
                )
            else:
                prev_article = most_recent

        if prev_article:
            self.current_article = prev_article
            self._show_status_message(
                stdscr, "Moved to previous read article.")
        else:
            self._show_status_message(stdscr, "No read articles yet.")

        self.browsing_read_history = True
        self._update_display(stdscr)
        return False  # Continue main loop

    def _handle_open_browser_key(self, stdscr):
        """Handle the 'o' key to open article in browser."""
        max_y, max_x = stdscr.getmaxyx()

        try:
            if self.current_article and self.current_article.link:
                message = f"Opening URL: {self.current_article.link}..."
                self._show_status_message(stdscr, message)
                success = open_url_in_browser(self.current_article.link)
                if success:
                    self._show_status_message(
                        stdscr, "Opened link in browser.")
                else:
                    self._show_status_message(
                        stdscr, "Failed to open browser.")
            else:
                self._show_status_message(stdscr, "No valid link to open.")
        except Exception as e:
            self._show_status_message(stdscr, f"Failed to open browser: {e}")
        return False  # Continue main loop

    def _handle_increase_weight_key(self, stdscr):
        """Handle the '+' key to increase feed weight."""
        if self.current_article and self.current_article.feedpath:
            try:
                self.feed_manager.update_weights(
                    self.current_article.feedpath, increment=10)
                self.feed_manager.save_config()
                message = ("Increased weights along feedpath and saved "
                           "configuration.")
                self._show_status_message(stdscr, message)
            except ValueError as e:
                self._show_status_message(stdscr, f"Error: {e}")
        else:
            message = "No feed associated with this article."
            self._show_status_message(stdscr, message)
        return False  # Continue main loop

    def _handle_decrease_weight_key(self, stdscr):
        """Handle the '-' key to decrease feed weight."""
        if self.current_article and self.current_article.feedpath:
            try:
                self.feed_manager.update_weights(
                    self.current_article.feedpath, increment=-10)
                self.feed_manager.save_config()
                message = ("Decreased weights along feedpath and saved "
                           "configuration.")
                self._show_status_message(stdscr, message)
            except ValueError as e:
                self._show_status_message(stdscr, f"Error: {e}")
        else:
            message = "No feed associated with this article."
            self._show_status_message(stdscr, message)
        return False  # Continue main loop

    def _handle_quit_key(self, stdscr):
        """Handle the 'q' key to quit the application."""
        max_y, max_x = stdscr.getmaxyx()
        stdscr.addstr(max_y - 2, 0, "Exiting...".ljust(max_x))
        stdscr.refresh()
        curses.napms(1000)
        return True  # Exit main loop

    def _handle_key_input(self, stdscr):
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(100)

        # Initialize state
        self.current_article = self.feed_manager.next_article()
        self.browsing_read_history = False

        if self.current_article and not self.browsing_read_history:
            self.article_manager.mark_as_read(self.current_article.id)

        self._update_display(stdscr)

        # Key handler mapping
        key_handlers = {
            ord("?"): self._handle_help_key,
            ord("n"): self._handle_next_article_key,
            ord("p"): self._handle_previous_article_key,
            ord("o"): self._handle_open_browser_key,
            ord("+"): self._handle_increase_weight_key,
            ord("-"): self._handle_decrease_weight_key,
            ord("q"): self._handle_quit_key
        }

        while True:
            # Check for session timeout
            if self._check_session_timeout():
                should_exit = self._handle_session_timeout(stdscr)
                if should_exit:
                    break
            
            key = stdscr.getch()
            handler = key_handlers.get(key)
            if handler:
                # Update activity timestamp on any valid key press
                self._update_activity()
                should_exit = handler(stdscr)
                if should_exit:
                    break
            stdscr.refresh()

    def start(self):
        curses.wrapper(self._handle_key_input)
