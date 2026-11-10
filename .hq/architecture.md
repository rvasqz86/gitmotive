DRAFT — confirm at Gate 1

# gitmotive architecture baseline

Derived from README.md, pyproject.toml, install.sh and the code (there is no CLAUDE.md, AGENTS.md or docs/).

## Components and boundaries
- `gitmotive/adapters.py`: normalizes each agent's hook payload (claude, cursor, copilot; omp rides the claude shape) into one canonical dict. This is the **only** place that knows about agent-specific field names.
- `gitmotive/capture.py`: the hook entrypoint (`gitmotive capture`). It reads the payload on stdin, normalizes it through adapters, adds the reasoning text from `transcript_path` (best-effort) and appends an Event.
- `gitmotive/store.py`: the `Event` dataclass plus the append-only JSONL store at `<repo>/.gitmotive/events.jsonl`, or `~/.gitmotive/repos/<hash>/` in user scope. `repo_root()` and `user_home()` live here.
- `gitmotive/resolve.py`: maps a line to events. It runs `git blame -p -w -C -C` and scores candidate edits (same commit +100, line text in edit +50, both uncommitted +10).
- `gitmotive/hq.py`: display-time dereferencing of orchestrator prompts (`.hq/tasks`, reviews, brief).
- `gitmotive/cli.py`: subcommands `why` (also `git motive file:line`), `log`, `stamp`, `install` and `capture`. Installers are the `install_<agent>(root, cmd)` functions.
- `install.sh`: a self-contained venv installer (`~/.gitmotive/venv`) with wrappers in `~/.local/bin`.
- `tests/`: plain-script tests (`python3 tests/test_x.py`), using functions named `test_*` and an `if __name__ == "__main__"` runner. pytest is not installed.

## Layering rules
- adapters ← capture ← store. resolve depends on store and git. cli depends on everything. Nothing imports cli.
- Agent specifics stay in adapters.py (payload shape) and in `install_<agent>` (config shape). Nothing else branches on agent.

## Conventions
- Pure stdlib with zero runtime dependencies (`dependencies = []`). Keep it that way. Dev-only tooling (build, twine) is acceptable.
- Python >= 3.10, `from __future__ import annotations`, and small functions with `cmd_<name>(args) -> int` returning an exit code.
- Provenance is deterministic: no LLM in the loop, no network, and the CLI says "none recorded" rather than guessing.
- Store files are append-only JSONL with one Event per line.
- Commands in docs and site must match the real CLI (`gitmotive install`, `git motive f:l` / `gitmotive why`, `log`, `stamp`). Don't invent `init` or `blame` unless a task adds them deliberately.

## Never
- Never add a runtime dependency, a network call, or telemetry to the CLI.
- Never commit captured prompts or transcripts from non-personal projects, or any client/employer name (denylist in the gitignored `.hq/brief-source.md`).
- Never push, force-push, rewrite published history, publish to PyPI, change repo visibility, or touch DNS without explicit human OK.
- Never let the site (`/site`) depend on a backend. The demo is static JSON plus client-side JS.
- `build/` artifacts must not be tracked. Note that `build/lib/` is currently tracked, which is a cleanup item.
