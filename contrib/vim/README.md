# FoF Vim Plugin

Provides syntax highlighting and omni-completion for **Feed of Feeds** configuration files (`*.fof`).

## What gets highlighted

| Element | Examples | Vim group |
|---------|----------|-----------|
| Feed type values | `"syndication"`, `"union"`, `"filter"` | `Type` |
| Filter type values | `"title_regex"`, `"content_regex"`, `"link_regex"`, `"author"` | `Identifier` |
| Time-period values | `"7d"`, `"12h"`, `"30m"`, `"7d12h"` | `Number` |

All other JSON structure (keys, braces, brackets, booleans, nulls) is highlighted by Vim's built-in JSON syntax.

## Omni-completion

Press **`CTRL-X CTRL-O`** (see `:help compl-omni`) while editing a `*.fof` file to trigger context-aware completion.

| Context | What gets completed |
|---------|---------------------|
| JSON field name (after `"`) | All FoF field names (`id`, `url`, `filter_type`, `criteria`, …) |
| `"filter_type": "` value | `title_regex`, `content_regex`, `link_regex`, `author` |

> **Tip:** Set `set completeopt+=menuone,noinsert` in your `vimrc` for the best experience.

## Installation

### Using a plugin manager (recommended)

**vim-plug**
```vim
Plug 'alzamon/feed-of-feeds', {'rtp': 'contrib/vim'}
```

**lazy.nvim**
```lua
{
  'alzamon/feed-of-feeds',
  config = false,
  vim.opt.runtimepath:append(vim.fn.stdpath('data') .. '/lazy/feed-of-feeds/contrib/vim'),
}
```

**Packer**
```lua
use { 'alzamon/feed-of-feeds', rtp = 'contrib/vim' }
```

### Manual installation

Copy (or symlink) the plugin directories into your Vim runtime path:

```bash
# Vim
cp -r contrib/vim/ftdetect ~/.vim/ftdetect
cp -r contrib/vim/ftplugin ~/.vim/ftplugin
cp -r contrib/vim/syntax   ~/.vim/syntax
cp -r contrib/vim/autoload ~/.vim/autoload

# Neovim
cp -r contrib/vim/ftdetect ~/.config/nvim/ftdetect
cp -r contrib/vim/ftplugin ~/.config/nvim/ftplugin
cp -r contrib/vim/syntax   ~/.config/nvim/syntax
cp -r contrib/vim/autoload ~/.config/nvim/autoload
```

Or add the plugin directory to your runtime path in `~/.vimrc` / `init.vim`:

```vim
set runtimepath+=/path/to/feed-of-feeds/contrib/vim
```

## JSON Schema (editor-agnostic)

The `schemas/` directory at the root of the repository contains JSON Schema files for each config type. These work with any editor that supports JSON Schema validation and autocompletion (VS Code, Neovim + `nvim-lsp`, etc.).

| Schema file | Config file |
|-------------|-------------|
| `schemas/syndication-feed.schema.json` | `feed.fof` |
| `schemas/union-feed.schema.json` | `union.fof` |
| `schemas/filter-feed.schema.json` | `filter.fof` |

### VS Code

Add to your workspace `.vscode/settings.json`:

```json
{
  "json.schemas": [
    {
      "fileMatch": ["**/feed.fof"],
      "url": "./schemas/syndication-feed.schema.json"
    },
    {
      "fileMatch": ["**/union.fof"],
      "url": "./schemas/union-feed.schema.json"
    },
    {
      "fileMatch": ["**/filter.fof"],
      "url": "./schemas/filter-feed.schema.json"
    }
  ]
}
```
