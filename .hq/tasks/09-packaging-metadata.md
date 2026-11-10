# Task 09: PyPI-ready packaging metadata and dist dry run
Status: done
Type: chore
Scope: packaging
Depends on: 08
## Goal
Make `pipx install gitmotive` work once published: complete the metadata (Homepage https://gitmotive.tech), pin the package list, require setuptools ≥ 77 for the SPDX license, and add a dry-run build plus `twine check` (spec "Packaging"). Do not publish.
## Files
- pyproject.toml (modify:
  - `[project.urls]` per spec
  - classifiers: Development Status :: 3 - Alpha, Environment :: Console, Intended Audience :: Developers, Operating System :: POSIX, Programming Language :: Python :: 3 :: Only, 3.10, 3.11, 3.12, 3.13, Topic :: Software Development :: Version Control :: Git. **No `License ::` classifier**
  - `dynamic = ["version"]` with `[tool.setuptools.dynamic] version = {attr = "gitmotive.__version__"}`
  - `[tool.setuptools] packages = ["gitmotive"]`
  - `[build-system] requires = ["setuptools>=77"]`)
- tests/_wheel.py (create: `build_wheel() -> Path | None`, an isolated `python -m build --wheel` into a cached temp dir; None on failure)
- scripts/check_dist.sh (create)
- tests/test_packaging.py (create)
## Acceptance criteria
- [ ] The `tomllib`-parsed pyproject has Homepage `https://gitmotive.tech`, `dependencies == []`, `packages == ["gitmotive"]`, both console scripts, `license == "MIT"`, and no classifier starting `License ::`
- [ ] `sh scripts/check_dist.sh` creates a throwaway venv in `$TMPDIR`, installs `build` and `twine` there only, builds the sdist and wheel to a temp dir, runs `twine check --strict`, prints the dist paths, and prints (without running) `python -m twine upload <dist paths>`
- [ ] When `build_wheel()` returns a wheel, its namelist is only `gitmotive/*.py` plus `*.dist-info/*`; otherwise the test prints `skip build`
- [ ] The PyPI name check is recorded in the report: `curl -s -o /dev/null -w '%{http_code}' https://pypi.org/pypi/gitmotive/json` with the date; 404 means the name is free; anything else is a Spec issue stop
- [ ] Nothing is uploaded; `~/.pypirc` is not created or read
## Tests
`tests/test_packaging.py` (metadata always; wheel contents via `_wheel.build_wheel`).
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`, plus `sh scripts/check_dist.sh` with its output recorded in the report
## Spec issue
none

## Implementation notes (round 1)
- `pyproject.toml`: `dynamic = ["version"]` from `gitmotive.__version__` (static `version` removed); classifiers as listed, no `License ::`; `[project.urls]` Homepage/Documentation/Repository/Issues per spec; `[tool.setuptools] packages = ["gitmotive"]`; `build-system.requires = ["setuptools>=77"]`.
- `tests/_wheel.py`: `build_wheel()` runs `sys.executable -m build --wheel` (isolated by default) into a `mkdtemp` dir, cached per process; returns None if `build` is missing, the run errors, or no wheel results.
- `tests/test_packaging.py`: metadata checks via `tomllib`; wheel namelist must be only top-level `gitmotive/*.py` plus `*.dist-info/*`, else prints `skip build`.
  - The system python3 has no `build` module, so the normal runner prints `skip build`. I also ran the test from a scratch venv that had `build` installed, and the wheel branch passed there.
- `scripts/check_dist.sh`: makes a venv under `$TMPDIR` (falls back to /tmp) and installs `build` + `twine` only inside it. It builds the sdist and wheel to `$WORK/dist` and runs `twine check --strict`. It then prints the dist paths and the `python -m twine upload …` line without running it. The venv is removed on exit and the dist dir is kept.
- PyPI name check, 2026-11-10: `curl -s -o /dev/null -w '%{http_code}' https://pypi.org/pypi/gitmotive/json` → `404` (name is free).
- Nothing uploaded. `~/.pypirc` does not exist and was neither created nor read.
- Full test command passes.
- `sh scripts/check_dist.sh` output (tail):
```
Successfully built gitmotive-0.1.0.tar.gz and gitmotive-0.1.0-py3-none-any.whl
Checking /tmp/gitmotive-dist.HinKhi/dist/gitmotive-0.1.0-py3-none-any.whl: PASSED
Checking /tmp/gitmotive-dist.HinKhi/dist/gitmotive-0.1.0.tar.gz: PASSED
dist files:
  /tmp/gitmotive-dist.HinKhi/dist/gitmotive-0.1.0-py3-none-any.whl
  /tmp/gitmotive-dist.HinKhi/dist/gitmotive-0.1.0.tar.gz
to publish (not run):
  python -m twine upload /tmp/gitmotive-dist.HinKhi/dist/gitmotive-0.1.0-py3-none-any.whl /tmp/gitmotive-dist.HinKhi/dist/gitmotive-0.1.0.tar.gz
```
