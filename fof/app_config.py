"""Application-level configuration management for FoF."""
import json
import os
import logging
from typing import Optional


logger = logging.getLogger(__name__)

DEFAULT_SESSION_TIMEOUT = 300  # 5 minutes in seconds


class AppConfig:
    """Manages application-level configuration settings."""

    def __init__(self, config_path: str):
        """Initialize application config manager.
        
        Args:
            config_path: Base configuration directory path
        """
        self.config_path = config_path
        self.config_file = os.path.join(config_path, "app.json")
        self._config = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file or create default if it doesn't exist."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self._config = json.load(f)
                logger.info(f"Loaded app config from {self.config_file}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load app config: {e}. Using defaults.")
                self._config = {}
        else:
            logger.info("No app config file found. Using defaults.")
            self._config = {}

        # Ensure default values are set
        if "session_timeout" not in self._config:
            self._config["session_timeout"] = DEFAULT_SESSION_TIMEOUT

    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            os.makedirs(self.config_path, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
            logger.info(f"Saved app config to {self.config_file}")
        except IOError as e:
            logger.error(f"Failed to save app config: {e}")

    @property
    def session_timeout(self) -> int:
        """Get session timeout in seconds."""
        return self._config.get("session_timeout", DEFAULT_SESSION_TIMEOUT)

    @session_timeout.setter
    def session_timeout(self, value: int) -> None:
        """Set session timeout in seconds."""
        if value <= 0:
            raise ValueError("Session timeout must be positive")
        self._config["session_timeout"] = value

    def get(self, key: str, default=None):
        """Get a configuration value."""
        return self._config.get(key, default)

    def set(self, key: str, value) -> None:
        """Set a configuration value."""
        self._config[key] = value