"""Test that errors are written to fof.log."""

import logging
import os
import shutil
import sys
import tempfile
import json
import pytest
from unittest.mock import patch
from fof.cli import main


@pytest.fixture
def test_config_dir():
    """Create a temporary test configuration directory with a basic config."""
    test_dir = tempfile.mkdtemp()
    tree_dir = os.path.join(test_dir, 'tree')
    os.makedirs(tree_dir)

    union_config = {
        "feed_type": "union",
        "id": "root",
        "title": "Root Feed",
        "description": "Root union feed for testing",
        "max_age": "7d",
        "weights": {}
    }
    with open(os.path.join(tree_dir, 'union.fof'), 'w') as f:
        json.dump(union_config, f)

    yield test_dir

    # Reset the root logger handlers so the log file is not locked
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)

    shutil.rmtree(test_dir)


def test_exception_is_logged_to_fof_log(test_config_dir):
    """Verify that an exception in the control loop is written to fof.log."""
    log_file = os.path.join(test_config_dir, 'fof.log')

    with patch('sys.argv', ['fof', '--config', test_config_dir]):
        with patch('fof.cli.ControlLoop') as mock_control_loop:
            mock_instance = mock_control_loop.return_value
            mock_instance.start.side_effect = RuntimeError(
                "test error sentinel"
            )

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

    assert os.path.exists(log_file), "fof.log was not created"

    with open(log_file, 'r') as f:
        log_contents = f.read()

    assert "test error sentinel" in log_contents, (
        "Exception message was not written to fof.log"
    )
    assert "ERROR" in log_contents, (
        "Log entry should have ERROR level"
    )
