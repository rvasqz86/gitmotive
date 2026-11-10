# Task 16: One-line installer served at gitmotive.tech/install.sh
Status: todo
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
