"""Tests for session timeout functionality in ControlLoop."""
import time
import unittest.mock as mock

from fof.control_loop import ControlLoop


def test_control_loop_timeout_tracking():
    """Test that ControlLoop properly tracks activity and timeouts."""
    # Mock dependencies
    mock_feed_manager = mock.Mock()
    mock_article_manager = mock.Mock()
    
    # Create control loop with 1-second timeout for testing
    control_loop = ControlLoop(mock_feed_manager, mock_article_manager, session_timeout=1)
    
    # Initially should not be timed out
    assert not control_loop._check_session_timeout()
    
    # Update activity and still should not be timed out
    control_loop._update_activity()
    assert not control_loop._check_session_timeout()
    
    # Wait for timeout to expire
    time.sleep(1.1)
    assert control_loop._check_session_timeout()


def test_control_loop_timeout_disabled():
    """Test that setting timeout to 0 disables the timeout functionality."""
    mock_feed_manager = mock.Mock()
    mock_article_manager = mock.Mock()
    
    # Create control loop with timeout disabled
    control_loop = ControlLoop(mock_feed_manager, mock_article_manager, session_timeout=0)
    
    # Should never timeout regardless of time passed
    assert not control_loop._check_session_timeout()
    
    # Even after waiting
    time.sleep(0.1)
    assert not control_loop._check_session_timeout()


def test_control_loop_negative_timeout():
    """Test that negative timeout values disable the timeout functionality."""
    mock_feed_manager = mock.Mock()
    mock_article_manager = mock.Mock()
    
    # Create control loop with negative timeout
    control_loop = ControlLoop(mock_feed_manager, mock_article_manager, session_timeout=-5)
    
    # Should never timeout
    assert not control_loop._check_session_timeout()


def test_control_loop_update_activity():
    """Test that updating activity resets the timeout timer."""
    mock_feed_manager = mock.Mock()
    mock_article_manager = mock.Mock()
    
    # Create control loop with short timeout
    control_loop = ControlLoop(mock_feed_manager, mock_article_manager, session_timeout=1)
    
    # Wait almost to timeout
    time.sleep(0.8)
    assert not control_loop._check_session_timeout()
    
    # Update activity
    control_loop._update_activity()
    
    # Wait again, should not timeout because activity was updated
    time.sleep(0.8)
    assert not control_loop._check_session_timeout()
    
    # But should timeout after full duration
    time.sleep(0.3)
    assert control_loop._check_session_timeout()


@mock.patch('fof.control_loop.curses')
def test_control_loop_timeout_message(mock_curses):
    """Test that timeout handler shows appropriate message."""
    mock_feed_manager = mock.Mock()
    mock_article_manager = mock.Mock()
    mock_stdscr = mock.Mock()
    
    # Mock curses screen dimensions
    mock_stdscr.getmaxyx.return_value = (25, 80)
    
    control_loop = ControlLoop(mock_feed_manager, mock_article_manager, session_timeout=300)
    
    # Call timeout handler
    result = control_loop._handle_session_timeout(mock_stdscr)
    
    # Should return True to exit
    assert result is True
    
    # Should display timeout message
    mock_stdscr.addstr.assert_called()
    call_args = mock_stdscr.addstr.call_args[0]
    assert "Session timed out after 5 minutes" in call_args[2]
    
    # Should refresh and wait
    mock_stdscr.refresh.assert_called()
    mock_curses.napms.assert_called_with(2000)