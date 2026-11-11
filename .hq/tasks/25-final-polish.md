# Task 25: Final polish (deferred review minors + honest reasoning)
Status: done
Type: fix
Scope: site
Depends on: 23
## Goal
Phase D cleanup. Apply the minor review findings deferred during tasks 09–23, and stop the demo from showing reasoning that belongs to a different tool call. Keep every change small. No new features.

## Items
### Capture honesty (gitmotive/capture.py, scripts/export_demo.py)
1. When `_transcript_context` cannot find the matching `tool_use` (the race from task 24), set **reasoning to None** instead of falling back to the last assistant text. This is the product principle: say "none recorded" rather than guess. Keep the model fallback from task 24. Add a test.
2. Older events in the store already carry fallback reasoning (one demo match shows the bare word `READY`). In the exporter, drop `reasoning` when it has fewer than 3 words. Add a test. Then regenerate `site/demo/data.json` with `GITMOTIVE_AUDIT_DENYLIST=.hq/audit-denylist`, and keep the deep links valid (existing tests enforce `line text in edit`).
3. README "Known gaps": update the first-edit-reasoning note to match. That reasoning is now omitted rather than possibly stale.

### Code
4. `gitmotive/cli.py`: remove the unused `import subprocess`.
5. Packaging: add `MANIFEST.in` with `include tests/_wheel.py` so `test_packaging.py` works from an unpacked sdist. `scripts/check_dist.sh` must still pass `twine check --strict`.

### Demo viewer (site/demo/)
6. Add `.meta[hidden] { display: none; }`.
7. Wrap the render phase in try/catch and call `showError("unreadable data")`.
8. A matched line with no commit shows `·` in the gutter, never an empty gutter.
9. The error state uses `role="alert"`, or focus moves to the state box after "Try again".
10. When `totalLines === 0`, the empty-data banner gets its own wording.

### Docs (scripts/docs_src, scripts/gen_docs.py, site/assets/site.css), then regenerate with `gen_docs.py`
11. data-format.md: "missing optional keys take their defaults; lines without kind/session/ts are skipped".
12. data-format.md: the `.git/info/exclude` entry is repo scope only.
13. Style `nav.toc` and `table.fields` in site.css, or remove the classes.
14. gen_docs.py: add a guard against a leading h3 in `toc_html`, and document the list-continuation limit in the docstring.

### Installer (site/install.sh, tests/test_site_install.py)
15. `[ -n "${HOME:-}" ] || die "HOME is not set"` before the defaults.
16. Reject a `GITMOTIVE_HOME` or `GITMOTIVE_BIN` that contains `"`, `$` or a backtick (`die`).

### Launch copy (launch/, site/DEMO_SCRIPT.md)
17. DEMO_SCRIPT.md "Before recording": add three prerequisites. Confirm `pipx install gitmotive` resolves from PyPI, and that the deployed demo shows the deep-linked line. Paste the prompt rather than type it, and cut from submit to the finished edit.
18. application.md:
    - Under Status, add a line listing the prerequisites before submitting: site deployed, repo public, PyPI published.
    - Fix the git-notes claim: notes refs are not pushed or fetched by default, so say gitmotive would configure the refspec. This is a planned milestone, so the wording must be future tense.
    - Change the figures line to "Fill in real figures before submitting; do not estimate."
19. product-hunt.md: describe the ranking as "scores same commit, then matching line text; newest wins ties". Point caption 1 at a real demo path, not `src/fetch.py:42`.
20. show-hn.md: lowercase "gitmotive" in the title, to be consistent.
21. launch/CHECKLIST.md: list `tests/test_export_demo_files.py` in the exporter's Done entry.

## Acceptance criteria
- [ ] Every item above is done, or skipped with a one-line reason in the implementation notes
- [ ] `python3 scripts/gen_docs.py --check` passes
- [ ] The full test command passes (`export GITMOTIVE_AUDIT_DENYLIST=.hq/audit-denylist; for f in tests/test_*.py; do python3 "$f" || exit 1; done`)
- [ ] `python3 scripts/audit_public.py --tree --denylist .hq/audit-denylist` exits 0
- [ ] `site/demo/data.json` has no `/tmp/` path, no `-home-` string and no reasoning under 3 words
## Tests
As listed in the items, plus the full suite.
## Spec issue
none

