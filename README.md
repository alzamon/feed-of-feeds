# Feed of Feeds (FoF)

**Feed of Feeds (FoF)** is a command-line tool and library for aggregating, filtering, and managing content from multiple RSS and Atom feeds. It features a hierarchical feed structure with weighted sampling, an interactive curses-based article reader, and SQLite-backed persistence for efficient article management.

## Features

- **Hierarchical Feed Structure**: Organize feeds into trees with Union feeds (weighted aggregation) and Filter feeds (content filtering)
- **Weighted Sampling**: Feeds can have weights that influence article selection probability
- **Interactive Article Reader**: Curses-based terminal interface for reading articles with keyboard navigation
- **SQLite-backed Persistence**: All articles are cached locally with read/unread and fetched/unfetched state tracking
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

For tab completion support:
```bash
pip install argcomplete
# Add to your shell configuration
eval "$(register-python-argcomplete fof)"
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

3. **View logs**:
   ```bash
   fof logs
   ```

4. **Clear article cache**:
   ```bash
   fof cache clear --feed <feed_id>
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

- **feedparser**: RSS/Atom feed parsing
- **requests**: HTTP fetching
- **pyyaml**: YAML configuration support
- **argcomplete**: Tab completion
- **sqlite3**: Built-in database (Python standard library)
- **curses**: Terminal interface (Python standard library)

## License

MIT License - see [LICENSE](LICENSE) file for details.

