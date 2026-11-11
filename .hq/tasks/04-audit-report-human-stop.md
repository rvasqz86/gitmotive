# Task 04: [HUMAN STOP] Run the audit, write the report and the proposed history-rewrite plan
Status: done
Type: chore
Scope: audit
Depends on: 03
## Goal
This is the brief's step-1 [CONFIRM]. Run `scripts/audit_public.py` over the tree and full history with the local denylist `.hq/audit-denylist`, then write a findings report and an exact proposed `git filter-repo` plan. Then **stop for the human**. **Make no commit, no history rewrite, no push, and no ref change.** Write only the two gitignored report files.
## Files
- .hq/audit-report.md (create; gitignored by task 01)
- .hq/history-rewrite-plan.md (create; gitignored by task 01)
## Acceptance criteria
- [ ] Denylist is `.hq/audit-denylist` (manager-created, gitignored; human chose this at Q6): pass `--denylist .hq/audit-denylist` everywhere. If it is missing, reply `BLOCKED: need denylist` and do nothing else
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
No new tests. Run the suite to show nothing changed (`for f in tests/test_*.py; do python3 "$f" || exit 1; done`), and run `python3 scripts/audit_public.py --tree --history --denylist .hq/audit-denylist --json`. Exit 1 here is the report, not a failure of this task.
## Spec issue
none
## Implementation notes (round 1)
- Ran the suite (all pass) and the audit with `--denylist .hq/audit-denylist` across tree+history (exit 1, high=0 medium=15), plus each scope on its own. Tree: 0 findings. History: 15 `artifact` findings under `build/` and `dist/`, introduced in `da374b4` and `856a54d`.
- Wrote `.hq/audit-report.md` (findings, counts per check and per scope, manual review counts, before/after refs and status) and `.hq/history-rewrite-plan.md`. The plan is `filter-repo --invert-paths --path build/ --path dist/`, with no `--replace-text` because history has 0 secret and 0 denylist hits. `git-filter-repo` isn't installed, and the plan says so.
- Task 05: there are no tree findings, so it has nothing to apply from this audit.
- Manual review: the dogfood store has 2 host (private-IP literals from test fixtures) and 34 own-home path hits. Task 13's exporter has to handle them.
- No source or test changes. No commit and no ref change. Denylist terms appear only as `<denylist:N>`, and neither report contains any.
