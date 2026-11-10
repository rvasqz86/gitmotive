# Task 15: /docs generated from the real CLI
Status: todo
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
