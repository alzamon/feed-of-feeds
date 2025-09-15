"""Tests for application configuration functionality."""
import tempfile
import os
import json
import pytest

from fof.app_config import AppConfig, DEFAULT_SESSION_TIMEOUT


def test_app_config_default_values():
    """Test that app config uses default values when no config file exists."""
    with tempfile.TemporaryDirectory() as temp_dir:
        app_config = AppConfig(temp_dir)
        assert app_config.session_timeout == DEFAULT_SESSION_TIMEOUT


def test_app_config_load_existing():
    """Test loading configuration from existing file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = os.path.join(temp_dir, "app.json")
        test_config = {"session_timeout": 600}
        
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
        
        app_config = AppConfig(temp_dir)
        assert app_config.session_timeout == 600


def test_app_config_save():
    """Test saving configuration to file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        app_config = AppConfig(temp_dir)
        app_config.session_timeout = 900
        app_config.save_config()
        
        config_file = os.path.join(temp_dir, "app.json")
        assert os.path.exists(config_file)
        
        with open(config_file, 'r') as f:
            saved_config = json.load(f)
        
        assert saved_config["session_timeout"] == 900


def test_app_config_session_timeout_validation():
    """Test that session timeout validation works."""
    with tempfile.TemporaryDirectory() as temp_dir:
        app_config = AppConfig(temp_dir)
        
        # Valid values should work
        app_config.session_timeout = 300
        assert app_config.session_timeout == 300
        
        # Zero and negative values should raise ValueError
        with pytest.raises(ValueError):
            app_config.session_timeout = 0
        
        with pytest.raises(ValueError):
            app_config.session_timeout = -1


def test_app_config_get_set():
    """Test generic get/set functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        app_config = AppConfig(temp_dir)
        
        # Test setting and getting arbitrary keys
        app_config.set("test_key", "test_value")
        assert app_config.get("test_key") == "test_value"
        
        # Test default value for missing key
        assert app_config.get("missing_key", "default") == "default"


def test_app_config_invalid_json():
    """Test handling of invalid JSON in config file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = os.path.join(temp_dir, "app.json")
        
        # Write invalid JSON
        with open(config_file, 'w') as f:
            f.write("{invalid json}")
        
        # Should fall back to defaults without crashing
        app_config = AppConfig(temp_dir)
        assert app_config.session_timeout == DEFAULT_SESSION_TIMEOUT