# Task 02: Public-release audit scanner (tree + full history)
Status: done
Type: feat
Scope: audit
Depends on: 01
## Goal
Add `scripts/audit_public.py` per the spec's "Audit scanner" and "Denylist handling": checks `secret`, `denylist`, `transcript`, `host`, `path`, `artifact` with the fixed severity table, `--tree`/`--history` scopes, a committed `.audit-allow`, a denylist read only from a local file or env var, and redaction of denylist hits as `<denylist:N>`.
## Files
- scripts/audit_public.py (create)
- .audit-allow (create: header comment explaining the format `<path-glob> <check-id>  # reason`; no entries)
- .gitignore (modify: add `.audit-denylist`)
- tests/test_audit.py (create)
## Acceptance criteria
- [ ] CLI: `--tree`, `--history`, `--denylist`, `--allow`, `--json`, `--root`; neither scope flag means both; exit codes 0 (no high or medium findings), 1 (high or medium findings), 2 (usage error)
- [ ] Importable API exactly as in spec Interfaces: `load_denylist` (returns None when no denylist is found), `scan_text(text, where, denylist, checks=...)`, `redact`, `Finding`, `SEVERITY`
- [ ] Severities match the spec table; own-home paths are `info`; `.audit-allow` matches are downgraded to `info` and shown as `allowed`; an `.audit-allow` line without a `# reason` is a usage error (exit 2)
- [ ] Secret regexes require a token body (a bare prefix in prose does not match); host IPv4 matches only bounded full private dotted quads with octets 0–255; version strings such as `10.1.2` and `3.10.12.4.1` do not match; `~/.local/bin` does not match the hostname rule
- [ ] **Self-match rule:** `audit_public.py` builds its literal regex prefixes by string concatenation; `tests/test_audit.py` builds every planted secret and IP by concatenation at runtime; `python3 scripts/audit_public.py --tree` on this repo reports no `secret` or `host` finding in either file
- [ ] `--history` finds a secret present only in a file deleted in a later commit, and reports the **oldest** commit from `git log --all --reverse --format=%H --find-object=<blob>` as the introducing commit
- [ ] `--history` checks commit messages and author/committer names and emails against the denylist
- [ ] Denylist terms never appear in stdout, `--json` or exception text; they appear only as `<denylist:N>`
- [ ] With no denylist, the summary line includes `denylist: skipped (no denylist)`
- [ ] Blobs with a NUL byte in the first 8 KiB are checked by path only
- [ ] No real organisation names anywhere in the script or tests (synthetic `acme-widgets`, `globex-internal`)
## Tests
`tests/test_audit.py` builds temp git repos (pattern from `tests/test_e2e.py`) covering: each check id firing; severities and exit codes; the history-only secret and its oldest introducing commit; a denylist hit in a commit message; `.audit-allow` downgrade; the redaction guarantee (the term is absent from captured stdout and JSON); the version-string and `~/.local` negatives; and a clean repo exiting 0.
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none
## Implementation notes (round 1)
- Added `scripts/audit_public.py`, `.audit-allow` (header comments only), `.audit-denylist` in `.gitignore`, and `tests/test_audit.py` (17 tests; full suite passes).
- API is as specified. `Finding` has exactly the five spec fields. The allow-list "allowed" flag lives in the CLI layer: the table prints `allowed` in the severity column, and `--json` adds `"allowed": true|false` to each finding.
- `load_denylist` returns a `list[str]` subclass (`Denylist`) that also records each term's 1-based file line number, so `<denylist:N>` is the real line number even when the file has comments or blank lines. For a plain `list[str]`, N is the 1-based index.
- `scan_text` also accepts the check id `path`, which the CLI uses. The default `checks` tuple matches the spec.
- Redaction: `where` and `excerpt` are redacted inside `scan_text` and again before output. Error and exception text is redacted. `redact()` also replaces substring hits, so a term embedded in a longer word never prints.
- Secret token bodies are masked in excerpts (the first 4 chars followed by `…[masked]`), so the audit output does not reprint secrets.
- An explicit `--denylist`/`--allow` path that does not exist is a usage error (exit 2). The env var path and `.audit-denylist` fall through as the spec says. A non-repo `--root` is also exit 2.
- `artifact` applies to tracked paths in the tree, and to every blob path in history. `transcript` (`.gitmotive/` path) applies to tracked and untracked-unignored files.
- Hostname rule: no match when the hostname is followed by `.<alnum>`, so `settings.local.json` and `.env.local` do not match.
- On this repo, `--tree` exits 0 with no findings. `--history` exits 1 with 6 medium `artifact` findings from the formerly tracked `build/lib/`, which is input for task 04.
## Implementation notes (round 2)
- [major] History path checks now run once per distinct historical path. The data comes from `git log --all --reverse -m --raw --no-abbrev --no-renames -z`, which yields (commit, path, blob) for every add or modify. Each path is reported with the oldest commit that added or changed it. Content checks still run once per distinct blob, using the oldest introducing commit from `--find-object`. Submodule entries are skipped. On this repo, `--history` now reports all 15 `build/`/`dist/` paths (round 1 found 6). New test `test_history_reports_every_path_of_a_shared_blob` covers `src/x.py`, an identical `build/lib/x.py` (artifact), and an identical `.gitmotive/x.py` (transcript).
- [major] + [minor] `_excerpt` now masks and redacts the full line first, then windows the scrubbed string. A window edge can only cut a `<denylist:N>` or `…[masked]` placeholder. New tests: `test_excerpt_window_never_cuts_a_denylist_term` (the reviewer's repro plus a far-edge case) and `test_excerpt_window_never_cuts_a_secret`.
- [minor] The hostname rule no longer matches when the name is followed by `(` (e.g. `threading.local()`). Bare attribute access such as `obj.internal_attr` still matches; use `.audit-allow` for those. Test: `test_hostname_rule_ignores_python_call`.
- [minor] The `.audit-allow` header now documents that globs match the redacted path, so a path containing a denylist term cannot be allowed.
- [minor] `import threading` moved to the module imports.
- Note: `--tree` on this repo now reports one medium `host` finding, in the untracked `.hq/reviews/02.md`. It comes from the review text's own `obj.internal_attr` example. The script and tests still have no `secret`/`host` findings (self-match test passes). The full test suite passes.
