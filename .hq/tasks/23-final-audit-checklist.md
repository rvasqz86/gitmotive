# Task 23: Regenerate demo data, final audit and human checklist
Status: done
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

## Implementation notes (round 1)
- **Default demo files changed** (per manager instruction) in `scripts/export_demo.py` `DEFAULT_FILES`:
  `site/demo/viewer.js`, `site/demo/viewer-core.mjs`, `launch/DEPLOY.md`, `tests/test_export_demo.py`.
  The old defaults `gitmotive/cli.py` and `gitmotive/adapters.py` have 0 matched lines at HEAD (their
  lines predate the dogfood step), so they could not meet the criterion. `scripts/export_demo.py` itself
  has model matches but is not a default: this task edits it, and the exporter refuses dirty files.
  `.hq/spec.md` (Demo data → Files) still lists the old defaults; the manager may want to update it.
- **data.json regenerated** with `GITMOTIVE_AUDIT_DENYLIST=.hq/audit-denylist python3 scripts/export_demo.py`
  (exit 0): 4 files, 859 matched lines, 5 prompts, 484421 bytes, no gate omissions. Matches with a
  non-null `model` per file: viewer.js 317/317, viewer-core.mjs 81/81, DEPLOY.md 96/96,
  test_export_demo.py 310/365. `rev` is HEAD 2b83f82; the exported files are clean at HEAD (the
  working tree has this task's uncommitted edits to other files, since implementers do not commit).
- **Deep link** moved from `#gitmotive/cli.py:42` (not in the export) to `#site/demo/viewer.js:14`
  (matched, model set, prompt and reasoning present) in `site/DEMO_SCRIPT.md` (both places),
  the hint in `site/demo/index.html`, and the home page CTA button in `site/index.html`.
- **New test** `tests/test_site.py::test_demo_data_and_deep_links`: data.json lists exactly the default
  files, each has a model match, and every `/demo/#file:n` deep link on the site and in the demo script
  resolves to a model-carrying line whose prompt is exported.
- **Guard fix** in `tests/test_public_text.py`: the command check misread
  `gh repo edit rvasqz86/gitmotive --visibility …` (required verbatim in the checklist) as an unknown
  `gitmotive --visibility` command. A `gh repo <verb>` prefix now marks the slug as not an invocation;
  self-test cases added for the skip and for a real invocation on the next line still being caught.
- **Audits:** `audit_public.py --tree --denylist .hq/audit-denylist` exits 0 (high=0 medium=0 info=2).
  `--history` exits 1: high=0, medium=15 (all `artifact`: tracked `build/` and `dist/` files from the two
  early commits), info=2 (`path` in `.hq/` notes). No secret, denylist, host or transcript findings.
  This is exactly what `.hq/history-rewrite-plan.md` removes (step 2, `--invert-paths --path build/ --path dist/`).
- **Checklist:** `launch/CHECKLIST.md` with Done (each item and path) and the 9 hand steps in order.
- Tests: all `tests/test_*.py` pass with the denylist exported; `node --test tests/js/viewer-core.test.mjs`
  passes 10/10. Nothing was pushed, published, deployed, or changed in visibility or DNS.

## Implementation notes (round 2)
- **Scratchpad path leak fixed:** `scripts/export_demo.py` has a new `repo_files(root, paths)`. It is used
  for each prompt's `files` list. Absolute paths inside the repo become repo-relative. Absolute paths
  elsewhere (`/tmp/...` scratchpads, other homes, `C:/...`) and `../` paths are dropped. Duplicates are removed.
- **Test location:** the new tests are in **`tests/test_export_demo_files.py`**, not `tests/test_export_demo.py`.
  That file is one of the exporter's `DEFAULT_FILES`, and editing it would make the regeneration refuse
  (dirty exported file). The new file reuses that module's helpers. It has an end-to-end test with a
  `/tmp/claude-1000/-home-<user>-…/scratchpad/walk.mjs` sibling, an in-repo absolute path, a `../` path
  and a foreign home path, plus a unit test of `repo_files`.
- **data.json regenerated** (exit 0): 4 files, 859 matched lines, 5 prompts, 484305 bytes. 0 hits for
  `scratchpad` or `/tmp/`. Prompt `66d26717e789` siblings are now all repo paths.
- **Deep link** is now `site/demo/viewer-core.mjs:19` (`export function colorFor(promptId)`). Its `why` is
  `same commit, line text in edit`, the model is set, and the reasoning ("contrast-checked 12-colour
  palette") describes the line. It is updated in `site/index.html`, `site/demo/index.html` and both places in
  `site/DEMO_SCRIPT.md`. `tests/test_site.py::test_demo_data_and_deep_links` now also requires
  `line text in edit` and non-empty reasoning for each deep link, and no `/`, `~` or `../` paths in any
  prompt's `files`.
- **Checklist (manager notes):** all rewrite and force-push steps are removed. "Done" now has a line saying
  the history was audited and only build/dist copies of our own code remain (accepted, harmless).
  The hand steps are in the manager's order: merge locally → `git push origin main` → flip visibility →
  Cloudflare/DNS (DEPLOY.md 1–5, verify with 6) → PyPI (before recording, since the demo script runs
  `pipx install gitmotive`) → record demo → application → post drafts. This makes 8 steps, not the
  original 9. The review's denylist-placeholder finding is moot because that step is gone.
- **Spec defaults:** already amended by the manager. The code matches.
- **Results:** all `tests/test_*.py` pass (with the denylist exported). Node viewer-core tests pass 10/10.
  `audit_public.py --tree` exits 0 (high=0 medium=0 info=2). `--history` is unchanged: high=0 medium=15
  (build/dist artifacts) info=2. Nothing was pushed, published, deployed or changed in visibility or DNS.

## Manager amendment
The human skipped the history rewrite at task 23. Criteria that reference the rewrite plan or a force-push are void; the checklist instead records "history audited; only build/dist copies of own code remain (accepted)".
