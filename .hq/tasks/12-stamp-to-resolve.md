# Task 12: Move stamping into resolve.stamp with a persist flag
Status: todo
Type: refactor
Scope: resolve
Depends on: 08
## Goal
Move `cli._stamp`, `_blob_lines` and `_commit_has` into `resolve.stamp(root, events, persist=True) -> int` (spec "Stamping moves to resolve"). The demo exporter can then stamp in memory without rewriting the developer's store, without importing `cli` (layering rule: nothing imports cli).
## Files
- gitmotive/resolve.py (modify: add `stamp`, plus the private `_blob_lines` and `_commit_has`)
- gitmotive/cli.py (modify: remove the three functions; `cmd_why` and `cmd_log` call `resolve.stamp(root, events)`; `cmd_stamp` prints `stamped N edit(s)` from the return value)
- tests/test_stamp.py (create)
## Acceptance criteria
- [ ] `resolve.stamp` behaves exactly like the old `_stamp`; existing `tests/test_e2e.py` passes unchanged
- [ ] With `persist=False`, the in-memory events get `commit` set and the events file is byte-identical before and after (tested with a temp `GITMOTIVE_HOME` and user-scope store, and with a repo-scope store)
- [ ] With `persist=True`, the file is rewritten with the stamps
- [ ] `grep -n "_stamp\|_commit_has\|_blob_lines" gitmotive/cli.py` finds nothing; `resolve.py` does not import cli
- [ ] `gitmotive stamp` output is unchanged
## Tests
`tests/test_stamp.py` as above.
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none
