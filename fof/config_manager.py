import os
import logging
import shutil

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
        return "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).rstrip()

    def persist_update(self, update_dir: str):
        """
        Atomically replace the current 'tree' directory with 'update_dir'.
        Handles chdir if currently inside tree dir to avoid errors.
        If update_dir does not exist or is empty, logs a warning and does nothing.
        """
        tree_dir = os.path.join(self.config_path, "tree")
        curdir = os.getcwd()

        # Check if update_dir exists and is non-empty
        if not os.path.exists(update_dir) or not os.path.isdir(update_dir) or not os.listdir(update_dir):
            logger.warning(f"'update' directory '{update_dir}' does not exist or is empty. Persist skipped.")
            return

        try:
            # If current working directory is inside tree_dir, move out before deleting tree_dir
            if os.path.commonpath([curdir, tree_dir]) == tree_dir:
                os.chdir(os.path.dirname(tree_dir))
            if os.path.exists(tree_dir):
                shutil.rmtree(tree_dir)
            os.rename(update_dir, tree_dir)
            logger.info(f"Persisted update: replaced '{tree_dir}' with '{update_dir}'.")
        finally:
            try:
                os.chdir(curdir)
            except FileNotFoundError:
                pass
