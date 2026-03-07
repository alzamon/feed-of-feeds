" Vim syntax file for Feed of Feeds (FoF) configuration files (*.fof).
"
" FoF config files are JSON with FoF-specific fields and values.
" This syntax file extends Vim's built-in JSON highlighting with
" additional colours for FoF keywords so you can see at a glance:
"   - which feed type a file defines  (syndication / union / filter)
"   - which filter_type values exist  (title_regex / content_regex / …)
"   - time-period values              ("7d", "12h", "30m", …)
"
" Installation: see contrib/vim/README.md

if exists("b:current_syntax")
  finish
endif

" Load Vim's built-in JSON syntax as the base layer.
runtime! syntax/json.vim
unlet! b:current_syntax

" ── Feed-type values ────────────────────────────────────────────────────────
" Matches the quoted strings "syndication", "union", "filter" anywhere in the
" file (they only appear as values of the "feed_type" key in practice).
syntax match fofFeedType /"\%(syndication\|union\|filter\)"/

" ── Filter-type values ──────────────────────────────────────────────────────
" The four filter_type values that FoF implements.
syntax match fofFilterType /"\%(title_regex\|content_regex\|link_regex\|author\)"/

" ── Time-period values ──────────────────────────────────────────────────────
" Matches strings like "7d", "12h", "30m", "10s", "7d12h30m".
" Each unit (d/h/m/s) appears at most once, in d→h→m→s order.
syntax match fofTimePeriod /"\%(\d\+d\%(\d\+h\%(\d\+m\%(\d\+s\)\?\)\?\)\?\|\d\+h\%(\d\+m\%(\d\+s\)\?\)\?\|\d\+m\%(\d\+s\)\?\|\d\+s\)"/

" ── Highlight links ─────────────────────────────────────────────────────────
" Use Vim's standard highlight groups so colours adapt to any colour scheme.
highlight default link fofFeedType   Type
highlight default link fofFilterType Identifier
highlight default link fofTimePeriod Number

let b:current_syntax = "fof"
