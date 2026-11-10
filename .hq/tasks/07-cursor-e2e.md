# Task 07: Claude Code and Cursor proven end to end through installed hook commands
Status: todo
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
