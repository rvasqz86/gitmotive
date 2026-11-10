# Task 06: Record agent and model on events; --source labels; upserting installers
Status: todo
Type: feat
Scope: capture
Depends on: 01
## Goal
Add optional `agent` and `model` to `store.Event` and fill them during capture (spec "Capture: agent and model"). `agent` is the producing product, so the copilot and omp installers write `--source copilot` and `--source omp`. Installers upsert an existing gitmotive hook entry, so re-running `install` refreshes commands.
## Files
- gitmotive/store.py (modify: `agent` and `model` fields; `FIELD_DOCS` with one entry per field)
- gitmotive/adapters.py (modify: `normalize(..., source=None)` returns `agent` (`source` or the resolved agent) and `model` (payload `model` or None))
- gitmotive/capture.py (modify: parse `--source`; add `_transcript_context(transcript_path, tool_use_id) -> (reasoning, model)`, keeping `_preceding_assistant_text` as a wrapper; set `agent` and `model` on prompt and edit events, with payload `model` winning over the transcript)
- gitmotive/cli.py (modify: `install_copilot`/`install_omp` append `--source copilot`/`--source omp`; `_claude_style`, `install_cursor` and `install_copilot` replace the command of an existing entry containing `gitmotive capture` instead of skipping; `why` appends `  via {agent}` and `  model {model}` when known)
- tests/test_capture_model.py (create)
- tests/test_adapters.py (modify: `agent` key per shape, plus `source` override)
## Acceptance criteria
- [ ] JSONL lines without `agent`/`model` load with both None
- [ ] A Claude PostToolUse payload plus a transcript whose matching assistant record has `"model": "claude-opus-5-5"` gives an edit event with `agent == "claude"` and `model == "claude-opus-5-5"`; a payload-level `model` wins
- [ ] A Cursor payload with `model` sets it; without one, it is None
- [ ] For each installer, the agent stored when the written command is run with a Claude-shaped (or Cursor-shaped) payload is `claude`, `cursor`, `copilot` or `omp` respectively (tested by running the written command string through `sh -c` with HOME set to a temp dir)
- [ ] Running `install --agent omp` against a config that holds an old `... gitmotive capture --agent claude` entry leaves exactly one gitmotive entry per event, with `--source omp`; running install twice is idempotent (file bytes equal)
- [ ] `why` for an event with agent and model contains `via claude  model claude-opus-5-5`; for old events the line is unchanged
- [ ] `FIELD_DOCS.keys() == {f.name for f in dataclasses.fields(Event)}`
- [ ] Agent-specific branching stays in adapters.py and the `install_<agent>` functions only
## Tests
`tests/test_capture_model.py` as above, plus updates to `tests/test_adapters.py`. HOME is always a temp dir.
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none
