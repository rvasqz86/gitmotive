# Task 10: Fresh-machine smoke test (Docker or clean venv)
Status: todo
Type: test
Scope: packaging
Depends on: 09
## Goal
Prove a stranger's path works using the real CLI (spec Open question 1: the brief's "init" is `gitmotive install`, its "blame" is `git motive <file>:<line>`): install from a locally built wheel, install hooks in a sample repo, simulate an AI-attributed edit through the installed Claude hook command, commit, and query.
## Files
- scripts/smoke_fresh.sh (create)
- scripts/smoke_inner.sh (create)
- tests/test_smoke.py (create)
## Acceptance criteria
- [ ] `--docker`: builds the wheel on the host, then runs `python:3.12-slim` with the wheel mounted read-only; installs git and pipx in the container; runs `pipx install /dist/gitmotive-*.whl`; runs `smoke_inner.sh`
- [ ] `--venv`: a new venv under `$TMPDIR` with `HOME` set to a temp dir; `pip install --no-index <wheel>` (no network)
- [ ] With no flag, `--docker` is chosen if `docker info` succeeds, otherwise `--venv`. `--docker` without Docker exits 2 with a message
- [ ] `smoke_inner.sh`, in order:
  1. `gitmotive --version`
  2. `git init` a sample repo and make the first commit
  3. `gitmotive install --agent claude`
  4. read the UserPromptSubmit and PostToolUse commands from `.claude/settings.json`
  5. pipe a prompt payload into the first, apply the edit, and pipe an edit payload (with a transcript containing reasoning and `"model": "claude-opus-5-5"`) into the second
  6. `git commit`
  7. **before any `why`/`log`**, assert that `.gitmotive/events.jsonl` has an edit with a non-null `commit` equal to `git rev-parse HEAD` (proving the post-commit hook ran)
  8. `git motive <file>:<line>` and grep for the prompt text, the reasoning text and `model claude-opus-5-5`
  9. `gitmotive log` shows the prompt
  10. print `SMOKE OK`
  Any miss exits non-zero
- [ ] The `--docker` run output is pasted into the report
## Tests
`tests/test_smoke.py` runs `sh scripts/smoke_fresh.sh --venv` when `_wheel.build_wheel()` returns a wheel (passing its path through `GITMOTIVE_WHEEL`), and asserts `SMOKE OK`. Otherwise it prints `skip smoke`.
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`, plus `sh scripts/smoke_fresh.sh --docker` (manual, recorded)
## Spec issue
none
