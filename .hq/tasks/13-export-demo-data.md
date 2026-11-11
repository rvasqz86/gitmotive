# Task 13: Demo data exporter with per-record sanitisation gate
Status: done
Type: feat
Scope: site
Depends on: 05, 06, 12
## Goal
Add `scripts/export_demo.py` per the spec's "Demo data": it exports HEAD only, aborts on dirty exported files, stamps in memory (`resolve.stamp(..., persist=False)`), emits only referenced prompts, sanitises the emitted fields, and runs the per-record gate followed by a whole-output rescan. Commit a first `site/demo/data.json`.
## Files
- tests/test_site.py (modify: pending rule = `<dir>/index.html` missing; update `test_internal_links_and_pending_dirs`)
- scripts/export_demo.py (create)
- site/demo/data.json (create: generated)
- tests/test_export_demo.py (create)
## Acceptance criteria
- [ ] The CLI is exactly `--root --file (repeatable) --out --max-prompt-chars --no-denylist` (no `--rev`). The default files are `gitmotive/cli.py gitmotive/adapters.py scripts/gen_docs.py site/demo/viewer-core.mjs`; files that don't exist yet are skipped with a stderr note
- [ ] Exits 2 when any exported file has uncommitted changes, when no denylist exists and `--no-denylist` is absent, or on a usage error
- [ ] Imports only `gitmotive.store`, `gitmotive.resolve`, `gitmotive.hq` and `audit_public`, never `gitmotive.cli`. Changes nothing under `gitmotive/`
- [ ] The store file is byte-identical before and after an export (tested)
- [ ] The output schema matches spec "Data changes". `prompts` keys are exactly the set of `match.prompt_id` values
- [ ] Sanitisation:
  - `$HOME` becomes `~`
  - path-like sessions become 8 characters
  - pasted-content bodies become `[pasted content omitted]`
  - text is truncated to `--max-prompt-chars`
- [ ] Per-record gate:
  - A prompt text, reasoning or hq field with a secret, host or denylist hit becomes `[omitted: <check>]`, and stderr gets `omitted N field(s): …`. The export still succeeds
  - A hit in source line `text` is fatal (exit 1, nothing written)
  - After serialising, the whole output is rescanned, and any surviving hit means exit 1 with nothing written
- [ ] Warns on stderr when the output is over 1.5 MB
- [ ] The committed `data.json` was produced with the real local denylist. `audit_public.py --tree --denylist .audit-denylist` and `tests/test_public_text.py` pass
## Tests
`tests/test_export_demo.py` uses a temp repo and a temp `GITMOTIVE_HOME` with synthetic events:
- a Claude edit with reasoning and a model
- an hq-style prompt
- a pasted-content prompt
- an unreferenced prompt containing `gitmotive blame`
- a referenced prompt containing `acme-widgets`, with that term in a temp denylist
- a referenced prompt with a concatenation-built secret

It asserts the schema, that the unreferenced prompt is absent, the omitted markers and stderr counts, that the term is absent from the output and the captured streams, the dirty-file abort, the source-line fatal path, and that the store bytes are unchanged.
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue (resolved by manager)
Resolved with option 1: `tests/test_site.py` is added to this task's Files. A site dir counts as pending while `<dir>/index.html` is missing (amends task 11's rule; local fix, no interface change).

### Original report
**Conflict with task 11's link rule.** `tests/test_site.py` (task 11 acceptance: "`/demo/` and `/docs/` count as pending only while their directories are missing", `PENDING_DIRS` check at `tests/test_site.py:223`) fails as soon as `site/demo/` exists without `index.html`. This task must create `site/demo/data.json`, but `site/demo/index.html` only arrives in task 14. So with this task's deliverable in place, `tests/test_site.py` fails (`site/index.html` and `site/404.html`: "internal link does not resolve: /demo/"), and the test command cannot pass. `test_site.py` is not in this task's Files, and changing it changes task 11's acceptance, so I stopped.

Proposed fix (pick one):
1. (Recommended) Amend task 11's rule to "pending while `<dir>/index.html` is missing": in `tests/test_site.py:223` check `(site / path.strip("/") / "index.html").exists()` instead of the directory, and update `test_internal_links_and_pending_dirs` (the `(site / "demo").mkdir()` step then expects `/demo/` to stay pending until `index.html` is written). Add `tests/test_site.py` to this task's Files.
2. Reorder so task 14 lands `site/demo/index.html` before the committed `data.json` (task 13 keeps the script and tests; the generated file moves to task 14 or later).

Everything else for this task is implemented and passing (see notes below); only this cross-task conflict blocks a green suite.

- [ ] Per-record gate and whole-output rescan also run the `path` check (medium) (spec review r2 minor)

