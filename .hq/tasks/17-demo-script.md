# Task 17: 60-second demo script for recording
Status: done
Type: docs
Scope: site
Depends on: 14
## Goal
Write `site/DEMO_SCRIPT.md`, a 60-second screen-recording script with real commands, browser beats and voice-over lines with timings. It is served publicly as-is (spec "Site"), and contains nothing sensitive.
## Files
- site/DEMO_SCRIPT.md (create)
- tests/test_site.py (modify: timestamp check)
## Acceptance criteria
- [ ] Timed sections ending at or before 0:60:
  - a hook (0–8 s)
  - `pipx install gitmotive` and `gitmotive install --agent claude`
  - a Claude Code edit
  - `git commit`
  - `git motive <file>:<line>` showing the prompt, reasoning and model
  - the gitmotive.tech/demo/ viewer via a deep link
  - a close on the tagline and URL
- [ ] A pre-recording checklist: clean terminal, font size, a prepared sample repo, `GITMOTIVE_STORE` unset
- [ ] Only real commands (`test_public_text.py`); no organisation names, no client repos
## Tests
Extend `tests/test_site.py`: parse the `m:ss` timestamps in `DEMO_SCRIPT.md` and assert the maximum is ≤ 1:00.
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none
## Implementation notes (round 1)
- Created `site/DEMO_SCRIPT.md` with seven back-to-back sections: 0:00–0:08 hook (`git blame`), 0:08–0:18 install, 0:18–0:30 Claude Code edit, 0:30–0:36 commit, 0:36–0:46 `git motive src/fetch.py:28`, 0:46–0:54 the viewer at `/demo/#gitmotive/cli.py:42`, and 0:54–1:00 close on the tagline and gitmotive.tech. It also has a pre-recording checklist (clean terminal, font size, sample repo setup commands, `unset GITMOTIVE_STORE`, a dry run, a check of the viewer link) and an after-recording privacy check.
- The sample outputs are real. In a throwaway repo in the session scratchpad I ran `gitmotive install --agent claude`, then a real headless Claude Code edit (`claude -p ... --model haiku`) with the installed hooks, then `git commit` and `git motive src/fetch.py:28`. The output is pasted verbatim. Only the absolute paths in the install output are shortened to `.../fetcher/`, and the doc says so.
- On the first try the output had no reasoning line, because the model wrote no text before its Edit. The prompt in the script ("First say in one sentence why, then edit.") reliably gives a reasoning line.
- Note for the recorder and the reviewer: the current `site/demo/data.json` has `prompts: {}`, so no line is matched yet. `#gitmotive/cli.py:42` will show `none recorded` until the data is re-exported after dogfooding. The checklist tells the recorder to check the link and pick a coloured line if needed. The link format is the one in the spec.
- Tests in `tests/test_site.py`:
  - `script_seconds` parses one-digit-minute `m:ss`, so a clock time like `21:32` in the pasted output is not read as `1:32`.
  - `test_script_timestamp_parser` self-tests the parser.
  - `test_demo_script` asserts the max ≤ 60 s, that the headings start at 0:00–0:08 with no gaps or overlaps, that the last section is Close, and that the required commands, the deep link, the tagline and the checklist items are present.
- `test_public_text.py` covers the new file: only `gitmotive install` appears as a `gitmotive` subcommand. The full test command passes.
