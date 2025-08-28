# GitHub Copilot Instructions for Feed of Feeds (FoF)

**ALWAYS follow these instructions first and only fallback to additional search and context gathering if the information here is incomplete or found to be in error.**

## Working Effectively in the Codebase

### Bootstrap, Build, and Test the Repository

**Python Setup (Required):**
- Python 3.7+ required (tested with Python 3.12.3)
- No special system dependencies - pure Python project

**Install Dependencies and Build:**
```bash
# Standard installation (works on most systems)
pip install -e ".[dev]"

# For Ubuntu with PEP 668 restrictions  
pipx install -e .

# For development work, always use:
pip install -e ".[dev]"
```

**Run Tests:**
```bash
python -m pytest tests/ -v
```
- **Timing: Tests run in ~0.4 seconds with 40 test cases. NEVER CANCEL.**
- All tests should pass - if they don't, the issue is unrelated to your changes unless you modified test-related code
- **No linting tools required** - project uses standard Python without additional code formatting requirements

**Verify Installation:**
```bash
fof --help
```

### Core Application Commands

**Interactive Article Reader (Main Usage):**
```bash
fof
```
- Launches curses-based terminal interface 
- **IMPORTANT: Will fail in non-interactive environments (CI, headless terminals) - this is expected**
- Keyboard controls: n (next), p (previous), o (open in browser), q (quit)

**CLI Commands (All Validated):**
```bash
# List configured feeds
fof feeds list

# List feeds under specific feed ID  
fof feeds list --feed tech_news

# View application logs
fof logs

# Clear article cache for a feed
fof cache clear --feed <feed_id>

# Use custom config directory
fof --config /path/to/config <command>

# Enable verbose logging
fof --verbose <command>
```

### Configuration Setup (Required for Testing)

**Configuration Structure:**
- Default location: `~/.config/fof/`
- Requires `tree/` subdirectory with feed configurations
- Root must have `union.json` with weighted feed aggregation

**Minimal Test Configuration:**
```bash
mkdir -p ~/.config/fof/tree/hackernews

# Create root union.json
cat > ~/.config/fof/tree/union.json << 'EOF'
{
  "id": "root",
  "title": "Root Feed",
  "description": "Top level feed aggregator", 
  "weights": {
    "hackernews": 100
  }
}
EOF

# Create syndication feed
cat > ~/.config/fof/tree/hackernews/feed.json << 'EOF'
{
  "feed_type": "syndication",
  "id": "hackernews", 
  "title": "Hacker News",
  "description": "Top stories from Hacker News",
  "url": "https://hnrss.org/frontpage",
  "max_age": "7d"
}
EOF
```

## Validation Requirements

**CRITICAL: Always validate changes with these scenarios:**

1. **Installation Validation:**
   ```bash
   pip install -e ".[dev]"
   fof --help  # Should show usage without errors
   ```

2. **Test Suite Validation:**
   ```bash
   python -m pytest tests/ -v  # Should pass all 40 tests in ~0.4s
   ```

3. **CLI Functionality Validation:**
   ```bash
   fof feeds list     # Should list configured feeds or show "No root feed loaded"
   fof logs          # Should show log file content
   ```

4. **Interactive Mode Validation (if terminal available):**
   ```bash
   fof  # Should launch curses interface (will fail in headless environments - this is expected)
   ```

**Manual Testing After Changes:**
- **Configuration Test**: Verify feed configurations load properly with `fof feeds list`
- **Article Fetching**: Interactive mode should fetch articles from RSS feeds (database created at `~/.config/fof/articles.db`)
- **CLI Arguments**: Test all CLI commands with `--config`, `--verbose`, and `--feed` options
- **Cross-Platform**: Test installation method appropriate for target platform (pip vs pipx)

## Codebase Structure and Navigation

**Key Directories:**
- `fof/` - Main application code
- `fof/models/` - Core data models (Article, Feed types)
- `fof/cli.py` - Command-line interface and argument parsing
- `tests/` - Comprehensive test suite (40 tests)
- `.github/` - GitHub workflows and this file

**Important Files:**
- `fof/cli.py` - Main entry point, CLI argument parsing
- `fof/control_loop.py` - Interactive curses interface  
- `fof/feed_manager.py` - Feed loading and management
- `fof/models/article_manager.py` - SQLite-backed article persistence
- `setup.py` - Package configuration and dependencies

**When modifying code, always check:**
- `fof/cli.py` - for CLI command changes
- `fof/models/` - for data model changes  
- `tests/` - for related test files that need updates

## Dependencies and Requirements

**Core Dependencies (automatically installed):**
- feedparser (RSS/Atom parsing)
- pyyaml (configuration files)
- requests (HTTP fetching)
- argcomplete (tab completion)
- colorama (terminal colors)

**Development Dependencies:**
- pytest (testing framework)

**No Build Process Required:**
- Pure Python project
- No compilation or external build tools needed
- Dependencies installed via pip/setuptools
- **No linting/formatting tools required** (no flake8, black, etc.)

**GitHub Workflows:**
- `.github/workflows/copilot-setup-steps.yml` - Basic CI that validates installation and runs tests
- Workflow runs on Ubuntu and tests the installation commands documented here

## Platform Compatibility Requirements

This project **must work on both Termux and Ubuntu** environments:

**Target Platforms:**
- **Ubuntu**: Standard Linux desktop/server environment
- **Termux**: Android terminal emulator with Linux userland

**Platform-Specific Installation:**
- **Ubuntu**: Use `pipx` for user installations due to PEP 668 restrictions
- **Termux**: Use `pkg` for system packages and `pip` for Python packages
- Always test installation methods on both platforms

**Cross-Platform Considerations:**
- Use Python's `pathlib` or `os.path` for file paths
- Handle permission errors gracefully
- Terminal/curses support may vary between platforms
- Test CLI functionality on both platforms

## Common Development Tasks

**Adding New CLI Commands:**
- Modify `fof/cli.py` parser setup
- Add corresponding handler in main() function
- Add tests in `tests/test_cli_*.py`

**Modifying Feed Types:**
- Core models in `fof/models/` (syndication_feed.py, union_feed.py, filter_feed.py)
- Update `fof/feed_loader.py` for loading logic
- Add tests in corresponding test files

**Database/Persistence Changes:**
- Modify `fof/models/article_manager.py`
- Handle database migrations for existing installations
- Test with both empty and existing databases

**Always run validation steps after any changes to ensure compatibility with both platforms and existing configurations.**
