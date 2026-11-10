# Task 10: Fresh-machine smoke test (Docker or clean venv)
Status: done
Type: test
Scope: packaging
Depends on: 09
## Goal
Prove a stranger's path works using the real CLI (spec Open question 1: the brief's "init" is `gitmotive install`, its "blame" is `git motive <file>:<line>`): install from a locally built wheel, install hooks in a sample repo, simulate an AI-attributed edit through the installed Claude hook command, commit, and query.
## Files
- scripts/smoke_fresh.sh (create)
- scripts/smoke_inner.sh (create)
- tests/test_smoke.py (create)
## Acceptance criteria
- [ ] `--docker`: builds the wheel on the host, then runs `python:3.12-slim` with the wheel mounted read-only; installs git and pipx in the container; runs `pipx install /dist/gitmotive-*.whl`; runs `smoke_inner.sh`
- [ ] `--venv`: a new venv under `$TMPDIR` with `HOME` set to a temp dir; `pip install --no-index <wheel>` (no network)
- [ ] With no flag, `--docker` is chosen if `docker info` succeeds, otherwise `--venv`. `--docker` without Docker exits 2 with a message
- [ ] `smoke_inner.sh`, in order:
  1. `gitmotive --version`
  2. `git init` a sample repo and make the first commit
  3. `gitmotive install --agent claude`
  4. read the UserPromptSubmit and PostToolUse commands from `.claude/settings.json`
  5. pipe a prompt payload into the first, apply the edit, and pipe an edit payload (with a transcript containing reasoning and `"model": "claude-opus-5-5"`) into the second
  6. `git commit`
  7. **before any `why`/`log`**, assert that `.gitmotive/events.jsonl` has an edit with a non-null `commit` equal to `git rev-parse HEAD` (proving the post-commit hook ran)
  8. `git motive <file>:<line>` and grep for the prompt text, the reasoning text and `model claude-opus-5-5`
  9. `gitmotive log` shows the prompt
  10. print `SMOKE OK`
  Any miss exits non-zero
