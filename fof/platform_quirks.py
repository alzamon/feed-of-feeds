"""Platform-specific quirks and functionality for cross-platform support."""
import os
import platform
import subprocess


def is_termux():
    """
    Detect whether we are running inside a Termux environment.

    Termux sets the PREFIX environment variable to a path under
    /data/data/com.termux, which is a reliable indicator that is present
    regardless of whether termux-open-url is on PATH.

    Returns:
        bool: True if running inside Termux, False otherwise
    """
    prefix = os.environ.get("PREFIX", "")
    return "com.termux" in prefix


def get_browser_open_command(url):
    """
    Get the platform-specific command to open a URL in the default browser.

    Args:
        url (str): The URL to open

    Returns:
        list: Command and arguments as a list suitable for subprocess

    Raises:
        RuntimeError: If the platform is not supported
    """
    system = platform.system().lower()

    if system == "windows":
        # For Windows (including Git-Bash), use 'start' command
        return ["start", url]
    elif system == "darwin":
        # For macOS, use 'open' command
        return ["open", url]
    elif system == "linux":
        if is_termux():
            # On Termux there is no display server ($DISPLAY/$WAYLAND_DISPLAY
            # are unset), so xdg-open exhausts all its handlers and exits with
            # a failure code that the caller never sees (stderr is redirected).
            # termux-open-url talks directly to Android's activity manager and
            # works without a display server.
            return ["termux-open-url", url]
        # For standard Linux/Ubuntu, use 'xdg-open' command
        return ["xdg-open", url]
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


def open_url_in_browser(url):
    """
    Open a URL in the default browser using platform-specific commands.

    Args:
        url (str): The URL to open

    Returns:
        bool: True if the command was executed successfully, False otherwise
    """
    try:
        url = url.strip()
        command = get_browser_open_command(url)

        # For Linux, redirect output to avoid cluttering the terminal
        if platform.system().lower() == "linux":
            # Run in background with output redirected to devnull
            subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            # For Windows and macOS, run normally
            subprocess.Popen(command)

        return True
    except (OSError, RuntimeError):
        # Log the error but don't raise it - browser opening is not critical
        # The calling code should handle the return value appropriately
        return False
