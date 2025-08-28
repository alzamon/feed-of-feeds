"""Device identity management for multi-device sync."""

import json
import os
import logging
from pathlib import Path
import socket

logger = logging.getLogger(__name__)


class DeviceManager:
    """Manages device identity for multi-device sync."""
    
    def __init__(self, config_path: str):
        """Initialize with config path."""
        self.config_path = Path(config_path).expanduser()
        self.device_file = self.config_path / "device.json"
        
    def get_device_name(self) -> str:
        """Get the current device name, creating one if needed."""
        if self.device_file.exists():
            try:
                with open(self.device_file, 'r') as f:
                    data = json.load(f)
                    return data.get('device_name', self._generate_device_name())
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Error reading device config: {e}, generating new device name")
                
        return self._generate_device_name()
    
    def set_device_name(self, device_name: str) -> None:
        """Set the device name."""
        if not device_name:
            raise ValueError("Device name cannot be empty")
            
        try:
            # Ensure config directory exists
            self.config_path.mkdir(parents=True, exist_ok=True)
            
            data = {'device_name': device_name}
            with open(self.device_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Set device name to: {device_name}")
            
        except OSError as e:
            logger.error(f"Error saving device config: {e}")
            raise
    
    def _generate_device_name(self) -> str:
        """Generate a default device name based on hostname."""
        try:
            hostname = socket.gethostname()
            # Clean hostname for use as device name
            device_name = ''.join(c for c in hostname if c.isalnum() or c in '_-')
            if not device_name:
                device_name = "unknown_device"
                
            # Save the generated name
            self.set_device_name(device_name)
            return device_name
            
        except Exception as e:
            logger.warning(f"Error generating device name: {e}")
            return "unknown_device"