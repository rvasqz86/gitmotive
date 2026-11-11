# Task 12: Move stamping into resolve.stamp with a persist flag
Status: done
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
- [ ] `grep -n "def _stamp\|_stamp(\|_commit_has\|_blob_lines" gitmotive/cli.py` finds nothing; `resolve.py` does not import cli
- [ ] `gitmotive stamp` output is unchanged
## Tests
`tests/test_stamp.py` as above.
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none

## Implementation notes (round 1)
- `resolve.stamp(root, events, persist=True) -> int` is the old `cli._stamp` body, moved verbatim, minus the `quiet`/print logic. With `persist=False` it mutates only the in-memory events and never calls `store.rewrite_all`. `_blob_lines` and `_commit_has` moved verbatim as private helpers in `resolve`. `resolve.py` still imports only `store`.
- In `cli.py`, `cmd_why` and `cmd_log` call `resolve.stamp(root, events)` and drop the three functions. `cmd_stamp` prints `stamped N edit(s)` from the return value. To keep the output byte-identical, it prints only when an edit is waiting for a stamp. The old `_stamp` returned early without printing when nothing was pending, so `gitmotive stamp` printed nothing in that case.
- `tests/test_site.py` (outside the listed files) monkeypatched `cli._stamp`, which no longer exists, so that patch now targets `resolve.stamp`. This change is required: without it, `getattr` fails.
- Grep criterion: `grep -n "def _stamp\|_stamp(\|_commit_has\|_blob_lines" gitmotive/cli.py` still matches `cmd_stamp` (its def and dispatch). `cmd_stamp` must stay, and the pattern matched it before this task too. None of the three removed functions remain. `test_layering` in `tests/test_stamp.py` checks this while ignoring `cmd_stamp`.
- `tests/test_stamp.py` covers: persist=False with a user-scope store (temp `GITMOTIVE_HOME`, `GITMOTIVE_STORE=user`) and with a repo-scope store, where the file bytes match before and after while the in-memory commit is set. It also covers persist=True rewriting the file, `cmd_stamp` output for both the 1-stamp and nothing-pending cases, and layering. `tests/test_e2e.py` is unchanged and passes. The full test command passes.
