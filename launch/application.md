Status: DRAFT — fill placeholders, do not submit without review
Prerequisites before submitting: site deployed at gitmotive.tech, repo public on GitHub, package published on PyPI.

# .tech No Excuses Fund: application draft

Product: gitmotive. Site: https://gitmotive.tech. Repo (MIT): https://github.com/rvasqz86/gitmotive

## What it is

gitmotive is "git blame for intent". `git blame` tells you who changed a line; `git motive` tells you why. It records the prompt and the agent's reasoning behind each AI-written edit and links them to the lines and commits that edit produced. Months later you can point at a line with `git motive src/fetch.py:42` and read the commit, the prompt, the agent's reasoning, the model, the session and the other files changed for the same request.

It is a Python command-line tool plus agent hooks. `gitmotive install --agent claude` wires Claude Code's own hooks; each prompt and file edit is appended to `.gitmotive/events.jsonl` in the repo, and a `post-commit` hook stamps new edits with their commit. Lookups run `git blame` on the line and score the recorded edits by commit and line text. It is deterministic: no LLM in the loop, no API key, no network calls, no telemetry. When nothing was recorded for a line it says "none recorded" instead of guessing.

Agents: Claude Code and Cursor are supported. GitHub Copilot CLI and oh-my-pi are experimental (prompts and edits only).

## The problem

AI coding agents now write more code than reviewers can read closely. The context that explains a change (what was asked, what the agent considered, which files it touched for the same request) exists only while the session is open. When the session ends, that context is gone. The commit message is a one-line summary at best, and `git blame` points at whoever ran the agent.

That leaves the same questions open in review, in incidents and in onboarding: was this line a deliberate decision or a side effect? What was the instruction? Was it the same request that changed the migration next to it? Today the answer is to ask the person who ran the agent and hope they remember.

## Who it's for

- Developers who use Claude Code or Cursor daily and want to know, weeks later, why a line in their own repo exists.
- Reviewers and tech leads who review AI-assisted pull requests and need the prompt behind a change, not only the diff.
- Teams with audit or change-control needs who must explain where a change came from, and want that record kept locally and produced deterministically.

## What's live at gitmotive.tech

The site is the product, not a page about it. Every path below is served from gitmotive.tech:

- `/`: the home page. It covers the problem, how it works in three steps, the install command and the repo link.
- `/demo/`: the live product, running in the browser. It loads gitmotive's own provenance data, recorded by dogfooding gitmotive while building gitmotive, and renders a blame-style view of the real source files. Clicking a line shows the prompt, the agent's reasoning, the session, the model and the timestamp. It runs fully client-side: the data is a static JSON file and the viewer is plain JavaScript, with no backend and no account.
- `/docs/`: install, quickstart, per-agent adapter setup, CLI reference and the on-disk data format, kept in sync with the real CLI help.
- `/install.sh`: the one-line installer, `curl -fsSL https://gitmotive.tech/install.sh | sh`. It installs the CLI with pipx, or into its own venv when pipx is not present, and can wire agent hooks in the same step.

## Traction

Fill in real figures before submitting; do not estimate.

- GitHub stars: [GitHub stars]
- pipx installs: [pipx installs]
- Design partners using it on a real codebase: [design partners]

## What the money funds

Today intent is recorded per developer, in one local clone. The grant funds three milestones that make it useful to a team, in this order:

1. **Team sync** (about 6 weeks). Deliverable: provenance shared through git notes. Recorded intent will be written to a dedicated notes ref. Git does not push or fetch notes refs by default, so gitmotive will configure the refspec for that ref; a teammate who clones the repo will then be able to run `git motive` on lines they did not write. No server, and the same git permissions that already guard the code.
2. **Hosted index** (about 8 weeks). Deliverable: an opt-in hosted index of provenance across a team's repos, so intent can be searched and browsed without cloning. It stays deterministic: the index stores and serves what was recorded and adds no model-generated guesses. Local use stays the default and works without it.
3. **PR review integration** (about 6 weeks). Deliverable: intent shown inline on PR diffs. Each AI-written hunk in a pull request shows the prompt and reasoning that produced it, so reviewers read the "why" next to the change instead of asking for it.

The money pays for my time on these milestones, hosting for the index, and test accounts for the agents and code hosts the integrations need.

## Why me

- 10+ years building backend systems and data platforms.
- I have built enterprise data platforms at large-scale orgs, where lineage, auditability and "where did this value come from" were core requirements. gitmotive applies the same idea, provenance, to code written by agents.
- I built gitmotive by using it: the provenance data in the live demo is my own record of building this tool with AI agents.

## Ownership and licensing

- I am the sole author of gitmotive.
- It is released under the MIT license.
- It was built on my personal time and on my personal equipment.
- For the public release I audited the working tree and the full git history for third-party material, including client or employer code, internal names, credentials and captured prompts from non-personal projects.
