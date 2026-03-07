# FoF Vim Plugin

Provides syntax highlighting, omni-completion, and new-file skeleton insertion for **Feed of Feeds** configuration files (`*.fof`).

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
| Top-level JSON field name (after `"`) | All top-level FoF field names (`id`, `url`, `criteria`, `weights`, …) |
| Inside a `criteria` array item | Sub-object fields: `filter_type`, `pattern`, `is_inclusion` |
| `"filter_type": "` value | `title_regex`, `content_regex`, `link_regex`, `author` |

The completion menu shows a tag indicating the context — `[fof]` for top-level fields and `[fof/criteria]` for fields inside a `criteria` item:

```vim
" Top-level keys — triggered anywhere in the outer object
{ "<C-X><C-O>           → id, url, criteria, weights, max_age, …  [fof]

" Inside a criteria item — triggered inside a { } nested under "criteria": [
{ "criteria": [
    { "<C-X><C-O>        → filter_type, pattern, is_inclusion      [fof/criteria]

" Value completion for filter_type
    { "filter_type": "<C-X><C-O>  → title_regex, content_regex, …  [fof]
```

> **Tip:** Set `set completeopt+=menuone,noinsert` in your `vimrc` for the best experience.

## New-file skeleton

When you open a **new, empty** `*.fof` file, the plugin automatically inserts a minimal JSON skeleton containing only the required fields for that feed type:

| File name | Required fields inserted |
|-----------|--------------------------|
| `feed.fof` | `id`, `url` |
| `union.fof` | `id`, `weights` |
| `filter.fof` | `id`, `criteria` |

The cursor is placed inside the empty `"id"` value so you can start typing immediately. Existing files are never modified.

## Installation

> **Important:** The Vim plugin lives inside `contrib/vim/`, not at the repository root.
> Every installation method must point at that subdirectory — otherwise Vim cannot find
> the filetype detection, ftplugin, syntax, or autoload files and nothing will work.

### Using a plugin manager (recommended)

**vim-plug**

```vim
" Default branch (main):
Plug 'alzamon/feed-of-feeds', {'rtp': 'contrib/vim'}

" Pin to a specific branch — include BOTH 'branch' AND 'rtp':
Plug 'alzamon/feed-of-feeds', {'branch': 'my-branch', 'rtp': 'contrib/vim'}
```

> If you omit `'rtp': 'contrib/vim'`, vim-plug adds the repo root to Vim's
> runtimepath and the plugin will not be loaded at all (no filetype detection,
> no skeleton, no completion).

**lazy.nvim**

```lua
{
  'alzamon/feed-of-feeds',
  config = false,
  init = function()
    vim.opt.runtimepath:append(
      vim.fn.stdpath('data') .. '/lazy/feed-of-feeds/contrib/vim'
    )
  end,
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

After any install, run `:PlugInstall` (vim-plug) or the equivalent for your manager,
then restart Vim.

### Verifying the installation

Open Vim and run:

```vim
:echo &runtimepath
```

You should see a path ending in `feed-of-feeds/contrib/vim` in the list.

Check that filetype detection is active:

```vim
:set filetype?          " inside a *.fof file → should print  filetype=fof
:echo &omnifunc         " should print  fof#complete
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No skeleton on new `*.fof` file | Plugin not loaded — `rtp` not set | Add `'rtp': 'contrib/vim'` to your plugin manager entry |
| `E117: Unknown function: fof#complete` | `autoload/fof.vim` not on runtimepath | Same as above |
| Filetype not detected (`fof`) | `ftdetect/fof.vim` not on runtimepath | Same as above |
| Skeleton appears on existing files | Should never happen — file a bug | — |

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
