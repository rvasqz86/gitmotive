# Launch checklist

Everything below "Done" is on the `feat/tech-launch-site` branch. Nothing on this branch has been
pushed, published, deployed or made public. "You do by hand" is the remaining work, in order.

## Done

- **Build output untracked** and ignored: `.gitignore`
- **Public-release audit scanner** (working tree and full history): `scripts/audit_public.py`,
  `tests/test_audit.py`
- **Public-text guard** for docs, site and launch copy: `tests/test_public_text.py`
- **Working-tree audit fixes** applied; `audit_public.py --tree` exits 0
- **History audited, no rewrite:** `audit_public.py --history` finds no secret, denylist, host or
  transcript hits; only `build/` and `dist/` copies of gitmotive's own code remain in two early
  commits (accepted, harmless). No history rewrite or force-push is needed.
- **Agent and model on every event**, `--source` labels, upserting installers:
  `gitmotive/adapters.py`, `gitmotive/capture.py`, `install.sh`, `tests/test_capture_model.py`
- **Claude Code and Cursor proven end to end** through the installed hooks: `tests/test_e2e_agents.py`
- **CLI `--version`, help, single-source usage, experimental labels**: `gitmotive/cli.py`,
  `tests/test_cli_meta.py`
- **PyPI-ready packaging** and a dist dry run: `pyproject.toml`, `scripts/check_dist.sh`,
  `tests/test_packaging.py`
- **Fresh-machine smoke test**: `scripts/smoke_fresh.sh`, `scripts/smoke_inner.sh`, `tests/test_smoke.py`
- **Stamping moved into `resolve.stamp`**: `gitmotive/resolve.py`, `tests/test_stamp.py`
- **Site home page**: `site/index.html`, `site/assets/site.css`, `site/assets/og.png`, `site/favicon.svg`,
  `site/404.html`
- **Demo data exporter** with a per-record sanitisation gate: `scripts/export_demo.py`,
  `tests/test_export_demo.py`
- **Demo data regenerated** from this branch's dogfood events, every default file with a model match:
  `site/demo/data.json`
- **Live demo viewer**: `site/demo/index.html`, `site/demo/viewer.js`, `site/demo/viewer-core.mjs`,
  `site/demo/viewer.css`
- **Docs generated from the real CLI**: `site/docs/index.html`, `scripts/gen_docs.py`, `scripts/docs_src/`
- **One-line installer** at `gitmotive.tech/install.sh`: `site/install.sh`
- **60-second demo script**: `site/DEMO_SCRIPT.md`
- **Cloudflare Pages deploy config**: `.github/workflows/deploy-site.yml`, `site/_headers`,
  `site/_redirects`, `launch/DEPLOY.md`
- **Deploy readiness review**: `.hq/deploy-readiness.md`
- **README for the public launch**: `README.md`
- **Launch post drafts**: `launch/show-hn.md`, `launch/product-hunt.md`, `launch/linkedin.md`
- **Grant application draft**: `launch/application.md`
- **This checklist**: `launch/CHECKLIST.md`

## You do by hand

1. **Review and merge this branch to `main` locally.**
   ```
   git checkout main
   git merge --no-ff feat/tech-launch-site
   ```
2. **Push `main` to GitHub (human only).** A normal push, no force:
   ```
   git push origin main
   ```
   The deploy workflow may fail on this push until the Cloudflare secrets from step 4 exist; that is
   expected, and step 4 re-runs it.
3. **Flip the repository public (human only).**
   ```
   gh repo edit rvasqz86/gitmotive --visibility public --accept-visibility-change-consequences
   ```
4. **Cloudflare and DNS.** Do sections 1–5 of `launch/DEPLOY.md` (Pages project and API token, GitHub
   secrets, nameservers, records and custom domains, the `www` redirect, then the first deploy from
   `main`), and run the checks in its section 6.
5. **Build, check and upload to PyPI.** Do this before recording: the demo script runs
   `pipx install gitmotive`.
   ```
   sh scripts/check_dist.sh
   python -m twine upload dist/*
   ```
6. **Record the demo** following `site/DEMO_SCRIPT.md` and add it as `docs/demo.gif`
   (`git add docs/demo.gif && git commit -m "docs: add demo recording" && git push origin main`).
7. **Fill the placeholders in `launch/application.md`** (the bracketed fields such as stars, installs
   and design partners) and submit it by **Dec 8, 2026** (deadline Dec 15, 2026).
8. **Post the launch drafts**: `launch/show-hn.md`, `launch/product-hunt.md`, `launch/linkedin.md`.
