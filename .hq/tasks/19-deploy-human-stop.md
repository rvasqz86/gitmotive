# Task 19: [HUMAN STOP] Deploy readiness review
Status: todo
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
