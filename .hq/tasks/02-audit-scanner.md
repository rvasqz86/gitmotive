# Task 02: Public-release audit scanner (tree + full history)
Status: todo
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
