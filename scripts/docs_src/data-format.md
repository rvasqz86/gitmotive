# Data format

Everything gitmotive records is one file, `events.jsonl`, with one JSON object per line. Each object is an event: a `prompt` you submitted, or an `edit` the agent made to a file.

## Store locations

The store is found in this order:

1. `GITMOTIVE_STORE=user` is set: `~/.gitmotive/repos/<hash>/events.jsonl`, where `<hash>` is derived from the repository's absolute path.
2. `<repo>/.gitmotive/events.jsonl` exists: use it.
3. `~/.gitmotive/repos/<hash>/events.jsonl` exists: use it.
4. Otherwise `<repo>/.gitmotive/events.jsonl`.

`GITMOTIVE_HOME` moves `~/.gitmotive` somewhere else. `gitmotive install` adds `.gitmotive/` to `.git/info/exclude`, so a repo-scope store (`<repo>/.gitmotive/`) is never committed. The entry applies to repo scope only; the user-scope store lives outside the repository.

## Append-only

Hooks only ever append a line, so concurrent hook runs never corrupt the file. The one exception is stamping: `gitmotive stamp`, `why` and `log` fill in the `commit` field of edits that have landed in a commit. They write a complete new file and atomically replace the old one. No event is ever removed.

## The agent field

`agent` is the product that produced the event (`claude`, `cursor`, `copilot` or `omp`), not the payload shape. Copilot CLI and oh-my-pi send Claude-shaped payloads but are recorded as `copilot` and `omp`. Events captured by older versions have no `agent` or `model`.

## Event fields

Unknown keys are ignored on read and missing optional keys take their defaults; lines without `kind`, `session` or `ts` are skipped. Older and newer files stay readable.
