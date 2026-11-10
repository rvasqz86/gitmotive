# Task 21: Launch post drafts (Show HN, Product Hunt, LinkedIn)
Status: done
Type: docs
Scope: launch
Depends on: 20
## Goal
Draft launch copy in `launch/`. Nothing is posted. The copy is concrete and hype-free and uses only real commands.
## Files
- launch/show-hn.md (create: sections `## Title` ≤ 80 chars, `## Body` ≤ 250 words covering what it is, how it works (hooks → local JSONL → blame scoring), that it is deterministic with no LLM and no network, supported vs experimental agents, the demo and repo links, limitations, and an ask for feedback)
- launch/product-hunt.md (create: `## Name`, `## Tagline` ≤ 60 chars, `## Description` ≤ 260 chars, `## First comment` ≤ 200 words, `## Gallery captions` (3), `## Topics`)
- launch/linkedin.md (create: `## Post` ≤ 1,300 chars, first person: problem → what I built → try it at gitmotive.tech)
- tests/test_public_text.py (modify: length limits per section)
## Acceptance criteria
- [ ] Each file starts with `Status: DRAFT — do not post without review`
- [ ] The section length limits are enforced by tests
- [ ] The only links are https://gitmotive.tech, https://gitmotive.tech/demo/ and https://github.com/rvasqz86/gitmotive
- [ ] No denylist names; no traction claims beyond `[N]` placeholders
## Tests
Extend `tests/test_public_text.py`.
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none

## Implementation notes (round 1)
- Created `launch/show-hn.md`, `launch/product-hunt.md`, `launch/linkedin.md`. Each starts with the DRAFT status line. Current sizes: HN title 68/80 chars, body 226/250 words; PH tagline 47/60, description 227/260 chars, first comment 158/200 words, 3 captions; LinkedIn post 1074/1300 chars.
- Claims were checked against README, `cli.py` (`cmd_why` scoring +100/+50/+10, `cmd_log` output) and `site/demo/index.html`. Reasoning is described as Claude Code only, Copilot CLI and oh-my-pi as experimental, and the known gaps are listed.
- No install command appears in the drafts on purpose. PyPI is not published yet (that is a human step), so `pipx install gitmotive` would not work today, and `https://gitmotive.tech/install.sh` is not one of the three allowed links. The drafts point readers to https://gitmotive.tech for install instead. The only commands quoted are `gitmotive install --agent claude`, `git motive <file>:<line>` and `gitmotive log`.
- No traction numbers are used, so no `[N]` placeholders were needed.
- `tests/test_public_text.py`: added `launch_violations()` with these checks:
  - the status line comes first;
  - per-section limits from `LAUNCH_LIMITS`, where chars are the stripped section length and words are whitespace-split. Name, Gallery captions and Topics have no limit in the task, so they get loose sanity caps: 60, 1000 and 500 chars;
  - every `http(s)://` URL is in `ALLOWED_LINKS`, after trailing punctuation is stripped;
  - no number next to a traction word (users/stars/downloads/…). `[N]` is allowed;
  - exactly 3 gallery captions.
- These checks cover only the three draft files, so `launch/DEPLOY.md` (task 18) is not link-checked. Two synthetic self-tests cover failing and boundary-passing cases, plus a real-tree test. The full test command passes. The denylist is active, not skipped.
- The denylist check over `launch/**` already existed. These drafts contain no organisation names.
