# Feed of Feeds (FoF)

**Feed of Feeds (FoF)** is a command-line tool and library for aggregating, filtering, and managing content from multiple RSS and Atom feeds. It is designed for power users who want to collect articles from many sources, keep track of what they have read, and work with feeds in a programmable, scriptable way.

## Features

- **Feed Aggregation**: Collects articles from multiple RSS/Atom sources.
- **SQLite-backed Persistence**: All articles are cached in a local SQLite database for efficient querying and offline access.
- **Article State Management**: Tracks read/unread and fetched/unfetched articles, allowing you to pick up where you left off.
- **Configurable Architecture**: Uses a config manager to allow per-user and per-project settings.
- **Tagging and Metadata**: Supports article tags and metadata for advanced filtering.
- **Tab Completion (Optional)**: Offers shell tab completion for its CLI commands using [argcomplete](https://pypi.org/project/argcomplete/).

## Architecture

- **ArticleManager**: Handles loading, caching, fetching, and marking state for articles in the database. Implements logic for only returning unread/unfetched articles, respecting article age, and more.
- **Article**: Data class representing a single feed entry, with fields for id, title, content, author, publication date, tags, etc.
- **Web Fetching**: Uses `requests` and `feedparser` to fetch and parse feeds from the web.
- **Config Manager**: Reads configuration from user-provided paths for per-user or per-project settings.
- **CLI**: (Assumed from tab completion support) Exposes commands for interacting with feeds and articles.

## Development & Testing

- **Tests**: Uses `pytest` for unit testing. Recommended to run tests before every commit (see the `.git/hooks/pre-commit` example).
- **Pre-commit Hook**: You can enforce passing tests before every commit with a pre-commit hook.

## Example (not actual CLI, just concept)