## Implementation notes (round 1)
- `scripts/export_demo.py`: CLI exactly `--root --file(+) --out --max-prompt-chars --no-denylist`. Imports only `gitmotive.store/resolve/hq` and `audit_public`. The denylist comes from `audit_public.load_denylist(None, root)` (env `GITMOTIVE_AUDIT_DENYLIST` or `<root>/.audit-denylist`), since the CLI has no `--denylist`. `--no-denylist` only permits exporting when none is found; a found denylist is still used. A relative `--out` resolves against `--root`.
- Order per prose field: `$HOME`→`~`, pasted bodies dropped, gate, then truncate (gate before truncation so a cut can't leave a partial secret). The gate uses checks secret/host/denylist/path and counts high/medium only (own-home `path` is info and is already `~`). When a field has several checks, the marker uses priority secret > denylist > host > path.
- `session` is the basename stem's first 8 chars when path-like, else the first 8 chars (matches `why`'s `sess8`). `match.prompt_id` is null when the prompt event is missing, so `prompts` keys equal the non-null set exactly. `hq` = {kind, task, task_title, goal, round}, with `goal` from `HqRef.task_goal`. `commit` fields are 10 chars; `date` is the blame author date in UTC.
- All stderr goes through `audit_public.redact`, and unexpected exceptions are caught and redacted (exit 2).
- Real export: run with `GITMOTIVE_AUDIT_DENYLIST=.hq/audit-denylist` (3 terms). `gen_docs.py` and `viewer-core.mjs` don't exist yet, so they were skipped. Result: 2 files, **0 matched lines, 0 prompts**. That is real: the dogfood store (112 events) has no edit events on `gitmotive/cli.py` or `gitmotive/adapters.py` yet. Store sha256 unchanged. Re-export after tasks 14/15 (task 23 checks matches).
- `audit_public.py --tree --denylist .hq/audit-denylist`: high=0 medium=0 (info=1, pre-existing own-home path in task 10). `tests/test_public_text.py` passes. `tests/test_export_demo.py`: 7 pass. Every other test passes except `tests/test_site.py` (see Spec issue).
- Spec issue option 1 applied: in `tests/test_site.py` a `PENDING_DIRS` entry is pending while `<dir>/index.html` is missing (not the directory). `test_internal_links_and_pending_dirs` now creates `site/demo/` with a `data.json` and asserts `/demo/` stays pending, then writes `index.html` and asserts it resolves to that file. The full test command passes (all 14 files). `audit_public.py --tree --denylist .hq/audit-denylist`: high=0 medium=0.

## Implementation notes (round 2)
Fixed every finding in review round 1, except the one about task 24's file, which the manager said to ignore.
- [major] HEAD only: each `--file` is resolved with symlinks followed. If it lands outside `--root` (`..`, an absolute path, a symlink), the export exits 2 with `outside --root`. Missing files are still skipped with a note. An existing file that `git cat-file -e HEAD:<rel>` rejects (ignored or untracked) exits 2 with `not tracked at HEAD`. The dirty check still runs after these. Test: `test_rejects_files_not_in_head` covers an ignored `local.cfg`, `../outside.txt`, an absolute outside path and an untracked file.
- [major] Substring denylist: a new `scan()` = blocking `scan_text` findings, plus a `denylist` (high) finding whenever `audit_public.redact(text) != text` and no whole-word hit was found. Its excerpt is the redacted line. The per-record gate (`Gate.field`), the source-line check and the whole-output rescan all use it. Test: referenced prompt `pv` with `~/<TERM>_v2/api.py` → `[omitted: denylist]`. A `x<TERM>2` author in the rescan unit test is also caught.
- [minor] Raw rescan: `rescan(data, text)` scans the serialised text and also every string leaf (keys and values) of `data` raw. Test: `test_rescan_checks_string_leaves_raw` puts a quoted-assignment secret in `match.why`. It shows that the serialised-text scan misses it and `rescan` catches it, with `why` in `where`.
- [minor] Home: `tilde` also rewrites `/home/<getpass user>` and `/Users/<getpass user>`, not only `$HOME`. `blocking()` now treats every `path` finding as blocking, whatever its severity. Test: `test_home_override_still_rewrites_user_home` runs with `HOME=<tmp>/fakehome` and asserts the user's `/home/<user>/w.txt` becomes `~/w.txt`.
- [minor] Host check: referenced prompt `pi` names a private hostname (built by concatenation) → `[omitted: host]`. The stderr assertion is now `omitted 5 field(s): secret=1 denylist=2 host=1 path=1`.
- [minor] `tests/test_site.py`: `==site` → `== site`.
- Re-exported `site/demo/data.json` with `.hq/audit-denylist`. The diff vs round 1 is only `generated_at` (still 0 matched lines, 0 prompts). Store sha256 unchanged. `tests/test_export_demo.py`: 10 pass. The full test command passes.
- `audit_public.py --tree --denylist .hq/audit-denylist`: high=0 medium=1 info=1, exit 0. The medium is the reviewer's own text in `.hq/reviews/13.md:9` (the example an example private hostname hostname in the host finding). It is not in this task's files, and that file is not mine to edit. The manager may want to reword it before committing `.hq/reviews/13.md`.

## Implementation notes (round 3)
Fixed both code findings in review round 2. The hostname prose had already been reworded by the manager, and no example hostnames or IPs were added here.
- [major] Unmasked secret in the substring-denylist excerpt: `scan()` now builds that excerpt from `audit_public.redact(audit_public._mask_secrets(text), denylist)`, the same order that `audit_public._excerpt` uses. The source-line fatal report and the rescan-survivor report both go through `scan()`, so both are covered. Test: `test_substring_denylist_excerpt_masks_secrets` takes a line with a planted key and an `x<TERM>2` hit. It asserts that no finding's excerpt from `scan` or `rescan` contains the key (or its tail) or the term.
- [minor] skip-worktree / assume-unchanged: on top of `git status --porcelain`, each exported file's `git hash-object -- <rel>` is compared with `git rev-parse HEAD:<rel>`. Any mismatch exits 2 with "uncommitted changes" and lists the file. Test: `test_skip_worktree_and_assume_unchanged_edits_abort` covers both flags and first asserts that `git status` really is blank.
- `tests/test_export_demo.py`: 12 pass. The full test command passes. A re-export with `.hq/audit-denylist` matches the committed `site/demo/data.json` except for `generated_at`, so it was left unchanged. `audit_public.py --tree --denylist .hq/audit-denylist`: high=0 medium=0 info=2 (both are pre-existing own-home `path` infos in other files).
