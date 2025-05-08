import hashlib
import sqlite3
from pathlib import Path

class ArticleManager:
    """Manages the state of read articles with persistence using SQLite."""
    
    def __init__(self, db_path: str = "~/.config/fof", db_filename: str = "read_articles.db"):
        """Initialize the ArticleManager.

        Args:
            db_path (str): Path to the database directory. Defaults to "~/.config/fof".
            db_filename (str): Name of the database file. Defaults to "read_articles.db".
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
        self.db_file = self.db_path / db_filename
        
        # Initialize the database
        self._initialize_database()
    
    def _initialize_database(self):
        """Create the articles table if it doesn't already exist."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS articles (
                        hash TEXT PRIMARY KEY
                    )
                """)
        except sqlite3.Error as e:
            print(f"Error initializing database: {e}")
    
    def _generate_hash(self, title: str, content: str) -> str:
        """Generate a hash based on the title and content of an article."""
        hasher = hashlib.sha256()
        hasher.update(title.encode('utf-8'))
        hasher.update(content.encode('utf-8'))
        return hasher.hexdigest()
    
    def is_read(self, title: str, content: str) -> bool:
        """Check if an article is already read."""
        article_hash = self._generate_hash(title, content)
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM articles WHERE hash = ?", (article_hash,))
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            print(f"Error checking article state: {e}")
            return False
    
    def mark_as_read(self, title: str, content: str):
        """Mark an article as read."""
        article_hash = self._generate_hash(title, content)
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO articles (hash) VALUES (?)", (article_hash,))
                conn.commit()
        except sqlite3.Error as e:
            print(f"Error marking article as read: {e}")
