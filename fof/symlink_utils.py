"""Utilities for preserving symlinks during configuration updates.

This module provides functionality to discover, copy, and track symlinks
in the feed tree directory structure to ensure they are preserved during
atomic configuration updates.
"""
import os
import logging
import shutil
from typing import Set, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


def discover_symlinks(tree_dir: str) -> Dict[str, str]:
    """
    Recursively discover all symlinks in a directory tree.

    Args:
        tree_dir: Root directory to scan for symlinks

    Returns:
        Dictionary mapping relative paths to symlink targets.
        Keys are relative paths from tree_dir, values are the symlink targets.
    """
    symlinks = {}
    tree_path = Path(tree_dir)

    if not tree_path.exists():
        logger.warning(f"Tree directory does not exist: {tree_dir}")
        return symlinks

    try:
        for root, dirs, files in os.walk(tree_dir, followlinks=False):
            # Check directories for symlinks
            for dirname in dirs[:]:  # Use slice copy to allow modification
                dir_path = os.path.join(root, dirname)
                if os.path.islink(dir_path):
                    rel_path = os.path.relpath(dir_path, tree_dir)
                    target = os.readlink(dir_path)
                    symlinks[rel_path] = target
                    logger.debug(
                        f"Found symlink directory: {rel_path} -> {target}"
                    )
                    # Don't descend into symlinked directories
                    dirs.remove(dirname)

            # Check files for symlinks
            for filename in files:
                file_path = os.path.join(root, filename)
                if os.path.islink(file_path):
                    rel_path = os.path.relpath(file_path, tree_dir)
                    target = os.readlink(file_path)
                    symlinks[rel_path] = target
                    logger.debug(
                        f"Found symlink file: {rel_path} -> {target}"
                    )

    except (OSError, ValueError) as e:
        logger.error(f"Error scanning for symlinks in {tree_dir}: {e}")

    logger.info(f"Discovered {len(symlinks)} symlinks in {tree_dir}")
    return symlinks


