# Task 20: README rewrite for public launch
Status: done
Type: docs
Scope: readme
Depends on: 10, 15
## Goal
Rewrite README.md for strangers: the tagline, a GIF placeholder with the exact recording sequence, install, quickstart, supported agents (Copilot and oh-my-pi experimental), and a link to gitmotive.tech. Keep the accurate technical content (how it links, known gaps, scopes, hq support), trimmed.
## Files
- README.md (modify)
- tests/test_public_text.py (modify: README must link `https://gitmotive.tech` and contain `pipx install gitmotive`)
## Acceptance criteria
- [ ] Order:
  1. Title and tagline, then a what/why paragraph
  2. `<!-- GIF: docs/demo.gif -->`, followed by a fenced recording sequence: `pipx install gitmotive`, `cd your-repo`, `gitmotive install --agent claude`, a Claude Code edit, `git commit -am "…"`, `git motive path/to/file.py:42`, `gitmotive log`
  3. Install (pipx, the curl one-liner, from source with `install.sh`)
  4. Quickstart
  5. Supported agents table with a Status column (`supported`/`experimental`)
  6. Commands (matching `cli.USAGE`, plus `--version`)
  7. How it links
  8. Privacy (local only, no network, no telemetry; prompts are stored verbatim; use `--scope user` for work you don't own)
  9. Known gaps
  10. Live demo and docs links
  11. License
- [ ] The example `git motive` output matches the current `why` format, including `via` and `model`
- [ ] `tests/test_public_text.py` and `audit_public.py --tree --denylist .hq/audit-denylist` pass
## Tests
`tests/test_public_text.py` (extended as above).
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none

## Implementation notes (round 1)
- I rewrote README.md in the required 11-section order: title and tagline with what/why, the GIF placeholder and recording sequence, Install (pipx, curl one-liner, from source), Quickstart, Supported agents, Commands, How it links, Privacy, Known gaps, Live demo and docs, and License. User scope (`--scope user`) sits under Quickstart, and hq support sits under Supported agents.
- The example `git motive` output follows `cli.cmd_why` as it is now: on the `edited` line, `[why]` comes before `via claude  model claude-opus-5-5`. The author name is the neutral `dev`.
- In the Supported agents table, Claude Code and Cursor are `supported`, and Copilot CLI and oh-my-pi are `experimental` (matching `cli.EXPERIMENTAL`).
- Commands lists every `cli.USAGE` entry plus `--version` / `-V`.
- Known gaps now opens with the manager-requested item about Claude Code's first edit per turn. That edit may carry the previous message's reasoning because of transcript flush timing (see task 24 notes). The same entry covers the related `/model` switch caveat.
- Hosting: README links point to `https://gitmotive.tech`, `/demo/` and `/docs/` (Cloudflare Pages). The README names no host.
- Test: I added `test_readme_links_site_and_pipx` to `tests/test_public_text.py`.
- Verification: the full test command from `.hq/runtime` passes. `audit_public.py --tree --denylist .hq/audit-denylist` exits 0 (high=0, medium=0, 2 info in .hq files I didn't touch). There is no `.audit-denylist` at the repo root, so I used the denylist path from `.hq/runtime`.

## Implementation notes (round 2)
- [major] Four README tests added to `tests/test_public_text.py`:
  - `test_readme_section_order`: the `##` headings must be exactly Install, Quickstart, Supported agents, Commands, How it links, Privacy, Known gaps, Live demo and docs, License, in that order.
  - `test_readme_gif_and_recording_sequence`: `<!-- GIF: docs/demo.gif -->` must come before `## Install` and be followed directly by a fence that holds the recording steps in order.
  - `test_readme_why_example_matches_cmd_why`: every example `edited` line must match the `cmd_why` layout (`by … session … [why]  via X  model Y`).
  - `test_readme_commands_match_usage`: each full `cli.USAGE[c][0]` string, with table `\|` unescaped, must appear in backticks in the Commands section, along with `gitmotive --version` and `-V`. This is stricter than checking only the command head. It would have caught the round-1 `help` row.
- [minor] Supported agents: the Claude row now reads "reasoning from the transcript, model from the payload or transcript". The Cursor row now reads "prompt, edits, model (when the payload sends one)".
- [minor] The Commands `help` row now reads `gitmotive help [cmd] | -h | --help`, matching USAGE.
- Denylist finding: resolved by the task, which now uses `.hq/audit-denylist`. No change was needed.
- Verification: the full test command from `.hq/runtime` passes, and `audit_public.py --tree --denylist .hq/audit-denylist` exits 0.
