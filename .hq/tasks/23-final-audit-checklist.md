# Task 23: Regenerate demo data, final audit and human checklist
Status: todo
Type: chore
Scope: launch
Depends on: 14, 19, 22
## Goal
Regenerate `site/demo/data.json` from the dogfood events captured while building this branch (after the dogfood reinstall step), re-run the audits, and write `launch/CHECKLIST.md` listing what is done and what the human does by hand.
## Files
- site/demo/data.json (modify: regenerated with `python3 scripts/export_demo.py` using the default files)
- launch/CHECKLIST.md (create)
## Acceptance criteria
- [ ] data.json is regenerated at a clean HEAD with the local denylist. **Every default file has at least one match with a non-null `model`**; matches from events before the dogfood step may have a null `model`. If any default file has none, stop with a Spec issue stating the cause (dogfood step not run, or the implementer's hooks expose no model, per spec Open questions 7 and 8) instead of fabricating or hand-editing data
- [ ] `audit_public.py --tree --denylist .hq/audit-denylist` exits 0. The `--history` result is summarised (redacted) in the report, with a pointer to `.hq/history-rewrite-plan.md`
- [ ] `launch/CHECKLIST.md` "Done" lists each delivered item with its path. "You do by hand" lists, in order, with exact commands or links:
  1. review and merge this branch to main locally
  2. run the approved `.hq/history-rewrite-plan.md` on a fresh clone, then `scripts/audit_public.py --history`, then `scripts/export_demo.py`, and commit
  3. force-push (human only)
  4. `sh scripts/check_dist.sh`, then `python -m twine upload dist/*`
  5. the Cloudflare and DNS steps from `launch/DEPLOY.md`
  6. flip the repo public with `gh repo edit rvasqz86/gitmotive --visibility public --accept-visibility-change-consequences` (human only)
  7. record the demo from `site/DEMO_SCRIPT.md` and add `docs/demo.gif`
  8. fill the `launch/application.md` placeholders and submit by Dec 8 (deadline Dec 15, 2026)
  9. post the launch drafts
- [ ] No command in this task pushes, publishes, deploys, changes visibility or touches DNS
## Tests
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done` and the audit commands above.
## Spec issue
none
