# Task 16: One-line installer served at gitmotive.tech/install.sh
Status: done
Type: feat
Scope: site
Depends on: 09, 11
## Goal
Add `site/install.sh` for `curl -fsSL https://gitmotive.tech/install.sh | sh` (spec "Site installer"). It uses pipx when available, otherwise a venv at `~/.gitmotive/venv` with wrappers written **in venv mode only**, and it passes args through to `gitmotive install`. The repo-root `install.sh` stays as it is.
## Files
- site/install.sh (create)
- tests/test_site_install.py (create)
## Acceptance criteria
- [ ] POSIX sh: `sh -n` passes, no bashisms, `set -eu`, everything inside `main`, which is called on the last line
- [ ] Checks for Python ≥ 3.10, with a clear error
- [ ] Installs `${GITMOTIVE_PIP_SPEC:-gitmotive}`:
  - with pipx: runs `pipx install` and writes no wrappers
  - without pipx: runs `python3 -m venv`, then `pip install`, then writes the `gitmotive` and `git-motive` wrappers to `$BIN`
- [ ] Honours `GITMOTIVE_HOME`, `GITMOTIVE_BIN` and `PYTHON`
- [ ] Prints the PATH hint when needed and the next step `gitmotive install --agent claude`. With args, runs `gitmotive install "$@"`
- [ ] No network calls other than pip or pipx, and no telemetry
## Tests
`tests/test_site_install.py`:
- `sh -n site/install.sh`
- when `_wheel.build_wheel()` returns a wheel: run the installer with `HOME=<tmp>`, a PATH without pipx, `GITMOTIVE_PIP_SPEC=<wheel>` and `PIP_NO_INDEX=1`, then assert that `<tmp>/.local/bin/gitmotive --version` prints `gitmotive 0.1.0`
- otherwise print `skip install run`
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none

## Implementation notes (round 1)
- `site/install.sh`: POSIX sh, `set -eu`, helpers + `main`, called with `main "$@"` on the last line, so a truncated `curl | sh` download runs nothing. Env vars: `GITMOTIVE_PIP_SPEC` (default `gitmotive`), `GITMOTIVE_HOME` (default `~/.gitmotive`), `GITMOTIVE_BIN` (default `~/.local/bin`), `PYTHON` (default `python3`).
- Python check: `$PY` missing → error; version < 3.10 → `needs Python 3.10 or newer; '<py>' is X.Y.Z`. Errors go to stderr with exit 1.
- pipx mode: `pipx install --force --python "$PY" "$SPEC"`. `--force` makes a rerun an upgrade; `--python` honours PYTHON. Writes no wrappers and no venv. Finds the bin dir from `$PIPX_BIN_DIR`, then `pipx environment --value PIPX_BIN_DIR`, then `~/.local/bin`; that dir is used for the PATH hint and the arg pass-through. Pass-through runs pipx's entry point; it is not a `python -m`, and its sys.path[0] is the venv bin dir, not the cwd.
- venv mode: `"$PY" -m venv`, then `venv/bin/python -m pip install -q --upgrade "$SPEC"`. Wrappers `exec "<venv>/bin/python" -I -m gitmotive "$@"` (task 10 lesson). Clear errors if the venv can't be created or has no pip (Debian python3-venv hint). Arg pass-through goes through the wrapper, so it also uses `-I`.
- No args → prints `next: gitmotive install --agent claude`. With args → `gitmotive install "$@"`. PATH hint only when the bin dir isn't on PATH.
- Tests (`tests/test_site_install.py`): `sh -n` (and `dash -n` if present); structure check (shebang, `set -eu`, nothing at top level except function defs and the final `main "$@"`, no common bashisms); no curl/wget/URLs outside comments; old python → clear error, nothing written; fake-pipx mode → `pipx install … --python <py> <spec>`, no wrappers/venv, args passed through, PATH hint, `next:` line without args; wheel run per the task (HOME=tmp, PATH without pipx, PIP_NO_INDEX=1, cwd=checkout, asserts `-I` wrappers and `gitmotive --version` == `gitmotive 0.1.0`), else prints `skip install run`.
- This host has no `build`, so the wheel test prints `skip install run`. I ran the venv path by hand instead: `GITMOTIVE_PIP_SPEC=<checkout>`, HOME=scratch, PATH without pipx → `gitmotive 0.1.0`. A rerun with `--agent claude` from a temp repo wrote hooks as `<home>/.gitmotive/venv/bin/python -I -m gitmotive capture`.
- Test command (`.hq/runtime` test=): all pass.
