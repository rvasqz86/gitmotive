# Task 21: Launch post drafts (Show HN, Product Hunt, LinkedIn)
Status: todo
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
