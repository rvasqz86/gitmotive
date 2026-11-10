# Task 18: Cloudflare Pages deploy config, GitHub Action and DNS instructions
Status: todo
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
