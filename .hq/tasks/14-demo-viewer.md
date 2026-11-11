# Task 14: Live demo viewer (client-side, blame-style)
Status: done
Type: feat
Scope: site
Depends on: 11, 13
## Goal
Build `/demo/`, the core "product runs here" page (spec "Demo viewer behaviour"): a fully client-side viewer for `data.json`. It shows a blame-style table, and a click or Enter opens the detail panel with the prompt, hq dereference, reasoning, session, agent, model, timestamp, tool, commit, match reason and sibling files. No backend.
## Files
- site/demo/index.html (create)
- site/demo/viewer.css (create: includes classes `.p0` to `.p11`, each with a contrast-checked colour in both schemes)
- site/demo/viewer-core.mjs (create: `PALETTE_SIZE`, `indexData`, `colorFor`, `parseHash`, `escapeHtml`, `detailModel` exactly as in spec Interfaces)
- site/demo/viewer.js (create: DOM wiring, an ES module that imports viewer-core.mjs)
- tests/js/viewer-core.test.mjs (create)
- tests/js/fixture.json (create: a small hand-written dataset in the same schema, with one `<script>` payload string, one null model and one hq block)
- tests/test_viewer.py (create)
## Acceptance criteria
- [ ] A file picker lists every file. The table has a gutter (short SHA, or `·`), the line number and the code; matched lines get the class `p<colorFor(prompt_id)>`
- [ ] **No inline styles anywhere**: no `style=` in markup, no `setAttribute('style', …)`, no `.style.` assignment except `el.style.setProperty`, which is not needed (tested by grepping `viewer.js`)
- [ ] Click or Enter fills an `aria-live="polite"` panel. A null model shows `unknown`; a line with no match shows `none recorded`
- [ ] Keyboard:
  - lines are focusable
  - ArrowUp/ArrowDown and j/k move between lines
  - Enter opens the panel
  - Escape returns focus to the table
  - the focus ring is visible
- [ ] `#gitmotive/cli.py:42` selects the file and line on load and on `hashchange`; selecting a line updates the hash
- [ ] Data text goes through `textContent`, or `escapeHtml` where a string is assembled
- [ ] Local time is displayed, with ISO 8601 in `title`
- [ ] The only network request is `data.json` (same origin); a load failure shows an error state
- [ ] The page's html, css and js total ≤ 100 KB, excluding data.json
- [ ] Manual check recorded: keyboard-only walkthrough via a briefly run `python3 -m http.server -d site`, then stopped
## Tests
`tests/js/viewer-core.test.mjs` (`node:test`) covers:
- `indexData` on the fixture
- `colorFor` stability and range
- `parseHash` on `""`, `#`, `#a.py`, `#a.py:x` and `#dir/a:b.py:7` (the last gives file `dir/a:b.py`, line 7)
- `escapeHtml`
- `detailModel` with a match, without a match, and with a null model

`tests/test_viewer.py` runs `node --test tests/js/viewer-core.test.mjs` (printing `skip node` if node is absent) and the no-inline-style grep. `tests/test_site.py` picks up `site/demo/index.html`.
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none

## Implementation notes (round 1)
**Files:** everything listed under Files was created. No existing file was changed.
- `site/demo/{index.html,viewer.css,viewer.js,viewer-core.mjs}`
- `tests/js/{viewer-core.test.mjs,fixture.json}`, `tests/test_viewer.py`

**Core (`viewer-core.mjs`)** exports exactly the six names in spec Interfaces.
- `colorFor` uses 32-bit FNV-1a mod 12. The test checks that it is stable, stays in range, and that 500 ids reach all 12 slots.
- `parseHash` splits on the last `:` only when the suffix is a positive integer. Otherwise the whole string is the file and `line` is null. So `#a.py:x` gives `{file:"a.py:x", line:null}`, and a colon path with no line number (`#dir/a:b.py`) still resolves. It also percent-decodes, falling back to the raw text if decoding fails.
- `detailModel` takes the file object or a path. `model` null becomes `"unknown"`. The model returns raw data strings, and escaping happens at render time.

