# Task 24: Reliable model capture from Claude Code transcripts
Status: done
Type: fix
Scope: capture
Depends on: 06
## Goal
Dogfood evidence: since the task-06 reinstall, only 2 of 19 Claude `edit` events have a non-null `model`. Both events come from the same sessions as events that recorded none (store `~/.gitmotive/repos/0663563df78ac40a/events.jsonl`; read it, and never copy prompt text from it into committed files). Strangers using Claude Code would see "model unknown" for most lines, and the live demo can't show the model, which the brief requires. Find the root cause and fix it in `capture._transcript_context`.
Candidate causes to check: the transcript isn't flushed yet when PostToolUse fires; the assistant record holding the `tool_use` isn't the one carrying `message.model`; streaming or partial records; matching by `tool_use_id`.
Use a fallback chain: the exact tool_use record's model, else the most recent assistant record in the transcript that has `message.model`, else the payload `model`, else None. Reasoning capture must not regress.
## Files
- gitmotive/capture.py (modify)
- tests/test_capture_model.py (modify: add a regression test built from a synthetic transcript reproducing the real failure shape; no real prompt text)
## Acceptance criteria
- [ ] The root cause is stated in the implementation notes, with evidence from the real transcript structure (field names and record shapes only, no content)
- [ ] For a transcript shaped like the failing real ones, `_transcript_context` returns the model
- [ ] Existing reasoning and model tests pass, and payload `model` still wins
- [ ] No new dependencies or network calls
## Tests
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none

## Implementation notes (round 1)
**Root cause: transcript write ordering. Claude Code writes the current turn's assistant records to disk only when it writes the first `tool_result`, and that happens after PostToolUse fires for the first tool of the turn.** So for the first Edit/Write in a turn, `_transcript_context` never finds the `tool_use_id` and returns `model=None` (reasoning falls back to the last text in the file). For later tools in the same parallel batch, the hook fires after that write, so the lookup succeeds. That is why every null-model event in the store is the first of a burst, and the events ~0.2s after it in the same session have the model.

Evidence (field names and record shapes only, from session `70e146a6…` in the store and its transcript):
- Assistant records are one content block per record (`thinking`, `text` or one `tool_use`). They share `message.id` and each carries `message.model`, plus top-level `requestId` and `apiBlockIndex`.
- Each turn also gets one `type: "api-request-blob"` record whose `message` has only `role: "assistant"` and `content` (all blocks batched, **no `model`**). It is written after all of the turn's `tool_result` records.
- Timing: line 117 (`file-history-delta`, ts …338.637) is written before lines 119–125 (the turn's assistant records, internal ts …321–338.58). The first edit hook ran at …338.745 and the first `tool_result` was written at …338.979. So the batch reached disk after line 117's write, around the time of the first tool_result, i.e. after the first hook.
- Live check in this session: during a running tool call, the transcript did not yet contain that call's own `tool_use` record; its last records belonged to the previous call.
- Ruled out: `tool_use_id` mismatch (ids match once the records are written), streaming or partial records (no partial JSON lines), and per-block records lacking a model (they all have one).

Fix (`capture._transcript_context`): track the most recent assistant `message.model` while walking the file. When the matching record has a model, return that model. When the match has none (e.g. found only in an `api-request-blob`), or the tool_use isn't on disk yet, return the most recent model. `handle()` is unchanged, so a payload `model` still wins, and None still comes back when there is no model anywhere. Reasoning logic is untouched.

Check against the real transcript: cut at the hook-time point (no `nUGA4s` tool_use present), it now returns `claude-opus-5-5`.

Tests: one assertion in `test_claude_model_from_transcript_and_payload_wins` changed on purpose. With no matching tool_use it now expects the transcript's latest model, as the new fallback chain requires; a new case covers "no model anywhere → None". Two tests were added: `test_model_when_current_tool_use_not_flushed`, which uses a synthetic transcript of the real failure shape, and `test_model_when_matched_record_has_no_model`, where the tool_use exists only in a model-less blob. The full suite passes.

Caveat: the fallback model belongs to an earlier record in the same session. That is right unless the user switched models with `/model` mid-session; then the first edit after the switch is attributed to the previous model.
