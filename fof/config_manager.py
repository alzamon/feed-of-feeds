import os
import logging
import shutil
import json
from .time_period import parse_time_period

logger = logging.getLogger(__name__)

# Constants
BACKUP_SUFFIX = ".backup"
DEFAULT_SESSION_TIMEOUT = "5m"  # 5 minutes


class ConfigManager:
    """Configuration manager that holds and validates the config path."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.app_config_file = os.path.join(config_path, "app.json")
        self._app_config = {}
        self._load_app_config()

    def _load_app_config(self) -> None:
        """Load application configuration from file or create default."""
        if os.path.exists(self.app_config_file):
            try:
                with open(self.app_config_file, 'r') as f:
                    self._app_config = json.load(f)
                logger.info(
                    f"Loaded app config from {self.app_config_file}"
                )
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(
                    f"Failed to load app config: {e}. Using defaults."
                )
                self._app_config = {}
        else:
            logger.info("No app config file found. Using defaults.")
            self._app_config = {}

        # Ensure default values are set
        if "session_timeout" not in self._app_config:
            self._app_config["session_timeout"] = DEFAULT_SESSION_TIMEOUT



    def get_session_timeout_seconds(self) -> int:
        """Get session timeout in seconds."""
        timeout_str = self._app_config.get(
            "session_timeout", DEFAULT_SESSION_TIMEOUT
        )
        if timeout_str == "0" or timeout_str == 0:
            return 0  # Disabled
        try:
            # Support both time period strings ("5m", "1h") and plain numbers
            if (isinstance(timeout_str, str) and
                    any(c in timeout_str for c in 'dhms')):
                return int(parse_time_period(timeout_str).total_seconds())
            else:
                # Legacy support: plain number assumed to be minutes
                return int(timeout_str) * 60
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid session timeout value: {timeout_str}. "
                f"Using default."
            )
            return int(
                parse_time_period(DEFAULT_SESSION_TIMEOUT).total_seconds()
            )



    @property
    def get_tree_dir(self) -> str:
        """
        Returns the path to the 'tree' directory in the config path.
        Validates that it exists and is a directory.
        Raises FileNotFoundError if missing.
        """
        tree_dir = os.path.join(self.config_path, "tree")
        if not os.path.exists(tree_dir) or not os.path.isdir(tree_dir):
            logger.error(f"'tree' directory not found at {tree_dir}.")
            raise FileNotFoundError(
                f"'tree' directory not found at {tree_dir}."
            )
        return tree_dir

    @property
    def get_update_dir(self) -> str:
        """
        Returns the path to the 'update' directory in the config path.
        Does not require that it exists.
        """
        return os.path.join(self.config_path, "update")

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """
        Remove or replace characters not suitable for filenames.
        """
        return "".join(
            c for c in name if c.isalnum() or c in (' ', '_', '-')
        ).rstrip()

    def persist_update(self, update_dir: str):
        """
        Replace the 'tree' directory with 'update_dir' atomically.
        Does nothing if 'update_dir' is missing or empty.
        """
        tree_dir = os.path.join(self.config_path, "tree")

        # Check if update_dir exists and is non-empty
        if (not os.path.exists(update_dir)
                or not os.path.isdir(update_dir)
                or not os.listdir(update_dir)):
            logger.warning(
                f"'update' directory '{update_dir}' does not exist or is "
                f"empty. Persist skipped."
            )
            return

        # Create backup for rollback if needed
        backup_dir = None
        try:
            if os.path.exists(tree_dir):
                backup_dir = tree_dir + BACKUP_SUFFIX
                if os.path.exists(backup_dir):
                    shutil.rmtree(backup_dir)
                os.rename(tree_dir, backup_dir)

            # Atomically move update to tree
            os.rename(update_dir, tree_dir)

            # Clean up backup on success
            if backup_dir and os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)

            logger.info(
                f"Persisted update: replaced '{tree_dir}' with "
                f"'{update_dir}'."
            )
        except Exception as e:
            logger.error(f"Error during persist_update: {e}")
            # Rollback if possible
            if backup_dir and os.path.exists(backup_dir):
                try:
                    if os.path.exists(tree_dir):
                        shutil.rmtree(tree_dir)
                    os.rename(backup_dir, tree_dir)
                    logger.info("Rolled back to previous tree directory")
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback: {rollback_error}")
            raise
