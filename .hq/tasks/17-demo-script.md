# Task 17: 60-second demo script for recording
Status: todo
Type: docs
Scope: site
Depends on: 14
## Goal
Write `site/DEMO_SCRIPT.md`, a 60-second screen-recording script with real commands, browser beats and voice-over lines with timings. It is served publicly as-is (spec "Site"), and contains nothing sensitive.
## Files
- site/DEMO_SCRIPT.md (create)
- tests/test_site.py (modify: timestamp check)
## Acceptance criteria
- [ ] Timed sections ending at or before 0:60:
  - a hook (0–8 s)
  - `pipx install gitmotive` and `gitmotive install --agent claude`
  - a Claude Code edit
  - `git commit`
  - `git motive <file>:<line>` showing the prompt, reasoning and model
  - the gitmotive.tech/demo/ viewer via a deep link
  - a close on the tagline and URL
- [ ] A pre-recording checklist: clean terminal, font size, a prepared sample repo, `GITMOTIVE_STORE` unset
- [ ] Only real commands (`test_public_text.py`); no organisation names, no client repos
## Tests
Extend `tests/test_site.py`: parse the `m:ss` timestamps in `DEMO_SCRIPT.md` and assert the maximum is ≤ 1:00.
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none
