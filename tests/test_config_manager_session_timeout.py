"""Tests for session timeout functionality in ConfigManager."""
import tempfile
import os
import json
import pytest

from fof.config_manager import ConfigManager, DEFAULT_SESSION_TIMEOUT


def test_config_manager_session_timeout_defaults():
    """Test that config manager uses default session timeout when no config file exists."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = ConfigManager(temp_dir)
        assert config_manager.get_session_timeout_seconds() == 300  # 5 minutes


def test_config_manager_session_timeout_time_period_parsing():
    """Test that config manager correctly parses time period strings."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = ConfigManager(temp_dir)
        
        # Test setting different time periods
        config_manager.set_session_timeout("10m")
        assert config_manager.get_session_timeout_seconds() == 600
        
        config_manager.set_session_timeout("1h")
        assert config_manager.get_session_timeout_seconds() == 3600
        
        config_manager.set_session_timeout("30s")
        assert config_manager.get_session_timeout_seconds() == 30
        
        config_manager.set_session_timeout("1h30m")
        assert config_manager.get_session_timeout_seconds() == 5400


def test_config_manager_session_timeout_integer_minutes():
    """Test that config manager handles integer minutes for backward compatibility."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = ConfigManager(temp_dir)
        
        # Test setting with integer (minutes)
        config_manager.set_session_timeout(10)
        assert config_manager.get_session_timeout_seconds() == 600


def test_config_manager_session_timeout_disabled():
    """Test that setting timeout to 0 disables it."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = ConfigManager(temp_dir)
        
        config_manager.set_session_timeout(0)
        assert config_manager.get_session_timeout_seconds() == 0
        
        config_manager.set_session_timeout("0")
        assert config_manager.get_session_timeout_seconds() == 0


def test_config_manager_session_timeout_validation():
    """Test that session timeout validation works."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = ConfigManager(temp_dir)
        
        # Negative values should raise ValueError
        with pytest.raises(ValueError):
            config_manager.set_session_timeout(-1)
        
        # Invalid time period strings should raise ValueError
        with pytest.raises(ValueError):
            config_manager.set_session_timeout("invalid")


def test_config_manager_session_timeout_persistence():
    """Test that session timeout settings are persisted."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a config manager and set timeout
        config_manager1 = ConfigManager(temp_dir)
        config_manager1.set_session_timeout("15m")
        
        # Create a new config manager and verify it loads the saved value
        config_manager2 = ConfigManager(temp_dir)
        assert config_manager2.get_session_timeout_seconds() == 900


def test_config_manager_session_timeout_load_existing():
    """Test loading session timeout from existing config file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = os.path.join(temp_dir, "app.json")
        test_config = {"session_timeout": "20m"}
        
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
        
        config_manager = ConfigManager(temp_dir)
        assert config_manager.get_session_timeout_seconds() == 1200


def test_config_manager_session_timeout_invalid_json():
    """Test handling of invalid JSON in config file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = os.path.join(temp_dir, "app.json")
        
        # Write invalid JSON
        with open(config_file, 'w') as f:
            f.write("{invalid json}")
        
        # Should fall back to defaults without crashing
        config_manager = ConfigManager(temp_dir)
        assert config_manager.get_session_timeout_seconds() == 300


def test_config_manager_session_timeout_legacy_format():
    """Test handling of legacy format (plain numbers) in existing config."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = os.path.join(temp_dir, "app.json")
        # Legacy format: plain number representing minutes
        test_config = {"session_timeout": 15}
        
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
        
        config_manager = ConfigManager(temp_dir)
        assert config_manager.get_session_timeout_seconds() == 900  # 15 minutes