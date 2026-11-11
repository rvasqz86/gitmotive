# Deploying gitmotive.tech

The site in `site/` is static and deploys to Cloudflare Pages through
`.github/workflows/deploy-site.yml`. The workflow does nothing useful until the steps below are
done: it runs on pushes to `main` that touch `site/**`, `gitmotive/**`, `scripts/gen_docs.py` or
`scripts/docs_src/**`, and on manual dispatch.

## 1. One-time Cloudflare setup

1. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** → **Upload assets**
   (direct-upload mode, not a Git connection). Name the project `gitmotive`. Upload any
   placeholder file to create it; the workflow replaces it on the first deploy.
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

In the `gitmotive.tech` zone → **DNS** → **Records**:

| Type  | Name | Target               | Proxy   |
|-------|------|----------------------|---------|
| CNAME | @    | gitmotive.pages.dev  | Proxied |
| CNAME | www  | gitmotive.pages.dev  | Proxied |

```
CNAME @ gitmotive.pages.dev    (proxied; Cloudflare flattens it at the apex)
CNAME www gitmotive.pages.dev  (proxied)
```

Then **Workers & Pages** → `gitmotive` → **Custom domains** → add both `gitmotive.tech` and
`www.gitmotive.tech`. If Pages offers to create or update the DNS record for a hostname, accept
it; the end state must be the two proxied CNAMEs above.

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
