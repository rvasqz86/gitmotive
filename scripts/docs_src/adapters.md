# Agent setup

`gitmotive install` writes hook entries into each agent's own config file. Pick agents with `--agent`, as a comma-separated list or `all`. The default is `claude`.

- Claude Code (`--agent claude`): supported.
- Cursor (`--agent cursor`): supported.
- GitHub Copilot CLI (`--agent copilot`): experimental.
- oh-my-pi (`--agent omp`): experimental, and needs the omp-hooks plugin (`omp install omp-hooks`).

Experimental agents record prompts and edits only, because their hook payloads are not fully documented yet. `gitmotive install` prints a note for each one.

## Repo scope and user scope

`--scope repo` is the default. Hook configs are written inside the repository, events go to `<repo>/.gitmotive/events.jsonl`, and a `post-commit` hook stamps edits with their commit.

`--scope user` writes nothing into any repository. Hook configs go under your home directory, the hook commands are prefixed with `GITMOTIVE_STORE=user`, and events go to `~/.gitmotive/repos/<hash>/events.jsonl`, one directory per repository. Set `GITMOTIVE_STORE=user` in your shell too, so `why` and `log` read the same store. There is no git hook in user scope: `why` and `log` attach edits to commits when they read them.

## Where the hooks go

- Claude Code: `.claude/settings.json` (user scope: `~/.claude/settings.json`), on `UserPromptSubmit` and on `PostToolUse` for `Edit|Write|MultiEdit`.
- Cursor: `.cursor/hooks.json` (user scope: `~/.cursor/hooks.json`), on `beforeSubmitPrompt` and `afterFileEdit`.
- GitHub Copilot CLI: `.github/hooks/gitmotive.json` (user scope: `~/.copilot/hooks/gitmotive.json`), on `UserPromptSubmit` and `PostToolUse`.
- oh-my-pi: `.omp/settings.json` (user scope: `~/.omp/agent/settings.json`), on `UserPromptSubmit` and every `PostToolUse`.

## Hook commands

Each hook runs a command of this form, where `<run>` is how the hook starts gitmotive:

```
claude : <run> capture
cursor : <run> capture --agent cursor --event <beforeSubmitPrompt|afterFileEdit>
copilot: <run> capture --agent claude --source copilot
omp    : <run> capture --agent claude --source omp
```

When gitmotive is installed into a site-packages directory (pipx, a venv, the install script), `<run>` is `<python> -I -m gitmotive`, with the absolute path of that Python. `-I` keeps a hook whose working directory is inside a gitmotive checkout from importing the checkout instead of the installed copy. When gitmotive runs from a source tree, `<run>` is `PYTHONPATH=<pkg> <python> -m gitmotive`. The `post-commit` stamp line uses the same `<run>`. In user scope every command starts with `GITMOTIVE_STORE=user`.

Copilot and oh-my-pi send Claude-shaped payloads, so they are parsed with `--agent claude`. `--source` records which product actually produced the event.

## After a Python or pipx change

The hook commands contain an absolute Python path. After you upgrade Python, reinstall with pipx, or move the venv, run `gitmotive install` again with the same `--agent` and `--scope`. It upserts: each existing gitmotive hook command and the `post-commit` stamp line are replaced in place, so stale paths heal and there is still exactly one gitmotive entry per hook event. Your other hooks are left alone.
