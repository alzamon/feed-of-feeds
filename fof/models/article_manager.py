import hashlib
import sqlite3
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta
import requests
import feedparser
import time
import json
from .article import Article


class ArticleManager:
    """Manages the state of read articles with persistence using SQLite and fetching logic."""
    
    def __init__(self, db_path: str = "~/.config/fof", db_filename: str = "articles.db"):
        """Initialize the ArticleManager.

        Args:
            db_path (str): Path to the database directory. Defaults to "~/.config/fof".
            db_filename (str): Name of the database file. Defaults to "articles.db".
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
        self.db_file = self.db_path / db_filename
        
        # Initialize the database
        self._initialize_database()
    
    def _initialize_database(self):
        """Create the articles and cache tables if they don't already exist."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                # Table for read articles
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS articles (
                        hash TEXT PRIMARY KEY
                    )
                """)
                # Table for article cache
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cache (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        content TEXT,
                        link TEXT NOT NULL,
                        author TEXT,
                        published_date TEXT,
                        feed_id TEXT,
                        feedpath TEXT,
                        read BOOLEAN DEFAULT 0,
                        score INTEGER,
                        cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    def store_articles(self, articles: List[Article]):
        """Store a list of articles in the cache, avoiding duplicates."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                for article in articles:
                    cursor.execute("""
                        INSERT OR REPLACE INTO cache (
                            id, title, content, link, author, published_date, 
                            feed_id, feedpath, read, score, cached_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        article.id,
                        article.title,
                        article.content,
                        article.link,
                        article.author,
                        article.published_date.isoformat() if article.published_date else None,
                        article.feed_id,
                        json.dumps(article.feedpath) if article.feedpath else None,
                        int(article.read),
                        article.score
                    ))
                conn.commit()
        except sqlite3.Error as e:
            print(f"Error storing articles in cache: {e}")

    def fetch_and_delete_article(self, article_id: str) -> Optional[Article]:
        """Fetch and delete an article from the cache."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM cache WHERE id = ?", (article_id,))
                row = cursor.fetchone()
                if row:
                    article = Article(
                        id=row[0],
                        title=row[1],
                        content=row[2],
                        link=row[3],
                        author=row[4],
                        published_date=datetime.fromisoformat(row[5]) if row[5] else None,
                        feed_id=row[6],
                        feedpath=json.loads(row[7]) if row[7] else None,
                        read=bool(row[8]),
                        score=row[9]
                    )
                    cursor.execute("DELETE FROM cache WHERE id = ?", (article_id,))
                    conn.commit()
                    return article
        except sqlite3.Error as e:
            print(f"Error fetching and deleting article from cache: {e}")
        return None

    def purge_articles_by_feedpath_and_date(self, feedpath: List[str], date: datetime) -> int:
        """Purge articles from the cache for a specific feedpath that were published before the given date."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM cache 
                    WHERE feedpath = ? AND published_date < ?
                """, (json.dumps(feedpath), date.isoformat()))
                deleted_count = cursor.rowcount
                conn.commit()
                return deleted_count
        except sqlite3.Error as e:
            print(f"Error purging articles from cache: {e}")
            return 0

    def fetch_unread_article(
        self, url: str, max_age: Optional[timedelta], feed_id: str, feedpath: List[str]
    ) -> Optional[Article]:
        """
        Fetch the first unread article from a feed URL. Check the cache first, purge old entries, 
        and fetch from the web if no suitable articles are found in the cache.

        Args:
            url (str): The RSS feed URL.
            max_age (Optional[timedelta]): The maximum age of articles to consider.
            feed_id (str): The ID of the feed.
            feedpath (List[str]): The feed's hierarchical path.

        Returns:
            Optional[Article]: The first unread article, or None if none are found.
        """
        try:
            # Step 1: Purge old articles from the cache if max_age is provided
            if max_age:
                cutoff_date = datetime.now() - max_age
                purged_count = self.purge_articles_by_feedpath_and_date(feedpath, cutoff_date)
                print(f"Purged {purged_count} old articles from the cache for feedpath: {feedpath}")

            # Step 2: Check the cache for an unread article
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM cache 
                    WHERE feedpath = ? 
                    ORDER BY published_date DESC LIMIT 1
                """, (json.dumps(feedpath),))
                row = cursor.fetchone()

                if row:
                    # Deserialize the cached article
                    cached_article = Article(
                        id=row[0],
                        title=row[1],
                        content=row[2],
                        link=row[3],
                        author=row[4],
                        published_date=datetime.fromisoformat(row[5]) if row[5] else None,
                        feed_id=row[6],
                        feedpath=json.loads(row[7]) if row[7] else None,
                        read=bool(row[8]),
                        score=row[9]
                    )

                    # Remove the article from the cache
                    cursor.execute("DELETE FROM cache WHERE id = ?", (cached_article.id,))
                    conn.commit()

                    # Mark the article as read
                    self.mark_as_read(cached_article.title, cached_article.content)

                    return cached_article

            # Step 3: Fetch articles from the web if the cache is empty
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            parsed = feedparser.parse(response.text)

            if not parsed.entries:
                return None

            articles_to_cache = []

            for entry in parsed.entries:
                title = entry.get('title', 'No Title')
                content = entry.get('summary', '')

                published_date = None
                if entry.get('published_parsed'):
                    published_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                elif entry.get('updated_parsed'):
                    published_date = datetime.fromtimestamp(time.mktime(entry.updated_parsed))

                if max_age and published_date and datetime.now() - published_date > max_age:
                    continue

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

                # Check if the article is already read
                if not self.is_read(title, content):
                    articles_to_cache.append(article)

            # Step 4: Store fetched articles in the cache
            self.store_articles(articles_to_cache)

            # Step 5: Return the first unread article from the fetched list
            for article in articles_to_cache:
                self.mark_as_read(article.title, article.content)
                return article

            return None

        except requests.exceptions.RequestException as e:
            print(f"Request error for feed {feed_id}: {e}")
            return None

        except Exception as e:
            print(f"Error fetching articles for feed {feed_id}: {e}")
            return None
