"""Platform-specific quirks and functionality for cross-platform support."""
import platform
import subprocess


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
        # For Linux/Ubuntu, use 'xdg-open' command
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
