"""Tests for platform-specific quirks functionality."""
import os
import subprocess
from unittest.mock import patch
import pytest
from fof.platform_quirks import get_browser_open_command, is_termux, open_url_in_browser


class TestIsTermux:
    """Test Termux environment detection."""

    def test_is_termux_with_termux_prefix(self):
        """Test that Termux is detected when PREFIX contains com.termux."""
        with patch.dict('os.environ', {'PREFIX': '/data/data/com.termux/files/usr'}):
            assert is_termux() is True

    def test_is_not_termux_with_standard_prefix(self):
        """Test that Termux is not detected on a standard Linux system."""
        with patch.dict('os.environ', {'PREFIX': '/usr'}):
            assert is_termux() is False

    def test_is_not_termux_without_prefix(self):
        """Test that Termux is not detected when PREFIX is absent."""
        env = {k: v for k, v in os.environ.items() if k != 'PREFIX'}
        with patch.dict('os.environ', env, clear=True):
            assert is_termux() is False

    def test_is_not_termux_with_empty_prefix(self):
        """Test that Termux is not detected when PREFIX is empty."""
        with patch.dict('os.environ', {'PREFIX': ''}):
            assert is_termux() is False


class TestGetBrowserOpenCommand:
    """Test platform-specific browser command selection."""

    def test_get_browser_open_command_windows(self):
        """Test browser command for Windows platform."""
        with patch('platform.system', return_value='Windows'):
            command = get_browser_open_command("https://example.com")
            assert command == ["start", "https://example.com"]

    def test_get_browser_open_command_macos(self):
        """Test browser command for macOS platform."""
        with patch('platform.system', return_value='Darwin'):
            command = get_browser_open_command("https://example.com")
            assert command == ["open", "https://example.com"]

    def test_get_browser_open_command_linux(self):
        """Test browser command for standard Linux (non-Termux) platform."""
        with patch('platform.system', return_value='Linux'), \
             patch('fof.platform_quirks.is_termux', return_value=False):
            command = get_browser_open_command("https://example.com")
            assert command == ["xdg-open", "https://example.com"]

    def test_get_browser_open_command_termux(self):
        """Test browser command for Termux uses termux-open-url."""
        with patch('platform.system', return_value='Linux'), \
             patch('fof.platform_quirks.is_termux', return_value=True):
            command = get_browser_open_command("https://example.com")
            assert command == ["termux-open-url", "https://example.com"]

    def test_get_browser_open_command_termux_android_system(self):
        """Test Termux command selection even when platform reports Android."""
        with patch('platform.system', return_value='Android'), \
             patch('fof.platform_quirks.is_termux', return_value=True):
            command = get_browser_open_command("https://example.com")
            assert command == ["termux-open-url", "https://example.com"]

    def test_get_browser_open_command_termux_long_url(self):
        """Test that long URLs are passed through intact on Termux."""
        long_url = (
            "https://example.com/articles/some-very-long-path-that-exceeds"
            "-typical-shell-argument-limits-on-android"
            "?utm_source=feed&utm_medium=rss&utm_campaign=newsletter"
            "&ref=abcdefghijklmnopqrstuvwxyz0123456789"
            "&extra=moreparameterstomakethistrulylongerthanandroidcanlhandle"
        )
        with patch('platform.system', return_value='Linux'), \
             patch('fof.platform_quirks.is_termux', return_value=True):
            command = get_browser_open_command(long_url)
            assert command == ["termux-open-url", long_url]

    def test_get_browser_open_command_unsupported_platform(self):
        """Test error handling for unsupported platforms."""
        with patch('platform.system', return_value='UnknownOS'):
            with pytest.raises(RuntimeError, match="Unsupported platform"):
                get_browser_open_command("https://example.com")


