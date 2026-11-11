# gitmotive public launch on gitmotive.tech

This branch, `feat/tech-launch-site`, makes gitmotive ready to go public, to be installed by strangers and to run live at gitmotive.tech for the .tech "No Excuses Fund" application. Nothing has been pushed, published, deployed or made public.

## What was built (per task)
- **01:** Untracked `build/` artifacts. Local-only hq reports are gitignored.
- **02:** `scripts/audit_public.py`, a public-release scanner covering the tree and the full history. Its checks are secret, denylist, host, path, transcript and artifact. Every excerpt is redacted.
- **03:** `tests/test_public_text.py`, a guard that fails on a denylist term or a non-existent `gitmotive` command in public text.
- **04:** The audit report and history-rewrite plan. This was human stop #1, and the human approved.
- **05:** Confirmed a clean tree with the real denylist. There was nothing to remediate.
- **06:** Events record `agent` and `model`. A `--source` label tags copilot and omp. Installers upsert rather than duplicate.
- **07:** Claude Code and Cursor are proven end to end through the exact installed hook commands.
- **08:** Added `--version`, per-command help with a single-source `USAGE`, and experimental labels for Copilot and oh-my-pi. `install --help` no longer runs an install.
- **09:** PyPI-ready metadata, with homepage https://gitmotive.tech. `check_dist.sh` runs the build plus `twine check --strict`. The `gitmotive` name was free on 2026-11-10.
- **10:** A fresh-machine smoke test passes in a venv and in Docker (py3.12). Installed hooks never import the source checkout (`python -I`), and the post-commit line self-heals.
- **11:** Site home page, CSS, favicons, OG image, CSP headers and 404. The design is terminal/diff themed.
- **12:** Stamping moved into `resolve.stamp(persist=…)`, which restores the "nothing imports cli" layering.
- **13:** `scripts/export_demo.py`, a demo exporter with a per-record privacy gate. Only HEAD-tracked files are exported. It applies whole-word and substring denylist checks, masks secrets, rewrites home paths, strips pasted content, and exports only the prompts that are referenced.
- **14:** The client-side blame-style demo viewer: gutter colours per prompt, a detail panel, deep links, keyboard navigation, and node tests.
- **15:** `/docs`, generated from the real CLI and data model. CI checks it with `gen_docs.py --check`.
- **16:** `/install.sh`, a one-line installer (pipx or venv).
- **17:** `site/DEMO_SCRIPT.md`, the 60-second recording script.
- **18:** Cloudflare Pages workflow (push to `main` only), `_headers`/`_redirects`, and `launch/DEPLOY.md` with the DNS steps.
- **19:** Deploy readiness review. This was human stop #2: Cloudflare Pages, approved.
- **20:** README rewritten for the public launch.
- **21:** Launch drafts: Show HN, Product Hunt and LinkedIn.
- **22:** Grant application draft (`launch/application.md`).
- **23:** Demo data regenerated from this branch's own dogfood events, a final audit, and `launch/CHECKLIST.md`.
- **24 (added):** Fixed model capture. Claude Code flushes a turn's transcript records only after the first PostToolUse, so model capture now falls back to the latest assistant model.
- **25 (added, Phase D):** Polish from the deferred review findings. Unmatched reasoning is now omitted instead of guessed.
- **26 (added, Phase D):** Fixed the checklist's PyPI upload step.

## Decisions and deviations
- The planner and spec reviewer were switched to Claude because Copilot returned a 403 on omp's model. The implementer was also switched to Claude, because the model is only reliably captured from Claude Code.
- The brief file stays local (`.hq/brief-source.md`, gitignored) because it names the organisations being audited for. The denylist is `.hq/audit-denylist` (gitignored), created by the manager at the human's choice.
- The brief's `init`/`blame` wording was mapped to the real CLI (`gitmotive install`, `git motive file:line`). No aliases were added.
- **History rewrite skipped (human, task 23).** History contains only `build/`/`dist/` copies of gitmotive's own code, with no secrets and no denylist hits. A rewrite would invalidate the commit IDs in the demo data.
- No analytics ship. Hosting is Cloudflare Pages (human-approved).
- Dogfood findings that changed the plan:
  - `install.sh` run inside the checkout baked the checkout into the hooks (fixed in task 10).
  - Edits made through shell commands are invisible to hooks, so implementers were told to use the Edit/Write tools.
  - Model and reasoning capture had a transcript-flush race (fixed in tasks 24 and 25).
- The spec was amended by the manager three times: hook command `<run>` form (task 10), model fallback chain (task 24), and demo default files (task 23).
- The final `site/demo/data.json` was regenerated at `01cca2a`, after task 25 changed the viewer, and is committed with this summary.

## Test results (final HEAD)
- The full suite (19 test files) passes, run with the real denylist.
- `audit_public.py --tree`: high 0, medium 0.
- `audit_public.py --history`: high 0, plus 15 medium findings, all build/dist artifacts (accepted).
- `gen_docs.py --check`: up to date.
- `check_dist.sh`: `twine check --strict` PASSED.
- Smoke tests pass in both venv and Docker.
- Demo: 4 files, 883 matched lines with agent and model, 6 prompts, 0 temp or home paths.

## Follow-ups
- A live Cursor session has not been verified. Cursor is labelled as verified against documented payloads only.
- Reasoning is captured only for Claude Code. For the first edit of a Claude turn, reasoning is now omitted rather than guessed.
- Hand steps are listed in order in `launch/CHECKLIST.md`: merge, push, make public, Cloudflare + DNS, PyPI, record the demo, fill in the application, post the drafts.
- Grant milestones (from the application): team sync via git notes, a hosted index, and PR review integration.
