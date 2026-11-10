# Task 14: Live demo viewer (client-side, blame-style)
Status: todo
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
