" Vim filetype detection for Feed of Feeds (FoF) configuration files.
"
" *.fof files are JSON-formatted FoF config files:
"   feed.fof   - syndication (RSS/Atom) feed
"   union.fof  - weighted-aggregation union feed
"   filter.fof - content-filtering feed

autocmd BufRead,BufNewFile *.fof setfiletype fof
