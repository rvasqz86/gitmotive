# Task 28: Switch deploy to Cloudflare Pages Git integration
Status: done
Type: fix
Scope: deploy
Depends on: 27
## Goal
The human will connect the Pages project to GitHub with Cloudflare's Git integration instead of direct upload. Cloudflare then deploys every push: `main` goes to production and other branches become previews. The GitHub Action must stop deploying, but keep the checks.

Source: https://developers.cloudflare.com/pages/get-started/git-integration/ (updated Apr 21, 2026). **Fetch this page yourself and quote its labels verbatim.** Do not invent UI labels. If a label you need (for example the build output field) isn't on the page, phrase it generically, as in "set the build output directory to `site`", and don't bold an unverified label. Labels already read from the page:
- "In the Cloudflare dashboard, go to the **Workers & Pages** page."
- "Select **Create application** > **Pages** > **Connect to Git**."
- "Select **GitHub** or **GitLab**. If prompted, authenticate with your Git provider."
- "Once you have selected a Git repository, select **Install & Authorize** and **Begin setup**. You can then customize your deployment in **Set up builds and deployments**."
- "select **Save and Deploy**."
- "You cannot switch to Direct Upload later".

## Changes
1. **Workflow.** Rename `.github/workflows/deploy-site.yml` to `.github/workflows/site-checks.yml` with `git mv`, then edit it with the Edit tool.
   - Set `name: site-checks`.
   - Triggers: `push` on `[main]` with the same four `paths`, plus `pull_request` with the same paths, plus `workflow_dispatch`.
   - Permissions: `contents: read` only.
   - One job, `checks`, with the steps checkout, setup-python 3.12, `gen_docs.py --check`, and the same site test loop.
   - Remove the wrangler step, the secrets, the `deployments` permission and the main-only `if` guard; the job deploys nothing, so the guard is no longer needed.
   - Update the header comment: Cloudflare deploys through the Git integration, and this workflow only checks.
2. **`launch/DEPLOY.md`**
   - Intro: Cloudflare Pages deploys from GitHub through the Git integration, and the workflow only runs checks.
   - Section 1: replace the direct-upload options, the API token, the account ID and the GitHub secrets with:
     - the Git integration click path (quoted)
     - selecting the `gitmotive` repo
     - project name `gitmotive`, so the hostname is `gitmotive.pages.dev`
     - production branch `main`
     - framework preset None, an empty build command, and build output directory `site`
     - Save and Deploy
     - a note that a Git-connected project cannot switch to Direct Upload later
     - a note that the repo can stay private; Cloudflare's GitHub app needs access to it
   - Sections 2–4 (nameservers, custom domains, the www redirect): unchanged.
   - Section 5, "First deploy": Save and Deploy triggers the first build, and after that every push to `main` deploys. Other branches and PRs get preview URLs. Remove the "manual runs must be started from `main`" text.
   - Section 6, verify: unchanged.
   - The Vercel alternative's last paragraph: say `_headers`/`_redirects` are Cloudflare Pages specific. Don't mention the workflow deploying.
   - Sources line: add the Git integration URL. Remove the `npx wrangler pages project create` option.
3. **`tests/test_deploy_config.py`**: point `WORKFLOW` at `site-checks.yml`.
   - Assert that the triggers include push to `[main]`, `pull_request` and `workflow_dispatch`, with the four paths on both push and pull_request.
   - Assert that the permissions block is exactly `contents: read`.
   - Assert the step order without wrangler.
   - Assert that the workflow has no `secrets.` reference and no `wrangler` text.
   - For DEPLOY.md, drop the asserts on "Account › Cloudflare Pages › Edit", CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, "Secrets and variables", "direct-upload", "Drag and drop your files", "npx wrangler pages project create" and "started from `main`".
   - Assert that "Connect to Git", "Install & Authorize", "Save and Deploy" and "`site`" are present.
   - Assert that "CLOUDFLARE_API_TOKEN" and "Upload assets" are absent.
   - Keep all the other existing asserts: domains, 522, redirect, verify, Vercel.
   - Update the module docstring.
