# Deploying gitmotive.tech

The site in `site/` is static. Cloudflare Pages deploys it from GitHub through its Git
integration: every push to `main` goes to production, and other branches get preview deployments.
`.github/workflows/site-checks.yml` deploys nothing; it only runs the site checks on pushes to
`main` and pull requests that touch `site/**`, `gitmotive/**`, `scripts/gen_docs.py` or
`scripts/docs_src/**`, and on manual dispatch.

## 1. One-time Cloudflare setup

Connect a Pages project to the GitHub repo. No API token and no GitHub secrets are needed.

1. In the Cloudflare dashboard, go to the **Workers & Pages** page.
2. Select **Create application** > **Pages** > **Connect to Git**.
3. Select **GitHub** or **GitLab**. If prompted, authenticate with your Git provider. Choose
   **GitHub**.
4. Select the `gitmotive` repository.
5. Once you have selected a Git repository, select **Install & Authorize** and **Begin setup**. You
   can then customize your deployment in **Set up builds and deployments**:
   - Project name: `gitmotive`. The project name is used to generate the hostname, so the site
     is served at `gitmotive.pages.dev`.
   - **Production branch**: `main`.
   - Framework preset: None. The site has no build step, so leave the **Build command** field
     blank.
   - Set the build output directory to `site`.
6. Select **Save and Deploy**.

Notes:

- You cannot switch to Direct Upload later: a Git-connected project stays Git-connected.
- The repo can stay private. Both private and public repositories are supported; Cloudflare's
  GitHub app only needs access to the `gitmotive` repo (granted at **Install & Authorize**).

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
<https://developers.cloudflare.com/pages/get-started/git-integration/>,
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

**Save and Deploy** in section 1 triggers the first build. After that, every push to `main`
deploys to production. Other branches and pull requests get preview URLs.

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

`site/_headers` and `site/_redirects` are Cloudflare Pages specific; on
Vercel the equivalent headers and redirects go in `vercel.json`.