- [ ] The `--docker` run output is pasted into the report
## Tests
`tests/test_smoke.py` runs `sh scripts/smoke_fresh.sh --venv` when `_wheel.build_wheel()` returns a wheel (passing its path through `GITMOTIVE_WHEEL`), and asserts `SMOKE OK`. Otherwise it prints `skip smoke`.
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`, plus `sh scripts/smoke_fresh.sh --docker` (manual, recorded)
## Spec issue
Resolved: hook command strings changed from `PYTHONPATH=<pkg> <python> -m gitmotive …` to `<run>` (installed: `<python> -I -m gitmotive`; source tree: `PYTHONPATH=<pkg> <python> -m gitmotive`). The manager amended spec.md (Hook command strings, `<run>` form) during task 10; the code follows it.

## Added by manager (found during dogfood reinstall)
- [ ] Bug: running `sh install.sh --agent ...` with cwd = the source checkout bakes `PYTHONPATH=<checkout>` into hook commands (because `python -m gitmotive` imports from cwd), so hooks run working-tree code instead of the venv. Fix in `install.sh` (run the post-install `gitmotive install` from a neutral cwd, e.g. `cd "$HOME"`, or `-I`/`-P` isolation) and/or in the HOOK_CMD derivation; the smoke test asserts hook commands reference the install venv, never the source dir, when install.sh is run from inside the checkout.

## Implementation notes (round 1)
- `scripts/smoke_fresh.sh`: `--docker` | `--venv` | auto (`docker info` → docker, else venv); `--docker` without a working daemon exits 2 with a message. Wheel = `$GITMOTIVE_WHEEL` or built on the host from a neutral cwd (`python -m build` if present, else a throwaway build venv). Docker: `python:3.12-slim`, wheel dir at `/dist:ro`, checkout at `/src:ro`, apt `git`, `pip install pipx`, `pipx install /dist/gitmotive-*.whl`, then `smoke_inner.sh`. Venv: new venv under a `$TMPDIR` work dir, temp `HOME`, `pip install --no-index <wheel>`, GITMOTIVE_*/PYTHONPATH unset.
- `scripts/smoke_inner.sh`: steps 1–10 in order as specified (step 7 checks `.gitmotive/events.jsonl` edit `commit == git rev-parse HEAD` before any why/log; step 8 is `git motive fetch.py:6`, grepping prompt, reasoning and `model claude-opus-5-5`). Step 9b (when `SMOKE_SRC`+`SMOKE_WHEEL` are set, which both modes do): runs `install.sh --agent claude --scope user` with cwd = the checkout, temp HOME, `GITMOTIVE_PKG=<wheel>`, `PIP_NO_INDEX=1`; asserts both hook commands contain `<install home>/.gitmotive/venv/` and never the checkout path. User scope so nothing is written into the checkout (read-only mount in docker).
- install.sh bug fix (manager item): root cause is `python -m gitmotive` putting cwd first on sys.path, so `pkg_dir` resolved to the checkout. Fixes:
  - `install.sh`: post-install `gitmotive install` and the `~/.local/bin` wrappers now run `"$VENV/bin/python" -I -m gitmotive` (isolated: no cwd, no PYTHONPATH; venv site-packages and the `.pth` fallback still work). New `GITMOTIVE_PKG` env (default: the checkout) to install a given wheel/dir — needed for an offline smoke; documented in the header.
  - `gitmotive/cli.py` HOOK_CMD derivation: replaced `HOOK_CMD` + `PYTHONPATH={pkg_dir}` with `_python_cmd()`: when the package lives in this interpreter's site-packages (wheel/pipx/install.sh venv) hooks and the post-commit stamp line are `<python> -I -m gitmotive ...` with no PYTHONPATH, so a hook fired with cwd inside a source checkout can't import the working tree either. Running from a source tree (tests, `.pth` fallback) keeps the `PYTHONPATH=<src> <python> -m gitmotive` form. Upsert matching (`gitmotive capture` / `gitmotive stamp` substrings) unchanged.
  - Regression proof: with `-I` removed from install.sh and the old cli.py, `smoke_fresh.sh --venv` fails at 9b: `UserPromptSubmit hook references the source checkout: GITMOTIVE_STORE=user PYTHONPATH=/home/ubuntu/development/gitmotive .../ihome/.gitmotive/venv/bin/python -m gitmotive capture`.
- `tests/_wheel.py` (outside Files list, one-line fix): `python -m build` now runs with `cwd=<out dir>`; from the repo root the ignored `build/` directory shadowed the `build` module, so `build_wheel()` always returned None there.
- `tests/test_smoke.py`: `test_smoke_fresh_venv` (skip smoke when no wheel) and `test_docker_flag_without_docker_exits_2` (fake failing `docker` on PATH). Host python has no `build`, so the suite prints `skip smoke`; I verified the non-skip path with a venv python that has `build`: `ok test_smoke_fresh_venv`, `ok test_docker_flag_without_docker_exits_2`, and `test_packaging` `test_wheel_contents` also ran.
- Test command (`.hq/runtime` test=): all pass. `sh scripts/smoke_fresh.sh --venv`: SMOKE OK. `sh scripts/smoke_fresh.sh --docker`: exit 0, SMOKE OK (output below; image-pull and build-backend lines trimmed).

### `--docker` run output
```
== building wheel on the host
== wheel: gitmotive-0.1.0-py3-none-any.whl  mode: docker
== container: Python 3.12.16
creating virtual environment...
creating shared libraries...
upgrading shared libraries...
installing gitmotive from spec '/dist/gitmotive-0.1.0-py3-none-any.whl'...
⚠️  Note: '/root/.local/bin' is not on your PATH environment variable. These
    apps will not be globally accessible until your PATH is updated. Run `pipx
    ensurepath` to automatically add it, or manually modify your PATH in your
    shell's config file (e.g. ~/.bashrc).
done! ✨ 🌟 ✨
  installed package gitmotive 0.1.0, installed using Python 3.12.16
  These apps are now available
    - git-motive
    - gitmotive
