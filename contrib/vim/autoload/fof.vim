" Vim omni-completion for Feed of Feeds (FoF) configuration files (*.fof).
"
" Triggered by CTRL-X CTRL-O (see :help compl-omni).
"
" What gets completed:
"   - JSON field names valid in any *.fof file
"   - Quoted string values for fields whose value is an enum:
"       filter_type → title_regex / content_regex / link_regex / author

" All field names that may appear in a *.fof file.
let s:keys = [
      \ 'id',
      \ 'title',
      \ 'description',
      \ 'url',
      \ 'max_age',
      \ 'purge_age',
      \ 'last_updated',
      \ 'weights',
      \ 'criteria',
      \ 'filter_type',
      \ 'pattern',
      \ 'is_inclusion',
      \ ]

" Enumerated string values for fields that have a fixed set of options.
let s:values = {
      \ 'filter_type': ['title_regex', 'content_regex', 'link_regex', 'author'],
      \ }

" fof#complete({findstart}, {base})
"
" Standard two-phase Vim omni-completion function.
"
" Phase 1 (findstart == 1):
"   Return the byte column where the word-to-complete begins.
"   We scan backwards past word characters so that partial input
"   (e.g. "filt in "filter_type") is replaced rather than duplicated.
"
" Phase 2 (findstart == 0):
"   Return a List of completion candidates filtered by {base}.
"   Context detection:
"     value context  – the line before the cursor ends with
"                      "<key>": "<partial  →  offer enum values for <key>
"     key context    – everything else  →  offer all FoF field names
function! fof#complete(findstart, base)
  if a:findstart
    " Scan left past word characters (letters, digits, underscore).
    let line = getline('.')
    let col  = col('.') - 1
    while col > 0 && line[col - 1] =~# '\w'
      let col -= 1
    endwhile
    return col
  endif

  " ── Determine context ───────────────────────────────────────────────────
  " Grab everything on the current line up to (but not including) the cursor.
  let before = strpart(getline('.'), 0, col('.') - 1)

  " Value context: line ends with  "some_key": "  (quote opened, not closed).
  " \zs / \ze mark the start/end of the returned text so matchstr returns only
  " the key name (e.g. "filter_type") without the surrounding punctuation.
  let current_key = matchstr(before, '"\zs\w\+\ze"\s*:\s*"\w*$')

  if !empty(current_key) && has_key(s:values, current_key)
    " Offer enum values for this key.
    let candidates = s:values[current_key]
    return filter(
          \ map(copy(candidates), {_, v -> {'word': v, 'menu': '[fof]'}}),
          \ {_, e -> e.word =~# '^' . a:base})
  endif

  " Default: complete JSON field names.
  return filter(
        \ map(copy(s:keys), {_, k -> {'word': k, 'menu': '[fof]'}}),
        \ {_, e -> e.word =~# '^' . a:base})
endfunction
