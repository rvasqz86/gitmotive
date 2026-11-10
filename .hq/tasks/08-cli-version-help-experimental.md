# Task 08: CLI --version, help, single-source USAGE, experimental labels
Status: done
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
## Implementation notes (round 1)
- `gitmotive/__init__.py` already had `__version__ = "0.1.0"`; no change needed.
- `cli.py`: removed the literal module docstring; `USAGE` (cmd -> (usage line, description)) now builds `__doc__` via `_usage_entry(cmd)` (descriptions wrapped at 56 cols, `break_on_hyphens=False`). Keys in order: why log stamp install capture help.
- `EXPERIMENTAL = ("copilot", "omp")` and `EXPERIMENTAL_NOTE`; `cmd_install` prints one note per distinct experimental agent (deduped), after validation and before writing configs, in both scopes.
- `main`: `--version`/`-V` -> `gitmotive 0.1.0`, exit 0; `help`/`-h`/`--help` -> `cmd_help(rest)`: no arg prints `__doc__`, `help <cmd>` prints only that entry, unknown cmd -> stderr message, exit 2. Bare `gitmotive` and unknown commands still print help and exit 2. `file:line` dispatch untouched.
- Docstring marks `copilot (experimental), omp (experimental)` in the install entry and documents `capture [--agent A] [--event E] [--source S]`.
- Tests: `tests/test_cli_meta.py` (11 tests; dispatch coverage parsed from `inspect.getsource(cli.main)`). Full test command passes.
## Implementation notes (round 2)
- [major] `main`: if the command is a `USAGE` key and `-h`/`--help` appears anywhere in its args, print `cmd_help([cmd])` (that command's entry) and exit 0 without running it. Checked before the `help` dispatch, so `help --help` prints help's entry. `file:line` dispatch untouched.
- [minor] `HELP_WIDTH = 80` constant (plus `_HELP_INDENT = 34`); descriptions wrap at `HELP_WIDTH - _HELP_INDENT`. Longest docstring line is now 79 cols.
- Tests added: `test_subcommand_help_flag_prints_entry_and_runs_nothing` (every USAGE cmd × `-h`/`--help`, flag alone and after other args; asserts exit 0, output == that entry, and no file in temp repo or HOME created/modified), `test_install_help_writes_no_hooks` (repo and user scope, `--agent all`: no files written, no notes), `test_help_fits_80_columns`. Verified the new tests fail with the routing disabled. Full test command passes.
- Not done (reviewer minors not requested by manager): dispatch-table refactor for the coverage test.
