# Task 01: Untrack build/ artifacts; ignore build output and local .hq reports
Status: done
Type: chore
Scope: repo
Depends on: none
## Goal
Remove the stale tracked `build/lib/` copy so later `--tree` audits don't hit it, make sure build output can never be tracked again, and keep the human-stop report files local while the rest of `.hq/` is committed (spec "`.hq/` is committed").
## Files
- build/lib/gitmotive/*.py (delete: `git rm -r build/`)
- .gitignore (modify: add `build/`)
- .hq/.gitignore (modify: add `audit-report*.md`, `history-rewrite-plan.md`, `deploy-readiness.md`; keep `brief-source.md` and `runtime.log*`)
- tests/test_repo_hygiene.py (create)
## Acceptance criteria
- [ ] `git ls-files build dist '*.whl' '*.egg-info'` prints nothing
- [ ] `.gitignore` contains `build/` and still contains `dist/`, `*.egg-info/`, `.gitmotive/`, `__pycache__/`
- [ ] `.hq/.gitignore` contains exactly the five local-only entries above; `.hq/` itself is NOT ignored (`git check-ignore .hq/spec.md` exits 1)
- [ ] `git check-ignore .hq/brief-source.md .hq/audit-report.md .hq/history-rewrite-plan.md .hq/deploy-readiness.md` matches all four
- [ ] No history rewrite; a normal deletion commit
## Tests
`tests/test_repo_hygiene.py`: asserts no tracked build artifacts, the root and `.hq` ignore entries above via `git check-ignore`, and that `.hq/spec.md` is not ignored.
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none

## Implementation notes (round 1)
- `git rm -r build/` (deletion staged, not committed); removed the leftover working-tree dir too.
- `.gitignore`: appended `build/`; existing `dist/`, `*.egg-info/`, `.gitmotive/`, `__pycache__/` kept.
- `.hq/.gitignore`: added `audit-report*.md`, `history-rewrite-plan.md`, `deploy-readiness.md`; kept `brief-source.md`, `runtime.log*`.
- `tests/test_repo_hygiene.py`: checks `git ls-files` for build artifacts, root + `.hq` ignores via `git check-ignore --no-index` (so results don't depend on whether a path is tracked), and that `.hq/spec.md` etc. are not ignored.
- Full test command passes. Commit is left to the manager (no history rewrite).
