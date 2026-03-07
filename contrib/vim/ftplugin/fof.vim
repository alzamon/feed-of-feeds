" Vim filetype plugin for Feed of Feeds (FoF) configuration files (*.fof).
"
" Sets omni-completion so that CTRL-X CTRL-O completes FoF field names and
" enum values.  The completion logic lives in autoload/fof.vim.
"
" When a new empty buffer is opened, inserts a skeleton with the required
" fields for the detected fof type (feed.fof / union.fof / filter.fof).

setlocal omnifunc=fof#complete

" ── New-file skeleton ─────────────────────────────────────────────────────────
" Only populate when the buffer is truly empty (new file, nothing typed yet).
if line('$') == 1 && getline(1) ==# ''
  call fof#insert_skeleton()
endif
