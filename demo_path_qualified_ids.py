#!/usr/bin/env python3
"""
Demo script for path-qualified feed IDs functionality.

This script demonstrates the key features implemented:
1. Local IDs in config files remain simple
2. Qualified IDs automatically generated from path
3. Feed lookup works with both local and qualified IDs
4. CLI scoping works with qualified IDs
5. No manual editing required when moving subtrees
"""

import tempfile
import os
import json
import shutil
from fof.models.article_manager import ArticleManager
from fof.config_manager import ConfigManager
from fof.feed_manager import FeedManager


def create_demo_config():
    """Create a demo configuration with conflicting local IDs."""
    test_dir = tempfile.mkdtemp()
    tree_dir = os.path.join(test_dir, 'tree')
    os.makedirs(tree_dir)

    # Root union feed
    with open(os.path.join(tree_dir, 'union.fof'), 'w') as f:
        json.dump({
            'id': 'root',
            'title': 'Root Feed',
            'max_age': '7d',
            'weights': {'work': 50, 'personal': 50}
        }, f, indent=2)

    # Work subtree
    work_dir = os.path.join(tree_dir, 'work')
    os.makedirs(work_dir)
    with open(os.path.join(work_dir, 'union.fof'), 'w') as f:
        json.dump({
            'id': 'work',
            'title': 'Work Projects',
            'max_age': '7d',
            'weights': {'cicd': 100}
        }, f, indent=2)

    # Work CI/CD feed (local ID: cicd)
    work_cicd_dir = os.path.join(work_dir, 'cicd')
    os.makedirs(work_cicd_dir)
    with open(os.path.join(work_cicd_dir, 'feed.fof'), 'w') as f:
        json.dump({
            'id': 'cicd',  # Local ID - simple!
            'title': 'Work CI/CD',
            'url': 'https://example.com/work-cicd.xml',
            'max_age': '7d'
        }, f, indent=2)

    # Personal subtree  
    personal_dir = os.path.join(tree_dir, 'personal')
    os.makedirs(personal_dir)
    with open(os.path.join(personal_dir, 'union.fof'), 'w') as f:
        json.dump({
            'id': 'personal',
            'title': 'Personal Projects',
            'max_age': '7d',
            'weights': {'cicd': 100}
        }, f, indent=2)

    # Personal CI/CD feed (local ID: cicd - same as work!)
    personal_cicd_dir = os.path.join(personal_dir, 'cicd')
    os.makedirs(personal_cicd_dir)
    with open(os.path.join(personal_cicd_dir, 'feed.fof'), 'w') as f:
        json.dump({
            'id': 'cicd',  # Same local ID - no conflict!
            'title': 'Personal CI/CD',
            'url': 'https://example.com/personal-cicd.xml',
            'max_age': '7d'
        }, f, indent=2)

    return test_dir


def demo_path_qualified_ids():
    """Demonstrate path-qualified feed ID functionality."""
    print("🔧 Feed of Feeds - Path-Qualified Feed IDs Demo")
    print("=" * 50)

    # Create demo configuration
    config_dir = create_demo_config()
    try:
        config_manager = ConfigManager(config_path=config_dir)
        article_manager = ArticleManager(config_manager=config_manager)
        feed_manager = FeedManager(
            article_manager=article_manager,
            config_manager=config_manager
        )

        print("\n📁 Configuration Structure:")
        print("tree/")
        print("├── work/")
        print("│   └── cicd/         # Local ID: 'cicd'")
        print("└── personal/")
        print("    └── cicd/         # Local ID: 'cicd' (same!)")

        print("\n🔍 1. Feed Lookup by Local ID:")
        cicd_local = feed_manager.get_feed_by_id('cicd')
        print(f"   get_feed_by_id('cicd') → {cicd_local.title}")
        print(f"   Qualified ID: {cicd_local.qualified_id}")

        print("\n🎯 2. Feed Lookup by Qualified ID:")
        work_cicd = feed_manager.get_feed_by_id('work/cicd')
        personal_cicd = feed_manager.get_feed_by_id('personal/cicd')
        print(f"   get_feed_by_id('work/cicd') → {work_cicd.title}")
        print(f"   get_feed_by_id('personal/cicd') → {personal_cicd.title}")

        print("\n📋 3. All Feed IDs:")
        feeds = []

        def collect_feeds(feed, ctx):
            if not (hasattr(feed, 'weight') and hasattr(feed, 'feed')):
                feeds.append(feed)

        feed_manager.perform_on_feeds(feed_manager.root_feed, collect_feeds)
        for feed in feeds:
            print(f"   Local ID: '{feed.id}' → Qualified ID: '{feed.qualified_id}'")

        print("\n💾 4. Configuration File Contents:")
        # Show that config files still use local IDs
        tree_dir = config_manager.get_tree_dir
        for root, dirs, files in os.walk(tree_dir):
            for file in files:
                if file.endswith('.fof'):
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r') as f:
                        config = json.load(f)
                    if 'id' in config:
                        rel_path = os.path.relpath(filepath, tree_dir)
                        print(f"   {rel_path}: \"id\": \"{config['id']}\"")

        print("\n🔒 5. CLI Feed Scoping:")
        # Test scoping with qualified ID
        scoped_manager = FeedManager(
            article_manager=ArticleManager(config_manager=config_manager),
            config_manager=config_manager,
            feed_id='work/cicd'  # Use qualified ID for scoping
        )

        work_scoped = scoped_manager.get_feed_by_id('work/cicd')
        personal_scoped = scoped_manager.get_feed_by_id('personal/cicd')
        print(f"   fof --feed work/cicd")
        print(f"   ├── work/cicd enabled: {not work_scoped.disabled_in_session}")
        print(f"   └── personal/cicd disabled: {personal_scoped.disabled_in_session}")

        print("\n✅ Key Benefits:")
        print("   • Local IDs stay simple in config files")
        print("   • Qualified IDs prevent conflicts across subtrees")
        print("   • No manual editing when moving/mounting subtrees")
        print("   • CLI works with both local and qualified IDs")
        print("   • Backward compatible with existing configurations")

    finally:
        # Cleanup
        shutil.rmtree(config_dir)


if __name__ == '__main__':
    demo_path_qualified_ids()