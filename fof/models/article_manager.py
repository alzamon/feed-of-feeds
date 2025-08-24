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

import logging

logger = logging.getLogger(__name__)

class ArticleManager:
    """Manages the state of articles with persistence using SQLite and fetching logic."""

    def __init__(self, config_manager, db_filename: str = "articles.db"):
        self.config_manager = config_manager
        self.db_path = Path(self.config_manager.config_path).expanduser()
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.db_file = self.db_path / db_filename

        self._initialize_database()

    def _initialize_database(self):
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                # Always create the table if it does not exist
                self._create_cache_table(cursor)
                # Now check for missing columns and add them if necessary
                cursor.execute("PRAGMA table_info(cache)")
                columns = [row[1] for row in cursor.fetchall()]
                if "fetched" not in columns:
                    cursor.execute("ALTER TABLE cache ADD COLUMN fetched TIMESTAMP DEFAULT NULL")
                if "tags" not in columns:
                    cursor.execute("ALTER TABLE cache ADD COLUMN tags TEXT DEFAULT NULL")
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {e}")

    def _create_cache_table(self, cursor):
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
                fetched TIMESTAMP DEFAULT NULL,
                score INTEGER,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tags TEXT DEFAULT NULL
            )
        """)

    def mark_as_read(self, article_id: str):
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE cache SET read = ? WHERE id = ?",
                    (datetime.now().isoformat(), article_id)
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error marking article as read: {e}")

    def mark_as_fetched(self, article_id: str):
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE cache SET fetched = ? WHERE id = ?",
                    (datetime.now().isoformat(), article_id)
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error marking article as fetched: {e}")

    def cache_articles(self, articles: List[Article]):
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                for article in articles:
                    self._insert_or_replace_article(cursor, article)
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error storing articles in cache: {e}")

    def _insert_or_replace_article(self, cursor, article: Article):
        cursor.execute("""
            INSERT INTO cache (
                id, title, content, link, author, published_date, 
                feed_id, feedpath, read, fetched, score, cached_at, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 
                      (SELECT read FROM cache WHERE id = ?), 
                      (SELECT fetched FROM cache WHERE id = ?), 
                      ?, CURRENT_TIMESTAMP, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                content=excluded.content,
                link=excluded.link,
                author=excluded.author,
                published_date=excluded.published_date,
                feed_id=excluded.feed_id,
                feedpath=excluded.feedpath,
                score=excluded.score,
                cached_at=excluded.cached_at,
                tags=excluded.tags
        """, (
            article.id,
            article.title,
            article.content,
            article.link,
            article.author,
            article.published_date.isoformat() if article.published_date else None,
            article.feed_id,
            json.dumps(article.feedpath) if article.feedpath is not None else None,
            article.id,  # Used to fetch existing 'read' value
            article.id,  # Used to fetch existing 'fetched' value
            article.score,
            json.dumps(article.tags) if article.tags else None
        ))

    def fetch_article(self, feedpath: List[str], url: str, feed_id: str, max_age: Optional[timedelta]) -> Optional[Article]:
        article = self._fetch_unfetched_article_from_cache(feedpath, max_age)
        if article:
            self.mark_as_fetched(article.id)
            return article
        articles = self._fetch_articles_from_web(url, feed_id, feedpath, max_age)
        self.cache_articles(articles)
        article = self._fetch_unfetched_article_from_cache(feedpath, max_age)
        if article:
            self.mark_as_fetched(article.id)
        return article

    def _fetch_unfetched_article_from_cache(self, feedpath: List[str], max_age: Optional[timedelta]) -> Optional[Article]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            sql = """
                SELECT * FROM cache 
                WHERE feedpath = ? AND fetched IS NULL AND read IS NULL
            """
            params = [json.dumps(feedpath)]
            if max_age:
                sql += " AND published_date >= ?"
                min_date = (datetime.now() - max_age).isoformat()
                params.append(min_date)
            sql += " ORDER BY published_date DESC LIMIT 1"
            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()
            if row:
                return self._row_to_article(row)
        return None

    def _row_to_article(self, row) -> Article:
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
            score=row[10],
            tags=json.loads(row[12]) if row[12] else []
        )

    def _fetch_articles_from_web(self, url: str, feed_id: str, feedpath: List[str], max_age: Optional[timedelta]) -> List[Article]:
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

        # Extract tags from entry if available (RSS feeds may provide tags/categories)
        tags = []
        if 'tags' in entry:
            tags = [tag['term'] for tag in entry['tags'] if 'term' in tag]

        return Article(
            id=article_id,
            title=title,
            content=content,
            link=link,
            author=author,
            published_date=published_date,
            feed_id=feed_id,
            feedpath=feedpath,
            tags=tags
        )

    def get_previous_read_article(self, current_read_timestamp: Optional[str] = None) -> Optional[Article]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            if current_read_timestamp:
                cursor.execute("""
                    SELECT * FROM cache
                    WHERE read IS NOT NULL AND read < ?
                    ORDER BY read DESC
                    LIMIT 1
                """, (current_read_timestamp,))
            else:
                cursor.execute("""
                    SELECT * FROM cache
                    WHERE read IS NOT NULL
                    ORDER BY read DESC
                    LIMIT 1
                """)
            row = cursor.fetchone()
            if row:
                return self._row_to_article(row)
        return None

    def get_next_read_article(self, current_read_timestamp: str) -> Optional[Article]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM cache
                WHERE read IS NOT NULL AND read > ?
                ORDER BY read ASC
                LIMIT 1
            """, (current_read_timestamp,))
            row = cursor.fetchone()
            if row:
                return self._row_to_article(row)
        return None

    def clear_cache(self, feed) -> int:
        """
        Clear cached articles for the exact feedpath of the given feed (SyndicationFeed).
        Returns the number of rows deleted.
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                fp_json = json.dumps(feed.feedpath)
                cursor.execute("DELETE FROM cache WHERE feedpath = ?", (fp_json,))
                deleted = cursor.rowcount
                conn.commit()
                logger.info(f"Cleared {deleted} articles from cache for feedpath {feed.feedpath}.")
                return deleted
        except sqlite3.Error as e:
            logger.error(f"Error clearing cache: {e}")
            return 0

    def purge_old_articles(self, feed) -> int:
        """
        Purge old articles for a feed based on its purge_age.
        Articles older than purge_age (based on published_date) will be deleted.
        If purge_age is not set, defaults to 2 * max_age.
        Returns the number of rows deleted.
        """
        # Determine the effective purge_age
        purge_age = getattr(feed, 'purge_age', None)
        if purge_age is None:
            max_age = getattr(feed, 'max_age', None)
            if max_age:
                purge_age = timedelta(seconds=max_age.total_seconds() * 2)
            else:
                logger.debug(f"Feed {feed.id} has no purge_age or max_age set, skipping purge.")
                return 0
        
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                fp_json = json.dumps(feed.feedpath)
                cutoff_date = (datetime.now() - purge_age).isoformat()
                cursor.execute(
                    "DELETE FROM cache WHERE feedpath = ? AND published_date < ?",
                    (fp_json, cutoff_date)
                )
                deleted = cursor.rowcount
                conn.commit()
                logger.info(f"Purged {deleted} old articles from cache for feedpath {feed.feedpath} (older than {cutoff_date}).")
                return deleted
        except sqlite3.Error as e:
            logger.error(f"Error purging old articles: {e}")
            return 0
