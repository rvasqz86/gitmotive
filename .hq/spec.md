# Spec: gitmotive public launch on gitmotive.tech

## Goal
Get gitmotive ready for a public repo and a live product site at gitmotive.tech, in time for the
.tech grant application (target Dec 8, 2026). Concretely:

1. A repeatable audit of the working tree **and** full git history for secrets, internal hostnames and
   IPs, organisation names on the local denylist, other users' home paths, captured prompts or
   transcripts, and build artifacts. It produces a report and a proposed `git filter-repo` plan, then
   stops for the human (human stop #1).
2. Strangers can install the CLI with `pipx install gitmotive` once it is published: complete pyproject
   metadata, passing `python -m build` and `twine check`, Claude Code and Cursor proven end to end, and
   Copilot and oh-my-pi labelled "experimental". A fresh-machine smoke test exists and passes.
3. A static site in `site/` that *is* the product: a home page; a client-side live demo viewer (a
   blame-style file view built from this repo's own dogfooded gitmotive data, showing prompt, reasoning,
   session, agent, model and timestamp per line); `/docs` generated from the real CLI; `/install.sh`;
   OG tags, a favicon and `site/DEMO_SCRIPT.md`.
4. Deploy configuration (Cloudflare Pages plus a GitHub Action) and exact DNS instructions. The deploy
   itself is human stop #2.
5. A rewritten README and launch drafts in `launch/` (Show HN, Product Hunt, LinkedIn, grant
   application). Nothing is posted.
6. A final checklist of what is done and what the human still does by hand.

## Non-goals
- Pushing, force-pushing, publishing to PyPI, changing repo visibility, triggering a deploy, or
  touching DNS. All of these are human actions. Tasks only write files and make local commits.
- Executing the history rewrite. The plan only proposes commands, and the human runs them.
- New CLI commands named `init` or `blame` (see Open questions).
- Making Copilot or oh-my-pi production grade. They only get the "experimental" label plus correct
  agent labelling.
- A backend, accounts, a hosted index, team sync or PR integration. These are future grant milestones,
  mentioned only in copy.
- Third-party analytics. None ship (see Open questions).
- Recording the demo GIF or video.
- Implementer tasks changing anything under `~/` (the user's venv, hook configs or dogfood store).

## Design

### `.hq/` is committed
The manager commits `.hq/` (spec, tasks, reviews, log) as `chore(hq): …` at Gate 1 and alongside each
task, so `.hq/**` is part of the public tree. Only these stay local, through the tracked
`.hq/.gitignore`:
- `brief-source.md`
- `runtime.log*`
- `audit-report*.md`
- `history-rewrite-plan.md`
- `deploy-readiness.md`

Task 01 adds the last three entries. Consequences:
- `audit_public.py --tree` covers `.hq/**` automatically, since it is tracked or untracked-unignored.
- `tests/test_public_text.py` applies only its **denylist** check to `.hq/**`. Spec and task text
  legitimately mention the `init`/`blame` wording.
- The demo's hq dereference can rely on committed `.hq/tasks/*.md`.

Spec and task text must not contain literal secret-shaped strings or full private IPv4 quads (they
would trip the tree audit). They describe them in words instead.

### Ordering and human stops
Tasks run in brief order. There are two **human-stop tasks**. Each writes only gitignored report files
under `.hq/`, makes **no commit and no irreversible change** (no ref moves, no push, no network
mutation), and ends with the manager halting for the human:
- **Task 04**: audit report and proposed history rewrite (brief step 1 [CONFIRM]).
- **Task 19**: deploy readiness (brief step 4 [CONFIRM]).

There is also one **manager/human environment step** between tasks 06 and 07, the dogfood reinstall
(see "Dogfood capture" below). It touches `~/` only, so no implementer task does it.

The history rewrite, if approved, should be run by the human **after** this branch merges to `main`
and before the repo goes public, because a rewrite changes every SHA. Task 23 re-runs the
full-history audit, and its checklist states this sequence.

### Denylist handling
Organisation names never appear in any committed file. `scripts/audit_public.py` reads the denylist
(one term per line, `#` comments allowed) from the first of these that exists:
1. `--denylist PATH`
2. env `GITMOTIVE_AUDIT_DENYLIST` (a path)
3. `.audit-denylist` at the repo root (gitignored in task 02)

With no denylist available, the denylist check reports `skipped: no denylist`, which is not a pass.
The human creates `.audit-denylist` locally (see Open questions). Every output (stdout, `--json`,
reports, exceptions) **redacts** hits as `<denylist:N>`, where N is the 1-based line number.

### Audit scanner (`scripts/audit_public.py`)
A dev-only, stdlib script that is not part of the installed package. Its checks, each with a fixed severity:

| check id | what | severity |
|---|---|---|
| `secret` | AWS access key id (`AKIA` + 16 upper-alnum); GitHub tokens (`gh[pousr]_` + ≥36 alnum, `github_pat_` + ≥22 `[A-Za-z0-9_]`); Anthropic (`sk-ant-` + ≥20 `[A-Za-z0-9_-]`); OpenAI-style (`sk-` + ≥20 alnum); Slack (`xox[baprs]-` + ≥10 `[A-Za-z0-9-]`); PEM private-key header; generic `(api[_-]?key\|secret\|token\|password)\s*[:=]\s*['"][^'"\s]{12,}['"]` | high |
| `denylist` | case-insensitive whole-word match of any denylist term | high |
| `transcript` | tracked/untracked-unignored path under `.gitmotive/`; any `*.jsonl` containing `"hook_event_name"`, `"transcript_path"`, `"tool_use_id"` or `"kind": "prompt"` | high |
| `host` | a full private IPv4 dotted quad (10/8, 172.16/12, 192.168/16) where every octet is 0–255, bounded so it is neither preceded nor followed by a digit or `.` (so `10.1.2` and `1.10.1.2.3` do not match); hostnames `<label>(.<label>)*.(internal\|corp\|intranet\|lan\|local)` with at least one label before the suffix (so `~/.local/` does not match) | medium |
| `path` | absolute home path of **another** user: `/home/<x>/` or `/Users/<x>/` where `<x>` is not the current user (`getpass.getuser()`) | medium |
| `path` (own home) | the same, where `<x>` is the current user | info |
| `artifact` | tracked `build/`, `dist/`, `*.whl`, `*.egg-info/` | medium |

**Self-match rule.** Test fixtures that plant secrets or private IPs build them by string
concatenation at runtime (e.g. `"AK" + "IA" + "X"*16`), so the committed source never contains a match.
The scanner builds its own regex prefixes the same way, so it does not match itself. The rule is
enforced by task 02's acceptance criteria and by running `--tree` on the repo.

**Allow-list.** A committed `.audit-allow` lists `<path-glob> <check-id>  # reason`, one per line,
with the reason required. Matching findings are downgraded to `info` and shown as `allowed`. It starts
empty and is only for genuine false positives approved at task 04. It never holds secret values.

Scopes:
- `--tree`: `git ls-files` plus `git ls-files -o --exclude-standard` (this includes the committed `.hq/`).
- `--history`: every blob reachable from `--all` (`git rev-list --objects --all`, contents through
  `git cat-file --batch`), plus every commit message and author/committer name and email. The
  introducing commit of a blob is the **oldest** commit from
  `git log --all --reverse --format=%H --find-object=<blob>`, taking the first line.
- No flag means both.

Binary blobs (NUL in the first 8 KiB) are checked by path only. Output is a table or `--json`. Exit
codes are 0 when there are no high/medium findings, 1 when there are, and 2 on a usage error.

### Public-text guard (`tests/test_public_text.py`, task 03)
This test runs over README.md, `site/**`, `launch/**` and `.hq/**`:
- **Denylist** (all of the above, including `site/demo/data.json`): uses `audit_public.load_denylist`.
  When there is no denylist it prints `skipped denylist`.
- **Command check** (README, `site/**` except `site/demo/data.json`, `launch/**`; not `.hq/**`):
  inside inline code, fenced code, `<code>` or `<pre>` only, there is no `gitmotive init` or
  `gitmotive blame`, and every `gitmotive <word>` is a real command (`why log stamp install capture
  help`) or `--version`/`-V`.

Later tasks extend it with copy-length and heading checks.

### Packaging
`pyproject.toml` changes:
- `[project.urls]`: Homepage `https://gitmotive.tech`, Documentation `https://gitmotive.tech/docs/`,
  Repository `https://github.com/rvasqz86/gitmotive`, Issues `https://github.com/rvasqz86/gitmotive/issues`.
- Classifiers, **without** a `License ::` classifier, because PEP 639 forbids combining one with the
  SPDX `license = "MIT"`.
- `build-system.requires = ["setuptools>=77"]`, needed for `license` as an SPDX string plus `license-files`.
- `[tool.setuptools] packages = ["gitmotive"]`. Once `site/`, `scripts/` and `launch/` exist, flat-layout
  auto-discovery would fail.
- `dynamic = ["version"]` from `gitmotive.__version__`.

`scripts/check_dist.sh` builds in a throwaway venv with `build` and `twine` (dev-only), then runs
`twine check --strict`.

Tests that need a wheel use a shared helper `tests/_wheel.py` (not picked up by the `test_*.py` runner).
`build_wheel() -> Path | None` tries `python -m build --wheel` (isolated, so the latest setuptools is
fetched) into a cached temp dir. It returns `None` (the caller prints `skip …`) when `build` is missing
or the build fails, for example when offline.

### Capture: agent and model
`Event` gains two optional fields, `agent` and `model`, both defaulting to `None`. The change is
backward compatible: `from_json` ignores unknown keys, and missing keys default.

`agent` means **the product that produced the event**, not the payload shape. Today `install_omp` and
`install_copilot` write `--agent claude` because they emit Claude-shaped payloads. They now also write
`--source omp` or `--source copilot`. `capture.main` parses `--source` and passes it to
`adapters.normalize(payload, agent=…, event=…, source=…)`, which uses `agent` for the payload shape and
sets `out["agent"] = source or agent_resolved`.

The installers **upsert**. When an existing hook entry's command contains `gitmotive capture`, its
command is replaced with the new one instead of being skipped. Re-running `gitmotive install` therefore
refreshes stale python paths and adds `--source` labels. There is still exactly one gitmotive entry per
event.

`model` is filled as follows:
- **Claude-shaped:** the payload `model` if present, else `message.model` of the assistant transcript
  record that holds the matching `tool_use`. This is read in the same pass as the reasoning, through
  `capture._transcript_context`.
- **Cursor:** the payload `model` if present.
- **Otherwise:** `None`.

`why` appends `  via {agent}` and `  model {model}` to the `edited` line when they are known.

### Cursor end to end
In `adapters.normalize` for `cursor`:
- `cwd` is the payload `cwd`, else `workspace_roots[0]`, else `None`.
- `detect()` returns cursor when `conversation_id` is present, even if `hook_event_name` is too.

Tests execute the **exact command strings** that `gitmotive install` wrote, through `sh -c` with the
payload on stdin. The payloads are synthetic but follow Cursor's documented shapes. A live Cursor session
check is a manual item: the implementer records it in the task report if Cursor is available, otherwise
the report states "unverified against live Cursor" (see Open questions).

### Experimental labelling
`EXPERIMENTAL = ("copilot", "omp")` in `cli.py`. `cmd_install` prints
`note: <agent> support is experimental (prompt + edits only; payload shape not fully documented)` once
per experimental agent. The help text, docs, README and site show the same label.

### Stamping moves to `resolve` (task 12)
`cli._stamp`, `_blob_lines` and `_commit_has` move to `resolve.stamp(root, events, persist=True) -> int`,
with the same helpers private in `resolve`. `cli.cmd_why`, `cmd_log` and `cmd_stamp` call
`resolve.stamp(...)` and keep printing `stamped N edit(s)` in `cmd_stamp`. With `persist=False`,
`stamp` mutates only the in-memory `Event` objects and never calls `store.rewrite_all`. This respects
the layering rule (resolve depends on store and git, nothing imports cli) and lets the exporter stamp
without rewriting the developer's real store.

### Dogfood capture (environment step after task 06)
Today the hooks run the **installed** copy of gitmotive, not this branch:
- `~/.claude/settings.json` runs `~/.gitmotive/venv/bin/python -m gitmotive capture` with that venv's site-packages.
- `~/.omp/agent/settings.json` does the same with `--agent claude`.

Events captured that way carry no `agent` or `model`. After task 06 merges locally, the manager asks
the human to run these from the repo root:
```
sh install.sh --agent claude,omp --scope user
```
This reinstalls the venv from the branch, then upserts the user-scope hook commands so that omp gains
`--source omp`. Only events captured after this step have `agent` and `model`. The demo's default files
are chosen from files that tasks after this step edit (see below). Events from before the step legitimately
lack them, and the viewer shows `unknown`.

### Demo data (`scripts/export_demo.py` → `site/demo/data.json`, task 13)
A dev script that uses `gitmotive.store`, `gitmotive.resolve` and `gitmotive.hq` as a library and adds
no CLI command.

- **Revision:** always `HEAD`. There is no `--rev` flag, because `resolve.find` blames the working tree
  and reads line text from disk. The exporter aborts with exit 2 if any exported file has uncommitted
  changes (`git status --porcelain -- <files>` non-empty).
- **Files:** `--file` is repeatable. The defaults are `gitmotive/cli.py`, `gitmotive/adapters.py`,
  `scripts/gen_docs.py` and `site/demo/viewer-core.mjs`. Each of these is created or edited by a task
  that runs after the dogfood step (07, 08, 14, 15). Files that don't exist yet are skipped with a note on stderr.
- **Stamping:** events are read once with `store.read_all`, then `resolve.stamp(root, events,
  persist=False)` runs. The store file is never written (tested by comparing bytes before and after).
- **Lines:** each line comes from `resolve.find(root, file, n, events)`.
- **Prompts:** **only prompts referenced by an exported `match` are emitted.** Unreferenced prompts
  never reach the output.

Sanitisation applies to **emitted string fields only**: line `text`, prompt `text`, `reasoning`,
`session`, `author`, the `hq` fields and `files`.
- Absolute paths under `$HOME` become `~/…`.
- A path-like `session` becomes the first 8 characters of its basename without the extension.
- Pasted-content bodies (`<pasted_content …>…</pasted_content>`) become `[pasted content omitted]`.
- Prompts and reasoning are truncated to `--max-prompt-chars` (default 4000) with `…`.

**Per-record gate.** Each emitted prompt `text`, each `reasoning` and each `hq` block is run through
`audit_public.scan_text` (secret, host and denylist checks).
- When a field has a hit, the field's value becomes `[omitted: <check>]`, and a count per check goes to
  stderr (`omitted 3 field(s): secret=1 denylist=2`).
- Line `text` is source code at HEAD, which the tree audit already covers. Its hits are reported but not
  rewritten, and they are fatal (exit 1).
- After serialising, the **whole output string** is scanned again. If any high or medium hit survives,
  nothing is written and the exit code is 1.
- Without a denylist the exporter exits 2, unless `--no-denylist` is given.
- It warns when the output is over 1.5 MB.

### Site (`site/`)
- Plain static HTML, CSS and vanilla JS: no build step, no framework, no CDN, no third-party fonts.
- Pages:
  - `/` (`site/index.html`): the problem, how it works in 3 steps, the install command, the GitHub
    link, and a call to action into the demo.
  - `/demo/` (`index.html`, `viewer.css`, `viewer.js`, `viewer-core.mjs`, `data.json`)
  - `/docs/` (generated)
  - `/install.sh`
  - `404.html`
  - `DEMO_SCRIPT.md`, which is public and harmless. It is served as-is, and there is no rule that tries
    to hide it, because Pages `_redirects` cannot return 404.
- **Test-only files live outside `site/`** (`tests/js/viewer-core.test.mjs`, `tests/js/fixture.json`), so
  everything in `site/` is meant to be deployed.
- **Visual direction:** a terminal and diff aesthetic with monospaced code as the hero. A two-pane
  "blame gutter + intent panel" motif from the demo is reused on the home page. Dark is the default,
  with a light scheme through `prefers-color-scheme`, and there is one accent colour. No stock
  illustrations, no gradient-blob template look.
- **Accessibility:** landmarks, a skip link and focusable demo lines with arrow and j/k navigation.
  Enter opens the line's details and Escape returns. The detail panel is `aria-live="polite"`. Contrast
  is at least 4.5:1, and `prefers-reduced-motion` is respected.
- **Budget:** each page is at most 100 KB before `data.json`, and `data.json` is at most 1.5 MB.
- **Meta:** title, description, `og:*` (image `/assets/og.png` at 1200×630, url `https://gitmotive.tech/`),
  `twitter:card summary_large_image`, `/favicon.svg` plus `/favicon.ico`, and `theme-color`.
- **CSP** via `site/_headers`: `default-src 'self'; img-src 'self' data:; style-src 'self'; script-src
  'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'`.
  - No inline `<script>` and no `style=` attributes.
  - Generated HTML must **never** set `style` through markup or `setAttribute('style', …)`. Per-prompt
    colours are CSS classes `.p0` to `.p11` defined in `viewer.css`, chosen by `colorFor`, which returns
    a palette index.
- No analytics, cookies or third-party requests.

### Demo viewer behaviour (`site/demo/viewer.js`, task 14)
- **Loading:** the viewer fetches `data.json` and shows a file picker.
- **File table:** three columns: the gutter (short SHA, or `·` when there is no match), the line number
  and the code. Matched lines get the class `p{colorFor(prompt_id)}`.
- **Detail panel:** a click or Enter fills it with the prompt, the hq dereference if any (task title and
  goal), reasoning, session, agent, model (or `unknown` when null), timestamp, tool, commit, match
  reason, and sibling files. The timestamp is shown in local time, with ISO 8601 in `title`. A line
  with no match shows `none recorded`.
- **Deep link:** `#<file>:<line>` deep-links, and selecting a line updates the hash.
- **Rendering:** data-derived text goes through `textContent` only, and `escapeHtml` where a string is
  assembled.
- **Pure functions:** these live in `site/demo/viewer-core.mjs` and are tested with
  `node --test tests/js/viewer-core.test.mjs`. `tests/test_viewer.py` wraps that run and skips it when
  `node` is absent.

### Docs (`scripts/gen_docs.py` → `site/docs/index.html`, task 15)
Generated from four sources:
- `cli.USAGE` and `cli.__doc__`, for the CLI reference.
- `dataclasses.fields(store.Event)` plus `store.FIELD_DOCS`, for the data format.
- Hand-written `scripts/docs_src/{install,quickstart,adapters,data-format}.md`.
- A stdlib Markdown-subset renderer.

`--check` exits 1 when the committed output is stale. `tests/test_docs_sync.py` runs it.

### Site installer (`site/install.sh`, task 16)
POSIX sh with `set -eu`, wrapped in `main` and called on the last line.
- **Python:** checks for Python ≥ 3.10.
- **pipx present:** runs `pipx install "${GITMOTIVE_PIP_SPEC:-gitmotive}"`. pipx creates its own entry
  points, so no wrappers are written.
- **No pipx:** creates the venv `${GITMOTIVE_HOME:-~/.gitmotive}/venv`, pip-installs the same spec, and
  writes `gitmotive` and `git-motive` wrappers to `${GITMOTIVE_BIN:-~/.local/bin}`. **Wrappers are written
  in venv mode only.**
- **Finish:** prints the PATH hint and the next step. Any arguments are passed through to
  `gitmotive install`.

The repo-root `install.sh` stays as it is for clones.

### Deploy (config only, task 18)
- `site/_headers`: CSP and the other security headers, `text/plain` for `/install.sh`.
- `site/_redirects`: `/docs /docs/ 301`.
- `.github/workflows/deploy-site.yml`
  - Triggers: `push` to `main` with paths `site/**`, `scripts/gen_docs.py` and `scripts/docs_src/**`,
    plus `workflow_dispatch`.
  - Steps: checkout, Python 3.12, `gen_docs.py --check`, the site tests, then
    `cloudflare/wrangler-action@v3` with `pages deploy site --project-name=gitmotive --branch=main`.
  - Secrets: `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`.
  - The workflow does nothing until the human pushes and adds the secrets.
- `launch/DEPLOY.md`: the exact human steps.

**DNS (Cloudflare Pages).** An apex custom domain on Pages requires the zone to be on Cloudflare
nameservers.
- At the registrar: change the nameservers to the two Cloudflare assigns (placeholders
  `<ns1>.ns.cloudflare.com` and `<ns2>.ns.cloudflare.com`).
- In Cloudflare:
  - `CNAME @ gitmotive.pages.dev` (proxied, flattened at the apex).
  - `CNAME www gitmotive.pages.dev` (proxied).
  - Both hostnames added as Pages custom domains.
  - A Redirect Rule: host `www.gitmotive.tech` → `https://gitmotive.tech${uri}`, 301, keeping the
    query string.
- The apex serves the site directly.
- Vercel alternative with DNS kept at the registrar: `A @ 76.76.21.21` and `CNAME www cname.vercel-dns.com`.

### README and launch copy
- **README:** rewritten around the real CLI. It has the tagline, a GIF placeholder with the exact
  recording sequence, `pipx install gitmotive`, a quickstart, and a supported-agents table with a status
  column. It also links to gitmotive.tech.
- **Launch drafts:** `launch/show-hn.md`, `launch/product-hunt.md`, `launch/linkedin.md` and
  `launch/application.md`.
- All of these are covered by `tests/test_public_text.py`.

## Interfaces

Audit (dev script):
```
python3 scripts/audit_public.py [--tree] [--history] [--denylist PATH] [--allow PATH] [--json] [--root DIR]
  # neither scope flag -> both; --allow defaults to <root>/.audit-allow if present
  exit 0 no high/medium | 1 high/medium findings | 2 usage
```
Importable (tests and exporter insert `scripts/` on `sys.path`):
```
audit_public.load_denylist(path: str | None, root: Path) -> list[str] | None   # None = no denylist found
audit_public.scan_text(text: str, where: str, denylist: list[str] | None, checks: tuple[str, ...] = ("secret", "host", "denylist")) -> list[Finding]
audit_public.redact(text: str, denylist: list[str] | None) -> str
@dataclass Finding: check: str, severity: str ("high"|"medium"|"info"), where: str, commit: str | None, excerpt: str   # excerpt redacted, ≤120 chars
SEVERITY: dict[str, str]   # check id -> default severity, per the table above
```

CLI (`gitmotive/cli.py`):
```
gitmotive --version | -V           -> "gitmotive 0.1.0", exit 0            (new, task 08)
gitmotive help [cmd] | -h | --help -> docstring / one USAGE entry, exit 0   (new, task 08; bare `gitmotive` unchanged: help, exit 2)
gitmotive install [--agent claude|cursor|copilot|omp|all] [--scope repo|user]
    upserts hook entries (task 06); prints experimental notes for copilot/omp (task 08)
gitmotive capture [--agent A] [--event E] [--source S]   # --source new (task 06): product label overriding agent
USAGE: dict[str, tuple[str, str]]     # cmd -> (usage line, description)
EXPERIMENTAL: tuple[str, ...] = ("copilot", "omp")
why "edited" line: "  edited   {ts}  by {tool}  session {sess8}  [{why}]" + ("  via {agent}" if agent) + ("  model {model}" if model)
```
Hook command strings written by installers (repo scope; user scope prefixes `GITMOTIVE_STORE=user`):
```
claude : PYTHONPATH=<pkg> <python> -m gitmotive capture
cursor : PYTHONPATH=<pkg> <python> -m gitmotive capture --agent cursor --event <beforeSubmitPrompt|afterFileEdit>
copilot: PYTHONPATH=<pkg> <python> -m gitmotive capture --agent claude --source copilot
omp    : PYTHONPATH=<pkg> <python> -m gitmotive capture --agent claude --source omp
```

Store, adapters, capture, resolve:
```
store.Event.agent: Optional[str] = None     # "claude" | "cursor" | "copilot" | "omp" | None
store.Event.model: Optional[str] = None
store.FIELD_DOCS: dict[str, str]            # one entry per Event field
adapters.normalize(payload, agent=None, event=None, source=None) -> dict   # adds "agent": str, "model": str | None
capture._transcript_context(transcript_path, tool_use_id) -> tuple[str | None, str | None]   # (reasoning, model)
resolve.stamp(root: Path, events: list[store.Event], persist: bool = True) -> int           # task 12; replaces cli._stamp
```

Dev scripts:
```
python3 scripts/export_demo.py [--root DIR] [--file PATH ...] [--out site/demo/data.json] [--max-prompt-chars 4000] [--no-denylist]
    exit 0 written | 1 gate hit survived / source-line hit | 2 dirty files, no denylist, usage
python3 scripts/gen_docs.py [--check]
sh scripts/check_dist.sh
sh scripts/smoke_fresh.sh [--docker|--venv]
tests/_wheel.py: build_wheel() -> Path | None
```

Viewer core (`site/demo/viewer-core.mjs`):
```
export const PALETTE_SIZE = 12
export function indexData(data) -> { files: Map<path, file>, prompts: Map<id, prompt> }
export function colorFor(promptId) -> number            // 0..PALETTE_SIZE-1, stable per id; used as class "p<n>"
export function parseHash(hash) -> { file: string|null, line: number|null }   // splits on the LAST ':'
export function escapeHtml(s) -> string
export function detailModel(file, lineNo, idx) -> { kind: "none" } | { kind: "intent", prompt, reasoning, session, agent, model, ts, tool, commit, why, siblings, hq }
```

Site URLs: `/`, `/demo/`, `/demo/#<path>:<line>`, `/docs/`, `/install.sh`, `/DEMO_SCRIPT.md`,
`/favicon.svg`, `/favicon.ico`, `/assets/og.png`, `/404.html`.

## Data changes
- `Event` gains the optional fields `agent` and `model`. Existing JSONL stays readable and there is no
  migration.
- Hook commands for copilot/omp gain `--source`. Installers upsert existing entries.
- `pyproject.toml` changes as listed under Packaging.
- Root `.gitignore`: add `build/` (task 01) and `.audit-denylist` (task 02).
- `.hq/.gitignore` (tracked): add `audit-report*.md`, `history-rewrite-plan.md` and `deploy-readiness.md` (task 01).
- New committed `.audit-allow`, initially comments only (task 02).
- New committed `site/demo/data.json`:
```json
{
  "version": 1,
  "generated_at": "2026-12-01T12:00:00Z",
  "repo": "rvasqz86/gitmotive",
  "rev": "<40-hex HEAD>",
  "files": [
    {"path": "gitmotive/cli.py",
     "lines": [
       {"n": 1, "text": "…", "commit": "5934f9c1ab", "author": "rvasqz86", "date": "2026-11-09", "match": null},
       {"n": 42, "text": "…", "commit": "…", "author": "…", "date": "…",
        "match": {"edit_id": "a1b2c3d4e5f6", "prompt_id": "16d846335950", "why": "same commit, line text in edit",
                  "ts": 1794331334.96, "tool": "Edit", "agent": "claude", "model": "claude-opus-5-5",
                  "session": "01a1c67b", "commit": "…", "reasoning": "…"}}
     ]}
  ],
  "prompts": {
    "16d846335950": {"text": "…", "ts": 1794331334.96, "session": "01a1c67b",
                     "hq": {"kind": "implement", "task": ".hq/tasks/14-demo-viewer.md", "task_title": "…", "goal": "…", "round": 1},
                     "files": ["gitmotive/cli.py", "site/demo/viewer.js"]}
  }
}
```
  `prompts` contains only ids referenced by some `match.prompt_id`. `hq` is `null` for non-orchestrator
  prompts, and its fields mirror `hq.HqRef`. `agent` and `model` may be `null` for pre-dogfood-step
  events. Any field can hold `[omitted: <check>]`.

## Risks
- **Leaking denylist names or secrets through dogfood data.** The store already contains pasted
  orchestrator prompts and secret-shaped strings from earlier spec edits. Mitigations: only referenced
  prompts are exported, pasted-content stripping, the per-record gate, the whole-output rescan, and the
  denylist check in `test_public_text.py` over `site/demo/data.json`.
- **The tree audit self-matching on tests and on the scanner.** The concatenation rule and `.audit-allow`
  (reasoned entries only) prevent it, and `.hq/` text avoids literal secret shapes and private quads.
- **Known `.hq/` tree finding.** `.hq/spec-review.md` (round 1, written by the reviewer) quotes a full
  private IPv4 test address from the round-1 task text. The planner may not edit that file. Task 04 will
  report it as a medium `host` finding. Task 05 resolves it with either an approved `.audit-allow` entry
  (`.hq/spec-review.md host  # quotes a planned synthetic test address, not infrastructure`) or a manager
  edit that rewords the quote, whichever the human picks.
- **The history rewrite invalidates this branch.** It is proposed in task 04 and run by the human after
  the merge, followed by a force-push and a demo re-export, as listed in task 23's checklist.
- **No `model` in the demo** if the dogfood step is skipped, or if the implementer agent's hooks don't
  expose a model (omp payloads may not carry one). Task 23 requires a non-null `model` on at least one
  match per default file. If that is impossible, it stops with a Spec issue rather than fabricating data.
  See Open questions on the implementer kind.
- **setuptools versions.** `license` as an SPDX string plus `license-files` requires setuptools ≥ 77.
  The local install is 75.8. Wheel-building tests use isolated builds and skip when offline.
- **Hook command portability under pipx.** Paths are baked in at install time. The upsert means
  re-running `gitmotive install` heals them, and the docs say so.
- **Cursor payload drift and a live-session check that may not run.** Adapters stay tolerant. The live
  check is manual and its status is recorded.
- **The PyPI name could be taken.** Task 09 records the check, and a taken name is a Spec issue stop.
- **The apex domain on Cloudflare needs a nameserver move.** This is documented, along with the Vercel
  alternative.
- **The Docker smoke test needs network.** The venv variant installs offline from the built wheel.

## Test plan
- Runner (`.hq/runtime`): `for f in tests/test_*.py; do python3 "$f" || exit 1; done`. Plain scripts
  with `test_*` functions and a `__main__` runner. Helpers named `tests/_*.py` are not run directly.
- New tests, by task:
  - `test_repo_hygiene.py` (01)
  - `test_audit.py` (02): temp repos with concatenation-built planted secrets and IPs, a history-only
    secret, a synthetic denylist term `acme-widgets`, `.audit-allow` downgrade, severities, version
    strings not matched, `~/.local` not matched, oldest introducing commit, and redaction
  - `test_public_text.py` (03; extended in 20, 21 and 22)
  - `test_capture_model.py` (06): includes per-installer `agent` labels and upsert idempotence
  - `test_e2e_agents.py` (07)
  - `test_cli_meta.py` (08)
  - `test_packaging.py` (09): uses `_wheel.py`
  - `test_smoke.py` (10)
  - `test_site.py` (11+)
  - `test_stamp.py` (12): `persist=False` leaves the store bytes unchanged
  - `test_export_demo.py` (13)
  - `test_viewer.py` (14), wrapping `node --test tests/js/viewer-core.test.mjs`
  - `test_docs_sync.py` (15)
  - `test_site_install.py` (16)
  - `test_deploy_config.py` (18)
- Existing tests (`test_adapters.py`, `test_e2e.py`, `test_hq.py`) keep passing. They are updated only
  where the `edited` line format or `normalize` keys require it.
- Repo-level gate from task 05 onward: `python3 scripts/audit_public.py --tree --denylist .audit-denylist`
  exits 0. Tasks 20 and 23 re-assert it.
- Manual checks, recorded in task reports:
  - `sh scripts/check_dist.sh`
  - `sh scripts/smoke_fresh.sh --docker`
  - the live Cursor check (07)
  - a keyboard walkthrough of the site via a briefly run `python3 -m http.server -d site`, stopped afterwards

## Open questions
1. **`init`/`blame` wording versus the real CLI.** The brief's smoke test says "init in a sample repo …
   run `gitmotive blame`". The real CLI is:
   - `gitmotive install`, which wires the hooks (the brief's "init").
   - `git motive <file>:<line>`, or `gitmotive why <file>:<line>` (the brief's "blame").

   **Decision: use the real commands everywhere and add no `init`/`blame` aliases.** The architecture
   forbids inventing them, and the tagline contrasts `git blame` with `git motive`.
   `tests/test_public_text.py` enforces this outside `.hq/`. If you want a `gitmotive init` alias, it
   becomes a one-line follow-up task.
2. **Hosting: Cloudflare Pages (default) or Vercel.** Cloudflare needs gitmotive.tech's nameservers
   moved to Cloudflare to serve the apex directly. Vercel works with DNS kept at the registrar. Both are
   documented in `launch/DEPLOY.md`. Confirm before task 18.
3. **History rewrite timing.** Recommended: run the approved `git filter-repo` plan after this branch
   merges to `main` and before you flip the repo public. Then force-push and re-export the demo (task
   23's checklist).
4. **Analytics.** None ship. Say if you want a Plausible tag, and it becomes a follow-up behind the CSP.
5. **Personal details in public copy.** The README and application use your name and GitHub handle,
   plus the generic "built enterprise data platforms at large-scale orgs". The `pyproject.toml` author
   email becomes public on PyPI. Confirm.
6. **Local denylist file (needed before task 04).** Create `.audit-denylist` (gitignored) at the repo
   root, with the organisation names from `.hq/brief-source.md` one per line, plus any internal
   hostnames or repo names you know of. Alternatively, authorise the implementer to create it from
   `brief-source.md`. It stays gitignored either way.
7. **Dogfood reinstall (manager/human step after task 06).** From the repo root, run
   `sh install.sh --agent claude,omp --scope user`. It reinstalls `~/.gitmotive/venv` from this branch
   and upserts the user-scope hooks so new events carry `agent` and `model`, and omp is labelled `omp`.
   Without this step, the demo shows `model unknown` for every line, and task 23 stops.
8. **Implementer agent kind.** `model` comes reliably from Claude Code transcripts. If tasks 07, 08, 14
   and 15 run under omp and omp exposes no model, the demo's model field stays `unknown` for those lines.
   Recommended: run implementers as Claude Code (`kind_impl=claude`) for at least those tasks.
9. **Live Cursor verification.** The Cursor e2e tests use synthetic, documented payloads. If you have
   Cursor installed, the task 07 report records a live run. Otherwise Cursor ships as "supported
   (verified against documented payloads)". Say if you would rather label it experimental until a live
   check.

## Changes in round 2
- **Dogfood capture (blocker 1, manager note):**
  - Added the "Dogfood capture" design section and Open questions 7 and 8 (the human reinstall after task 06 touches `~/`, so no task does it).
  - Changed the demo's default files to files edited after that step.
  - Task 23 now requires a non-null `model` on at least one match per default file, accepts null `model` on earlier events, and stops with a Spec issue rather than fabricating.
- **Suppression (blocker 2):**
  - Added the self-match rule (fixtures and scanner prefixes built by concatenation) and a committed `.audit-allow` (reason required; entries downgraded to `info`).
  - Secret regexes now require a token body, so prose mentioning prefixes doesn't match.
  - The exporter gate applies to emitted fields only.
  - Removed the literal private IP from task text.
- **Per-record gate:** a field with a hit becomes `[omitted: <check>]`, with counts on stderr. Exit 1 only if a hit survives in the serialised output, or for source-line hits.
- **`--rev`:** removed. The export is HEAD only and aborts on dirty exported files.
- **`_stamp` side effect:** new task 12 moves stamping to `resolve.stamp(root, events, persist=True)`. The exporter uses `persist=False`, which is tested by comparing store bytes. This also fixes the "nothing imports cli" layering rule the old exporter design broke.
- **Prompts scope:** only prompts referenced by a match are exported. `test_public_text.py` runs the denylist check on `data.json` but skips the command check there.
- **Agent labels:** added `--source` to capture, written by the copilot and omp installers. Installers upsert existing gitmotive entries, with tests per installer and for idempotence.
- **Packaging:** dropped the License classifier and set `setuptools>=77`. Wheel tests use isolated builds through `tests/_wheel.py` and skip when a build is impossible.
- **`_redirects` 404:** dropped the rule. `DEMO_SCRIPT.md` is public, and the test files moved to `tests/js/`, so `site/` holds only deployable files. Task 19 lists the deployed files.
- **`test_public_text.py` dependency:** now created early in its own task 03 (depends on 02). Site, docs, README and launch tasks depend on it transitively; task 05 only runs the remediation.
- **`.hq/` tracking (manager note):** `.hq/` is committed. Its `.gitignore` keeps `brief-source.md`, `runtime.log*` and the report files local (task 01). The audit and the denylist check cover `.hq/**`, and the human-stop git-status criteria now refer to a tracked `.hq/`.
- **Severities:** added a per-check severity table. `path` now means other users' home paths only. The IPv4 rule matches only bounded full private dotted quads, and the hostname rule requires a label.
- **Site installer:** wrappers are written in venv mode only (spec and task aligned).
- **Smoke test:** checks `commit` in `events.jsonl` right after `git commit`, before `log`/`why`.
- **CSP colours:** `colorFor` returns a palette index mapped to classes `.p0` to `.p11`. Generated HTML never sets inline styles.
- **History introducing commit:** this is the oldest commit (`--reverse`, first line).
- **Cursor live check:** a manual item in task 07's report, plus Open question 9.
- **Known finding:** recorded that `.hq/spec-review.md` quotes the old literal test IP. Tasks 04 and 05 handle it through `.audit-allow` or a manager edit.
- **Renumbering:** tasks are now 01–23. New: 03 (public-text guard) and 12 (stamping refactor). Human stops are 04 and 19.

### Carried from spec review round 2 (minor, max rounds reached; manager will apply)
- Dogfood reinstall verification: after `sh install.sh`, the manager asserts `'source' in inspect.signature(gitmotive.adapters.normalize).parameters` in `~/.gitmotive/venv/bin/python` and greps `~/.omp/agent/settings.json` for `--source omp`. If the check fails, rerun with `pip install --force-reinstall`. The result is logged.
- Dogfood is a snapshot taken at the reinstall. Later `capture.py`/`adapters.py` edits don't reach the dogfood hooks. Implementers must run in this checkout, not a worktree, because the user-scope store is keyed by absolute path.
- The private IP quoted in `.hq/spec-review.md` was reworded before the Gate 1 commit, so no `.audit-allow` entry is needed for it.
- Task 13 (export demo): include the `path` check (medium) in both the per-record gate and the whole-output rescan.
- Task 18 (deploy config): add `gitmotive/**` to the workflow `paths` so a CLI change regenerates the docs.
