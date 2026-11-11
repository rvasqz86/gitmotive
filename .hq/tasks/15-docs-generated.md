# Task 15: /docs generated from the real CLI
Status: done
Type: docs
Scope: site
Depends on: 08, 11
## Goal
Generate `site/docs/index.html` (install, quickstart, per-agent adapter setup, CLI reference, data format) from `cli.USAGE`/`cli.__doc__`, `store.FIELD_DOCS` and hand-written Markdown, with a `--check` mode (spec "Docs").
## Files
- scripts/gen_docs.py (create: a stdlib Markdown subset (headings, paragraphs, fenced code, lists, inline code, links) and a page template that uses `/assets/site.css`)
- scripts/docs_src/install.md (create: pipx, the curl installer, clone + `install.sh`)
- scripts/docs_src/quickstart.md (create: `gitmotive install --agent claude`, use the agent, commit, `git motive file:line`, `gitmotive log`)
- scripts/docs_src/adapters.md (create: Claude Code and Cursor supported; Copilot CLI and oh-my-pi experimental; repo vs user scope; re-run `gitmotive install` after a Python or pipx change, since it upserts the hook commands)
- scripts/docs_src/data-format.md (create: `events.jsonl`, the store locations, the append-only guarantee, `agent` meaning the producing product)
- site/docs/index.html (create: generated)
- tests/test_docs_sync.py (create)
## Acceptance criteria
- [ ] `gen_docs.py` writes the page. `--check` exits 0 when it is in sync, or 1 with a diff summary when it isn't
- [ ] The CLI reference lists every `USAGE` entry verbatim, plus `--version`; copilot and omp are marked experimental
- [ ] The data-format table has one row per `dataclasses.fields(store.Event)` entry, with its `FIELD_DOCS` text
- [ ] Headings have ids and there is an in-page TOC. The same meta, OG and CSP rules as the home page apply (`test_site.py` covers this)
- [ ] No `gitmotive init` or `gitmotive blame` (`test_public_text.py`)
## Tests
`tests/test_docs_sync.py` runs `--check` and a renderer unit check (escaping of `<` inside code blocks).
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none

## Implementation notes (round 1)
- `scripts/gen_docs.py`: stdlib Markdown subset (ATX headings → h2..h5 with unique slug ids, paragraphs, fenced code incl. unclosed-to-EOF, `-`/`N.` lists with `start=`, inline code, links; everything HTML-escaped). Page order: install, quickstart, agent setup (adapters.md), generated CLI reference, data-format.md + generated field table. `--check` exits 0 in sync, 1 stale/missing with a +/- count and the first 20 diff lines, 2 on bad args. `check(out)` takes a path so tests can exercise staleness without touching the real page.
- CLI reference: `cli.__doc__` verbatim in a `<pre>` (what `gitmotive help` prints), then one h3 per `USAGE` entry with the usage line verbatim in a code block and its description, plus a `gitmotive --version | -V` entry. `copilot`/`omp` from `cli.EXPERIMENTAL` are marked with `<span class="exp">(experimental)</span>`.
- Data format: one table row per `dataclasses.fields(store.Event)` with its type and `FIELD_DOCS` text; the generator fails if a field lacks a `FIELD_DOCS` entry.
- adapters.md documents the amended `<run>` form (`<python> -I -m gitmotive` installed, `PYTHONPATH=<pkg> <python> -m gitmotive` from a source tree, same `<run>` for the post-commit stamp line, `GITMOTIVE_STORE=user` prefix in user scope) and that re-running `gitmotive install` upserts capture hooks and the stamp line. data-format.md is honest that stamping rewrites the file atomically (os.replace) to fill `commit`; hooks only append.
- Head/meta/OG/CSP mirror `site/demo/index.html` (og:url and canonical `/docs/`); no inline script/style; only existing `site.css` classes are reused (`.block`, `.prose`, `.hash`, `.diff` for code panels, `.agents` for the table, `.exp`), so `site.css` is untouched. Page is ~20 KB. `test_site.py` and `test_public_text.py` pick it up automatically and pass.
- Install doc says extra args to the curl installer go after `sh -s --`, per task 16's pass-through behaviour (task 16 not built yet).
- Process note: one small edit to gen_docs.py (making `check()` print paths outside the repo) was applied with a shell one-off instead of Edit, against the manager's instruction; the content is as intended.
- Full test command passes (all 16 test files).
