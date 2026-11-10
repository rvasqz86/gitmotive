# Task 05: Apply approved working-tree audit fixes
Status: done
Type: chore
Scope: audit
Depends on: 04
## Goal
Apply the working-tree fixes the human approved in `.hq/audit-report.md` (edits, removals, `.audit-allow` entries with reasons) so the tree audit becomes a standing gate. History is not touched.
## Files
- Files named in the approved working-tree section of `.hq/audit-report.md` (modify). If the approved changes exceed about 300 lines, stop with a Spec issue proposing a split
- .audit-allow (modify only for approved false positives, each with a reason)
- tests/test_public_text.py (modify: remove any expected-fail marker added in task 03)
## Acceptance criteria
- [ ] `python3 scripts/audit_public.py --tree --denylist .audit-denylist` exits 0
- [ ] `tests/test_public_text.py` passes with the real denylist present, with no expected-fail markers
- [ ] Every `.audit-allow` entry matches an approved item in the report
- [ ] The known `host` finding in `.hq/spec-review.md` (spec Risks) is resolved as the human chose: an `.audit-allow` entry with a reason, or left for the manager to reword (the implementer does not edit `.hq/` review files)
- [ ] No denylist term in any changed line (verified by the two commands above)
- [ ] Existing tests pass
## Tests
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done` and `python3 scripts/audit_public.py --tree --denylist .audit-denylist`
## Spec issue
none

## Manager notes
No working-tree findings (audit report, human approved). Verified by manager: `audit_public.py --tree --denylist .hq/audit-denylist` exit 0; `tests/test_public_text.py` passes with GITMOTIVE_AUDIT_DENYLIST set; no expected-fail markers; spec-review private-IP quote already reworded by manager before Gate 1. No code change, so Type changed from fix to chore.
