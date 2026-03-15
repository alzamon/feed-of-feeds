"""Tests for the WebUI class."""
import threading
import time
import unittest
from unittest.mock import Mock, patch

from fof.web_ui import WebUI


class TestWebUIInit(unittest.TestCase):
    """Test WebUI initialisation."""

    def setUp(self):
        self.mock_feed_manager = Mock()
        self.mock_article_manager = Mock()

    def test_init_state_matches_control_loop(self):
        """WebUI.__init__ mirrors ControlLoop state fields."""
        web_ui = WebUI(
            self.mock_feed_manager,
            self.mock_article_manager,
            session_timeout=300
        )
        self.assertIsNone(web_ui.current_article)
        self.assertFalse(web_ui.browsing_read_history)
        self.assertEqual(web_ui.session_timeout, 300)
        self.assertAlmostEqual(
            web_ui.last_activity_time, time.time(), delta=1.0
        )

    def test_default_session_timeout(self):
        """Default session timeout is 300 seconds."""
        web_ui = WebUI(
            self.mock_feed_manager,
            self.mock_article_manager
        )
        self.assertEqual(web_ui.session_timeout, 300)


class TestWebUIGetArticleJson(unittest.TestCase):
    """Test _get_article_json serialisation."""

    def setUp(self):
        self.mock_feed_manager = Mock()
        self.mock_article_manager = Mock()
        self.web_ui = WebUI(
            self.mock_feed_manager, self.mock_article_manager
        )

    def test_none_article_returns_none(self):
        result = self.web_ui._get_article_json(None)
        self.assertIsNone(result)

    def test_basic_article_serialisation(self):
        article = Mock()
        article.title = "Test Title"
        article.link = "https://example.com/article"
        article.author = "Test Author"
        article.published_date = "2024-01-01"
        article.feedpath = ["root", "tech"]
        article.content = "Short content"
        article.tags = ["python", "testing"]

        result = self.web_ui._get_article_json(article)

        self.assertEqual(result["title"], "Test Title")
        self.assertEqual(result["link"], "https://example.com/article")
        self.assertEqual(result["author"], "Test Author")
        self.assertEqual(result["published_date"], "2024-01-01")
        self.assertEqual(result["feedpath"], ["root", "tech"])
        self.assertEqual(result["content_preview"], "Short content")
        self.assertEqual(result["tags"], ["python", "testing"])

    def test_long_content_is_truncated(self):
        article = Mock()
        article.title = "Title"
        article.link = "https://example.com"
        article.author = ""
        article.published_date = ""
        article.feedpath = []
        article.content = "x" * 600
        article.tags = []

        result = self.web_ui._get_article_json(article)

        self.assertTrue(result["content_preview"].endswith("..."))
        self.assertLessEqual(len(result["content_preview"]), 503)

    def test_none_content_handled(self):
        article = Mock()
        article.title = "Title"
        article.link = "https://example.com"
        article.author = None
        article.published_date = None
        article.feedpath = []
        article.content = None
        article.tags = []

        result = self.web_ui._get_article_json(article)

        self.assertEqual(result["content_preview"], "")
        self.assertEqual(result["author"], "")

    def test_datetime_published_date_serialised(self):
        from datetime import datetime
        article = Mock()
        article.title = "T"
        article.link = "https://example.com"
        article.author = ""
        article.published_date = datetime(2024, 6, 1, 12, 0, 0)
        article.feedpath = []
        article.content = ""
        article.tags = []

        result = self.web_ui._get_article_json(article)

        self.assertIn("2024-06-01", result["published_date"])