**Rendering (`viewer.js`)**
- All DOM is built by a small `h()` helper. Strings become text nodes or `textContent`. The helper throws on a `style` or `on*` attribute.
- There is no `innerHTML`, `insertAdjacentHTML` or `.style` anywhere. No markup is assembled from strings, so `escapeHtml` is exported and tested but not needed by viewer.js. The task allows either route.
- The only network call is `fetch(new URL("data.json", import.meta.url))`.
- Times render as `<time datetime=ISO title=ISO>` in the local format.
- Selecting a line uses `history.replaceState` to update the hash, so no `hashchange` loop. File-picker links and sibling links are plain `#path` anchors that go through `hashchange`.
- Deep links keep `/` and `:` readable and only escape `#`, `?` and `%`.

**Keyboard**
- Rows use a roving tabindex: one row is in the Tab order, and the selected row gets `aria-current`.
- ↑/↓, j/k, Home/End and PageUp/PageDown move between rows. Enter fills the panel and moves focus to it (`#detail`, `tabindex=-1`, `aria-live=polite`). Escape anywhere in the viewer returns focus to the active row.
- The focus ring is a 2px accent outline, inset so the scroll pane doesn't clip it.

**States**
- Loading: `role=status` box.
- Error: `fatal: could not load data.json (HTTP 404)` plus a "Try again" button. This also covers invalid JSON or an export with no files.
- Zero matches (the current committed data.json): an `@@ intent: 0 of 473 lines @@` banner explains that every line shows `·` and answers "none recorded", the same answer the CLI gives for a line no hook saw. The meta row reads `0 of 473 with intent`, and the file chips read `0 intent`. Once task 23 re-exports with matches, the banner hides itself.

**Palette:** 12 hues 30° apart, with dark and light values in `viewer.css`. Each one is checked as text on `--panel` and on `--hl` (the selected row) in both schemes. That is 48 pairs, all ≥ 4.82:1, documented in the same comment format as site.css. `test_viewer.py` recomputes every pair with `test_site.contrast_problems` and checks that each stated value matches the declaration in the right scheme.

**test_viewer.py** covers:
- the node run
- the inline-style grep, with its own self-test
- the HTML-sink grep
- the single fetch, with no other network APIs or foreign URLs
- the palette and contrast check
- the focus-ring CSS
- the demo page's markup, using test_site's checkers
- the budget, including site.css and favicon.svg: 40.9 KB of 100 KB
- the fixture's required cases
- the committed data.json schema

`test_site.py` picks up `site/demo/index.html` automatically, so `/demo/` links now resolve.

**Manual check (done):** I served the page with `python3 -m http.server -d site` (and a scratch copy with the fixture as data.json, and one with no data.json) on 127.0.0.1, drove it keyboard-only through headless Chromium over CDP, then stopped the servers.
- Tab order: skip link → nav → file chips → the active row.
- j/j/k/↓/↑ move the focused row. Enter puts focus on `#detail` and sets the hash to `#gitmotive/cli.py:43`. Esc puts focus back on the row.
- Deep link `#gitmotive/cli.py:42` selects the line without scrolling the window. Setting `location.hash` switches files.
- In the fixture, the `<script>` payloads render as text (0 script elements) and the null model shows `unknown`. There are 0 `[style]` elements and 0 console errors.
- The requests were only the page's own html, css, js and mjs files, `data.json` and `favicon.svg`.
- The 404 case shows the error state.
- Checked visually in both colour schemes.
- I fixed two layout issues this turned up: deep links were scrolling the page, and the gutter collapsed when it held only `·`.

**For the reviewer:** the committed data.json shows `"author": "Raul"` on blame lines. It comes from the task 13 exporter, not the viewer, and the viewer only displays it. Task 23 should decide whether that is the intended public author name.
