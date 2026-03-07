" Vim filetype plugin for Feed of Feeds (FoF) configuration files (*.fof).
"
" Sets omni-completion so that CTRL-X CTRL-O completes FoF field names and
" enum values.  The completion logic lives in autoload/fof.vim.

setlocal omnifunc=fof#complete
