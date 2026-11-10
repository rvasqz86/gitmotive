Status: DRAFT — do not post without review

# LinkedIn draft

## Post

When an AI agent writes code for me, the prompt and its reasoning disappear when the session ends. A few weeks later I'm looking at a line, git blame says I committed it, and I can't say why it's there.

So I built gitmotive. It hooks into Claude Code and Cursor, records each prompt and edit to a local file, and links them to the commits they landed in. Then `git motive src/fetch.py:42` shows the prompt, the agent's reasoning and the model behind that line, plus the other files changed for the same request.

A few things I cared about:
- It's deterministic. Matching uses git blame and a fixed score, with no LLM in the loop.
- It stays local: no network calls, no telemetry, and the event log is excluded from git.
- When it didn't see an edit, it says "none recorded" instead of guessing.

It has limits. It only records edits made after you install it, reasoning is captured on Claude Code only, and Copilot CLI and oh-my-pi support is still experimental.

It's open source (MIT). Try it at https://gitmotive.tech, where a live demo browses gitmotive's own history.
