# Task 03: Public-text guard test
Status: done
Type: test
Scope: audit
Depends on: 02
## Goal
Create `tests/test_public_text.py` early, so every later site, docs, README and launch task is guarded automatically (spec "Public-text guard"): a denylist check over README.md, `site/**`, `launch/**` and `.hq/**`, and a real-command check over README, `site/**` (except `site/demo/data.json`) and `launch/**`.
## Files
- tests/test_public_text.py (create)
## Acceptance criteria
- [ ] The denylist check uses `audit_public.load_denylist` and `scan_text(..., checks=("denylist",))`, and prints `skipped denylist` when none is found; it scans README.md, `site/**`, `launch/**` and `.hq/**` (gitignored files under `.hq/` excluded, via `git ls-files -co --exclude-standard`)
- [ ] The command check looks only inside inline code, fenced code blocks and `<code>`/`<pre>`, so prose such as "gitmotive links lines" is ignored. It fails on `gitmotive init` or `gitmotive blame`, and on any `gitmotive <word>` that is not one of `why log stamp install capture help --version -V`. It does not scan `.hq/**` or `site/demo/data.json`
- [ ] Missing directories (`site/`, `launch/`) are fine
- [ ] Self-tests with a temp denylist containing `acme-widgets` and temp files prove both checks detect violations and that the reported text is redacted
- [ ] The test passes on the current tree, assuming no denylist hits in README or `.hq/` (if it finds any, record them for task 04 and mark the real-tree assertion as expected-fail **only** for the denylist part until task 05; state this in the report)
## Tests
`tests/test_public_text.py` itself.
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none

## Implementation notes (round 1)
- Created `tests/test_public_text.py` (plain-script runner, stdlib only). Files are listed with `git ls-files -co --exclude-standard -z -- <scope>`, so gitignored files (e.g. under `.hq/`) are skipped and missing `site/`/`launch/` are fine.
- Denylist check: `audit_public.load_denylist(None, ROOT)` + `scan_text(..., checks=("denylist",))` over README.md, `site/**` (incl. `site/demo/data.json`), `launch/**`, `.hq/**`; output lines pass through `audit_public.redact`. Prints `skipped denylist` when no denylist is found.
- Command check: extracts fenced blocks (``` / ~~~), inline backtick code, and `<code>`/`<pre>` (tags stripped, entities unescaped); flags any `gitmotive <word>` whose word is not in `why log stamp install capture help --version -V`. `gitmotive` preceded by `/ . - \w` (paths, URLs, `~/.gitmotive`) is not treated as an invocation, and only same-line arguments count. Skips `.hq/**` and `site/demo/data.json`. Reported paths are redacted too.
- Self-tests use temp git repos and a temp denylist with the synthetic `acme-widgets`, covering detection, scope, gitignore exclusion, missing dirs, prose ignored, and redaction (`<denylist:N>`).
- Real tree: no `.audit-denylist` or `$GITMOTIVE_AUDIT_DENYLIST` exists locally, so the denylist part prints `skipped denylist` (no hits recorded for task 04; nothing marked expected-fail). The command check passes on the current README. Full test command passes.

## Implementation notes (round 2)
- [major] `_INLINE` now stays within one paragraph (`(?!\n[ \t]*\n)` per char) and requires exact backtick-run lengths, so a stray backtick no longer shifts pairing. Reviewer's repro added as `test_command_check_stray_backtick_does_not_shift_pairing` (expects `R:3: ... gitmotive init`).
- [minor] Unclosed fences run to end of document (`\Z` accepted as fence end, and the opening line may end at `\Z`). Test: `test_command_check_unclosed_fence_runs_to_end`.
- [minor] `_INVOCATION` now matches `gitmotive` case-insensitively and allows a path prefix ending in `/` (`./gitmotive`, `bin/gitmotive`, `/usr/bin/gitmotive`); it must start at line start or after whitespace/`;&|(`'"$`. Dotfiles like `~/.gitmotive/venv` still don't count. The subcommand word is compared exactly (the CLI is case-sensitive), so `Gitmotive Init` is flagged as `Init`. Test: `test_command_check_paths_and_case`.
- [minor] Findings are deduplicated on (line, word), so `<code>`gitmotive init`</code>` reports once. Test: `test_command_check_dedupes_overlapping_regions`.
- [minor] Temp repos are recorded and removed by an `atexit` handler (`shutil.rmtree`). Verified: `/tmp/pubtext-*` count is unchanged after a run. Test: `test_temp_repos_are_cleaned_up`. About 30 `/tmp/pubtext-*` dirs left over from round-1 runs are still there; I left them alone.
- Full test command passes. The real tree still prints `skipped denylist` (no local denylist), and nothing is expected-fail.
