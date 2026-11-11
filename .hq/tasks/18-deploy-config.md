# Task 18: Cloudflare Pages deploy config, GitHub Action and DNS instructions
Status: done
Type: chore
Scope: deploy
Depends on: 15, 16, 17
## Goal
Add inert deploy configuration and exact human instructions (spec "Deploy (config only)"). This task deploys nothing, pushes nothing and changes no DNS.
## Files
- .github/workflows/deploy-site.yml (create)
- site/_redirects (create: `/docs /docs/ 301` only)
- launch/DEPLOY.md (create)
- tests/test_deploy_config.py (create)
## Acceptance criteria
- [ ] Workflow:
  - Triggers: `on.push.branches: [main]`, `paths: ['site/**', 'scripts/gen_docs.py', 'scripts/docs_src/**']`, and `workflow_dispatch`
  - `permissions: contents: read, deployments: write`
  - Steps: checkout, setup-python 3.12, `python3 scripts/gen_docs.py --check`, `for f in tests/test_site*.py tests/test_docs_sync.py tests/test_viewer.py; do python3 "$f" || exit 1; done`, then `cloudflare/wrangler-action@v3` with `apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}`, `accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}` and `command: pages deploy site --project-name=gitmotive --branch=main`
- [ ] `launch/DEPLOY.md`:
  - one-time Cloudflare setup: a Pages project `gitmotive` in direct-upload mode, an API token with "Account › Cloudflare Pages › Edit", and where to add the two repo secrets
  - the nameserver change at the registrar (placeholders `<ns1>.ns.cloudflare.com` and `<ns2>.ns.cloudflare.com`)
  - the records `CNAME @ gitmotive.pages.dev` (proxied) and `CNAME www gitmotive.pages.dev` (proxied), with both hostnames added as Pages custom domains
  - the www → `https://gitmotive.tech${uri}` 301 Redirect Rule, keeping the query string
  - verification commands: `dig +short gitmotive.tech`, `curl -sI https://www.gitmotive.tech/ | grep -i location`, `curl -s https://gitmotive.tech/install.sh | head -3`
  - a statement that the apex serves the site directly, not a redirect
  - the Vercel alternative (`A @ 76.76.21.21`, `CNAME www cname.vercel-dns.com`)
- [ ] This task runs no wrangler, gh, git push, or DNS or API calls
## Tests
`tests/test_deploy_config.py`: line-level checks on the workflow (trigger branch, paths, exactly those two secrets, the project name), and that every `site/_redirects` line has 3 fields with a status in {301, 302, 303, 307, 308, 200}.
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none

- [ ] Workflow `paths` include `gitmotive/**` as well as `site/**` (spec review r2 minor)

## Implementation notes (round 1)
- Created `.github/workflows/deploy-site.yml`: push to `main` with paths `site/**`, `gitmotive/**`, `scripts/gen_docs.py`, `scripts/docs_src/**`, plus `workflow_dispatch`; `permissions: contents: read, deployments: write`; steps checkout@v4, setup-python@v5 (3.12), `gen_docs.py --check`, the site test loop, then `cloudflare/wrangler-action@v3` with the two secrets and `pages deploy site --project-name=gitmotive --branch=main`. Added a non-cancelling `concurrency` group so two pushes can't race deploys.
- Created `site/_redirects` with the single rule `/docs /docs/ 301`.
- Created `launch/DEPLOY.md` covering every acceptance bullet (Pages direct-upload project, token permission, secrets location, nameserver placeholders, both proxied CNAMEs + custom domains, www→apex 301 Redirect Rule with Preserve query string, verification commands, apex-serves-directly statement, Vercel alternative). Code spans avoid `gitmotive <word>` invocations so `test_public_text.py` stays green.
- Created `tests/test_deploy_config.py` (stdlib only, line-level): triggers/branch/exact paths list, permissions block, step order, exactly the two secrets, project name, a `_redirects` checker with self-tests (3 fields, status in {301,302,303,307,308,200}), and DEPLOY.md content checks.
- Full test command passes. No wrangler, gh, git push, DNS or API calls were made.

## Implementation notes (round 2)
- [major] Guarded `jobs.deploy` with `if: github.ref == 'refs/heads/main'` so a `workflow_dispatch` from another branch is skipped instead of publishing as production; `test_workflow_triggers` asserts the guard line under `deploy:`. DEPLOY.md §5 now says manual runs must be started from `main`.
- [minor] DEPLOY.md §6 adds `curl -sI https://gitmotive.tech/ | head -1` with expected `HTTP/2 200` and no `location:`; `test_deploy_md_content` asserts the command, `HTTP/2 200`, and the §5 "started from `main`" note.
- [minor] DEPLOY.md §3 adds: if Pages offers to create/update the DNS record, accept it; end state must be the two proxied CNAMEs.
- [minor] `concurrency` block left as is (reviewer: no change needed).
- Full `test=` command passes. No wrangler, gh, git push, DNS or API calls.
