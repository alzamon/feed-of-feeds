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

### Symlinked Curated Subtrees

FoF supports modular configuration by allowing parts of your feed tree to be symlinks to curated subtrees. This enables you to `git clone` curated configuration trees elsewhere and reference them in your main configuration using symbolic links.

**Symlink Policy:**
- **Symlinked directories are treated as static, curated subtrees.**
- FoF will **never modify, overwrite, or delete the contents of symlinked directories** during serialization or configuration updates.
- If a symlink exists inside your feed tree (e.g., `~/.config/fof/tree/curated_feeds` is a symlink), FoF will skip writing or updating any files inside that subtree.
- **Top-level symlink caution:** If your entire `tree` directory is a symlink, it may be replaced if you perform a configuration update (see atomic update logic). For curated subtrees, symlink only subdirectories, not the top-level `tree`.

**Use Case Example:**
- You can maintain curated feed configurations in a separate git repository, clone them to a location of your choice, and symlink them into your main FoF configuration tree.
- This allows you to share, update, and reuse feed subtrees without risk of accidental modification by FoF.

**Best Practice:**
Symlink only subdirectories within your configuration tree for curated content. Avoid making the top-level `tree` directory a symlink if you want to preserve it across updates.

**Example Usage:**
```bash
# Clone a curated feed repository
git clone https://github.com/example/curated-feeds.git ~/curated

# Create symlink in your feed tree
ln -s ~/curated/tech-news ~/.config/fof/tree/tech_news
```

**Directory Naming:** Feed directories are named using the feed's `local_id` field (not the title). Ensure your feed configurations have appropriate `local_id` values that match your desired directory structure.

### Path-Qualified Feed IDs

FoF supports modular configuration through **path-qualified feed IDs** that enable self-contained subtrees without ID conflicts.

#### Local vs. Qualified IDs

- **Local ID**: Simple identifier used in configuration files (e.g., `"id": "cicd"`)
- **Qualified ID**: Global identifier that includes the full path (e.g., `work/da/cicd`)

#### Configuration Convention

Each feed defines a simple local `id` in its configuration file:

```json
{
  "id": "cicd",
  "title": "CI/CD Feed",
  "description": "Build and deployment feeds"
}
```

The system automatically generates qualified IDs based on the directory structure:

- Feed at `~/.config/fof/tree/work/da/cicd/` gets qualified ID: `work/da/cicd`
- Feed at `~/.config/fof/tree/personal/cicd/` gets qualified ID: `personal/cicd`

#### Benefits

- **No Manual Editing**: Moving subtrees doesn't require updating feed IDs
- **Conflict Resolution**: Feeds with the same local ID in different subtrees are distinguished
- **Modular Design**: Subtrees can be developed and mounted independently

#### CLI Usage

You can reference feeds by either local or qualified ID:

```bash
# Using local ID (finds first match)
fof --feed cicd

# Using qualified ID (specific match)
fof --feed work/da/cicd
fof --feed personal/cicd
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
python -m venv .venv
source .venv/bin/activate
pip install ".[dev]"
pytest
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
