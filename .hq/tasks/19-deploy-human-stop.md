# Task 19: [HUMAN STOP] Deploy readiness review
Status: done
Type: chore
Scope: deploy
Depends on: 18
## Goal
This is the brief's step-4 [CONFIRM]. Verify the site is deployable and give the human a go/no-go summary. **Make no commit and no irreversible change**: no push, no wrangler, no Cloudflare, registrar or DNS change, no visibility change. Then stop.
## Files
- .hq/deploy-readiness.md (create; gitignored by task 01)
## Acceptance criteria
- [ ] The report includes:
  - the full test-suite result
  - the `gen_docs.py --check` result
  - the `audit_public.py --tree --denylist .audit-denylist` result
  - bytes per page
  - every file that would be deployed (`find site -type f | sort`), noting that `DEMO_SCRIPT.md` is intentionally public and that no test files are inside `site/`
- [ ] The report repeats the human steps from `launch/DEPLOY.md` in order, as checkboxes, and notes that the workflow deploys only after the human merges and pushes to main
- [ ] `git rev-parse --all` and `git status --porcelain` are identical before and after (both recorded); the report file is ignored
- [ ] The reply ends with `HUMAN STOP: review .hq/deploy-readiness.md before any push or DNS change`
## Tests
Run only: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none

## Implementation notes (round 1)
- Wrote `.hq/deploy-readiness.md`. It is ignored via `.hq/.gitignore:7`. Verdict: GO. Nothing was deployed, pushed or committed, and no code changed.
- Test suite: all 18 test files exit 0. `gen_docs.py --check`: up to date, exit 0.
- `audit_public.py --tree --denylist .audit-denylist` exits 2 because there is no `.audit-denylist` file in the repo root. The project's denylist is `.hq/audit-denylist`, which the runtime `test=` line also uses. Run with that file, the audit exits 0: high=0, medium=0, info=2. Both info hits are local paths in `.hq/` notes, which are not deployed. The report records both runs and suggests an optional `cp`.
- `site/` holds 16 files, 234,048 bytes, and no test files. `DEMO_SCRIPT.md` is noted as intentionally public.
- `git rev-parse --all` and `git status --porcelain` were captured before and after. They are identical, and both are recorded in the report.
- One acceptance criterion says the reply should end with the HUMAN STOP line. The manager asked for an exact one-line `DONE` reply, so that line is the last line of the report file instead.
