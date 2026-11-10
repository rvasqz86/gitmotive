# Task 08: CLI --version, help, single-source USAGE, experimental labels
Status: todo
Type: feat
Scope: cli
Depends on: 07
## Goal
Add `--version` and `help`, make `USAGE` the single source of truth for the command list (the docs generator reuses it), and label Copilot and oh-my-pi as experimental.
## Files
- gitmotive/__init__.py (modify: `__version__ = "0.1.0"`)
- gitmotive/cli.py (modify: `USAGE` dict and the module docstring built from it; `EXPERIMENTAL`; `--version`/`-V`; `help [cmd]`/`-h`/`--help`; experimental notes in `cmd_install`)
- tests/test_cli_meta.py (create)
## Acceptance criteria
- [ ] `gitmotive --version` and `-V` print `gitmotive 0.1.0` and exit 0
- [ ] `help`, `-h` and `--help` print the docstring and exit 0; `help why` prints only why's entry; bare `gitmotive` prints help and exits 2 (unchanged)
- [ ] `USAGE` keys are exactly `why log stamp install capture help`; each appears in `cli.__doc__`; every command dispatched in `main` has an entry (tested)
- [ ] The docstring marks copilot and omp `(experimental)` and documents `capture --source`
- [ ] `install --agent copilot,claude` prints exactly one `note: copilot support is experimental …` line; `--agent all` prints the note for copilot and omp only
- [ ] The `git motive file:line` dispatch is unchanged
## Tests
`tests/test_cli_meta.py` (captured stdout, temp repo, temp HOME).
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none