class TestOpenUrlInBrowser:
    """Test the open_url_in_browser function."""

    @patch('subprocess.Popen')
    def test_open_url_in_browser_linux_success(self, mock_popen):
        """Test successful URL opening on standard Linux with output redirection."""
        with patch('platform.system', return_value='Linux'), \
             patch('fof.platform_quirks.is_termux', return_value=False):
            result = open_url_in_browser("https://example.com")

            assert result is True
            mock_popen.assert_called_once_with(
                ["xdg-open", "https://example.com"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    @patch('subprocess.Popen')
    def test_open_url_in_browser_termux_success(self, mock_popen):
        """Test successful URL opening on Termux uses termux-open-url."""
        with patch('platform.system', return_value='Linux'), \
             patch('fof.platform_quirks.is_termux', return_value=True):
            result = open_url_in_browser("https://example.com")

            assert result is True
            mock_popen.assert_called_once_with(
                ["termux-open-url", "https://example.com"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    @patch('subprocess.Popen')
    def test_open_url_in_browser_termux_long_url(self, mock_popen):
        """Test that long URLs are handled correctly on Termux."""
        long_url = (
            "https://example.com/articles/some-very-long-path"
            "?utm_source=feed&utm_medium=rss&utm_campaign=newsletter"
            "&ref=abcdefghijklmnopqrstuvwxyz0123456789"
            "&extra=moreparameterstomakethistrulylongerthanandroidcanlhandle"
        )
        with patch('platform.system', return_value='Linux'), \
             patch('fof.platform_quirks.is_termux', return_value=True):
            result = open_url_in_browser(long_url)

            assert result is True
            mock_popen.assert_called_once_with(
                ["termux-open-url", long_url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    @patch('subprocess.Popen')
    def test_open_url_in_browser_windows_success(self, mock_popen):
        """Test successful URL opening on Windows."""
        with patch('platform.system', return_value='Windows'):
            result = open_url_in_browser("https://example.com")

            assert result is True
            mock_popen.assert_called_once_with(
                ["start", "https://example.com"])

    @patch('subprocess.Popen')
    def test_open_url_in_browser_macos_success(self, mock_popen):
        """Test successful URL opening on macOS."""
        with patch('platform.system', return_value='Darwin'):
            result = open_url_in_browser("https://example.com")

            assert result is True
            mock_popen.assert_called_once_with(["open", "https://example.com"])

    @patch('subprocess.Popen')
    def test_open_url_in_browser_failure(self, mock_popen):
        """Test error handling when subprocess fails."""
        mock_popen.side_effect = OSError("Command not found")

        with patch('platform.system', return_value='Linux'), \
             patch('fof.platform_quirks.is_termux', return_value=False):
            result = open_url_in_browser("https://example.com")

            assert result is False

    def test_open_url_in_browser_unsupported_platform(self):
        """Test error handling for unsupported platform."""
        with patch('platform.system', return_value='UnknownOS'):
            result = open_url_in_browser("https://example.com")

            assert result is False

    @patch('subprocess.Popen')
    def test_open_url_in_browser_strips_whitespace(self, mock_popen):
        """Test that leading/trailing whitespace is stripped from the URL."""
        with patch('platform.system', return_value='Linux'), \
             patch('fof.platform_quirks.is_termux', return_value=False):
            result = open_url_in_browser("  https://example.com/path\n")

            assert result is True
            mock_popen.assert_called_once_with(
                ["xdg-open", "https://example.com/path"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    @patch('subprocess.Popen')
    def test_open_url_in_browser_strips_newlines(self, mock_popen):
        """Test that newline characters are stripped from the URL."""
        with patch('platform.system', return_value='Linux'), \
             patch('fof.platform_quirks.is_termux', return_value=False):
            result = open_url_in_browser("https://example.com/path\r\n")

            assert result is True
            mock_popen.assert_called_once_with(
                ["xdg-open", "https://example.com/path"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    @patch('subprocess.Popen')
    def test_open_url_in_browser_strips_whitespace_macos(self, mock_popen):
        """Test that whitespace is stripped from the URL on macOS."""
        with patch('platform.system', return_value='Darwin'):
            result = open_url_in_browser("  https://example.com/path\n")

            assert result is True
            mock_popen.assert_called_once_with(
                ["open", "https://example.com/path"]
            )
