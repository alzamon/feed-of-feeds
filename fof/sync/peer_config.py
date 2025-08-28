"""Peer configuration management for multi-device sync."""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PeerConfig:
    """Configuration for a sync peer device."""
    device_name: str
    host: str
    user: str
    port: int = 22
    
    def __post_init__(self):
        """Validate peer configuration."""
        if not self.device_name:
            raise ValueError("device_name cannot be empty")
        if not self.host:
            raise ValueError("host cannot be empty") 
        if not self.user:
            raise ValueError("user cannot be empty")
        if not isinstance(self.port, int) or self.port <= 0:
            raise ValueError("port must be a positive integer")


class PeerManager:
    """Manages peer configuration for multi-device sync."""
    
    def __init__(self, config_path: str):
        """Initialize with config path."""
        self.config_path = Path(config_path).expanduser()
        self.peers_file = self.config_path / "peers.json"
        
    def load_peers(self) -> Dict[str, PeerConfig]:
        """Load peer configurations from peers.json."""
        if not self.peers_file.exists():
            logger.info(f"No peers configuration found at {self.peers_file}")
            return {}
            
        try:
            with open(self.peers_file, 'r') as f:
                peers_data = json.load(f)
                
            peers = {}
            for device_name, config in peers_data.items():
                try:
                    peers[device_name] = PeerConfig(
                        device_name=device_name,
                        host=config['host'],
                        user=config['user'],
                        port=config.get('port', 22)
                    )
                except (KeyError, ValueError) as e:
                    logger.error(f"Invalid peer config for {device_name}: {e}")
                    continue
                    
            logger.info(f"Loaded {len(peers)} peer configurations")
            return peers
            
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Error loading peers configuration: {e}")
            return {}
    
    def save_peers(self, peers: Dict[str, PeerConfig]) -> None:
        """Save peer configurations to peers.json."""
        try:
            # Ensure config directory exists
            self.config_path.mkdir(parents=True, exist_ok=True)
            
            # Convert to JSON format
            peers_data = {}
            for device_name, peer in peers.items():
                peers_data[device_name] = {
                    'host': peer.host,
                    'user': peer.user,
                    'port': peer.port
                }
                
            with open(self.peers_file, 'w') as f:
                json.dump(peers_data, f, indent=2)
                
            logger.info(f"Saved {len(peers)} peer configurations")
            
        except OSError as e:
            logger.error(f"Error saving peers configuration: {e}")
            raise
    
    def add_peer(self, device_name: str, host: str, user: str, port: int = 22) -> None:
        """Add a new peer configuration."""
        peers = self.load_peers()
        peers[device_name] = PeerConfig(device_name, host, user, port)
        self.save_peers(peers)
        
    def remove_peer(self, device_name: str) -> bool:
        """Remove a peer configuration. Returns True if peer was found and removed."""
        peers = self.load_peers()
        if device_name in peers:
            del peers[device_name]
            self.save_peers(peers)
            return True
        return False
    
    def get_peer(self, device_name: str) -> Optional[PeerConfig]:
        """Get configuration for a specific peer."""
        peers = self.load_peers()
        return peers.get(device_name)