import os
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Configuration manager that holds and validates the config path."""

    def __init__(self, config_path: str):
        self.config_path = config_path

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
            raise FileNotFoundError(f"'tree' directory not found at {tree_dir}.")
        return tree_dir

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """
        Remove or replace characters not suitable for filenames.
        """
        return "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).rstrip()

