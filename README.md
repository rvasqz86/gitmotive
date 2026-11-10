# gitmotive

`git blame` tells you **who**. `git motive` tells you **why**.

Every line an AI coding agent writes comes from a prompt and a chain of reasoning. That context exists only while the agent is working, and it is gone when the session ends. gitmotive records it through the agent's own hooks and links it to the lines and commits it produced, so months later you can point at a line and read the prompt, the reasoning and the other files changed for the same request. It runs locally, it is deterministic (no LLM in the loop, no API key), and when it did not see an edit it says "none recorded" rather than guessing.

<!-- GIF: docs/demo.gif -->

```sh
pipx install gitmotive
cd your-repo
gitmotive install --agent claude
# ask Claude Code for a change, let it edit a file
git commit -am "add retry with backoff"
git motive path/to/file.py:42
gitmotive log
```

## Install

With [pipx](https://pipx.pypa.io/):

```sh
pipx install gitmotive
```

Or with the one-line installer, which needs no system pip:

```sh
curl -fsSL https://gitmotive.tech/install.sh | sh
curl -fsSL https://gitmotive.tech/install.sh | sh -s -- --agent claude   # also wire hooks
```

Or from source:

```sh
git clone https://github.com/rvasqz86/gitmotive ~/src/gitmotive
sh ~/src/gitmotive/install.sh
```

`install.sh` creates a venv at `~/.gitmotive/venv`, installs the package into it, and puts `gitmotive` and `git-motive` wrappers in `~/.local/bin`. Pass agent args (`--agent claude --scope user`) to run the hook setup in the same step.

## Quickstart

1. From the root of a git repository, hook up your agent:

   ```sh
   gitmotive install --agent claude
   ```

   This writes the capture hooks to `.claude/settings.json`, adds a `post-commit` hook that runs `gitmotive stamp`, and adds `.gitmotive/` to `.git/info/exclude`, so nothing gitmotive records gets committed.

2. Use the agent as usual. Each prompt and each file edit is appended to `.gitmotive/events.jsonl`.

3. Commit. The `post-commit` hook stamps the new edits with the commit they landed in.

4. Ask a line why it exists:

   ```
   $ git motive src/fetch.py:42
   src/fetch.py:42
     |             time.sleep(2 ** attempt)
     commit   134d8dd9e6  dev  2026-10-29  add retry
     edited   2026-10-29 06:19  by Edit  session 3f9a2c1e  [same commit, line text in edit]  via claude  model claude-opus-5-5
     prompt
       add retry with exponential backoff to fetch()
     reasoning
       Wrapping the call in a retry loop; 3 attempts with backoff since the upstream
       flakes under load.
     also changed for same prompt
       src/http_errors.py
       tests/test_fetch.py
   ```

   `gitmotive why src/fetch.py:42` is the same command. When nothing was recorded for a line it prints `intent   (none recorded)` and exits 1.

5. List everything recorded, optionally for one file: `gitmotive log [file]`.

### Machines where you don't own the repo: `--scope user`

```sh
gitmotive install --agent claude --scope user
export GITMOTIVE_STORE=user   # add to your shell rc
```

This writes nothing into any repository. Hook configs go under your home directory (`~/.claude/settings.json`, `~/.cursor/hooks.json`, `~/.copilot/hooks/`, `~/.omp/agent/settings.json`) and events go to `~/.gitmotive/repos/<hash-of-repo-path>/`. There is no git hook; `why` and `log` attach edits to commits when you run them. `git status` stays clean.

## Supported agents

| Agent | Config written | Captures | Status |
|---|---|---|---|
| Claude Code | `.claude/settings.json` (`UserPromptSubmit`, `PostToolUse` on `Edit\|Write\|MultiEdit`) | prompt, edits, reasoning from the transcript, model from the payload or transcript | supported |
| Cursor | `.cursor/hooks.json` (`beforeSubmitPrompt`, `afterFileEdit`) | prompt, edits, model (when the payload sends one) | supported |
| GitHub Copilot CLI | `.github/hooks/gitmotive.json` | prompt, edits | experimental |
| oh-my-pi | `.omp/settings.json` via the [omp-hooks](https://github.com/ZeR020/omp-hooks) plugin | prompt, edits | experimental |

`gitmotive install --agent all` wires all four. Experimental means prompt and edits only, against a payload shape that is not fully documented; `install` prints a note when you pick one.

### Orchestrators (hq)

When an orchestrator such as [hq](https://github.com/rvasqz86/herdr-config) drives the agent, the prompt the hook sees is the orchestrator's ("Implement .hq/tasks/03-add-retry.md, round 2 …"). gitmotive recognises these prompts and, at display time, shows the task title and goal from `.hq/tasks/NN-*.md`, the review findings a later round fixed from `.hq/reviews/NN.md`, and the original brief from `.hq/brief.md`. Nothing extra is stored. Capture still has to be installed for each tool hq assigns to a role.

## Commands

| Command | What it does |
|---|---|
| `git motive <file>:<line>` | Why does this line exist (also `gitmotive why <file>:<line>`). `--all` lists older candidates |
| `gitmotive log [file]` | Prompts recorded, with the files they touched and the commits they landed in |
| `gitmotive stamp` | Tag uncommitted edit events with `HEAD` (the `post-commit` hook runs this) |
| `gitmotive install [--agent claude\|cursor\|copilot\|omp\|all] [--scope repo\|user]` | Wire the hooks. `repo`: in this repo. `user`: under `~/`, nothing written to the repo |
| `gitmotive capture [--agent A] [--event E] [--source S]` | Internal hook entrypoint; reads the payload on stdin |
| `gitmotive help [cmd] \| -h \| --help` | Show help, or one command's entry |
| `gitmotive --version` | Print the version (also `-V`) |

## How it links

- Hooks append to `.gitmotive/events.jsonl` (or the user-scope store). The file is append-only, so concurrent hook runs never corrupt it.
- Each `edit` event links to the latest `prompt` event in the same session. On Claude Code it also records the assistant text before the tool call and the model, read from the session transcript.
- `stamp` attaches each unstamped edit to the first later commit that introduced one of its lines.
- `why` runs `git blame -p -w -C -C` on the line, then scores edit events: same commit (+100), line text appears in the edit (+50), both uncommitted (+10). The top score wins; ties go to the most recent.

## Privacy

- Everything stays on your machine. The CLI makes no network calls and has no telemetry.
- Prompts are stored verbatim, and they can contain anything you typed, including other people's material. For work you don't own, use `--scope user` so nothing lands in the repo, and check the project's tooling policy first, as you would for any agent transcript.
- `.gitmotive/` is excluded from git by `install`, so events are never committed by accident.

## Known gaps

- **Claude Code: the first edit of a turn may carry the previous message's reasoning.** Claude Code writes a turn's assistant records to the transcript only after the hook for that turn's first edit has run. For that first edit gitmotive cannot see the current reasoning yet, so it falls back to the latest assistant text on disk, which belongs to the previous message. The model falls back the same way, so the first edit after a `/model` switch is attributed to the previous model. Later edits in the same turn are exact.
- Reasoning is captured on Claude Code only. Cursor, Copilot CLI and oh-my-pi expose it differently or not at all.
- Agents without hooks (e.g. Codex) are not supported.
- Events are local to the clone. Publishing intent to `git notes` so it travels with the repo is a possible next step.
- Hand edits after the agent are not recorded; blame `-C` still leads back to the agent's intent for the original line.
- The Claude Code transcript format is undocumented. If it changes, reasoning capture degrades; prompt linkage does not depend on it.
- Line matching uses exact stripped text, so reformatting after the edit (black, prettier) loses the +50 signal. The commit signal still holds.

## Live demo and docs

- Site: [https://gitmotive.tech](https://gitmotive.tech)
- Live demo, browsing gitmotive's own history: [https://gitmotive.tech/demo/](https://gitmotive.tech/demo/)
- Docs: [https://gitmotive.tech/docs/](https://gitmotive.tech/docs/)

## License

MIT