class TestWebUIUpdateActivity(unittest.TestCase):
    """Test session activity tracking."""

    def setUp(self):
        self.mock_feed_manager = Mock()
        self.mock_article_manager = Mock()
        self.web_ui = WebUI(
            self.mock_feed_manager, self.mock_article_manager
        )

    def test_update_activity_resets_timer(self):
        before = self.web_ui.last_activity_time
        time.sleep(0.05)
        self.web_ui._update_activity()
        self.assertGreater(
            self.web_ui.last_activity_time, before
        )

    def test_timeout_disabled_when_zero(self):
        web_ui = WebUI(
            self.mock_feed_manager,
            self.mock_article_manager,
            session_timeout=0
        )
        # Force last_activity far in the past
        web_ui.last_activity_time = time.time() - 9999
        elapsed = time.time() - web_ui.last_activity_time
        # Even though elapsed >> 0, timeout is disabled
        self.assertFalse(
            web_ui.session_timeout > 0
            and elapsed >= web_ui.session_timeout
        )


class TestWebUIShutdown(unittest.TestCase):
    """Test _shutdown behaviour."""

    def setUp(self):
        self.mock_feed_manager = Mock()
        self.mock_article_manager = Mock()
        self.web_ui = WebUI(
            self.mock_feed_manager, self.mock_article_manager
        )

    def test_shutdown_sets_event(self):
        self.assertFalse(self.web_ui._shutdown_event.is_set())
        self.web_ui._shutdown()
        self.assertTrue(self.web_ui._shutdown_event.is_set())

    def test_shutdown_calls_purge_and_save(self):
        self.web_ui._shutdown()
        self.mock_feed_manager.purge_old_articles.assert_called_once()
        self.mock_feed_manager.save_config.assert_called_once()

    def test_shutdown_idempotent(self):
        """Calling _shutdown twice only purges/saves once."""
        self.web_ui._shutdown()
        self.web_ui._shutdown()
        self.mock_feed_manager.purge_old_articles.assert_called_once()
        self.mock_feed_manager.save_config.assert_called_once()


class TestWebUIAdvanceToNext(unittest.TestCase):
    """Test _advance_to_next article logic."""

    def setUp(self):
        self.mock_feed_manager = Mock()
        self.mock_article_manager = Mock()
        self.web_ui = WebUI(
            self.mock_feed_manager, self.mock_article_manager
        )

    def test_advance_calls_next_article(self):
        next_art = Mock()
        next_art.id = "art1"
        self.mock_feed_manager.next_article.return_value = next_art

        self.web_ui._advance_to_next()

        self.assertEqual(self.web_ui.current_article, next_art)
        self.assertFalse(self.web_ui.browsing_read_history)
        self.mock_article_manager.mark_as_read.assert_called_once_with(
            "art1"
        )

    def test_advance_no_mark_when_no_article(self):
        self.mock_feed_manager.next_article.return_value = None

        self.web_ui._advance_to_next()

        self.assertIsNone(self.web_ui.current_article)
        self.mock_article_manager.mark_as_read.assert_not_called()


class TestWebUIFindFreePort(unittest.TestCase):
    """Test _find_free_port returns a valid port."""

    def setUp(self):
        self.web_ui = WebUI(Mock(), Mock())

    def test_returns_valid_port(self):
        port = self.web_ui._find_free_port()
        self.assertIsInstance(port, int)
        self.assertGreater(port, 0)
        self.assertLessEqual(port, 65535)


class TestWebUIHtmlTemplate(unittest.TestCase):
    """Test that HTML_TEMPLATE is well-formed enough to serve."""

    def test_template_contains_key_elements(self):
        from fof.web_ui import HTML_TEMPLATE
        self.assertIn("<!DOCTYPE html>", HTML_TEMPLATE)
        # API endpoints are built dynamically: fetch('/api/'+action)
        self.assertIn("'/api/'", HTML_TEMPLATE)
        self.assertIn("/api/article", HTML_TEMPLATE)
        self.assertIn("/api/quit", HTML_TEMPLATE)
        self.assertIn("touchstart", HTML_TEMPLATE)
        self.assertIn("touchend", HTML_TEMPLATE)
        self.assertIn("ArrowRight", HTML_TEMPLATE)
        self.assertIn("ArrowLeft", HTML_TEMPLATE)
        # Action strings used by buttons and keyboard handler
        self.assertIn("dislike", HTML_TEMPLATE)
        self.assertIn("like", HTML_TEMPLATE)
        self.assertIn("previous", HTML_TEMPLATE)
        self.assertIn("quit", HTML_TEMPLATE)

    def test_template_has_content_div(self):
        from fof.web_ui import HTML_TEMPLATE
        self.assertIn('id="content-wrap"', HTML_TEMPLATE)
        self.assertIn('id="content"', HTML_TEMPLATE)
        self.assertIn('id="open-link"', HTML_TEMPLATE)


