"""Tests for digest summary functionality."""

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

from fof.cli import main
from fof.config_manager import ConfigManager
from fof.models.article import Article
from fof.models.article_manager import ArticleManager


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def _build_test_config():
    test_dir = tempfile.mkdtemp()
    tree_dir = os.path.join(test_dir, 'tree')
    os.makedirs(tree_dir)

    with open(os.path.join(tree_dir, 'union.fof'), 'w') as f:
        json.dump({
            "feed_type": "union",
            "id": "root",
            "title": "Root Feed",
            "description": "Root feed",
            "weights": {"news": 100}
        }, f)

    news_dir = os.path.join(tree_dir, 'news')
    os.makedirs(news_dir)
    with open(os.path.join(news_dir, 'feed.fof'), 'w') as f:
        json.dump({
            "feed_type": "syndication",
            "id": "news",
            "title": "News Feed",
            "description": "News",
            "url": "https://example.com/feed.xml",
            "max_age": "7d"
        }, f)

    return test_dir


def test_recent_unread_category_counts_uses_24h_window():
    test_dir = _build_test_config()
    try:
        config_manager = ConfigManager(config_path=test_dir)
        article_manager = ArticleManager(config_manager=config_manager)
        now = datetime.now()

        articles = [
            Article(
                id="recent-tech",
                title="New AI model released",
                content="Latest software and cloud updates.",
                link="https://example.com/a",
                feed_id="news",
                feedpath=["root", "news"],
                published_date=now - timedelta(hours=2),
                tags=["ai"]
            ),
            Article(
                id="old-sports",
                title="Football finals recap",
                content="Sports highlights.",
                link="https://example.com/b",
                feed_id="news",
                feedpath=["root", "news"],
                published_date=now - timedelta(hours=30),
                tags=["football"]
            )
        ]
        article_manager.cache_articles(articles)

        total, breakdown = article_manager.get_recent_unread_category_counts(
            feedpaths=[["root", "news"]],
            hours=24
        )

        assert total == 1
        assert breakdown == {"Technology": 1}
    finally:
        shutil.rmtree(test_dir)


def test_digest_command_prints_summary():
    test_dir = _build_test_config()
    try:
        with patch(
            'fof.models.article_manager.ArticleManager.fetch_and_cache_all_articles',
            return_value=8
        ) as mock_fetch_all:
            with patch(
                'fof.models.article_manager.ArticleManager.'
                'get_recent_unread_category_counts',
                return_value=(12, {"Sports": 4, "Technology": 8})
            ):
                with patch(
                    'sys.argv',
                    ['fof', 'digest', '--config', test_dir, '--feed', 'news']
                ):
                    with patch('builtins.print') as mock_print:
                        with patch('sys.exit', side_effect=SystemExit):
                            try:
                                main()
                            except SystemExit:
                                pass

        assert mock_fetch_all.called
        printed = [str(call.args[0]) for call in mock_print.call_args_list]
        assert any("Good morning!" in line for line in printed)
        assert any("12 unread articles from the last 24h" in line for line in printed)
        assert any("8 about technology" in line for line in printed)
    finally:
        shutil.rmtree(test_dir)
