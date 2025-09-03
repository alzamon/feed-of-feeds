import os
import logging
import shutil

logger = logging.getLogger(__name__)

# Constants
BACKUP_SUFFIX = ".backup"


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
