# Task 27: Make DEPLOY.md match Cloudflare's documented UI
Status: done
Type: fix
Scope: launch
Depends on: 18
## Goal
The human followed `launch/DEPLOY.md` and found that its dashboard labels don't match Cloudflare's UI: there is no "Pages" tab and no "Upload assets" button. Section 3 also has the human add CNAMEs by hand before attaching the custom domains, and Cloudflare's docs warn this gives a 522. Rewrite those parts so they follow Cloudflare's current docs **verbatim**. Don't invent labels.

Sources (read on 2026-11-11):
- https://developers.cloudflare.com/pages/get-started/direct-upload/ (updated Apr 21, 2026)
- https://developers.cloudflare.com/pages/configuration/custom-domains/ (updated Nov 11, 2026)

## Changes
1. `launch/DEPLOY.md` section 1, step 1: replace it with two options, plus a one-line note that a Direct Upload project cannot later switch to Git integration. Keep the project name `gitmotive` and the words "direct-upload".
   - **Option A (dashboard)**, quoted from the Direct Upload doc:
     1. "In the Cloudflare dashboard, go to the **Workers & Pages** page."
     2. "Select **Create application** > **Get started** > **Drag and drop your files**."
     3. "Enter your project name in the provided field and drag and drop your assets." Use the name `gitmotive` and any placeholder file.
     4. "Select **Deploy site**."
   - **Option B (CLI)**, used when the dashboard labels differ:
     ```
     npx wrangler login
     npx wrangler pages project create
     ```
     The CLI prompts for the project name (`gitmotive`) and the production branch (`main`).
2. `launch/DEPLOY.md` section 3, "Records and custom domains". Reorder it so the human never adds CNAMEs by hand. Keep "(proxied" at least twice and keep the strings `CNAME @ gitmotive.pages.dev` and `CNAME www gitmotive.pages.dev`, now framed as the expected result.
   - First: **Workers & Pages** → select the `gitmotive` project → **Custom domains** → **Set up a domain** → enter `gitmotive.tech` → **Continue**. Repeat for `www.gitmotive.tech`. Cloudflare creates the DNS records itself.
   - Then: in the zone's **DNS** → **Records**, check that the end state is the two proxied CNAMEs.
   - Add a warning quoting the doc: adding a CNAME manually before associating the domain in Pages makes the domain fail to resolve with a 522.
   - Note: the apex requires the zone to be on Cloudflare nameservers on the same account. Section 2 already covers this; reference it.
3. `launch/DEPLOY.md`: add a short "Sources" line at the end of section 1 or 3 with the two URLs above.
4. `tests/test_deploy_config.py`, `test_deploy_md_content`:
   - Assert that "Create application", "Drag and drop your files" and "npx wrangler pages project create" are present.
   - Assert that "Set up a domain" and "522" are present.
   - Assert that "Upload assets" is absent.
   - Keep all the other existing asserts passing.
5. `launch/CHECKLIST.md` step 4: if its wording now contradicts DEPLOY.md, adjust it minimally. Otherwise leave it.

Don't touch the workflow, `site/`, or any other section of DEPLOY.md. Edit files with the Edit/Write tools, not shell redirection.

## Acceptance criteria
- [ ] DEPLOY.md section 1 and section 3 match the quoted doc steps
- [ ] The full test command passes: `export GITMOTIVE_AUDIT_DENYLIST=.hq/audit-denylist; for f in tests/test_*.py; do python3 "$f" || exit 1; done`
- [ ] `python3 scripts/audit_public.py --tree --denylist .hq/audit-denylist` exits 0
## Tests
test_deploy_config.py as in item 4, plus the full suite.
## Spec issue
none (spec amended by the manager for this task)

## Implementation notes (round 1)
- `launch/DEPLOY.md` §1 step 1: replaced the "Create → Pages → Upload assets" line with an intro
  (direct-upload, name `gitmotive`, one-line note that Direct Upload can't later switch to Git
  integration), Option A (the four Direct Upload doc steps, quoted as given in this task, bold
  labels kept), and Option B (`npx wrangler login` / `npx wrangler pages project create`, prompts
  for `gitmotive` and `main`). Steps 2–4 unchanged.
- `launch/DEPLOY.md` §3: now opens with "don't add records by hand" plus a quoted 522 warning;
  numbered steps: Custom domains → Set up a domain → `gitmotive.tech` → Continue, repeat for
  `www.gitmotive.tech`, then check DNS → Records for the two proxied CNAMEs (table and the
  `CNAME @/www gitmotive.pages.dev (proxied…)` block kept, framed as the expected result).
  Added the apex/nameserver note pointing to section 2 and a "Sources (read 2026-11-11)" line with
  both URLs at the end of §3. No other sections touched.
- I did not re-fetch the Cloudflare pages; the wording comes from the quotes in this task.
- `tests/test_deploy_config.py::test_deploy_md_content`: added asserts for "Create application",
  "Drag and drop your files", "npx wrangler pages project create", "Set up a domain", "522", and
  that "Upload assets" is absent. All existing asserts unchanged ("(proxied" still appears 2×).
- `launch/CHECKLIST.md` step 4 left as is: it only says "records and custom domains", which still
  matches the section title.
- Full test command: all pass. `audit_public.py --tree --denylist .hq/audit-denylist`: exit 0
  (high=0 medium=0 info=2, both pre-existing in `.hq/`).
