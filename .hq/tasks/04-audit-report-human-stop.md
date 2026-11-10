# Task 04: [HUMAN STOP] Run the audit, write the report and the proposed history-rewrite plan
Status: todo
Type: chore
Scope: audit
Depends on: 03
## Goal
This is the brief's step-1 [CONFIRM]. Run `scripts/audit_public.py` over the tree and full history with the local `.audit-denylist` (spec Open question 6), then write a findings report and an exact proposed `git filter-repo` plan. Then **stop for the human**. **Make no commit, no history rewrite, no push, and no ref change.** Write only the two gitignored report files.
## Files
- .hq/audit-report.md (create; gitignored by task 01)
- .hq/history-rewrite-plan.md (create; gitignored by task 01)
## Acceptance criteria
- [ ] If `.audit-denylist` is missing, reply `BLOCKED: need .audit-denylist (spec Open question 6)` and do nothing else
- [ ] `audit-report.md` contains:
  - the commands run, the date and the HEAD SHA
  - counts per check and per scope
  - every finding: check, severity, path or blob, introducing commit, redacted excerpt
  - a separate "manual review" section covering tracked test fixtures, README examples, the committed `.hq/**`, and the user-scope dogfood store for this repo (`~/.gitmotive/repos/<hash>/events.jsonl`, which feeds the demo), summarised by check counts only
  - for each working-tree finding, a proposed fix: edit, remove, or an `.audit-allow` entry with its reason, for task 05 to apply after approval
- [ ] `history-rewrite-plan.md` gives exact commands for each history finding:
  - the backup mirror clone command
  - the `git filter-repo` invocations (e.g. `--invert-paths --path build/ --path dist/`, and `--replace-text <file>` with the replacements file placed under a gitignored path and its content described in redacted form)
  - the post-rewrite `audit_public.py --history` verification
  - the force-push command, labelled "HUMAN ONLY — after merge to main, before visibility flip"
  If the history is clean, the plan says so and proposes nothing
- [ ] Denylist terms appear only as `<denylist:N>` in both files
- [ ] `git rev-parse --all` is identical before and after (both outputs recorded in the report)
- [ ] `git status --porcelain` is identical before and after; the report files are ignored and don't show
- [ ] The reply ends with `HUMAN STOP: review .hq/audit-report.md and .hq/history-rewrite-plan.md`
## Tests
No new tests. Run the suite to show nothing changed (`for f in tests/test_*.py; do python3 "$f" || exit 1; done`), and run `python3 scripts/audit_public.py --tree --history --denylist .audit-denylist --json`. Exit 1 here is the report, not a failure of this task.
## Spec issue
none
