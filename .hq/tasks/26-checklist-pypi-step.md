# Task 26: Fix the PyPI upload step in the launch checklist
Status: done
Type: docs
Scope: launch
Depends on: 25
## Goal
Step 5 of `launch/CHECKLIST.md` says `python -m twine upload dist/*`, but `scripts/check_dist.sh` builds into a temp dir (`$TMPDIR/gitmotive-dist.XXXXXX/dist`). It prints the exact `twine upload …` command and never writes `./dist`, so the step as written fails with "no files". Change the step to: run `sh scripts/check_dist.sh`, then run the `python -m twine upload …` line it prints (twine must be installed, e.g. `pipx run twine upload …` or `python -m pip install --user twine`). Mention that a PyPI account plus an API token are needed. Also check `launch/DEPLOY.md`, `README.md` and `site/` for the same wrong `dist/*` instruction, and fix it wherever it appears.
## Files
- launch/CHECKLIST.md (modify)
- any other file that has the same wrong instruction (modify)
- tests/test_public_text.py (modify: assert that no launch, README or site text says `twine upload dist/*`)
## Acceptance criteria
- [ ] Step 5 works as written against the real `check_dist.sh` behaviour
- [ ] The new assertion passes, and so does the full suite
## Tests
`export GITMOTIVE_AUDIT_DENYLIST=.hq/audit-denylist; for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none
## Implementation notes (round 1)
- `launch/CHECKLIST.md` step 5: now runs only `sh scripts/check_dist.sh`, explains that it builds into `$TMPDIR/gitmotive-dist.XXXXXX/dist` (not `./dist`) and prints the exact `python -m twine upload …` line under `to publish (not run):`, says to run that line, and how to get twine (`python -m pip install --user twine`, or `pipx run twine upload …` with the same paths). It also says a PyPI account and API token are needed (username `__token__`).
- I grepped `launch/` (DEPLOY.md included), `README.md` and `site/` for `twine` / `dist/*`. The wrong instruction was only in CHECKLIST.md.
- `tests/test_public_text.py`: added `twine_dist_violations` over COMMAND_SCOPE (README, site, launch), matching `twine upload dist/*` and `./dist/*`. There is a self-test on a temp repo and a real-tree test. The full suite passes.
