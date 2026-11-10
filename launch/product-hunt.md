Status: DRAFT — do not post without review

# Product Hunt draft

## Name

gitmotive

## Tagline

git blame for the prompt behind AI-written code

## Description

Point at a line and see the prompt, reasoning and model behind the AI edit that wrote it. Captured through agent hooks, stored locally, linked to commits by git blame. No LLM, no network calls. Claude Code and Cursor supported.

## First comment

Hi Product Hunt. I built gitmotive because I kept finding lines an agent wrote weeks earlier and had no record of what I had asked for.

`gitmotive install --agent claude` adds hooks to the agent. Every prompt and edit goes to a local JSONL file that git ignores. When you commit, the edits are stamped with the commit. `git motive file.py:42` runs git blame on the line and picks the recorded edit that best matches it: same commit, then line text, then recency.

What it is not: there is no model in the loop, nothing leaves your machine, and when no edit was recorded it prints "none recorded" rather than guessing.

Claude Code and Cursor are supported. GitHub Copilot CLI and oh-my-pi are experimental. Reasoning is captured on Claude Code only, and only edits made after install are recorded.

The live demo browses gitmotive's own development history: https://gitmotive.tech/demo/

Code (MIT): https://github.com/rvasqz86/gitmotive

Feedback on what's missing is very welcome.

## Gallery captions

1. `git motive src/fetch.py:42` shows the commit, prompt, reasoning and model behind one line.
2. `gitmotive log` lists each recorded prompt with the files it touched and the commits it landed in.
3. The live demo: browse gitmotive's own history, line by line, in the browser.

## Topics

- Developer Tools
- GitHub
- Open Source
- Artificial Intelligence
