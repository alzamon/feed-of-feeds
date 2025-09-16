"""Tests for session timeout functionality in ConfigManager."""
import tempfile
import os
import json
import pytest

from fof.config_manager import ConfigManager, DEFAULT_SESSION_TIMEOUT
from fof.cli import parse_session_timeout


def test_config_manager_session_timeout_defaults():
    """Test that config manager uses default session timeout when no config file exists."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = ConfigManager(temp_dir)
        assert config_manager.get_session_timeout_seconds() == 300  # 5 minutes


def test_config_manager_session_timeout_time_period_parsing():
    """Test that config manager correctly parses time period strings from config file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = os.path.join(temp_dir, "app.json")
        
        # Test loading different time periods from config file
        test_config = {"session_timeout": "10m"}
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
        
        config_manager = ConfigManager(temp_dir)
        assert config_manager.get_session_timeout_seconds() == 600
        
        # Test loading hour format
        test_config = {"session_timeout": "1h"}
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
            
        config_manager = ConfigManager(temp_dir)
        assert config_manager.get_session_timeout_seconds() == 3600


def test_config_manager_session_timeout_integer_minutes():
    """Test that config manager handles integer minutes from config file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = os.path.join(temp_dir, "app.json")
        
        # Test loading with integer (minutes) from config file
        test_config = {"session_timeout": 10}
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
            
        config_manager = ConfigManager(temp_dir)
        assert config_manager.get_session_timeout_seconds() == 600


def test_config_manager_session_timeout_disabled():
    """Test that setting timeout to 0 in config disables it."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = os.path.join(temp_dir, "app.json")
        
        # Test disabled timeout from config file
        test_config = {"session_timeout": 0}
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
            
        config_manager = ConfigManager(temp_dir)
        assert config_manager.get_session_timeout_seconds() == 0
        
        # Test disabled timeout with string
        test_config = {"session_timeout": "0"}
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
            
        config_manager = ConfigManager(temp_dir)
        assert config_manager.get_session_timeout_seconds() == 0





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


def test_cli_parse_session_timeout():
    """Test CLI session timeout parsing function."""
    # Test time period strings
    assert parse_session_timeout("5m") == 300
    assert parse_session_timeout("1h") == 3600
    assert parse_session_timeout("30s") == 30
    assert parse_session_timeout("1h30m") == 5400
    
    # Test plain numbers (minutes)
    assert parse_session_timeout("10") == 600
    assert parse_session_timeout(10) == 600
    
    # Test disabled
    assert parse_session_timeout("0") == 0
    assert parse_session_timeout(0) == 0
    
    # Test invalid values
    with pytest.raises(ValueError):
        parse_session_timeout("invalid")
    
    with pytest.raises(ValueError):
        parse_session_timeout(-1)