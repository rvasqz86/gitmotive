Status: DRAFT — do not post without review

# Show HN draft

## Title

Show HN: gitmotive – git blame for the prompt behind AI-written code

## Body

gitmotive records why an AI coding agent wrote a line. Point it at a line with `git motive src/fetch.py:42` and it prints the commit, the prompt that led to the edit, the agent's reasoning (Claude Code only), the model, and the other files changed for the same prompt.

How it works: `gitmotive install --agent claude` wires the agent's own hooks. Each prompt and file edit is appended to `.gitmotive/events.jsonl` in the repo, which is excluded from git. A post-commit hook stamps new edits with their commit. `why` runs `git blame -p -w -C -C` on the line and scores the recorded edits: same commit +100, line text in the edit +50, both uncommitted +10. The top score wins.

It is deterministic: no LLM, no API key, no network calls, no telemetry. If nothing was recorded for a line, it says "none recorded" instead of guessing.

Agents: Claude Code and Cursor are supported. GitHub Copilot CLI and oh-my-pi are experimental (prompts and edits only).

Limitations: only edits made after install are recorded; events stay in your local clone; hand edits are not captured; reformatting loses the line-text signal; on Claude Code the first edit of a turn can carry the previous message's reasoning.

Demo, browsing gitmotive's own history: https://gitmotive.tech/demo/
Site: https://gitmotive.tech
Repo (MIT): https://github.com/rvasqz86/gitmotive

I'd like feedback on the scoring, and on which agents to support next.