== 1. gitmotive --version
gitmotive 0.1.0
== 2. git init sample repo + first commit
== 3. gitmotive install --agent claude
wrote /tmp/gitmotive-smoke.crKQXz/repo/.claude/settings.json
wrote /tmp/gitmotive-smoke.crKQXz/repo/.git/hooks/post-commit
excluded .gitmotive/ from git
== 4. read hook commands from .claude/settings.json
UserPromptSubmit: /root/.local/share/pipx/venvs/gitmotive/bin/python -I -m gitmotive capture
PostToolUse:      /root/.local/share/pipx/venvs/gitmotive/bin/python -I -m gitmotive capture
== 5. prompt payload -> hook, apply edit, edit payload (+ transcript) -> hook
== 6. git commit
== 7. post-commit hook stamped the edit with HEAD (before any why/log)
edit commits: ['11df30abe5417fd255334f123d46f3a6ed828f29']
== 8. git motive fetch.py:6
fetch.py:6
  |             time.sleep(2 ** attempt)
  commit   11df30abe5  smoke  2026-11-10  add retry
  edited   2026-11-10 20:21  by Edit  session sess-smo  [same commit, line text in edit]  via claude  model claude-opus-5-5
  prompt
    add retry with exponential backoff to fetch
  reasoning
    Wrapping the call in a retry loop because the upstream flakes.
== 9. gitmotive log
2026-11-10 20:21  cbd9bda8689e  session sess-smo  1 edit(s)  11df30ab
    add retry with exponential backoff to fetch
      fetch.py
== 9b. install.sh run from inside the checkout bakes the install venv into hooks, not the checkout
installed: /tmp/gitmotive-smoke.crKQXz/ihome/bin/gitmotive  (venv: /tmp/gitmotive-smoke.crKQXz/ihome/.gitmotive/venv)
add to your shell rc:  export PATH="/tmp/gitmotive-smoke.crKQXz/ihome/bin:$PATH"
wrote /tmp/gitmotive-smoke.crKQXz/ihome/.claude/settings.json
events stored under ~/.gitmotive/repos/  (set GITMOTIVE_STORE=user in your shell so why/log read the same place)
stamping is lazy: why/log attach edits to commits on read, no git hook needed
UserPromptSubmit: GITMOTIVE_STORE=user /tmp/gitmotive-smoke.crKQXz/ihome/.gitmotive/venv/bin/python -I -m gitmotive capture
PostToolUse: GITMOTIVE_STORE=user /tmp/gitmotive-smoke.crKQXz/ihome/.gitmotive/venv/bin/python -I -m gitmotive capture
wrapper from checkout cwd: gitmotive 0.1.0
SMOKE OK
```

## Implementation notes (round 2)
- [major] post-commit not healed → `cmd_install` now upserts the stamp line: every existing line containing `gitmotive stamp` is dropped, other lines are kept, and one fresh `<run> stamp >/dev/null 2>&1 || true` line is appended (a hook file left empty gets a `#!/bin/sh` shebang). Idempotent. Test: `tests/test_capture_model.py::test_install_upserts_stale_post_commit_stamp_line` pre-seeds `post-commit` with `#!/bin/sh`, an unrelated line, and `PYTHONPATH=/stale … -m gitmotive stamp …`; asserts exactly one stamp line, no `/stale`, the line starts with `_python_cmd() + " stamp"`, the unrelated line is preserved, and a second install is byte-identical.
- [major] spec interface → the manager amended spec.md (`<run>` form, stamp-line upsert); `## Spec issue` updated to record it. The code matches: `_python_cmd()` gives both forms, and the stamp line uses the same `<run>`.
- [minor] `_python_cmd()` unit test → `test_python_cmd_installed_vs_source_tree` monkeypatches `sysconfig.get_paths` so purelib/platlib = the package's parent (asserts `<python> -I -m gitmotive`, no PYTHONPATH), then a nonexistent site dir (asserts `PYTHONPATH=<pkg> <python> -m gitmotive`). Runs in the default test command.
- [minor] smoke_inner.sh 9b false positive → the check now matches `PYTHONPATH=$SMOKE_SRC` instead of any substring containing the checkout path.
- [minor] tests/_wheel.py → no change (as the review says).
- Test command (`.hq/runtime` test=): all pass (host has no `build`, so test_smoke prints `skip smoke`).
- `sh scripts/smoke_fresh.sh --docker` (round 2): exit 0, `SMOKE OK`. Output below; image-pull, apt and pip lines trimmed.

