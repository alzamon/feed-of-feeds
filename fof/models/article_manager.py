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
from ..error_logger import log_error_with_readkey


class ArticleManager:
    """Manages the state of articles with persistence using SQLite and fetching logic."""

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
        """Create the cache table if it doesn't already exist."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                self._create_cache_table(cursor)
        except sqlite3.Error as e:
            log_error_with_readkey(f"Error initializing database: {e}")

    def _create_cache_table(self, cursor):
        """Create the cache table."""
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
                read TIMESTAMP DEFAULT NULL,
                score INTEGER,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def mark_as_read(self, article_id: str):
        """Mark an article as read by updating the 'read' column with the current timestamp."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE cache SET read = ? WHERE id = ?",
                    (datetime.now().isoformat(), article_id)
                )
                conn.commit()
        except sqlite3.Error as e:
            log_error_with_readkey(f"Error marking article as read: {e}")

    def cache_articles(self, articles: List[Article]):
        """Store a list of articles in the cache, avoiding duplicates."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                for article in articles:
                    self._insert_or_replace_article(cursor, article)
                conn.commit()
        except sqlite3.Error as e:
            log_error_with_readkey(f"Error storing articles in cache: {e}")


    def _insert_or_replace_article(self, cursor, article: Article):
        """Insert or replace a single article into the cache, preserving the 'read' status if it exists."""
        cursor.execute("""
            INSERT INTO cache (
                id, title, content, link, author, published_date, 
                feed_id, feedpath, read, score, cached_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, (SELECT read FROM cache WHERE id = ?), ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                content=excluded.content,
                link=excluded.link,
                author=excluded.author,
                published_date=excluded.published_date,
                feed_id=excluded.feed_id,
                feedpath=excluded.feedpath,
                score=excluded.score,
                cached_at=excluded.cached_at
        """, (
            article.id,
            article.title,
            article.content,
            article.link,
            article.author,
            article.published_date.isoformat() if article.published_date else None,
            article.feed_id,
            json.dumps(article.feedpath) if article.feedpath else None,
            article.id,  # Used to fetch existing 'read' value
            article.score
        ))

    def fetch_article(self, feedpath: List[str], url: str, feed_id: str, max_age: Optional[timedelta]) -> Optional[Article]:
        """
        Fetch the newest unread article by feedpath. If none exist in the cache, fetch from the source,
        cache the articles, and then retrieve the newest unread article.

        Args:
            feedpath (List[str]): The feed's hierarchical path.
            url (str): The RSS feed URL.
            feed_id (str): The ID of the feed.
            max_age (Optional[timedelta]): The maximum age of articles to consider.

        Returns:
            Optional[Article]: The newest unread article, or None if none are found.
        """
        # Fetch the newest unread article from the cache
        article = self._fetch_article_from_cache(feedpath)
        
        # If an article is found in the cache, mark it as read
        if article:
            self.mark_as_read(article.id)
            return article

        # If no unread articles in the cache, fetch from the source
        articles = self._fetch_articles_from_web(url, feed_id, feedpath, max_age)
        self.cache_articles(articles)

        # Retrieve the newest unread article from the cache
        article = self._fetch_article_from_cache(feedpath)
        if article:
            self.mark_as_read(article.id)
        return article

    def _fetch_article_from_cache(self, feedpath: List[str]) -> Optional[Article]:
        """Fetch the newest unread article from the cache by feedpath."""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM cache 
                WHERE feedpath = ? AND read IS NULL 
                ORDER BY published_date DESC LIMIT 1
            """, (json.dumps(feedpath),))
            row = cursor.fetchone()
            if row:
                return self._row_to_article(row)
        return None

    def _row_to_article(self, row) -> Article:
        """Convert a database row to an Article object."""
        return Article(
            id=row[0],
            title=row[1],
            content=row[2],
            link=row[3],
            author=row[4],
            published_date=datetime.fromisoformat(row[5]) if row[5] else None,
            feed_id=row[6],
            feedpath=json.loads(row[7]) if row[7] else None,
            read=datetime.fromisoformat(row[8]) if row[8] else None,
            score=row[9]
        )

    def _fetch_articles_from_web(self, url: str, feed_id: str, feedpath: List[str], max_age: Optional[timedelta]) -> List[Article]:
        """Fetch articles from the web and return them as a list."""
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        parsed = feedparser.parse(response.text)

        articles = []
        if parsed.entries:
            for entry in parsed.entries:
                article = self._create_article_from_entry(entry, feed_id, feedpath, max_age)
                if article:
                    articles.append(article)
        return articles

    def _create_article_from_entry(self, entry, feed_id: str, feedpath: List[str], max_age: Optional[timedelta]) -> Optional[Article]:
        """Convert an RSS feed entry into an Article object."""
        title = entry.get('title', 'No Title')
        content = entry.get('summary', '')
        published_date = None

        if entry.get('published_parsed'):
            published_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
        elif entry.get('updated_parsed'):
            published_date = datetime.fromtimestamp(time.mktime(entry.updated_parsed))

        if max_age and published_date and datetime.now() - published_date > max_age:
            return None

        article_id = entry.get('id', entry.get('link', ''))
        link = entry.get('link', '')
        author = entry.get('author', 'Unknown')

        return Article(
            id=article_id,
            title=title,
            content=content,
            link=link,
            author=author,
            published_date=published_date,
            feed_id=feed_id,
            feedpath=feedpath,
        )
