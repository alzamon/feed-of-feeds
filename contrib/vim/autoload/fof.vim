" Vim omni-completion for Feed of Feeds (FoF) configuration files (*.fof).
"
" Triggered by CTRL-X CTRL-O (see :help compl-omni).
"
" What gets completed:
"   - Top-level JSON field names valid in any *.fof file
"   - Sub-object field names when inside a known array (e.g. criteria items)
"   - Quoted string values for fields whose value is an enum:
"       filter_type → title_regex / content_regex / link_regex / author

" Top-level field names (common to all *.fof types).
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
      \ ]

" Field names valid inside sub-objects of a named array key.
" Each entry maps an array key to the list of fields its items may contain.
let s:subkeys = {
      \ 'criteria': ['filter_type', 'pattern', 'is_inclusion'],
      \ }

" Enumerated string values for fields that have a fixed set of options.
let s:values = {
      \ 'filter_type': ['title_regex', 'content_regex', 'link_regex', 'author'],
      \ }

" s:find_parent_context()
"
" Scans from the top of the file down to (but not including) the current line,
" tracking JSON brace/bracket depth.  Returns the key name of the nearest
" enclosing array if the cursor is currently inside a sub-object of that
" array, or '' when the cursor is at the top-level object.
"
" Example: inside a criteria item the function returns 'criteria'.
"
" The parser tracks whether it is inside a JSON string so that braces and
" brackets that appear in string values do not corrupt the depth counters.
" Backslash-escaped characters (including \") are skipped correctly.
function! s:find_parent_context()
  let brace_depth   = 0
  let bracket_depth = 0
  let last_array_key = ''

  for lnum in range(1, line('.') - 1)
    let l = getline(lnum)
    let in_string = 0
    let col_idx   = 0
    let line_len  = len(l)

    while col_idx < line_len
      let ch = l[col_idx]

      if in_string
        if ch ==# '\'
          " Skip the next character (escaped, e.g. \" or \\).
          let col_idx += 1
        elseif ch ==# '"'
          let in_string = 0
        endif
      else
        if ch ==# '"'
          let in_string = 1
        elseif ch ==# '{'
          let brace_depth += 1
        elseif ch ==# '}'
          let brace_depth -= 1
        elseif ch ==# '['
          let bracket_depth += 1
          if bracket_depth == 1
            " Look for "key": [ on the portion of the line ending at this [.
            " Using the sub-string rather than the full line avoids picking
            " up an earlier key when multiple arrays appear on one line.
            let portion = strpart(l, 0, col_idx + 1)
            let key = matchstr(portion, '"\zs\w\+\ze"\s*:\s*\[$')
            if !empty(key)
              let last_array_key = key
            endif
          endif
        elseif ch ==# ']'
          let bracket_depth -= 1
          if bracket_depth == 0
            let last_array_key = ''
          endif
        endif
      endif

      let col_idx += 1
    endwhile
  endfor

  " brace_depth > 1 means we are inside a nested object (depth 1 = top-level
  " object; depth 2+ = a sub-object such as a criteria item).
  if brace_depth > 1 && bracket_depth > 0
    return last_array_key
  endif
  return ''
endfunction

" fof#insert_skeleton()
"
" Called automatically when a new empty *.fof buffer is opened.
" Detects the feed type from the file name and inserts a minimal JSON skeleton
" containing only the fields that are required by that feed's schema:
"
"   feed.fof   → id + url
"   union.fof  → id + weights
"   filter.fof → id + criteria
"
" A "$schema" key is included so that JSON-aware editors and language servers
" (VS Code, neovim jsonls, GitHub Copilot) automatically validate and complete
" the file using the published schema.
"
" The cursor is left inside the empty "id" value so the user can start typing.
function! fof#insert_skeleton()
  let fname = expand('%:t')
  let base_url = 'https://raw.githubusercontent.com/alzamon/feed-of-feeds/main/schemas/'

  if fname ==# 'feed.fof'
    let lines = [
          \ '{',
          \ '  "$schema": "' . base_url . 'syndication-feed.schema.json",',
          \ '  "id": "",',
          \ '  "url": ""',
          \ '}',
          \ ]
  elseif fname ==# 'union.fof'
    let lines = [
          \ '{',
          \ '  "$schema": "' . base_url . 'union-feed.schema.json",',
          \ '  "id": "",',
          \ '  "weights": {}',
          \ '}',
          \ ]
  elseif fname ==# 'filter.fof'
    let lines = [
          \ '{',
          \ '  "$schema": "' . base_url . 'filter-feed.schema.json",',
          \ '  "id": "",',
          \ '  "criteria": []',
          \ '}',
          \ ]
  else
    return
  endif

  call setline(1, lines[0])
  call append(1, lines[1:])
  " Place cursor on the closing quote of the empty "id" value so that pressing
  " 'i' in normal mode inserts text between the two quotes.
  " With the $schema line added, "id" is now on line 3.
  " Line 3 is:  '  "id": "",'
  "              col:     910  → col 10 = closing quote of the empty id string.
  call cursor(3, 10)
endfunction

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
"   Completion words follow JSON conventions so the result is always valid
"   JSON when the user has already typed the opening '"':
"
"     Field names:  word = key":   →  with user's "  →  "key": 
"     Enum values:  word = val"    →  with user's "  →  "val"
"
"   Context detection (in priority order):
"     value context  – the line before the cursor ends with
"                      "<key>": "<partial  →  offer enum values for <key>
"     sub-object     – cursor is inside a known array's item object
"                      (e.g. inside a criteria entry)  →  offer that
"                      sub-object's field names
"     key context    – everything else  →  offer top-level FoF field names
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
    " The word includes the closing quote so the final result is:
    "   "filter_type": "title_regex"
    " (the user's opening " before the value is already in the buffer).
    let candidates = s:values[current_key]
    return filter(
          \ map(copy(candidates), {_, v -> {'word': v . '"', 'abbr': v, 'menu': '[fof]'}}),
          \ {_, e -> e.abbr =~# '^' . a:base})
  endif

  " Sub-object context: inside a known array's item (e.g. criteria entries).
  let parent_key = s:find_parent_context()
  if !empty(parent_key) && has_key(s:subkeys, parent_key)
    " Filter the raw key list by prefix, then build completion dicts.
    " word = key":  so the user's leading " plus the inserted text gives
    " "filter_type": — ready for the user to type the value.
    let candidates = filter(copy(s:subkeys[parent_key]), {_, k -> k =~# '^' . a:base})
    return map(candidates, {_, k -> {'word': k . '": ', 'abbr': '"' . k . '"', 'menu': '[fof/' . parent_key . ']'}})
  endif

  " Default: complete top-level JSON field names.
  " Filter the raw key list by prefix, then build completion dicts.
  " Same convention: word = key":  so that with the user's leading " the
  " result is "id": , "url": , etc.
  let candidates = filter(copy(s:keys), {_, k -> k =~# '^' . a:base})
  return map(candidates, {_, k -> {'word': k . '": ', 'abbr': '"' . k . '"', 'menu': '[fof]'}})
endfunction