4. **`launch/CHECKLIST.md`**
   - Change the Done entry to `.github/workflows/site-checks.yml`.
   - Step 2: drop the "may fail until the Cloudflare secrets" note.
   - Step 4: describe the Git integration, without secrets.
   - Keep the wording minimal.
5. **Other references.** Grep the tracked files, excluding `.hq/`, for `deploy-site`, `CLOUDFLARE_API_TOKEN` and `wrangler`, and fix any you find in the same spirit. Don't touch `.hq/`.

Edit files with the Edit/Write tools (plus `git mv` for the rename). Don't commit.

## Acceptance criteria
- [ ] The workflow has no deploy step and no secrets, and runs the checks on push/PR
- [ ] DEPLOY.md section 1 follows the Git integration doc verbatim; other sections are unchanged apart from section 5 and the small edits listed
- [ ] The full test command passes: `export GITMOTIVE_AUDIT_DENYLIST=.hq/audit-denylist; for f in tests/test_*.py; do python3 "$f" || exit 1; done`
- [ ] `python3 scripts/audit_public.py --tree --denylist .hq/audit-denylist` exits 0
## Tests
test_deploy_config.py as in item 3, plus the full suite.
## Spec issue
none (spec amended by the manager: "Deploy amendment (task 28)")

## Implementation notes (round 1)
- I fetched the Git integration doc (page says "Last updated Apr 21, 2026"). The six labels listed above match it verbatim. I also used these phrases from the page: "**Production branch**", "leave the **Build command** field blank", "Your **project name** will be used to generate your project's hostname" (paraphrased, no bold), and "Both private and public repositories are supported."
- The page doesn't name the framework-preset or build-output fields as bold labels, so they're written generically: "Framework preset: None" and "Set the build output directory to `site`".
- Workflow: renamed with `git mv` to `.github/workflows/site-checks.yml` and rewritten as listed (name, push/PR/dispatch triggers with the same paths, `contents: read`, one `checks` job, four steps). I also removed the `concurrency: group: deploy-site` block. It existed only to serialise deploys, and the old name would have left a stale `deploy-site` reference.
- DEPLOY.md: rewrote the intro, section 1 and section 5, and edited the Vercel paragraph. In section 3's Sources line, I replaced the direct-upload URL with the Git integration URL instead of adding a second link, because nothing in the doc describes Direct Upload any more. Sections 2, 3 (other than Sources), 4 and 6 are unchanged.
- Tests: in `tests/test_deploy_config.py`, I added a `_block` helper for indented YAML blocks and new checks that:
  - the trigger keys are exactly push, pull_request and workflow_dispatch;
  - push and pull_request each have the four paths;
  - permissions are exactly `contents: read`;
  - there is a single `checks` job with no `if:`, and exactly four steps in order;
  - there is no `secrets.`, `wrangler` or `deployments:`;
  - the old workflow file is gone.

  The DEPLOY.md asserts were updated as listed, with an extra check for the Git integration source URL.
- CHECKLIST.md: changed the Done entry path, removed the step 2 secrets note, and changed step 4 to describe the Git integration.
- Other references: `git grep` (excluding `.hq/`) now finds `deploy-site`, `CLOUDFLARE_API_TOKEN` and `wrangler` only in the tests' own negative asserts and in `site/demo/data.json`. That file is captured dogfood event data, generated by `scripts/export_demo.py`, so it quotes old file contents historically. I left it unedited, because hand-editing generated demo data would break its provenance. Regenerating it is a separate task if the manager wants that.
- Verification: the full test command exits 0 across all 19 files. `python3 scripts/audit_public.py --tree --denylist .hq/audit-denylist` exits 0 with high=0, medium=0 and info=2; both info hits are pre-existing `.hq/` paths.
