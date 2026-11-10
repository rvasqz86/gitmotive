# Task 20: README rewrite for public launch
Status: todo
Type: docs
Scope: readme
Depends on: 10, 15
## Goal
Rewrite README.md for strangers: the tagline, a GIF placeholder with the exact recording sequence, install, quickstart, supported agents (Copilot and oh-my-pi experimental), and a link to gitmotive.tech. Keep the accurate technical content (how it links, known gaps, scopes, hq support), trimmed.
## Files
- README.md (modify)
- tests/test_public_text.py (modify: README must link `https://gitmotive.tech` and contain `pipx install gitmotive`)
## Acceptance criteria
- [ ] Order:
  1. Title and tagline, then a what/why paragraph
  2. `<!-- GIF: docs/demo.gif -->`, followed by a fenced recording sequence: `pipx install gitmotive`, `cd your-repo`, `gitmotive install --agent claude`, a Claude Code edit, `git commit -am "…"`, `git motive path/to/file.py:42`, `gitmotive log`
  3. Install (pipx, the curl one-liner, from source with `install.sh`)
  4. Quickstart
  5. Supported agents table with a Status column (`supported`/`experimental`)
  6. Commands (matching `cli.USAGE`, plus `--version`)
  7. How it links
  8. Privacy (local only, no network, no telemetry; prompts are stored verbatim; use `--scope user` for work you don't own)
  9. Known gaps
  10. Live demo and docs links
  11. License
- [ ] The example `git motive` output matches the current `why` format, including `via` and `model`
- [ ] `tests/test_public_text.py` and `audit_public.py --tree --denylist .audit-denylist` pass
## Tests
`tests/test_public_text.py` (extended as above).
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none
