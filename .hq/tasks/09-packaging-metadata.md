# Task 09: PyPI-ready packaging metadata and dist dry run
Status: todo
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
