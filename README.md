# gitwhy

`git blame` answers *who* and *when*. `gitwhy` answers *why*.

Every line an AI agent writes came from a prompt and a chain of reasoning. That context exists only at generation time and evaporates when the session ends. gitwhy captures it via Claude Code hooks and lets you query it later:

```
$ gitwhy why src/fetch.py:42
src/fetch.py:42
  |             time.sleep(2 ** attempt)
  commit   134d8dd9e6  raul  2026-10-29  add retry
  edited   2026-10-29 06:19  by Edit  session 3f9a2c1e  [same commit, line text in edit]
  prompt
    add retry with exponential backoff to fetch()
  reasoning
    Wrapping the call in a retry loop; 3 attempts with backoff since the upstream
    flakes under load.
  also changed for same prompt
    src/http_errors.py
    tests/test_fetch.py
```

## Install (dogfood mode)

```sh
git clone <this repo> ~/src/gitwhy
cd ~/src/gitwhy && pip install -e .
cd ~/your/project
gitwhy install
```

`gitwhy install` does three things in the current repo:

1. Adds `UserPromptSubmit` and `PostToolUse` (Edit/Write/MultiEdit) hooks to `.claude/settings.json`
2. Adds a git `post-commit` hook that runs `gitwhy stamp`
3. Excludes `.gitwhy/` from git via `.git/info/exclude`

Then use Claude Code normally.

## Commands

| command | what |
|---|---|
| `gitwhy why <file>:<line>` | prompt + reasoning + sibling files for that line. `--all` lists older candidates |
| `gitwhy log [file]` | every recorded prompt, with files it touched and commits it landed in |
| `gitwhy stamp` | tag uncommitted edit events with `HEAD` (post-commit hook runs this) |
| `gitwhy install` | wire hooks in the current repo |

## How it links

- Hooks append to `.gitwhy/events.jsonl`. Append-only, so concurrent hook runs never corrupt it.
- Each `edit` event links to the latest `prompt` event in the same session, and captures the assistant text block that preceded the tool call (read from `transcript_path`, best-effort).
- `stamp` matches unstamped edits to `HEAD` by file + time.
- `why` runs `git blame -p -w -C -C` on the line, then scores edit events: same commit (+100), line text appears in the edit's new content (+50), both uncommitted (+10). Top score wins; ties go to most recent.

Deterministic provenance, no LLM in the loop. If the hook did not see the edit, `why` says "none recorded" rather than guessing.

## Known gaps (v0.1)

- Claude Code only. Copilot CLI, Cursor, Codex need adapters.
- Events are local to the clone. Next step: publish per-commit intent to `git notes` so provenance travels with the repo.
- Edits by hand after the agent are not recorded; `why` will still return the agent's intent for the parent line via blame `-C`, which is usually what you want.
- `transcript_path` format is undocumented. Reasoning capture degrades to "last assistant text" if the structure changes; prompt linkage does not depend on it.
- Line matching uses exact stripped-text equality. Reformatting (black, prettier) after the edit breaks the +50 signal; the commit signal still holds.