def copy_symlinks_to_update_dir(
    symlinks: Dict[str, str], tree_dir: str, update_dir: str
) -> Set[str]:
    """
    Copy symlinks from tree directory to update directory.

    Args:
        symlinks: Dictionary of relative_path -> target mappings
        tree_dir: Original tree directory
        update_dir: Target update directory

    Returns:
        Set of relative paths that were successfully copied as symlinks
    """
    copied_symlinks = set()

    for rel_path, target in symlinks.items():
        update_path = os.path.join(update_dir, rel_path)

        try:
            # Create parent directories if they don't exist
            parent_dir = os.path.dirname(update_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            # Create the symlink
            os.symlink(target, update_path)
            copied_symlinks.add(rel_path)
            logger.debug(f"Copied symlink: {rel_path} -> {target}")

        except (OSError, ValueError) as e:
            logger.error(f"Failed to copy symlink {rel_path}: {e}")
            continue

    logger.info(
        f"Successfully copied {len(copied_symlinks)} symlinks to "
        f"update directory"
    )
    return copied_symlinks


def is_path_symlinked(
    path: str, update_dir: str, preserved_symlinks: Set[str]
) -> bool:
    """
    Check if a path (relative to update_dir) is already preserved as a symlink.

    Args:
        path: Absolute path in the update directory
        update_dir: Root update directory path
        preserved_symlinks: Set of relative paths that are preserved symlinks

    Returns:
        True if the path or any parent path is a preserved symlink
    """
    try:
        rel_path = os.path.relpath(path, update_dir)

        # Check if this exact path is a symlink
        if rel_path in preserved_symlinks:
            return True

        # Check if any parent path is a symlink
        path_parts = Path(rel_path).parts
        for i in range(1, len(path_parts)):
            parent_path = os.path.join(*path_parts[:i])
            if parent_path in preserved_symlinks:
                return True

    except ValueError:
        # Path is not relative to update_dir
        pass

    return False


def preserve_symlinks_for_update(tree_dir: str, update_dir: str) -> Set[str]:
    """
    Complete symlink preservation workflow for atomic updates.

    This function:
    1. Discovers all symlinks in the tree directory
    2. Copies them to the update directory
    3. Returns the set of preserved symlink paths

    Args:
        tree_dir: Original tree directory
        update_dir: Update directory being prepared

    Returns:
        Set of relative paths that are preserved as symlinks
    """
    # Discover symlinks in the original tree first
    symlinks = discover_symlinks(tree_dir)

    if not symlinks:
        logger.debug("No symlinks found in tree directory")
        return set()

    logger.info(f"Preserving {len(symlinks)} symlinks from {tree_dir} to {update_dir}")

    # Ensure update directory exists
    os.makedirs(update_dir, exist_ok=True)

    # Copy symlinks to update directory
    preserved_symlinks = copy_symlinks_to_update_dir(
        symlinks, tree_dir, update_dir
    )

    logger.info(
        f"Symlink preservation complete: {len(preserved_symlinks)} "
        "symlinks preserved"
    )
    return preserved_symlinks


def post_process_symlinks(
    update_dir: str, tree_dir: str, preserved_symlinks: Set[str]
) -> None:
    """
    Post-process the update directory to restore symlinks where appropriate.

    This function:
    1. Scans for directories in update_dir that should be symlinks
    2. Removes those directories and replaces them with the preserved symlinks
    3. Handles cases where feed titles differ from original directory names

    Args:
        update_dir: The update directory with serialized content
        tree_dir: The original tree directory
        preserved_symlinks: Set of relative paths that should be symlinks
    """
    # Build a mapping of original symlink targets to their relative paths
    symlink_targets = {}
    for rel_path in preserved_symlinks:
        original_symlink = os.path.join(tree_dir, rel_path)
        if os.path.islink(original_symlink):
            target = os.readlink(original_symlink)
            # Store the mapping: target -> relative path in tree
            symlink_targets[target] = rel_path

    # Scan update directory for directories that might need to be replaced with symlinks
    for root, dirs, files in os.walk(update_dir):
        rel_root = os.path.relpath(root, update_dir)
        if rel_root == ".":
            rel_root = ""

        for dirname in dirs[:]:  # Use slice to allow modification during iteration
            dir_path = os.path.join(root, dirname)
            rel_path = os.path.join(rel_root, dirname) if rel_root else dirname

            # Check if this path should be a symlink
            if rel_path in preserved_symlinks:
                # Remove the serialized directory
                if os.path.exists(dir_path):
                    shutil.rmtree(dir_path)

                # Restore the symlink
                original_symlink = os.path.join(tree_dir, rel_path)
                if os.path.islink(original_symlink):
                    target = os.readlink(original_symlink)
                    os.symlink(target, dir_path)
                    logger.info(f"Restored symlink: {rel_path} -> {target}")

                # Don't descend into this directory since it's now a symlink
                dirs.remove(dirname)


def validate_symlink_integrity(tree_dir: str) -> bool:
    """
    Validate that all symlinks in the tree directory are valid.

    Args:
        tree_dir: Directory to validate

    Returns:
        True if all symlinks are valid, False if any broken symlinks found
    """
    symlinks = discover_symlinks(tree_dir)
    broken_symlinks = []

    for rel_path, target in symlinks.items():
        symlink_path = os.path.join(tree_dir, rel_path)

        # Check if the symlink target exists
        if os.path.isabs(target):
            # Absolute target
            target_exists = os.path.exists(target)
        else:
            # Relative target - resolve relative to symlink location
            symlink_dir = os.path.dirname(symlink_path)
            abs_target = os.path.join(symlink_dir, target)
            target_exists = os.path.exists(abs_target)

        if not target_exists:
            broken_symlinks.append(rel_path)
            logger.warning(f"Broken symlink detected: {rel_path} -> {target}")

    if broken_symlinks:
        logger.error(
            f"Found {len(broken_symlinks)} broken symlinks in {tree_dir}"
        )
        return False

    logger.info(f"All {len(symlinks)} symlinks in {tree_dir} are valid")
    return True
