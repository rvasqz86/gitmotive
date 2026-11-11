# Deploying gitmotive.tech

The site in `site/` is static and deploys to Cloudflare Pages through
`.github/workflows/deploy-site.yml`. The workflow does nothing useful until the steps below are
done: it runs on pushes to `main` that touch `site/**`, `gitmotive/**`, `scripts/gen_docs.py` or
`scripts/docs_src/**`, and on manual dispatch.

## 1. One-time Cloudflare setup

1. Create a direct-upload Pages project (not a Git connection) named `gitmotive`. Either option
   works; the workflow replaces the content on the first deploy. A Direct Upload project cannot
   later be switched to Git integration.

   **Option A (dashboard).**
   1. In the Cloudflare dashboard, go to the **Workers & Pages** page.
   2. Select **Create application** > **Get started** > **Drag and drop your files**.
   3. Enter your project name in the provided field and drag and drop your assets. Use the name
      `gitmotive` and any placeholder file.
   4. Select **Deploy site**.

   **Option B (CLI)**, if the dashboard labels differ from the above:

   ```
   npx wrangler login
   npx wrangler pages project create
   ```

   The CLI prompts for the project name (`gitmotive`) and the production branch (`main`).
2. **My Profile** → **API Tokens** → **Create Token** → **Custom token** with the permission
   **Account › Cloudflare Pages › Edit**, scoped to your account. Copy the token.
3. Note your **Account ID** (dashboard sidebar, or the URL `dash.cloudflare.com/<account-id>`).
4. GitHub → the repo → **Settings** → **Secrets and variables** → **Actions** →
   **New repository secret**, twice:
   - `CLOUDFLARE_API_TOKEN` = the token from step 2
   - `CLOUDFLARE_ACCOUNT_ID` = the ID from step 3

## 2. Move DNS to Cloudflare

An apex custom domain on Pages requires the zone to be on Cloudflare nameservers.

1. Cloudflare dashboard → **Add a domain** → `gitmotive.tech` (Free plan). Cloudflare assigns two
   nameservers.
2. At the registrar, replace the nameservers with the two Cloudflare assigned:

   ```
   <ns1>.ns.cloudflare.com
   <ns2>.ns.cloudflare.com
   ```

3. Wait until Cloudflare shows the zone as **Active**.

## 3. Records and custom domains

Do not add any DNS records by hand. Attach the custom domains first and let Cloudflare create the
records.

> **Warning:** adding a CNAME manually before associating the domain in Pages makes the domain
> fail to resolve with a 522 error. Always attach the custom domain in Pages first.

1. **Workers & Pages** → select the `gitmotive` project → **Custom domains** → **Set up a domain**
   → enter `gitmotive.tech` → **Continue**. Cloudflare creates the DNS record itself.
2. Repeat for `www.gitmotive.tech`.
3. In the `gitmotive.tech` zone → **DNS** → **Records**, check that the end state is these two
   records (created by Cloudflare, not by you):

   | Type  | Name | Target               | Proxy   |
   |-------|------|----------------------|---------|
   | CNAME | @    | gitmotive.pages.dev  | Proxied |
   | CNAME | www  | gitmotive.pages.dev  | Proxied |

   ```
   CNAME @ gitmotive.pages.dev    (proxied; Cloudflare flattens it at the apex)
   CNAME www gitmotive.pages.dev  (proxied)
   ```

The apex `gitmotive.tech` can only be attached because the zone is on Cloudflare nameservers in
the same account as the Pages project (section 2).

Sources (read 2026-11-11):
<https://developers.cloudflare.com/pages/get-started/direct-upload/>,
<https://developers.cloudflare.com/pages/configuration/custom-domains/>.

## 4. www → apex redirect

Zone → **Rules** → **Redirect Rules** → **Create rule**:

- When incoming requests match: hostname equals `www.gitmotive.tech`
- Then: **Dynamic** redirect to the expression `concat("https://gitmotive.tech", http.request.uri.path)`,
  i.e. `https://gitmotive.tech${uri}`
- Status code: **301**
- **Preserve query string**: on

The apex `gitmotive.tech` serves the site directly; it is not a redirect. Only `www` redirects.

## 5. First deploy

Push to `main` (or run the workflow from the **Actions** tab with **Run workflow**). Manual runs
must be started from `main`: the deploy job is skipped on any other branch, because it always
publishes as the production (`main`) deployment.

## 6. Verify

```
dig +short gitmotive.tech
curl -sI https://www.gitmotive.tech/ | grep -i location
curl -sI https://gitmotive.tech/ | head -1
curl -s https://gitmotive.tech/install.sh | head -3
```

Expect Cloudflare IPs from `dig`, `location: https://gitmotive.tech/` from the second command,
`HTTP/2 200` from the third (the apex serves the site directly; no `location:` header), and the
first lines of the shell installer (not HTML) from the fourth.

## Alternative: Vercel, DNS kept at the registrar

If you would rather not move nameservers, deploy `site/` to Vercel instead and add these records at
the registrar:

```
A @ 76.76.21.21
CNAME www cname.vercel-dns.com
```

The Cloudflare workflow and `site/_headers`/`site/_redirects` are Cloudflare Pages specific; on
Vercel the equivalent headers and redirects go in `vercel.json`.