class TestWebUIStart(unittest.TestCase):
    """Test WebUI.start() integration (with mocks)."""

    def setUp(self):
        self.mock_feed_manager = Mock()
        self.mock_article_manager = Mock()
        self.mock_feed_manager.next_article.return_value = None
        self.mock_feed_manager.purge_old_articles.return_value = 0

    def test_start_opens_browser_and_shuts_down(self):
        """WebUI.start() opens browser and shuts down via event."""
        web_ui = WebUI(
            self.mock_feed_manager,
            self.mock_article_manager,
            session_timeout=0
        )

        with patch('fof.web_ui.open_url_in_browser') as mock_browser:
            # Trigger shutdown shortly after start
            def trigger_shutdown():
                time.sleep(0.2)
                web_ui._shutdown()

            t = threading.Thread(target=trigger_shutdown, daemon=True)
            t.start()
            web_ui.start()
            t.join(timeout=2)

        mock_browser.assert_called_once()
        called_url = mock_browser.call_args[0][0]
        self.assertTrue(called_url.startswith("http://localhost:"))

    def test_start_prints_url(self):
        """WebUI.start() prints the server URL."""
        import io
        web_ui = WebUI(
            self.mock_feed_manager,
            self.mock_article_manager,
            session_timeout=0
        )

        captured = io.StringIO()
        with patch('fof.web_ui.open_url_in_browser'):
            def trigger_shutdown():
                time.sleep(0.2)
                web_ui._shutdown()

            t = threading.Thread(target=trigger_shutdown, daemon=True)
            t.start()
            with patch('sys.stdout', captured):
                web_ui.start()
            t.join(timeout=2)

        output = captured.getvalue()
        self.assertIn("FoF web UI:", output)
        self.assertIn("http://localhost:", output)


class TestWebUICliTuiFlag(unittest.TestCase):
    """Test that --tui flag routes to ControlLoop."""

    def test_tui_flag_uses_control_loop(self):
        """--tui should invoke ControlLoop, not WebUI."""
        import tempfile
        import json
        import os

        with tempfile.TemporaryDirectory() as tmp:
            tree_dir = os.path.join(tmp, "tree")
            os.makedirs(tree_dir)
            cfg = {
                "id": "root",
                "title": "R",
                "description": "d",
                "url": "http://example.com/f.xml",
                "max_age": "7d"
            }
            with open(os.path.join(tree_dir, "feed.fof"), "w") as f:
                json.dump(cfg, f)

            with patch('fof.cli.ControlLoop') as mock_cl, \
                    patch('sys.argv', [
                        'fof', '--config', tmp, '--tui'
                    ]):
                mock_cl.return_value.start.return_value = None
                from fof.cli import main
                try:
                    main()
                except SystemExit:
                    pass
            mock_cl.assert_called_once()

    def test_default_uses_web_ui(self):
        """Default (no --tui) should invoke WebUI."""
        import tempfile
        import json
        import os

        with tempfile.TemporaryDirectory() as tmp:
            tree_dir = os.path.join(tmp, "tree")
            os.makedirs(tree_dir)
            cfg = {
                "id": "root",
                "title": "R",
                "description": "d",
                "url": "http://example.com/f.xml",
                "max_age": "7d"
            }
            with open(os.path.join(tree_dir, "feed.fof"), "w") as f:
                json.dump(cfg, f)

            with patch('fof.web_ui.WebUI') as mock_wu, \
                    patch('sys.argv', ['fof', '--config', tmp]):
                mock_wu.return_value.start.return_value = None
                from fof.cli import main
                try:
                    main()
                except SystemExit:
                    pass
            mock_wu.assert_called_once()


if __name__ == "__main__":
    unittest.main()
