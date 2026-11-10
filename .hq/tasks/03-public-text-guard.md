# Task 03: Public-text guard test
Status: todo
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
