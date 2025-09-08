"""Tests for the purge functionality."""
import tempfile
import os
import json
import sqlite3
from datetime import datetime, timedelta

from fof.config_manager import ConfigManager
from fof.models.article_manager import ArticleManager
from fof.models.syndication_feed import SyndicationFeed
from fof.models.article import Article
from fof.feed_manager import FeedManager


class DummyArticleManager:
    """Dummy article manager for testing."""


def test_syndication_feed_purge_with_explicit_purge_age():
    """Test that syndication feed purges old articles when purge_age is explicitly set."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = ConfigManager(temp_dir)
        article_manager = ArticleManager(config_manager)

        # Create a syndication feed with explicit purge_age
        feed = SyndicationFeed(
            title="Test Feed",
            description="A test feed",
            last_updated=datetime.now(),
            url="http://example.com/feed.xml",
            max_age=timedelta(days=7),
            article_manager=article_manager,
            feedpath=["test_feed"],
            purge_age=timedelta(days=10)  # Explicit purge_age
        )

        # Create some test articles - some old, some new
        now = datetime.now()
        old_article = Article(
            id="old_article",
            title="Old Article",
            content="Old content",
            link="http://example.com/old",
            author="Author",
            published_date=now - timedelta(days=15),  # Older than purge_age
            feed_id="test_feed",
            feedpath=["test_feed"]
        )

        new_article = Article(
            id="new_article",
            title="New Article",
            content="New content",
            link="http://example.com/new",
            author="Author",
            published_date=now - timedelta(days=5),  # Newer than purge_age
            feed_id="test_feed",
            feedpath=["test_feed"]
        )

        # Cache the articles
        article_manager.cache_articles([old_article, new_article])

        # Verify both articles are in cache initially
        with sqlite3.connect(article_manager.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM cache WHERE feedpath = ?",
                (json.dumps(
                    ["test_feed"]),
                 ))
            count = cursor.fetchone()[0]
            assert count == 2, "Both articles should be in cache initially"

        # Purge old articles
        purged_count = article_manager.purge_old_articles(feed)

        # Should have purged 1 article (the old one)
        assert purged_count == 1, "Should have purged 1 old article"

        # Verify only the new article remains
        with sqlite3.connect(article_manager.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM cache WHERE feedpath = ?",
                (json.dumps(
                    ["test_feed"]),
                 ))
            remaining_ids = [row[0] for row in cursor.fetchall()]
            assert remaining_ids == [
                "new_article"], "Only new article should remain"


def test_syndication_feed_purge_with_default_purge_age():
    """Test that syndication feed purges old articles using default purge_age (2 * max_age)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = ConfigManager(temp_dir)
        article_manager = ArticleManager(config_manager)

        # Create a syndication feed without explicit purge_age (should default
        # to 2 * max_age)
        feed = SyndicationFeed(
            title="Test Feed",
            description="A test feed",
            last_updated=datetime.now(),
            url="http://example.com/feed.xml",
            max_age=timedelta(days=7),
            # max_age = 7 days, so default purge_age = 14 days
            article_manager=article_manager,
            feedpath=["test_feed"]
        )

        # Create test articles
        now = datetime.now()
        very_old_article = Article(
            id="very_old_article",
            title="Very Old Article",
            content="Very old content",
            link="http://example.com/very_old",
            author="Author",
            # Older than default purge_age (14 days)
            published_date=now - timedelta(days=20),
            feed_id="test_feed",
            feedpath=["test_feed"]
        )

        old_article = Article(
            id="old_article",
            title="Old Article",
            content="Old content",
            link="http://example.com/old",
            author="Author",
            # Between max_age and purge_age
            published_date=now - timedelta(days=10),
            feed_id="test_feed",
            feedpath=["test_feed"]
        )

        new_article = Article(
            id="new_article",
            title="New Article",
            content="New content",
            link="http://example.com/new",
            author="Author",
            published_date=now - timedelta(days=3),  # Newer than max_age
            feed_id="test_feed",
            feedpath=["test_feed"]
        )

        # Cache the articles
        article_manager.cache_articles(
            [very_old_article, old_article, new_article])

        # Purge old articles (should use default purge_age = 14 days)
        purged_count = article_manager.purge_old_articles(feed)

        # Should have purged 1 article (the very old one)
        assert purged_count == 1, "Should have purged 1 very old article"

        # Verify the remaining articles
        with sqlite3.connect(article_manager.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM cache WHERE feedpath = ? ORDER BY id",
                (json.dumps(
                    ["test_feed"]),
                 ))
            remaining_ids = [row[0] for row in cursor.fetchall()]
            assert set(remaining_ids) == {
                "new_article", "old_article"}, "New and old articles should remain"


def test_feed_manager_purge_old_articles():
    """Test that FeedManager.purge_old_articles() calls purge on all feeds."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create tree directory
        tree_dir = os.path.join(temp_dir, "tree")
        os.makedirs(tree_dir)

        # Create a simple syndication feed config
        feed_config = {
            "id": "test_feed",
            "title": "Test Feed",
            "description": "A test feed",
            "last_updated": datetime.now().isoformat(),
            "url": "http://example.com/feed.xml",
            "max_age": "7d",
            "purge_age": "14d"
        }

        feed_json_path = os.path.join(tree_dir, "feed.json")
        with open(feed_json_path, "w") as f:
            json.dump(feed_config, f, indent=2)

        # Create config and feed managers
        config_manager = ConfigManager(temp_dir)
        article_manager = ArticleManager(config_manager)
        feed_manager = FeedManager(article_manager, config_manager)

        # Create some test articles
        now = datetime.now()

        # Cache the article using the correct feedpath (should be empty list
        # for root feed)
        article_manager.cache_articles([Article(
            id="old_article",
            title="Old Article",
            content="Old content",
            link="http://example.com/old",
            author="Author",
            published_date=now - timedelta(days=20),  # Older than purge_age
            feed_id="test_feed",
            feedpath=[]  # Root feed has empty feedpath
        )])

        # Call purge_old_articles on feed manager
        total_purged = feed_manager.purge_old_articles()

        # Should have purged the old article
        assert total_purged == 1, "Should have purged 1 old article"


def test_no_purge_when_no_max_age_or_purge_age():
    """Test that no purging occurs when feed has neither max_age nor purge_age."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = ConfigManager(temp_dir)
        article_manager = ArticleManager(config_manager)

        # Create a syndication feed without max_age or purge_age
        feed = SyndicationFeed(
            title="Test Feed",
            description="A test feed",
            last_updated=datetime.now(),
            url="http://example.com/feed.xml",
            max_age=None,
            article_manager=article_manager,
            feedpath=["test_feed"],
            purge_age=None
        )

        # Create a very old article
        now = datetime.now()
        very_old_article = Article(
            id="very_old_article",
            title="Very Old Article",
            content="Very old content",
            link="http://example.com/very_old",
            author="Author",
            published_date=now - timedelta(days=365),  # Very old
            feed_id="test_feed",
            feedpath=["test_feed"]
        )

        # Cache the article
        article_manager.cache_articles([very_old_article])

        # Try to purge - should not purge anything since no max_age or
        # purge_age
        purged_count = article_manager.purge_old_articles(feed)

        # Should have purged nothing
        assert purged_count == 0, "Should not have purged anything when no max_age or purge_age"

        # Verify article is still there
        with sqlite3.connect(article_manager.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM cache WHERE feedpath = ?",
                (json.dumps(
                    ["test_feed"]),
                 ))
            count = cursor.fetchone()[0]
            assert count == 1, "Article should still be in cache"
