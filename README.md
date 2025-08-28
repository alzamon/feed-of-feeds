# Feed of Feeds (FoF)

**Feed of Feeds (FoF)** is a command-line tool and library for aggregating, filtering, and managing content from multiple RSS and Atom feeds. It features a hierarchical feed structure with weighted sampling, an interactive curses-based article reader, and SQLite-backed persistence for efficient article management.

## Features

- **Hierarchical Feed Structure**: Organize feeds into trees with Union feeds (weighted aggregation) and Filter feeds (content filtering)
- **Weighted Sampling**: Feeds can have weights that influence article selection probability
- **Interactive Article Reader**: Curses-based terminal interface for reading articles with keyboard navigation
- **SQLite-backed Persistence**: All articles are cached locally with read/unread and fetched/unfetched state tracking
- **Multi-Device Synchronization**: Sync read article status across multiple devices using SSH/SCP
- **Directory-based Configuration**: Feed configurations stored as JSON files in a directory structure
- **Content Filtering**: Filter articles by title, content, author, or link using regex patterns
- **Tab Completion**: Shell tab completion support using [argcomplete](https://pypi.org/project/argcomplete/)
- **Article Age Management**: Configure maximum age for articles per feed
- **Cache Management**: Clear cached articles for specific feeds

## Installation

Install from source:

```bash
git clone https://github.com/alzamon/feed-of-feeds.git
cd feed-of-feeds
pip install -e .
```

For systems with protected global Python package installs (like Ubuntu), use pipx:
```bash
git clone https://github.com/alzamon/feed-of-feeds.git
cd feed-of-feeds
pipx install -e .
```

For tab completion support:
```bash
pip install argcomplete
# Add to your shell configuration
eval "$(register-python-argcomplete fof)"
```

## Platform Compatibility

FoF is designed to work on both standard Linux environments and Termux (Android):

- **Ubuntu/Debian**: Full functionality including multi-device sync
- **Termux (Android)**: Complete compatibility with package installation via `pkg install openssh`
- **Other Linux**: Should work on most distributions with SSH client/server

For multi-device sync on Termux:
```bash
pkg install openssh
fof sync device prepare
```

## Quick Start

1. **Start the interactive reader** (main usage):
   ```bash
   fof
   ```
   This launches the curses-based interface where you can read articles with keyboard navigation.

2. **List configured feeds**:
   ```bash
   fof feeds list
   ```

   Or list feeds under a specific feed ID:
   ```bash
   fof feeds list --feed tech_news
   ```

3. **View logs**:
   ```bash
   fof logs
   ```

4. **Clear article cache**:
   ```bash
   fof cache clear --feed <feed_id>
   ```

5. **Set up multi-device sync** (optional):
   ```bash
   # Set device name
   fof sync device name my-laptop
   
   # Prepare for sync (generates SSH keys, etc.)
   fof sync device prepare
   
   # Add other devices
   fof sync peer add desktop-pc 192.168.1.100 user
   
   # Check sync status
   fof sync status
   ```

## Configuration

FoF uses directory-based configuration stored in `~/.config/fof/` by default. You can specify a different path with the `--config` option.

### Feed Configuration Structure

Feed configurations are stored as JSON files in a hierarchical directory structure under `~/.config/fof/tree/`. Each feed type has its own format:

#### Syndication Feed (RSS/Atom)
```json
{
  "feed_type": "syndication",
  "id": "example_blog",
  "title": "Example Blog",
  "description": "A tech blog",
  "url": "https://example.com/feed.xml",
  "max_age": "7d"
}
```

#### Union Feed (Weighted Aggregation)
```json
{
  "feed_type": "union",
  "id": "tech_news",
  "title": "Tech News Aggregate",
  "description": "Collection of tech news sources",
  "feeds": [
    {"feed_id": "blog1", "weight": 60},
    {"feed_id": "blog2", "weight": 40}
  ]
}
```

#### Filter Feed (Content Filtering)
```json
{
  "feed_type": "filter",
  "id": "python_only",
  "title": "Python Articles Only",
  "description": "Filters for Python-related content",
  "source_feed_id": "tech_news",
  "max_age": "30d",
  "criteria": [
    {
      "filter_type": "title_regex",
      "pattern": "python|django|flask",
      "is_inclusion": true
    }
  ]
}
```

## Usage

### Interactive Article Reader

The main interface is launched with `fof` (no arguments). This starts a curses-based terminal application with the following keyboard controls:

- **n**: Next article
- **p**: Previous (read) article
- **o**: Open article link in browser
- **+**: Increase weight along feed path (+10)
- **-**: Decrease weight along feed path (-10)
- **?**: Show/hide hotkey help
- **q**: Quit

The interface displays:
- Article title, author, publication date
- Feed path (hierarchy of feeds leading to this article)
- Content preview
- Article tags (if available)
- Cumulative likelihood percentage

### Command Line Interface

#### Feed Management

List all configured feeds with their paths and cumulative likelihoods:
```bash
fof feeds list
```

List feeds under a specific feed ID:
```bash
fof feeds list --feed tech_news
```

#### Cache Management

Clear cached articles for all syndication feeds under a specific feed:
```bash
fof cache clear --feed tech_news
```

#### Multi-Device Synchronization

FoF supports synchronizing read article status across multiple devices using SSH/SCP.

##### Device Setup

Set your device name:
```bash
fof sync device name my-laptop
```

Prepare your device for syncing (generates SSH keys, sets up SSH server):
```bash
fof sync device prepare
```

##### Peer Management

Add a sync peer:
```bash
fof sync peer add desktop-pc 192.168.1.100 myuser
fof sync peer add server example.com serveruser --port 2222
```

List configured peers:
```bash
fof sync peer list
```

Remove a peer:
```bash
fof sync peer remove desktop-pc
```

##### Sync Operations

Check sync status and peer connectivity:
```bash
fof sync status
```

Perform manual sync with all peers:
```bash
fof sync now
```

Automatic sync occurs on app startup (pull from peers) and exit (push to peers).

##### How Sync Works

1. **Export**: Read articles are exported to `~/.config/fof/sync/read_articles_on_<device>.json`
2. **Pull**: On startup, the app downloads peer files via SCP
3. **Merge**: Articles are deduplicated by GUID (preferred) or URL and marked as read locally
4. **Push**: On exit, the local file is uploaded to all configured peers
5. **Fallback**: Cached peer files are used if fresh downloads fail

##### Requirements

- SSH access between devices
- OpenSSH client (`ssh`, `scp`, `ssh-keygen` commands)
- SSH server running on each device that others sync from

#### Logging

View the application log file:
```bash
fof logs
```

#### Configuration Path

All commands accept a custom configuration path:
```bash
fof --config /path/to/config feeds list
fof --config /path/to/config logs
```

#### Verbose Output

Enable debug logging to console:
```bash
fof --verbose
```

## Architecture

### Core Components

- **FeedManager**: Manages the hierarchical feed structure, serialization, and weight updates
- **ArticleManager**: Handles SQLite-based article persistence, caching, and state management
- **ControlLoop**: Provides the interactive curses-based article reading interface
- **ConfigManager**: Manages directory-based configuration with atomic updates

### Feed Types

1. **SyndicationFeed**: Fetches articles from RSS/Atom URLs using `feedparser` and `requests`
2. **UnionFeed**: Aggregates multiple feeds with weighted random sampling
3. **FilterFeed**: Applies regex-based filtering to articles from a source feed

### Article State Management

Articles have multiple states tracked in the SQLite database:
- **Cached**: Article is stored locally
- **Fetched**: Article has been retrieved for reading
- **Read**: Article has been displayed to the user

### Weight-based Sampling

Union feeds use weighted random sampling to select articles:
- Each child feed has an associated weight
- Higher weights increase the probability of selection
- Weights can be adjusted interactively (+/- keys)
- Cumulative likelihood is displayed for each feed path

## Development & Testing

### Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

### Development Installation

```bash
git clone https://github.com/alzamon/feed-of-feeds.git
cd feed-of-feeds
pip install -e ".[dev]"
```

### Testing Dependencies

```bash
pip install ".[test]"
```

## Dependencies

Dependencies are automatically installed via `pip install`. See `setup.py` for the complete list.

## License

MIT License - see [LICENSE](LICENSE) file for details.