### `--docker` run output (round 2)
```
== wheel: gitmotive-0.1.0-py3-none-any.whl  mode: docker
== container: Python 3.12.16
creating virtual environment...
creating shared libraries...
upgrading shared libraries...
installing gitmotive from spec '/dist/gitmotive-0.1.0-py3-none-any.whl'...
⚠️  Note: '/root/.local/bin' is not on your PATH environment variable. These
    apps will not be globally accessible until your PATH is updated. Run `pipx
    ensurepath` to automatically add it, or manually modify your PATH in your
    shell's config file (e.g. ~/.bashrc).
done! ✨ 🌟 ✨
  installed package gitmotive 0.1.0, installed using Python 3.12.16
  These apps are now available
    - git-motive
    - gitmotive
== 1. gitmotive --version
gitmotive 0.1.0
== 2. git init sample repo + first commit
== 3. gitmotive install --agent claude
wrote /tmp/gitmotive-smoke.Hu7PMe/repo/.claude/settings.json
wrote /tmp/gitmotive-smoke.Hu7PMe/repo/.git/hooks/post-commit
excluded .gitmotive/ from git
== 4. read hook commands from .claude/settings.json
UserPromptSubmit: /root/.local/share/pipx/venvs/gitmotive/bin/python -I -m gitmotive capture
PostToolUse:      /root/.local/share/pipx/venvs/gitmotive/bin/python -I -m gitmotive capture
== 5. prompt payload -> hook, apply edit, edit payload (+ transcript) -> hook
== 6. git commit
== 7. post-commit hook stamped the edit with HEAD (before any why/log)
edit commits: ['4a6df1a5c18f2911a0288995541e768d3ea2e750']
== 8. git motive fetch.py:6
fetch.py:6
  |             time.sleep(2 ** attempt)
  commit   4a6df1a5c1  smoke  2026-11-10  add retry
  edited   2026-11-10 20:25  by Edit  session sess-smo  [same commit, line text in edit]  via claude  model claude-opus-5-5
  prompt
    add retry with exponential backoff to fetch
  reasoning
    Wrapping the call in a retry loop because the upstream flakes.
== 9. gitmotive log
2026-11-10 20:25  6381e42c0c35  session sess-smo  1 edit(s)  4a6df1a5
    add retry with exponential backoff to fetch
      fetch.py
== 9b. install.sh run from inside the checkout bakes the install venv into hooks, not the checkout
installed: /tmp/gitmotive-smoke.Hu7PMe/ihome/bin/gitmotive  (venv: /tmp/gitmotive-smoke.Hu7PMe/ihome/.gitmotive/venv)
add to your shell rc:  export PATH="/tmp/gitmotive-smoke.Hu7PMe/ihome/bin:$PATH"
wrote /tmp/gitmotive-smoke.Hu7PMe/ihome/.claude/settings.json
events stored under ~/.gitmotive/repos/  (set GITMOTIVE_STORE=user in your shell so why/log read the same place)
stamping is lazy: why/log attach edits to commits on read, no git hook needed
UserPromptSubmit: GITMOTIVE_STORE=user /tmp/gitmotive-smoke.Hu7PMe/ihome/.gitmotive/venv/bin/python -I -m gitmotive capture
PostToolUse: GITMOTIVE_STORE=user /tmp/gitmotive-smoke.Hu7PMe/ihome/.gitmotive/venv/bin/python -I -m gitmotive capture
wrapper from checkout cwd: gitmotive 0.1.0
SMOKE OK
```
