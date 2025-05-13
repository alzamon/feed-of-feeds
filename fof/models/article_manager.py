import hashlib
import sqlite3
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta
import requests
import feedparser
import time
from .article import Article


class ArticleManager:
    """Manages the state of read articles with persistence using SQLite and fetching logic."""
    
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

    def fetch_unread_article(
        self, url: str, max_age: Optional[timedelta], feed_id: str, feedpath: List[str]
    ) -> Optional[Article]:
        """Fetch the first unread article from a feed URL.

        Args:
            url (str): The RSS feed URL.
            max_age (Optional[timedelta]): The maximum age of articles to consider.
            feed_id (str): The ID of the feed.
            feedpath (List[str]): The feed's hierarchical path.

        Returns:
            Optional[Article]: The first unread article, or None if none are found.
        """
        try:
            # Fetch feed data with a timeout
            response = requests.get(url, timeout=5)  # Set timeout to 5 seconds
            response.raise_for_status()  # Raise an HTTPError if the HTTP request returned an unsuccessful status code

            # Parse the feed
            parsed = feedparser.parse(response.text)
            
            if not parsed.entries:
                return None
            
            for entry in parsed.entries:
                title = entry.get('title', 'No Title')
                content = entry.get('summary', '')

                # Handle published date conversion using time.mktime
                published_date = None
                if entry.get('published_parsed'):
                    published_date = datetime.fromtimestamp(
                        time.mktime(entry.published_parsed)
                    )
                elif entry.get('updated_parsed'):
                    published_date = datetime.fromtimestamp(
                        time.mktime(entry.updated_parsed)
                    )

                # Check if the article is too old
                if max_age and published_date:
                    if datetime.now() - published_date > max_age:
                        continue

                # Check if the article is already read
                if not self.is_read(title, content):
                    article_id = entry.get('id', entry.get('link', ''))
                    link = entry.get('link', '')
                    author = entry.get('author', 'Unknown')

                    # Create the article object
                    article = Article(
                        id=article_id,
                        title=title,
                        content=content,
                        link=link,
                        author=author,
                        published_date=published_date,
                        feed_id=feed_id,
                        feedpath=feedpath,
                    )

                    # Mark the article as read
                    self.mark_as_read(title, content)

                    return article
            
            return None
        
        except requests.exceptions.RequestException as e:
            print(f"Request error for feed {feed_id}: {e}")
            return None
        
        except Exception as e:
            # Log the error and return None
            print(f"Error fetching articles for feed {feed_id}: {e}")
            return None
