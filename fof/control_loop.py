import urllib.parse
import curses
import os
import textwrap

class ControlLoop:
    """Manages display and keyboard interactions for navigating articles in a feed."""

    def __init__(self, feed_manager, article_manager):
        self.feed_manager = feed_manager
        self.article_manager = article_manager
        self.current_article = None
        self.browsing_read_history = False

    def _display_article(self, stdscr):
        max_y, max_x = stdscr.getmaxyx()
        stdscr.clear()
        if self.current_article:
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
            preview = self.current_article.content[:200] + "..." if len(self.current_article.content) > 200 else self.current_article.content
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
        prompt = "\n[n] Next | [p] Previous | [o] Open | [+] Increase Weight | [-] Reduce Weight | [q] Quit"
        prompt_lines = prompt.split("\n")
        for i, line in enumerate(prompt_lines):
            stdscr.addstr(max_y - len(prompt_lines) + i - 1, 0, line[:max_x])

    def _handle_key_input(self, stdscr):
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(100)

        max_y, max_x = stdscr.getmaxyx()

        self.current_article = self.feed_manager.next_article()
        self.browsing_read_history = False
        if self.current_article and not self.browsing_read_history:
            self.article_manager.mark_as_read(self.current_article.id)
        self._display_article(stdscr)
        self._display_prompt(stdscr)

        while True:
            key = stdscr.getch()
            if key == ord("n"):
                if self.browsing_read_history:
                    if self.current_article and getattr(self.current_article, "read", None):
                        next_article = self.article_manager.get_next_read_article(
                            self.current_article.read.isoformat()
                        )
                        if next_article:
                            self.current_article = next_article
                            stdscr.addstr(max_y - 2, 0, "Moved to newer read article.".ljust(max_x))
                            self._display_article(stdscr)
                            self._display_prompt(stdscr)
                        else:
                            # At most recent read article. Switch to unread mode.
                            self.browsing_read_history = False
                            self.current_article = self.feed_manager.next_article()
                            if self.current_article:
                                self.article_manager.mark_as_read(self.current_article.id)
                                stdscr.addstr(max_y - 2, 0, "Switched to unread. Showing next unread article.".ljust(max_x))
                            else:
                                stdscr.addstr(0, 0, "All caught up! No more articles to display.")
                            self._display_article(stdscr)
                            self._display_prompt(stdscr)
                    else:
                        stdscr.addstr(max_y - 2, 0, "Not in read history.".ljust(max_x))
                        self._display_prompt(stdscr)
                else:
                    # Get next unread article
                    self.current_article = self.feed_manager.next_article()
                    if self.current_article:
                        self.article_manager.mark_as_read(self.current_article.id)
                    else:
                        stdscr.addstr(0, 0, "All caught up! No more articles to display.")
                    self._display_article(stdscr)
                    self._display_prompt(stdscr)

            elif key == ord("p"):
                prev_article = None
                if self.current_article and getattr(self.current_article, "read", None):
                    prev_article = self.article_manager.get_previous_read_article(
                        self.current_article.read.isoformat()
                    )
                else:
                    most_recent = self.article_manager.get_previous_read_article()
                    if most_recent and self.current_article and most_recent.id == self.current_article.id:
                        prev_article = self.article_manager.get_previous_read_article(most_recent.read.isoformat())
                    else:
                        prev_article = most_recent
                if prev_article:
                    self.current_article = prev_article
                    stdscr.addstr(max_y - 2, 0, "Moved to previous read article.".ljust(max_x))
                else:
                    stdscr.addstr(max_y - 2, 0, "No read articles yet.".ljust(max_x))
                self.browsing_read_history = True
                self._display_article(stdscr)
                self._display_prompt(stdscr)

            elif key == ord("o"):
                try:
                    if self.current_article and self.current_article.link:
                        stdscr.addstr(max_y - 2, 0, f"Opening URL: {self.current_article.link}...".ljust(max_x))
                        encoded_url = urllib.parse.quote(self.current_article.link, safe=":/?")
                        os.system(f"xdg-open {encoded_url}")
                        stdscr.addstr(max_y - 2, 0, "Opened link in browser.".ljust(max_x))
                    else:
                        stdscr.addstr(max_y - 2, 0, "No valid link to open.".ljust(max_x))
                except Exception as e:
                    stdscr.addstr(max_y - 2, 0, f"Failed to open browser: {e}".ljust(max_x))
                self._display_prompt(stdscr)

            elif key == ord("+"):
                if self.current_article and self.current_article.feedpath:
                    try:
                        self.feed_manager.update_weights(self.current_article.feedpath, increment=10)
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
                        self.feed_manager.update_weights(self.current_article.feedpath, increment=-10)
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
        curses.wrapper(self._handle_key_input)
