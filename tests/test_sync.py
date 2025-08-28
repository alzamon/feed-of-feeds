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

    def test_sync_timestamp_filtering(self):
        """Test that only articles read after last sync are exported."""
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            # Create mock article manager with test database
            db_file = temp_dir / "test.db"
            article_manager = MagicMock()
            article_manager.db_file = str(db_file)
            
            # Create test database with articles
            import sqlite3
            from datetime import datetime, timedelta
            
            # Create the database and table structure
            with sqlite3.connect(str(db_file)) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE cache (
                        id TEXT PRIMARY KEY,
                        title TEXT,
                        link TEXT,
                        author TEXT,
                        read TEXT,
                        feed_id TEXT
                    )
                """)
                
                # Insert test articles with different read timestamps
                now = datetime.now()
                old_time = (now - timedelta(hours=2)).isoformat()
                recent_time = (now - timedelta(minutes=10)).isoformat()
                
                test_articles = [
                    ("article1", "Old Article", "http://example.com/1", "Author1", old_time, "feed1"),
                    ("article2", "Recent Article", "http://example.com/2", "Author2", recent_time, "feed1"),
                    ("article3", "Unread Article", "http://example.com/3", "Author3", None, "feed1"),
                ]
                
                cursor.executemany(
                    "INSERT INTO cache (id, title, link, author, read, feed_id) VALUES (?, ?, ?, ?, ?, ?)",
                    test_articles
                )
                conn.commit()
            
            # Create sync manager and sync timestamp manager
            config_path = temp_dir / "config"
            sync_manager = ArticleSyncManager(article_manager, str(config_path), "test-device")
            
            # First export (no previous sync) - should export all read articles
            export_file = sync_manager.export_read_articles()
            with open(export_file, 'r') as f:
                export_data = json.load(f)
            
            assert len(export_data['articles']) == 2  # Both read articles
            article_ids = [a['guid'] for a in export_data['articles']]
            assert "article1" in article_ids
            assert "article2" in article_ids
            
            # Set last sync timestamp to 1 hour ago
            one_hour_ago = (now - timedelta(hours=1)).isoformat()
            sync_manager._set_last_sync_timestamp(one_hour_ago)
            
            # Second export - should only export recent article
            export_file2 = sync_manager.export_read_articles()
            with open(export_file2, 'r') as f:
                export_data2 = json.load(f)
            
            assert len(export_data2['articles']) == 1  # Only recent article
            assert export_data2['articles'][0]['guid'] == "article2"
            
            # Update sync timestamp to current time
            sync_manager.update_last_sync_timestamp()
            
            # Mark another article as read after the sync timestamp
            with sqlite3.connect(str(db_file)) as conn:
                cursor = conn.cursor()
                future_time = (now + timedelta(minutes=5)).isoformat()
                cursor.execute(
                    "UPDATE cache SET read = ? WHERE id = ?",
                    (future_time, "article3")
                )
                conn.commit()
            
            # Third export - should only export the newly read article
            export_file3 = sync_manager.export_read_articles()
            with open(export_file3, 'r') as f:
                export_data3 = json.load(f)
            
            assert len(export_data3['articles']) == 1  # Only newly read article
            assert export_data3['articles'][0]['guid'] == "article3"