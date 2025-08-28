"""Main synchronization manager that coordinates all sync operations."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from .peer_config import PeerManager, PeerConfig
from .device_manager import DeviceManager
from .article_sync import ArticleSyncManager
from .ssh_sync import SSHSyncManager

logger = logging.getLogger(__name__)


class SyncManager:
    """Main synchronization manager that coordinates multi-device sync operations."""
    
    def __init__(self, article_manager, config_path: str):
        """Initialize with article manager and config path."""
        self.article_manager = article_manager
        self.config_path = config_path
        
        # Initialize sub-managers
        self.device_manager = DeviceManager(config_path)
        self.peer_manager = PeerManager(config_path)
        
        # Get device name
        self.device_name = self.device_manager.get_device_name()
        
        # Initialize sync managers
        self.article_sync = ArticleSyncManager(article_manager, config_path, self.device_name)
        self.ssh_sync = SSHSyncManager(config_path, self.device_name)
    
    def sync_on_startup(self) -> None:
        """Perform sync operations on application startup."""
        logger.info("Starting sync on application startup")
        
        try:
            # Load peer configurations
            peers = self.peer_manager.load_peers()
            if not peers:
                logger.info("No peers configured, skipping sync")
                return
            
            # Pull from all peers
            downloaded_files = self.ssh_sync.pull_from_all_peers(peers)
            
            # Use cached files as fallback if no fresh downloads
            if not downloaded_files:
                logger.info("No fresh peer data downloaded, checking for cached files")
                downloaded_files = self.ssh_sync.get_cached_peer_files()
            
            # Import and merge articles from all available files
            total_merged = 0
            for file_path in downloaded_files:
                try:
                    merged_count = self.article_sync.import_and_merge_articles(file_path)
                    total_merged += merged_count
                except Exception as e:
                    logger.error(f"Error merging articles from {file_path}: {e}")
                    continue
            
            if total_merged > 0:
                logger.info(f"Startup sync completed: merged {total_merged} read articles")
            else:
                logger.info("Startup sync completed: no new articles to merge")
            
            # Cleanup old cache files
            self.ssh_sync.cleanup_cache()
            
        except Exception as e:
            logger.error(f"Error during startup sync: {e}")
            # Don't raise - sync failures shouldn't prevent app startup
    
    def sync_on_exit(self) -> None:
        """Perform sync operations on application exit."""
        logger.info("Starting sync on application exit")
        
        try:
            # Export local read articles
            local_file = self.article_sync.export_read_articles()
            
            # Load peer configurations
            peers = self.peer_manager.load_peers()
            if not peers:
                logger.info("No peers configured, export completed but no push")
                # Still update sync timestamp for local export
                self.article_sync.update_last_sync_timestamp()
                return
            
            # Push to all peers
            success_count = self.ssh_sync.push_to_all_peers(peers, local_file)
            
            if success_count > 0:
                logger.info(f"Exit sync completed: pushed to {success_count} peers")
                # Update last sync timestamp after successful push
                self.article_sync.update_last_sync_timestamp()
            else:
                logger.warning("Exit sync completed: failed to push to any peers")
                
        except Exception as e:
            logger.error(f"Error during exit sync: {e}")
            # Don't raise - sync failures shouldn't prevent app exit
    
    def manual_sync(self) -> Dict[str, int]:
        """
        Perform a manual sync operation (both pull and push).
        Returns dictionary with sync statistics.
        """
        logger.info("Starting manual sync operation")
        stats = {
            'pulled_peers': 0,
            'merged_articles': 0,
            'pushed_peers': 0
        }
        
        try:
            # Load peer configurations
            peers = self.peer_manager.load_peers()
            if not peers:
                logger.info("No peers configured for manual sync")
                return stats
            
            # Pull from all peers
            downloaded_files = self.ssh_sync.pull_from_all_peers(peers)
            stats['pulled_peers'] = len(downloaded_files)
            
            # Import and merge articles
            for file_path in downloaded_files:
                try:
                    merged_count = self.article_sync.import_and_merge_articles(file_path)
                    stats['merged_articles'] += merged_count
                except Exception as e:
                    logger.error(f"Error merging articles from {file_path}: {e}")
                    continue
            
            # Export and push local articles
            local_file = self.article_sync.export_read_articles()
            success_count = self.ssh_sync.push_to_all_peers(peers, local_file)
            stats['pushed_peers'] = success_count
            
            # Update last sync timestamp after successful operations
            if success_count > 0:
                self.article_sync.update_last_sync_timestamp()
            
            # Cleanup
            self.ssh_sync.cleanup_cache()
            
            logger.info(f"Manual sync completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error during manual sync: {e}")
            return stats
    
    def get_sync_status(self) -> Dict:
        """Get current sync status and configuration."""
        try:
            peers = self.peer_manager.load_peers()
            
            # Test connectivity to peers
            peer_status = {}
            for device_name, peer in peers.items():
                peer_status[device_name] = {
                    'host': peer.host,
                    'user': peer.user,
                    'port': peer.port,
                    'reachable': self.ssh_sync.check_ssh_connectivity(peer)
                }
            
            return {
                'device_name': self.device_name,
                'config_path': self.config_path,
                'peer_count': len(peers),
                'peers': peer_status
            }
            
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return {
                'device_name': self.device_name,
                'config_path': self.config_path,
                'error': str(e)
            }
    
    def add_peer(self, device_name: str, host: str, user: str, port: int = 22) -> None:
        """Add a new peer for synchronization."""
        self.peer_manager.add_peer(device_name, host, user, port)
        logger.info(f"Added peer: {device_name}@{host}:{port}")
    
    def remove_peer(self, device_name: str) -> bool:
        """Remove a peer from synchronization."""
        result = self.peer_manager.remove_peer(device_name)
        if result:
            logger.info(f"Removed peer: {device_name}")
        else:
            logger.warning(f"Peer not found: {device_name}")
        return result
    
    def list_peers(self) -> Dict[str, PeerConfig]:
        """List all configured peers."""
        return self.peer_manager.load_peers()
    
    def set_device_name(self, device_name: str) -> None:
        """Set the device name for this device."""
        self.device_manager.set_device_name(device_name)
        self.device_name = device_name
        
        # Update sync managers with new device name
        self.article_sync = ArticleSyncManager(
            self.article_manager, self.config_path, self.device_name
        )
        self.ssh_sync = SSHSyncManager(self.config_path, self.device_name)
        
        logger.info(f"Device name updated to: {device_name}")
    
    def get_device_name(self) -> str:
        """Get the current device name."""
        return self.device_name