"""Tests for sync functionality."""

import pytest
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from fof.sync.peer_config import PeerConfig, PeerManager
from fof.sync.device_manager import DeviceManager
from fof.sync.article_sync import ArticleMetadata, ArticleSyncManager
from fof.sync.sync_manager import SyncManager


class TestPeerConfig:
    """Test peer configuration."""
    
    def test_peer_config_creation(self):
        """Test creating a valid peer config."""
        peer = PeerConfig("laptop", "192.168.1.100", "user", 22)
        assert peer.device_name == "laptop"
        assert peer.host == "192.168.1.100"
        assert peer.user == "user"
        assert peer.port == 22
    
    def test_peer_config_validation(self):
        """Test peer config validation."""
        with pytest.raises(ValueError):
            PeerConfig("", "host", "user")  # Empty device name
            
        with pytest.raises(ValueError):
            PeerConfig("device", "", "user")  # Empty host
            
        with pytest.raises(ValueError):
            PeerConfig("device", "host", "")  # Empty user
            
        with pytest.raises(ValueError):
            PeerConfig("device", "host", "user", 0)  # Invalid port


class TestPeerManager:
    """Test peer management."""
    
    def test_load_peers_empty(self):
        """Test loading peers when no config exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PeerManager(tmpdir)
            peers = manager.load_peers()
            assert peers == {}
    
    def test_save_and_load_peers(self):
        """Test saving and loading peer configurations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PeerManager(tmpdir)
            
            # Add some peers
            peer1 = PeerConfig("laptop", "192.168.1.100", "user1", 22)
            peer2 = PeerConfig("desktop", "192.168.1.101", "user2", 2222)
            peers = {"laptop": peer1, "desktop": peer2}
            
            manager.save_peers(peers)
            
            # Load and verify
            loaded_peers = manager.load_peers()
            assert len(loaded_peers) == 2
            assert loaded_peers["laptop"].device_name == "laptop"
            assert loaded_peers["laptop"].host == "192.168.1.100"
            assert loaded_peers["desktop"].port == 2222
    
    def test_add_remove_peer(self):
        """Test adding and removing peers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PeerManager(tmpdir)
            
            # Add peer
            manager.add_peer("test", "localhost", "testuser", 2222)
            peers = manager.load_peers()
            assert "test" in peers
            assert peers["test"].port == 2222
            
            # Remove peer
            result = manager.remove_peer("test")
            assert result is True
            
            peers = manager.load_peers()
            assert "test" not in peers
            
            # Remove non-existent peer
            result = manager.remove_peer("nonexistent")
            assert result is False


class TestDeviceManager:
    """Test device management."""
    
    def test_device_name_generation(self):
        """Test device name generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DeviceManager(tmpdir)
            name = manager.get_device_name()
            assert isinstance(name, str)
            assert len(name) > 0
    
    def test_set_device_name(self):
        """Test setting device name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DeviceManager(tmpdir)
            
            manager.set_device_name("my-device")
            name = manager.get_device_name()
            assert name == "my-device"
    
    def test_device_name_persistence(self):
        """Test device name persistence across instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager1 = DeviceManager(tmpdir)
            manager1.set_device_name("persistent-device")
            
            manager2 = DeviceManager(tmpdir)
            name = manager2.get_device_name()
            assert name == "persistent-device"


class TestArticleMetadata:
    """Test article metadata handling."""
    
    def test_article_metadata_creation(self):
        """Test creating article metadata."""
        metadata = ArticleMetadata(
            guid="test-guid",
            url="https://example.com/article",
            title="Test Article",
            read_timestamp="2024-01-01T12:00:00",
            feed_id="test-feed",
            author="Test Author"
        )
        
        assert metadata.guid == "test-guid"
        assert metadata.url == "https://example.com/article"
        assert metadata.title == "Test Article"
    
    def test_article_metadata_serialization(self):
        """Test converting metadata to/from dict."""
        metadata = ArticleMetadata(
            guid="test-guid",
            url="https://example.com/article", 
            title="Test Article",
            read_timestamp="2024-01-01T12:00:00"
        )
        
        data = metadata.to_dict()
        assert data["guid"] == "test-guid"
        assert data["url"] == "https://example.com/article"
        
        metadata2 = ArticleMetadata.from_dict(data)
        assert metadata2.guid == metadata.guid
        assert metadata2.url == metadata.url


class TestArticleSyncManager:
    """Test article synchronization."""
    
    def test_export_read_articles(self):
        """Test exporting read articles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock article manager
            mock_article_manager = MagicMock()
            mock_article_manager.db_file = Path(tmpdir) / "test.db"
            
            sync_manager = ArticleSyncManager(mock_article_manager, tmpdir, "test-device")
            
            # Mock database query results
            with patch.object(sync_manager, '_get_read_articles_from_db') as mock_query:
                mock_query.return_value = [
                    {
                        'id': 'article-1',
                        'title': 'Test Article 1', 
                        'link': 'https://example.com/1',
                        'read': '2024-01-01T12:00:00',
                        'feed_id': 'test-feed',
                        'author': 'Test Author'
                    }
                ]
                
                file_path = sync_manager.export_read_articles()
                assert os.path.exists(file_path)
                assert "read_articles_on_test-device.json" in file_path
                
                # Verify file content
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                assert data['device_name'] == 'test-device'
                assert len(data['articles']) == 1
                assert data['articles'][0]['guid'] == 'article-1'


@pytest.fixture
def mock_article_manager():
    """Create a mock article manager for testing."""
    mock = MagicMock()
    mock.db_file = "/tmp/test.db"
    return mock


class TestSyncManager:
    """Test the main sync manager."""
    
    def test_sync_manager_initialization(self, mock_article_manager):
        """Test sync manager initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync_manager = SyncManager(mock_article_manager, tmpdir)
            
            assert sync_manager.config_path == tmpdir
            assert isinstance(sync_manager.device_name, str)
    
    def test_get_sync_status(self, mock_article_manager):
        """Test getting sync status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync_manager = SyncManager(mock_article_manager, tmpdir)
            
            status = sync_manager.get_sync_status()
            
            assert 'device_name' in status
            assert 'config_path' in status
            assert 'peer_count' in status
            assert status['peer_count'] == 0
    
    def test_peer_management(self, mock_article_manager):
        """Test peer management through sync manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync_manager = SyncManager(mock_article_manager, tmpdir)
            
            # Add peer
            sync_manager.add_peer("test-peer", "localhost", "testuser", 2222)
            
            # List peers
            peers = sync_manager.list_peers()
            assert "test-peer" in peers
            assert peers["test-peer"].port == 2222
            
            # Remove peer
            result = sync_manager.remove_peer("test-peer")
            assert result is True
            
            peers = sync_manager.list_peers()
            assert "test-peer" not in peers