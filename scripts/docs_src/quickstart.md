# Quickstart

1. Hook up your agent, from the root of a git repository:

```sh
gitmotive install --agent claude
```

This writes the capture hooks to `.claude/settings.json`, adds a `post-commit` hook that runs `stamp`, and adds `.gitmotive/` to `.git/info/exclude`, so nothing gitmotive records is committed.

2. Use the agent as usual. Every prompt you submit and every file edit it makes is appended to `.gitmotive/events.jsonl`.

3. Commit:

```sh
git commit -am "add retry with backoff"
```

The `post-commit` hook stamps the new edits with the commit they landed in.

4. Ask any line why it exists:

```sh
git motive path/to/file.py:42
```

`gitmotive why path/to/file.py:42` is the same command. It prints the line, the commit from `git blame`, the edit that wrote it, the prompt behind that edit, the agent's reasoning and the other files changed for the same prompt. When nothing was recorded for a line it says `(none recorded)` and exits 1. It never guesses.

5. List what was recorded:

```sh
gitmotive log
gitmotive log path/to/file.py
```

Each prompt is shown with its edit count, the commits its edits landed in and the files it touched.
