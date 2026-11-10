# Task 13: Demo data exporter with per-record sanitisation gate
Status: todo
Type: feat
Scope: site
Depends on: 05, 06, 12
## Goal
Add `scripts/export_demo.py` per the spec's "Demo data": it exports HEAD only, aborts on dirty exported files, stamps in memory (`resolve.stamp(..., persist=False)`), emits only referenced prompts, sanitises the emitted fields, and runs the per-record gate followed by a whole-output rescan. Commit a first `site/demo/data.json`.
## Files
- scripts/export_demo.py (create)
- site/demo/data.json (create: generated)
- tests/test_export_demo.py (create)
## Acceptance criteria
- [ ] The CLI is exactly `--root --file (repeatable) --out --max-prompt-chars --no-denylist` (no `--rev`). The default files are `gitmotive/cli.py gitmotive/adapters.py scripts/gen_docs.py site/demo/viewer-core.mjs`; files that don't exist yet are skipped with a stderr note
- [ ] Exits 2 when any exported file has uncommitted changes, when no denylist exists and `--no-denylist` is absent, or on a usage error
- [ ] Imports only `gitmotive.store`, `gitmotive.resolve`, `gitmotive.hq` and `audit_public`, never `gitmotive.cli`. Changes nothing under `gitmotive/`
- [ ] The store file is byte-identical before and after an export (tested)
- [ ] The output schema matches spec "Data changes". `prompts` keys are exactly the set of `match.prompt_id` values
- [ ] Sanitisation:
  - `$HOME` becomes `~`
  - path-like sessions become 8 characters
  - pasted-content bodies become `[pasted content omitted]`
  - text is truncated to `--max-prompt-chars`
- [ ] Per-record gate:
  - A prompt text, reasoning or hq field with a secret, host or denylist hit becomes `[omitted: <check>]`, and stderr gets `omitted N field(s): …`. The export still succeeds
  - A hit in source line `text` is fatal (exit 1, nothing written)
  - After serialising, the whole output is rescanned, and any surviving hit means exit 1 with nothing written
- [ ] Warns on stderr when the output is over 1.5 MB
- [ ] The committed `data.json` was produced with the real local denylist. `audit_public.py --tree --denylist .audit-denylist` and `tests/test_public_text.py` pass
## Tests
`tests/test_export_demo.py` uses a temp repo and a temp `GITMOTIVE_HOME` with synthetic events:
- a Claude edit with reasoning and a model
- an hq-style prompt
- a pasted-content prompt
- an unreferenced prompt containing `gitmotive blame`
- a referenced prompt containing `acme-widgets`, with that term in a temp denylist
- a referenced prompt with a concatenation-built secret

It asserts the schema, that the unreferenced prompt is absent, the omitted markers and stderr counts, that the term is absent from the output and the captured streams, the dirty-file abort, the source-line fatal path, and that the store bytes are unchanged.
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none

- [ ] Per-record gate and whole-output rescan also run the `path` check (medium) (spec review r2 minor)
