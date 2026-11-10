# Task 22: Grant application draft
Status: done
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
## Implementation notes (round 1)
- Created `launch/application.md`: starts with the required status line, exactly the eight `##` headings in order. Facts taken from README/site (adapters, deterministic scoring, `/demo/` loads gitmotive's own dogfood data from static JSON, client-side). Why me uses "large-scale orgs" only; no organisation names. Traction is placeholders only, no numbers.
- Milestones are a numbered list `N. **Name** (about N weeks). Deliverable: ...`: team sync ~6 weeks (git notes), hosted index ~8 weeks (opt-in, deterministic), PR review integration ~6 weeks (intent inline on PR diffs). Timeframes are rough guesses for the user to adjust.
- Ownership claims the audit was done "for the public release" (audit commits e5d87cd, 19c3448 exist); user should confirm before submitting.
- `tests/test_public_text.py`: added `application_violations()` (status header, exact headings, hype words incl. variants like "disruptive"/"game changing", `_TRACTION` number claims, the four live paths + "client-side", the three placeholders and no digits in Traction, each milestone with `Deliverable:` and `(about N weeks)`), a self-test on a synthetic bad file, and a real-tree test that also checks Why me / Ownership content. Existing denylist scan already covers `launch/`.
- Full test command passes with the denylist set (denylist check ran, not skipped).
