# Task 07: Claude Code and Cursor proven end to end through installed hook commands
Status: done
Type: feat
Scope: adapters
Depends on: 06
## Goal
Make Cursor capture robust to current payloads (`workspace_roots` instead of `cwd`, with `hook_event_name` present) and prove Claude Code and Cursor end to end by running the exact hook commands `gitmotive install` writes (spec "Cursor end to end"). **Precondition:** the manager has run, or asked the human to run, the dogfood reinstall step from spec Open question 7 after task 06; this task does not touch `~/`.
## Files
- gitmotive/adapters.py (modify: Cursor `cwd` falls back to `workspace_roots[0]`; `detect()` returns cursor when `conversation_id` is present, even alongside `hook_event_name`)
- tests/test_e2e_agents.py (create)
- tests/test_adapters.py (modify: cases for `workspace_roots` and for `conversation_id` with `hook_event_name`)
## Acceptance criteria
- [ ] For each of claude and cursor, in a temp git repo with HOME set to a temp dir:
  - `cli.main(["install","--agent",A])` writes the config
  - the test reads the command strings back from `.claude/settings.json` or `.cursor/hooks.json` and runs them with `sh -c`, feeding the prompt payload and then the edit payload on stdin
  - after the file edit and `git commit`, `python3 -m gitmotive why <file>:<line>` (as a subprocess) prints the prompt and exits 0; for Claude it also prints the transcript reasoning and `model claude-`
- [ ] A Cursor edit payload with only `workspace_roots`, run from a different cwd, stores the event in the right repo
- [ ] An untouched line prints `(none recorded)` and exits 1
- [ ] Copilot and omp behaviour is unchanged (existing tests pass)
- [ ] The task report records a live Cursor check (real `.cursor/hooks.json` session, then `git motive` output) if Cursor is available, or else states `unverified against live Cursor` (spec Open question 9)
## Tests
`tests/test_e2e_agents.py`, plus extensions to `tests/test_adapters.py`.
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none

## Implementation notes (round 1)
- `gitmotive/adapters.py`: in the cursor branch, `cwd` now comes from the payload `cwd`, else `workspace_roots[0]` (if it is a string), else `None`. `detect()` returns `cursor` whenever `conversation_id` is present, including alongside `hook_event_name`. I also updated the module docstring. The claude/copilot/omp paths are unchanged.
- `tests/test_adapters.py`: added `test_cursor_workspace_roots_as_cwd` (fallback, `cwd` wins when present, `None` when neither is present) and `test_cursor_detect_with_hook_event_name` (auto-detect plus normalize for both edit and prompt payloads that carry `hook_event_name`).
- `tests/test_e2e_agents.py` (new): each test sets up a temp git repo and a temp HOME (`GITMOTIVE_*` env stripped; cwd and env restored afterwards). It then:
  - calls `cli.main(["install","--agent",A])`
  - reads the command strings back from `.claude/settings.json` or `.cursor/hooks.json`
  - runs them with `sh -c`: the prompt payload first, then the agent edits the file, then the edit payload
  - runs `git commit`
  - runs `python3 -m gitmotive why fetch.py:6` as a subprocess and asserts exit 0 and that the prompt is printed. For claude it also checks the transcript reasoning and `model claude-`; for cursor it checks `via cursor`.
  - runs `fetch.py:1` (untouched) and asserts `(none recorded)` with exit 1
- In the Cursor test, both hooks run from a different cwd (the temp HOME) with payloads that carry only `workspace_roots` plus `hook_event_name`, with no `cwd`. It asserts the events landed in `<repo>/.gitmotive/events.jsonl` and that no `.gitmotive` was created in the other cwd.
- Sanity check: I ran the e2e against the pre-change `adapters.py` and the Cursor test fails (no store in the repo). With the change, the full test command passes (all 8 files).
- **Live Cursor check: unverified against live Cursor.** `cursor-agent` is installed and logged in on this machine. My attempt to run it headless (`cursor-agent -p --force --trust "<edit prompt>"` in a scratch repo with `gitmotive install --agent cursor`) was denied by the implementer's permission policy (launching another autonomous agent). To verify by hand:
  1. In a scratch git repo, run `PYTHONPATH=<checkout> python3 -m gitmotive install --agent cursor`.
  2. Run one Cursor session (IDE or `cursor-agent -p --force`) that edits a file.
  3. Commit, then run `git motive <file>:<line>`.
