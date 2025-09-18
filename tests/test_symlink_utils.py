"""Tests for symlink preservation utilities."""
import os
import tempfile
import shutil
import unittest
from pathlib import Path

from fof.symlink_utils import (
    discover_symlinks,
    copy_symlinks_to_update_dir,
    is_path_symlinked,
    preserve_symlinks_for_update,
    validate_symlink_integrity
)


class TestSymlinkUtils(unittest.TestCase):
    """Test symlink preservation utilities."""

    def setUp(self):
        """Set up test directories and symlinks."""
        self.test_dir = tempfile.mkdtemp()
        self.tree_dir = os.path.join(self.test_dir, "tree")
        self.update_dir = os.path.join(self.test_dir, "update")

        # Create tree directory structure
        os.makedirs(self.tree_dir)

        # Create some regular directories and files
        os.makedirs(os.path.join(self.tree_dir, "regular_dir"))
        with open(os.path.join(self.tree_dir, "regular_file.txt"), "w") as f:
            f.write("regular content")

        # Create target directory outside tree
        self.external_target = os.path.join(self.test_dir, "external")
        os.makedirs(self.external_target)
        with open(os.path.join(self.external_target, "target_file.txt"), "w") as f:
            f.write("target content")

        # Create symlinks
        self.symlink_dir = os.path.join(self.tree_dir, "symlinked_dir")
        self.symlink_file = os.path.join(self.tree_dir, "symlinked_file.txt")

        os.symlink(self.external_target, self.symlink_dir)
        os.symlink(os.path.join(self.external_target, "target_file.txt"), self.symlink_file)

        # Create nested symlink
        nested_dir = os.path.join(self.tree_dir, "nested")
        os.makedirs(nested_dir)
        self.nested_symlink = os.path.join(nested_dir, "nested_symlink")
        os.symlink("../regular_dir", self.nested_symlink)

    def tearDown(self):
        """Clean up test directories."""
        shutil.rmtree(self.test_dir)

    def test_discover_symlinks(self):
        """Test symlink discovery."""
        symlinks = discover_symlinks(self.tree_dir)

        # Should find all symlinks with correct relative paths
        expected = {
            "symlinked_dir": self.external_target,
            "symlinked_file.txt": os.path.join(self.external_target, "target_file.txt"),
            "nested/nested_symlink": "../regular_dir"
        }

        self.assertEqual(len(symlinks), 3)
        for rel_path, target in expected.items():
            self.assertIn(rel_path, symlinks)
            self.assertEqual(symlinks[rel_path], target)

    def test_discover_symlinks_empty_dir(self):
        """Test symlink discovery in directory with no symlinks."""
        empty_dir = os.path.join(self.test_dir, "empty")
        os.makedirs(empty_dir)

        symlinks = discover_symlinks(empty_dir)
        self.assertEqual(len(symlinks), 0)

    def test_discover_symlinks_nonexistent_dir(self):
        """Test symlink discovery in nonexistent directory."""
        nonexistent = os.path.join(self.test_dir, "nonexistent")

        symlinks = discover_symlinks(nonexistent)
        self.assertEqual(len(symlinks), 0)

    def test_copy_symlinks_to_update_dir(self):
        """Test copying symlinks to update directory."""
        # First discover symlinks
        symlinks = discover_symlinks(self.tree_dir)

        # Copy them to update directory
        os.makedirs(self.update_dir)
        copied = copy_symlinks_to_update_dir(symlinks, self.tree_dir, self.update_dir)

        # Check that all symlinks were copied
        self.assertEqual(len(copied), 3)

        # Verify symlinks exist and point to correct targets
        for rel_path in copied:
            update_path = os.path.join(self.update_dir, rel_path)
            self.assertTrue(os.path.islink(update_path))

            # Check that target matches original
            original_path = os.path.join(self.tree_dir, rel_path)
            self.assertEqual(os.readlink(update_path), os.readlink(original_path))

    def test_is_path_symlinked(self):
        """Test path symlink checking."""
        preserved_symlinks = {"symlinked_dir", "nested/nested_symlink"}

        # Direct symlink paths
        symlink_path = os.path.join(self.update_dir, "symlinked_dir")
        self.assertTrue(is_path_symlinked(symlink_path, self.update_dir, preserved_symlinks))

        # Child of symlinked directory
        child_path = os.path.join(self.update_dir, "symlinked_dir", "child")
        self.assertTrue(is_path_symlinked(child_path, self.update_dir, preserved_symlinks))

        # Regular path
        regular_path = os.path.join(self.update_dir, "regular_dir")
        self.assertFalse(is_path_symlinked(regular_path, self.update_dir, preserved_symlinks))

    def test_preserve_symlinks_for_update(self):
        """Test complete symlink preservation workflow."""
        # Run the complete preservation workflow
        preserved = preserve_symlinks_for_update(self.tree_dir, self.update_dir)

        # Check that update directory was created
        self.assertTrue(os.path.exists(self.update_dir))

        # Check that all symlinks were preserved
        self.assertEqual(len(preserved), 3)

        # Verify each symlink exists in update directory
        for rel_path in preserved:
            update_path = os.path.join(self.update_dir, rel_path)
            self.assertTrue(os.path.islink(update_path))

    def test_validate_symlink_integrity_valid(self):
        """Test symlink validation with all valid symlinks."""
        result = validate_symlink_integrity(self.tree_dir)
        self.assertTrue(result)

    def test_validate_symlink_integrity_broken(self):
        """Test symlink validation with broken symlinks."""
        # Create a broken symlink
        broken_symlink = os.path.join(self.tree_dir, "broken_symlink")
        os.symlink("/nonexistent/path", broken_symlink)

        result = validate_symlink_integrity(self.tree_dir)
        self.assertFalse(result)

    def test_relative_symlinks(self):
        """Test handling of relative symlinks."""
        # Create a relative symlink
        rel_symlink = os.path.join(self.tree_dir, "rel_symlink")
        os.symlink("regular_dir", rel_symlink)

        # Discover symlinks
        symlinks = discover_symlinks(self.tree_dir)

        # Should include the relative symlink
        self.assertIn("rel_symlink", symlinks)
        self.assertEqual(symlinks["rel_symlink"], "regular_dir")

        # Validate that it's considered valid
        result = validate_symlink_integrity(self.tree_dir)
        self.assertTrue(result)

    def test_nested_directory_symlinks(self):
        """Test symlinks in nested directories."""
        # Create deeper nesting
        deep_dir = os.path.join(self.tree_dir, "level1", "level2")
        os.makedirs(deep_dir)

        deep_symlink = os.path.join(deep_dir, "deep_symlink")
        os.symlink("../../regular_dir", deep_symlink)

        # Discover symlinks
        symlinks = discover_symlinks(self.tree_dir)

        # Should find the deep symlink
        self.assertIn("level1/level2/deep_symlink", symlinks)

        # Validate integrity
        result = validate_symlink_integrity(self.tree_dir)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
