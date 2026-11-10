# Task 11: Site skeleton and home page
Status: todo
Type: feat
Scope: site
Depends on: 03, 08
## Goal
Create the static site in `site/`: the home page, a shared stylesheet, favicons, the OG image, a 404 page and the security headers, following the spec's "Site" section. Cover the problem, how it works in 3 steps, the install command, the GitHub link and a CTA into `/demo/`. Use a distinctive terminal/diff design, not a template look.
## Files
- site/index.html (create)
- site/404.html (create)
- site/assets/site.css (create)
- site/favicon.svg (create)
- site/favicon.ico (create: 32×32 binary)
- site/assets/og.png (create: 1200×630 binary; any generator script must be stdlib-only or a one-off not committed)
- site/_headers (create: the spec CSP, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, and `/install.sh` served as `Content-Type: text/plain; charset=utf-8`)
- tests/test_site.py (create)
## Acceptance criteria
- [ ] `index.html` has a `<title>`, a meta description, `og:title`, `og:description`, `og:image` = `https://gitmotive.tech/assets/og.png`, `og:url` = `https://gitmotive.tech/`, `twitter:card` = `summary_large_image`, `theme-color`, `<link rel="icon" href="/favicon.svg">`, `lang="en"`, a skip link and `<main>`
- [ ] Copy:
  - the tagline "git blame tells you who. git motive tells you why."
  - the problem: AI writes more code than reviewers can absorb, and the why is lost when the session ends
  - three steps: install, `gitmotive install --agent claude`, `git motive path/to/file.py:42`
  - `pipx install gitmotive` and `curl -fsSL https://gitmotive.tech/install.sh | sh`
  - links to https://github.com/rvasqz86/gitmotive, `/demo/` and `/docs/`
- [ ] Agents listed with Copilot and oh-my-pi marked experimental
- [ ] No inline `<script>`, no `style=` attributes, and no `<style>` blocks. No external `src`/`href` other than the GitHub repo and gitmotive.tech. No third-party requests or analytics
- [ ] site.css handles `prefers-color-scheme` and `prefers-reduced-motion`; a CSS comment lists the colour pairs and their contrast ratios, each ≥ 4.5:1
- [ ] index.html, site.css and favicon.svg together total ≤ 100 KB
- [ ] Manual check recorded: briefly ran `python3 -m http.server -d site 8000`, checked rendering and keyboard navigation, then stopped the server
## Tests
`tests/test_site.py` (`html.parser`) checks:
- the meta tags
- the external-URL allowlist
- no inline scripts or styles
- the budget
- internal links resolve to files under `site/` (`/demo/` and `/docs/` are allowed as pending only while those directories don't exist)
- every `.html` under `site/` (this picks up later pages automatically)

`tests/test_public_text.py` covers the copy.
Run: `for f in tests/test_*.py; do python3 "$f" || exit 1; done`
## Spec issue
none
