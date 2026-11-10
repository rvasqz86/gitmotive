# Task 22: Grant application draft
Status: todo
Type: docs
Scope: launch
Depends on: 19, 20
## Goal
Draft `launch/application.md` with concrete answers for the .tech fund. Cover:
- what it is, the problem, and who it's for
- what's live at gitmotive.tech: the product itself (live demo, docs, installer), not a landing page
- traction placeholders
- what the money funds: the milestones team sync, hosted index and PR review integration
- why me: 10+ years in backend and data platforms; built enterprise data platforms at large-scale orgs; no organisation names
## Files
- launch/application.md (create)
- tests/test_public_text.py (modify: required headings, banned hype words)
## Acceptance criteria
- [ ] Header `Status: DRAFT — fill placeholders, do not submit without review`
- [ ] The headings are exactly: `## What it is`, `## The problem`, `## Who it's for`, `## What's live at gitmotive.tech`, `## Traction`, `## What the money funds`, `## Why me`, `## Ownership and licensing`
- [ ] "What's live" names `/`, `/demo/`, `/docs/` and `/install.sh`, and explains that the demo runs gitmotive's own provenance data client-side
- [ ] Traction uses the placeholders `[GitHub stars]`, `[pipx installs]` and `[design partners]`; no invented numbers
- [ ] Milestones each have a deliverable and a rough timeframe:
  - team sync: provenance shared through git notes
  - hosted index: opt-in, still deterministic
  - PR review integration: intent inline on PR diffs
- [ ] "Ownership and licensing": sole author, MIT, built on personal time and equipment, history audited for third-party material (no names)
- [ ] None of the words `revolutionary`, `game-changing` or `disrupt` (tested); no denylist names
## Tests
Extend `tests/test_public_text.py`.
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none
