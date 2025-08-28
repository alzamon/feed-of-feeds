"""Article metadata synchronization for multi-device sync."""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ArticleMetadata:
    """Represents metadata for a read article."""
    
    def __init__(self, guid: str, url: str, title: str, read_timestamp: str, 
                 feed_id: Optional[str] = None, author: Optional[str] = None):
        self.guid = guid
        self.url = url
        self.title = title
        self.read_timestamp = read_timestamp
        self.feed_id = feed_id
        self.author = author
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'guid': self.guid,
            'url': self.url,
            'title': self.title,
            'read_timestamp': self.read_timestamp,
            'feed_id': self.feed_id,
            'author': self.author
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ArticleMetadata':
        """Create from dictionary."""
        return cls(
            guid=data['guid'],
            url=data['url'],
            title=data['title'],
            read_timestamp=data['read_timestamp'],
            feed_id=data.get('feed_id'),
            author=data.get('author')
        )


class ArticleSyncManager:
    """Manages article metadata synchronization."""
    
    def __init__(self, article_manager, config_path: str, device_name: str):
        """Initialize with article manager, config path, and device name."""
        self.article_manager = article_manager
        self.config_path = Path(config_path).expanduser()
        self.device_name = device_name
        self.sync_dir = self.config_path / "sync"
    
    def export_read_articles(self) -> str:
        """Export all read articles metadata to JSON file. Returns the file path."""
        try:
            # Ensure sync directory exists
            self.sync_dir.mkdir(parents=True, exist_ok=True)
            
            # Query all read articles from database
            read_articles = self._get_read_articles_from_db()
            
            # Convert to metadata format
            metadata_list = []
            for article_data in read_articles:
                metadata = ArticleMetadata(
                    guid=article_data['id'],  # Using ID as GUID
                    url=article_data['link'],
                    title=article_data['title'],
                    read_timestamp=article_data['read'],
                    feed_id=article_data['feed_id'],
                    author=article_data['author']
                )
                metadata_list.append(metadata.to_dict())
            
            # Save to file
            filename = f"read_articles_on_{self.device_name}.json"
            file_path = self.sync_dir / filename
            
            export_data = {
                'device_name': self.device_name,
                'export_timestamp': datetime.now().isoformat(),
                'articles': metadata_list
            }
            
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Exported {len(metadata_list)} read articles to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error exporting read articles: {e}")
            raise
    
    def import_and_merge_articles(self, peer_file_path: str) -> int:
        """Import and merge read articles from a peer file. Returns number of articles merged."""
        try:
            with open(peer_file_path, 'r') as f:
                peer_data = json.load(f)
            
            peer_device = peer_data.get('device_name', 'unknown')
            peer_articles = peer_data.get('articles', [])
            
            if not peer_articles:
                logger.info(f"No articles to import from {peer_device}")
                return 0
            
            # Get currently read articles for deduplication
            existing_read = self._get_read_article_identifiers()
            
            # Process each peer article
            merged_count = 0
            for article_data in peer_articles:
                try:
                    metadata = ArticleMetadata.from_dict(article_data)
                    
                    # Check if already marked as read (deduplicate by guid first, then url)
                    if metadata.guid in existing_read or metadata.url in existing_read:
                        continue
                    
                    # Try to find the article in our database and mark as read
                    if self._mark_article_as_read_by_identifier(metadata):
                        merged_count += 1
                        existing_read.add(metadata.guid)
                        existing_read.add(metadata.url)
                        
                except Exception as e:
                    logger.warning(f"Error processing article from {peer_device}: {e}")
                    continue
            
            logger.info(f"Merged {merged_count} read articles from {peer_device}")
            return merged_count
            
        except Exception as e:
            logger.error(f"Error importing articles from {peer_file_path}: {e}")
            raise
    
    def _get_read_articles_from_db(self) -> List[Dict]:
        """Get all read articles from the database."""
        try:
            with sqlite3.connect(self.article_manager.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, title, link, author, read, feed_id
                    FROM cache 
                    WHERE read IS NOT NULL
                    ORDER BY read DESC
                """)
                
                columns = ['id', 'title', 'link', 'author', 'read', 'feed_id']
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error querying read articles: {e}")
            return []
    
    def _get_read_article_identifiers(self) -> Set[str]:
        """Get set of identifiers (guids/urls) for already read articles."""
        try:
            with sqlite3.connect(self.article_manager.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, link FROM cache WHERE read IS NOT NULL
                """)
                
                identifiers = set()
                for row in cursor.fetchall():
                    identifiers.add(row[0])  # id (guid)
                    identifiers.add(row[1])  # link (url)
                return identifiers
                
        except sqlite3.Error as e:
            logger.error(f"Error querying read article identifiers: {e}")
            return set()
    
    def _mark_article_as_read_by_identifier(self, metadata: ArticleMetadata) -> bool:
        """Mark an article as read by finding it via guid or url. Returns True if found and marked."""
        try:
            with sqlite3.connect(self.article_manager.db_file) as conn:
                cursor = conn.cursor()
                
                # Try to find by guid (id) first
                cursor.execute("SELECT id FROM cache WHERE id = ? AND read IS NULL", (metadata.guid,))
                result = cursor.fetchone()
                
                if result:
                    # Mark as read using the existing timestamp from peer
                    cursor.execute(
                        "UPDATE cache SET read = ? WHERE id = ?",
                        (metadata.read_timestamp, metadata.guid)
                    )
                    conn.commit()
                    logger.debug(f"Marked article as read by guid: {metadata.guid}")
                    return True
                
                # Try to find by URL if guid didn't match
                cursor.execute("SELECT id FROM cache WHERE link = ? AND read IS NULL", (metadata.url,))
                result = cursor.fetchone()
                
                if result:
                    article_id = result[0]
                    cursor.execute(
                        "UPDATE cache SET read = ? WHERE id = ?",
                        (metadata.read_timestamp, article_id)
                    )
                    conn.commit()
                    logger.debug(f"Marked article as read by url: {metadata.url}")
                    return True
                
                # Article not found in local database
                logger.debug(f"Article not found locally: {metadata.guid} / {metadata.url}")
                return False
                
        except sqlite3.Error as e:
            logger.error(f"Error marking article as read: {e}")
            return False