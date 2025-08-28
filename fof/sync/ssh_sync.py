"""SSH/SCP synchronization functionality for multi-device sync."""

import os
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from .peer_config import PeerConfig

logger = logging.getLogger(__name__)


class SSHSyncManager:
    """Manages SSH/SCP-based file synchronization between devices."""
    
    def __init__(self, config_path: str, device_name: str):
        """Initialize with config path and device name."""
        self.config_path = Path(config_path).expanduser()
        self.device_name = device_name
        self.sync_dir = self.config_path / "sync"
        self.cache_dir = self.sync_dir / "cache"
        
        # Ensure directories exist
        self.sync_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def pull_from_peer(self, peer: PeerConfig, timeout: int = 30) -> Optional[str]:
        """
        Pull the peer's read articles file via SCP.
        Returns the local file path if successful, None otherwise.
        """
        try:
            # Remote file path (assuming same config structure)
            remote_file = f"~/.config/fof/sync/read_articles_on_{peer.device_name}.json"
            local_file = self.cache_dir / f"read_articles_on_{peer.device_name}.json"
            
            # Build SCP command
            scp_cmd = [
                "scp",
                "-o", "ConnectTimeout=10",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "LogLevel=ERROR",
                "-P", str(peer.port),
                f"{peer.user}@{peer.host}:{remote_file}",
                str(local_file)
            ]
            
            logger.debug(f"Pulling from {peer.device_name}: {' '.join(scp_cmd)}")
            
            # Execute SCP command
            result = subprocess.run(
                scp_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully pulled articles from {peer.device_name}")
                return str(local_file)
            else:
                logger.warning(f"Failed to pull from {peer.device_name}: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout pulling from {peer.device_name}")
            return None
        except Exception as e:
            logger.error(f"Error pulling from {peer.device_name}: {e}")
            return None
    
    def push_to_peer(self, peer: PeerConfig, local_file_path: str, timeout: int = 30) -> bool:
        """
        Push the local read articles file to a peer via SCP.
        Returns True if successful, False otherwise.
        """
        try:
            # Remote file path
            remote_file = f"~/.config/fof/sync/read_articles_on_{self.device_name}.json"
            
            # Ensure remote sync directory exists first
            mkdir_cmd = [
                "ssh",
                "-o", "ConnectTimeout=10", 
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "LogLevel=ERROR",
                "-p", str(peer.port),
                f"{peer.user}@{peer.host}",
                "mkdir -p ~/.config/fof/sync"
            ]
            
            subprocess.run(mkdir_cmd, capture_output=True, timeout=timeout)
            
            # Build SCP command
            scp_cmd = [
                "scp",
                "-o", "ConnectTimeout=10",
                "-o", "StrictHostKeyChecking=no", 
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "LogLevel=ERROR",
                "-P", str(peer.port),
                local_file_path,
                f"{peer.user}@{peer.host}:{remote_file}"
            ]
            
            logger.debug(f"Pushing to {peer.device_name}: {' '.join(scp_cmd)}")
            
            # Execute SCP command
            result = subprocess.run(
                scp_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully pushed articles to {peer.device_name}")
                return True
            else:
                logger.warning(f"Failed to push to {peer.device_name}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout pushing to {peer.device_name}")
            return False
        except Exception as e:
            logger.error(f"Error pushing to {peer.device_name}: {e}")
            return False
    
    def pull_from_all_peers(self, peers: Dict[str, PeerConfig]) -> List[str]:
        """
        Pull read articles from all peers.
        Returns list of successfully downloaded file paths.
        """
        downloaded_files = []
        
        for device_name, peer in peers.items():
            logger.info(f"Pulling articles from peer: {device_name}")
            
            try:
                file_path = self.pull_from_peer(peer)
                if file_path:
                    downloaded_files.append(file_path)
            except Exception as e:
                logger.error(f"Error pulling from {device_name}: {e}")
                # Continue with other peers
                continue
        
        logger.info(f"Successfully pulled from {len(downloaded_files)} peers")
        return downloaded_files
    
    def push_to_all_peers(self, peers: Dict[str, PeerConfig], local_file_path: str) -> int:
        """
        Push local read articles file to all peers.
        Returns number of successful pushes.
        """
        success_count = 0
        
        for device_name, peer in peers.items():
            logger.info(f"Pushing articles to peer: {device_name}")
            
            try:
                if self.push_to_peer(peer, local_file_path):
                    success_count += 1
            except Exception as e:
                logger.error(f"Error pushing to {device_name}: {e}")
                # Continue with other peers
                continue
        
        logger.info(f"Successfully pushed to {success_count} peers")
        return success_count
    
    def cleanup_cache(self, keep_latest: int = 5) -> None:
        """Clean up old cached files, keeping only the latest ones."""
        try:
            # Get all cached files
            cached_files = list(self.cache_dir.glob("read_articles_on_*.json"))
            
            if len(cached_files) <= keep_latest:
                return
                
            # Sort by modification time (newest first)
            cached_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # Remove old files
            for old_file in cached_files[keep_latest:]:
                try:
                    old_file.unlink()
                    logger.debug(f"Removed old cache file: {old_file}")
                except OSError as e:
                    logger.warning(f"Error removing cache file {old_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
    
    def check_ssh_connectivity(self, peer: PeerConfig) -> bool:
        """Test SSH connectivity to a peer. Returns True if reachable."""
        try:
            # Simple SSH test command
            test_cmd = [
                "ssh",
                "-o", "ConnectTimeout=5",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null", 
                "-o", "LogLevel=ERROR",
                "-p", str(peer.port),
                f"{peer.user}@{peer.host}",
                "echo 'test'"
            ]
            
            result = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return result.returncode == 0
            
        except Exception:
            return False
    
    def get_cached_peer_files(self) -> List[str]:
        """Get list of cached peer files for fallback purposes."""
        try:
            cached_files = list(self.cache_dir.glob("read_articles_on_*.json"))
            return [str(f) for f in cached_files if f.name != f"read_articles_on_{self.device_name}.json"]
        except Exception as e:
            logger.error(f"Error getting cached peer files: {e}")
            return []