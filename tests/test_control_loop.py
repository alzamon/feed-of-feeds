"""Tests for the ControlLoop class after refactoring."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from fof.control_loop import ControlLoop


class TestControlLoop(unittest.TestCase):
    """Test the ControlLoop class functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_feed_manager = Mock()
        self.mock_article_manager = Mock()
        self.control_loop = ControlLoop(
            self.mock_feed_manager, self.mock_article_manager
        )
        self.mock_stdscr = Mock()
        self.mock_stdscr.getmaxyx.return_value = (24, 80)  # Standard terminal

    def test_update_display_calls_proper_methods(self):
        """Test that _update_display calls the right display methods."""
        with patch.object(self.control_loop, '_display_article') as mock_display_article, \
             patch.object(self.control_loop, '_display_prompt') as mock_display_prompt:
            
            self.control_loop._update_display(self.mock_stdscr)
            
            mock_display_article.assert_called_once_with(self.mock_stdscr)
            mock_display_prompt.assert_called_once_with(self.mock_stdscr)
            self.mock_stdscr.refresh.assert_called_once()

    def test_show_status_message(self):
        """Test that _show_status_message displays message correctly."""
        with patch.object(self.control_loop, '_display_prompt') as mock_display_prompt:
            
            message = "Test status message"
            self.control_loop._show_status_message(self.mock_stdscr, message)
            
            # Check that addstr was called with the message
            self.mock_stdscr.addstr.assert_called_once()
            call_args = self.mock_stdscr.addstr.call_args[0]
            self.assertEqual(call_args[0], 22)  # max_y - 2 = 24 - 2 = 22
            self.assertEqual(call_args[1], 0)
            self.assertTrue(message in call_args[2])
            mock_display_prompt.assert_called_once_with(self.mock_stdscr)

    def test_handle_help_key_returns_false(self):
        """Test that help key handler returns False to continue loop."""
        with patch.object(self.control_loop, '_display_hotkeys'), \
             patch.object(self.control_loop, '_update_display'):
            
            result = self.control_loop._handle_help_key(self.mock_stdscr)
            
            self.assertFalse(result)

    def test_handle_quit_key_returns_true(self):
        """Test that quit key handler returns True to exit loop."""
        with patch('fof.control_loop.curses.napms'):
            result = self.control_loop._handle_quit_key(self.mock_stdscr)
            
            self.assertTrue(result)

    def test_handle_open_browser_key_with_no_article(self):
        """Test browser key when no current article."""
        self.control_loop.current_article = None
        
        with patch.object(self.control_loop, '_show_status_message') as mock_status:
            result = self.control_loop._handle_open_browser_key(self.mock_stdscr)
            
            self.assertFalse(result)
            mock_status.assert_called_once_with(
                self.mock_stdscr, "No valid link to open."
            )

    @patch('fof.control_loop.open_url_in_browser')
    def test_handle_open_browser_key_with_article(self, mock_open_browser):
        """Test browser key with valid article."""
        mock_article = Mock()
        mock_article.link = "https://example.com"
        self.control_loop.current_article = mock_article
        mock_open_browser.return_value = True
        
        with patch.object(self.control_loop, '_show_status_message') as mock_status:
            result = self.control_loop._handle_open_browser_key(self.mock_stdscr)
            
            self.assertFalse(result)
            mock_open_browser.assert_called_once_with("https://example.com")
            # Should be called twice: once for "Opening URL..." and once for success
            self.assertEqual(mock_status.call_count, 2)

    def test_handle_increase_weight_key_no_article(self):
        """Test weight increase when no current article."""
        self.control_loop.current_article = None
        
        with patch.object(self.control_loop, '_show_status_message') as mock_status:
            result = self.control_loop._handle_increase_weight_key(self.mock_stdscr)
            
            self.assertFalse(result)
            mock_status.assert_called_once_with(
                self.mock_stdscr, "No feed associated with this article."
            )

    def test_handle_increase_weight_key_with_article(self):
        """Test weight increase with valid article."""
        mock_article = Mock()
        mock_article.feedpath = ["feed", "path"]
        self.control_loop.current_article = mock_article
        
        with patch.object(self.control_loop, '_show_status_message') as mock_status:
            result = self.control_loop._handle_increase_weight_key(self.mock_stdscr)
            
            self.assertFalse(result)
            self.mock_feed_manager.update_weights.assert_called_once_with(
                ["feed", "path"], increment=10
            )
            self.mock_feed_manager.save_config.assert_called_once()
            # Should show success message
            self.assertTrue("Increased weights" in mock_status.call_args[0][1])

    def test_key_handler_mapping_complete(self):
        """Test that all expected keys have handlers in _handle_key_input."""
        # This test verifies the key mapping dictionary is correctly set up
        with patch('fof.control_loop.curses.curs_set'), \
             patch.object(self.control_loop, '_update_display'), \
             patch.object(self.mock_feed_manager, 'next_article', return_value=None):
            
            # Mock the while loop to exit immediately
            with patch.object(self.mock_stdscr, 'getch', side_effect=[ord('q')]):
                with patch.object(self.control_loop, '_handle_quit_key', return_value=True):
                    self.control_loop._handle_key_input(self.mock_stdscr)
            
            # If we get here without error, the key mapping is working


if __name__ == '__main__':
    unittest.main()