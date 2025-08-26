import pytest
import tempfile
import os
import sqlite3
import json
from datetime import datetime
from fof.models.article_manager import ArticleManager
from fof.models.article import Article
from fof.feed_manager import FeedManager
from fof.models.union_feed import UnionFeed, WeightedFeed
from fof.models.syndication_feed import SyndicationFeed

class DummyConfigManager:
    def __init__(self, config_path):
        self.config_path = config_path

    @property
    def get_tree_dir(self):
        return "tree_dir"
    
    def sanitize_filename(self, name):
        return name.replace(" ", "_")
    
    @property
    def get_update_dir(self):
        return "update_dir"
    
    def persist_update(self, dir):
        pass

def test_events_table_creation():
    """Test that the events table is created properly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = DummyConfigManager(temp_dir)
        article_manager = ArticleManager(config_manager)
        
        # Check that the events table exists
        with sqlite3.connect(article_manager.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
            result = cursor.fetchone()
            assert result is not None, "Events table was not created"
            
            # Check table structure
            cursor.execute("PRAGMA table_info(events)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            expected_columns = {
                'id': 'INTEGER',
                'article_title': 'TEXT',
                'feedpath': 'TEXT', 
                'action': 'TEXT',
                'timestamp': 'TIMESTAMP'
            }
            for col_name, col_type in expected_columns.items():
                assert col_name in columns, f"Column {col_name} not found"
                assert col_type in columns[col_name], f"Column {col_name} has wrong type: {columns[col_name]}"

def test_log_weight_event():
    """Test logging weight change events."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = DummyConfigManager(temp_dir)
        article_manager = ArticleManager(config_manager)
        
        # Log a liked event
        article_title = "Test Article"
        feedpath = ["feed1", "feed2"]
        action = "liked"
        
        article_manager.log_weight_event(article_title, feedpath, action)
        
        # Verify the event was logged
        with sqlite3.connect(article_manager.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT article_title, feedpath, action FROM events WHERE article_title = ?", (article_title,))
            result = cursor.fetchone()
            
            assert result is not None, "Event was not logged"
            assert result[0] == article_title
            assert json.loads(result[1]) == feedpath
            assert result[2] == action

def test_weight_update_with_event_logging():
    """Test that weight updates log events when article is provided."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = DummyConfigManager(temp_dir)
        article_manager = ArticleManager(config_manager)
        feed_manager = FeedManager(article_manager, config_manager)
        
        # Create test feeds
        feed1 = SyndicationFeed(
            id="feed1",
            title="Feed One",
            description="desc1",
            last_updated=datetime.now(),
            url="http://example.com/1",
            max_age=None,
            article_manager=article_manager,
            feedpath=["feed1"],
        )
        feed2 = SyndicationFeed(
            id="feed2", 
            title="Feed Two",
            description="desc2",
            last_updated=datetime.now(),
            url="http://example.com/2",
            max_age=None,
            article_manager=article_manager,
            feedpath=["feed2"],
        )
        
        wf1 = WeightedFeed(feed=feed1, weight=60)
        wf2 = WeightedFeed(feed=feed2, weight=40)
        
        union_feed = UnionFeed(
            id="union",
            title="A Union",
            description="A union feed",
            last_updated=datetime.now(),
            feeds=[wf1, wf2],
            max_age=None,
            feedpath=[],
        )
        
        # Override the root feed after FeedManager initialization
        feed_manager.root_feed = union_feed
        
        # Create test article
        article = Article(
            id="test_article_id",
            title="Test Article Title",
            content="Some content",
            link="http://example.com/article",
            feedpath=["feed1"]
        )
        
        # Update weights with article info to trigger event logging
        feed_manager.update_weights(["feed1"], increment=10, article=article)
        
        # Check that the weight was updated
        assert wf1.weight == 70
        
        # Check that the event was logged
        with sqlite3.connect(article_manager.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT article_title, feedpath, action FROM events")
            result = cursor.fetchone()
            
            assert result is not None, "Event was not logged"
            assert result[0] == "Test Article Title"
            assert json.loads(result[1]) == ["feed1"]
            assert result[2] == "liked"

def test_weight_update_dislike_event():
    """Test that negative weight updates log 'disliked' events."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = DummyConfigManager(temp_dir)
        article_manager = ArticleManager(config_manager)
        feed_manager = FeedManager(article_manager, config_manager)
        
        # Create test feeds
        feed1 = SyndicationFeed(
            id="feed1",
            title="Feed One", 
            description="desc1",
            last_updated=datetime.now(),
            url="http://example.com/1",
            max_age=None,
            article_manager=article_manager,
            feedpath=["feed1"],
        )
        
        wf1 = WeightedFeed(feed=feed1, weight=60)
        
        union_feed = UnionFeed(
            id="union",
            title="A Union",
            description="A union feed",
            last_updated=datetime.now(),
            feeds=[wf1],
            max_age=None,
            feedpath=[],
        )
        
        # Override the root feed after FeedManager initialization
        feed_manager.root_feed = union_feed
        
        # Create test article
        article = Article(
            id="test_article_id",
            title="Disliked Article",
            content="Some content",
            link="http://example.com/article",
            feedpath=["feed1"]
        )
        
        # Update weights with negative increment
        feed_manager.update_weights(["feed1"], increment=-10, article=article)
        
        # Check that the weight was updated (starts at 100 due to normalization, then -10)
        assert wf1.weight == 90
        
        # Check that the dislike event was logged
        with sqlite3.connect(article_manager.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT article_title, action FROM events")
            result = cursor.fetchone()
            
            assert result is not None, "Event was not logged"
            assert result[0] == "Disliked Article"
            assert result[1] == "disliked"

def test_weight_update_without_article_no_event():
    """Test that weight updates without article info don't log events."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = DummyConfigManager(temp_dir)
        article_manager = ArticleManager(config_manager)
        feed_manager = FeedManager(article_manager, config_manager)
        
        # Create test feeds
        feed1 = SyndicationFeed(
            id="feed1",
            title="Feed One",
            description="desc1", 
            last_updated=datetime.now(),
            url="http://example.com/1",
            max_age=None,
            article_manager=article_manager,
            feedpath=["feed1"],
        )
        
        wf1 = WeightedFeed(feed=feed1, weight=60)
        
        union_feed = UnionFeed(
            id="union",
            title="A Union",
            description="A union feed",
            last_updated=datetime.now(),
            feeds=[wf1],
            max_age=None,
            feedpath=[],
        )
        
        # Override the root feed after FeedManager initialization
        feed_manager.root_feed = union_feed
        
        # Update weights without article info (backward compatibility)
        feed_manager.update_weights(["feed1"], increment=10)
        
        # Check that the weight was updated (starts at 100 due to normalization, then +10)
        assert wf1.weight == 110
        
        # Check that NO event was logged
        with sqlite3.connect(article_manager.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM events")
            count = cursor.fetchone()[0]
            
            assert count == 0, "Event was logged when it shouldn't have been"