## Implementation notes (round 1)
All 21 items done; none skipped.

- **1** `capture._transcript_context` returns `(None, last_model)` when no `tool_use` matches, which covers a missing id too. If the match is found but its own message has no text, it still carries over the preceding assistant text, as before. Tests: `test_model_when_current_tool_use_not_flushed` now expects `reasoning is None`. The new `test_no_matching_tool_use_records_no_reasoning` covers it end to end through `handle`.
- **2** `export_demo.reasoning_text()` drops reasoning under 3 words (`MIN_REASONING_WORDS`) before the gate. Tests: `test_short_reasoning_dropped`, and in the integration fixture edit `eh` now carries `READY` and must export `None`. The `ed` path fixture became `"notes are in <path>"` so it stays 3+ words and still exercises the path gate.
- **2, regeneration:** the exporter refuses files that differ from HEAD, and `site/demo/viewer.js` is modified by this task. I can't commit, so I exported from a temporary detached `git worktree` of HEAD in the scratchpad. Its `.gitmotive/events.jsonl` was a symlink to the real user store, and it ran the new `export_demo.py` with the same denylist. The worktree was removed and pruned afterwards; the store was read-only (`persist=False`).
  - Result: `rev` = e92279f. The demo's copy of `viewer.js` is the HEAD version, without this task's ~15-line viewer change.
  - Data checks: 0 `/tmp/` or `-home-` strings. All 96 `launch/DEPLOY.md` matches lost their `READY` reasoning; the other 3 files keep theirs. The deep-link tests pass.
  - **For the reviewer/manager:** if you want `rev` to include this commit, re-run `scripts/export_demo.py` after committing.
  - `test_viewer.test_committed_data_matches_schema` now also asserts no `/tmp/`, no `-home-` and no reasoning under 3 words.
- **3** README "Known gaps" note: the first edit of a turn now has no reasoning; the model fallback is unchanged.
- **4** Removed `import subprocess` from `cli.py`. Nothing else used it.
- **5** `MANIFEST.in` (`include tests/_wheel.py`). `scripts/check_dist.sh` passes `twine check --strict`, and the sdist contains `tests/_wheel.py`.
- **6–10** Viewer changes:
  - `.meta[hidden]` rule added.
  - The render phase is in try/catch → `showError("unreadable data")`, which also resets `S.idx` and hides the meta.
  - The gutter falls back to `·`.
  - `setState` sets `role="alert"` for `err` and `role="status"` otherwise.
  - When `totalLines === 0` the banner reads "This snapshot has no source lines."
  - Static checks are in `test_viewer.test_state_handling`.
- **11–12** data-format.md wording. Defaults and skipping were verified against `store.from_json`/`read_all` (a missing required field → TypeError → skipped).
- **13** Styled `nav.toc` and `table.fields` in site.css.
- **14** `toc_html` lists a leading h3 at the top level instead of emitting `<ol><ol>`. The list-continuation limit is now in the module docstring. Test: `test_toc_leading_h3_is_well_formed`. Docs regenerated, and `--check` passes.
- **15–16** `install.sh`:
  - HOME guard first in `main`.
  - `check_path` rejects `"`, `$` and backticks in `GITMOTIVE_HOME`/`GITMOTIVE_BIN`. It uses escaped case patterns, because `'$'` trips the `$'` bashism check.
  - Tests: `test_unset_home_fails_clearly` and `test_rejects_shell_metachars_in_paths`.
- **17–21** Launch copy as specified. Product Hunt caption 1 now uses `site/demo/viewer-core.mjs:19`, which matches by line text in the regenerated data.
- **Verification:** the full test command passes, `gen_docs.py --check` passes, and `audit_public.py --tree --denylist .hq/audit-denylist` exits 0.
