# Task 11: Site skeleton and home page
Status: done
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

## Implementation notes (round 1)
- **Design.** The tagline is set as a diff hunk (`@@ -1 +1,2 @@`). "git blame tells you who." is the context line and "git motive tells you why." is the added `+` line. Under it sits the spec's two-pane motif: a blame gutter for `src/fetch.py` with line 42 selected, next to the `git motive` intent panel. The intent panel uses the real `cmd_why` output format, with fields from the README example.
  - The problem section shows a diff whose deleted lines are the prompt, reasoning and session.
  - Steps are a real `<ol>`, so they are numbered.
  - One accent colour (amber). Dark is the default; light comes from `prefers-color-scheme: light`.
  - System mono and sans stacks only, with no web fonts.
  - The only motion is a caret that blinks 5 times after the hero command. Reduced motion turns it off.
- **Files.** `site/index.html`, `site/404.html`, `site/assets/site.css`, `site/favicon.svg`, `site/favicon.ico` (32×32 ICO wrapping a PNG), `site/assets/og.png` (1200×630), `site/_headers`, `tests/test_site.py`.
  - og.png and the ico were rendered once with headless Chromium plus a stdlib ICO wrapper. Neither generator is committed.
- **Size.** index.html + site.css + favicon.svg = 23,263 bytes (budget 102,400).
- **Contrast.** The colour-pair comment in site.css lists 18 pairs; the lowest is 5.21:1 (light accent on the highlight). `test_css` recomputes every listed ratio, fails anything below 4.5, fails a stated ratio that is off by more than 0.05, and fails a listed colour that `:root` doesn't declare.
- **Tests.** `tests/test_site.py` checks every `.html` under `site/` for:
  - lang, title, main, the skip link, favicon and viewport
  - no inline script, `<style>`, `style=` or `on*=` attributes
  - the external-URL allowlist: only the GitHub repo and https://gitmotive.tech, including meta `content` URLs and CSS `url()`
  - internal links and fragments (`/demo/` and `/docs/` count as pending only while their directories are missing)
  - the per-page 100 KB limit

  It also checks the home meta tags, the copy (tagline, problem, three steps in order, both install commands, the links), the agent rows (Copilot and oh-my-pi experimental; Claude Code and Cursor not), the CSS media queries and contrast, the budget, the PNG/ICO sizes and `_headers`. Self-tests feed the checkers synthetic bad pages.
- **Copy-check location.** The copy assertions live in `test_site.py` (`test_home_copy`, `test_home_agents_labelled`) because `test_public_text.py` isn't in this task's file list. `test_public_text.py` already passes over `site/` (command check and denylist).
- **Manual check.**
  - Port 8000 was already taken on this machine by an unrelated listener, so I briefly ran `python3 -m http.server -b 127.0.0.1 -d site 18431` and stopped it after each check.
  - Rendering: screenshots at 1440 and 390 px in dark and light, plus the 404 page.
  - Keyboard (Playwright-driven Tab walk): skip link → logo → nav → hero buttons → scrollable code panes → CTA → footer, all with a visible focus outline. Skip link + Enter lands on `#main`.
  - No horizontal page scroll at 360 px, no console errors and no failed requests.
- **Example data.** The hero uses a made-up author ("alex") and model string, not real dogfood data. The live demo (task 14) shows the real data.
- **Full suite and tree audit.** The full test command passes, and `scripts/audit_public.py --tree` exits 0.

## Implementation notes (round 2)
- **[major] aria-label on `pre`.** Every focusable scroll `pre` now has `role="region"`: the blame pane, the intent pane, the lost-context diff and the 404 terminal. The `curl` install `pre` (index.html:118) was focusable with no name at all, so it now has `role="region"` and `aria-label="Install script command"`. `markup_problems` now fails `aria-label` on `pre`/`div`/`span` (and the other generic-role tags: `b i u s small code p`) when there is no `role`. The new self-test `test_checker_flags_aria_label_without_role` covers the bad cases (pre, div, span) and the good ones (`pre` with a role, `nav`, `a`).
- **[minor] Intent panel = real `cmd_why` output.** After the `$ git motive src/fetch.py:42` command line, the panel is now exactly what `cmd_why` prints:
  - `src/fetch.py:42`, then `  |` and the line text
  - 2-space indented fields
  - `[same commit, line text in edit]  via claude  model …` on the `edited` line
  - the reasoning wrapped by `_wrap` at 88 columns
  - siblings indented by 4

  `test_home_intent_panel_is_real_cmd_why_output` runs the real `cli.cmd_why`. It patches only the data sources (`store.repo_root`/`read_all`, `_stamp`, `resolve.find`/`siblings`, `hq.parse`) and asserts the panel text equals stdout byte for byte. If the CLI format changes, this test fails. A mutation check (widening the `commit` gap by 2 spaces) made it fail as expected.
- **[minor] Steps list.** `<ol class="steps" role="list">`. The copy test regex is updated to match.
- **[minor] 404 og/twitter tags.** Removed. `test_404_has_no_share_tags` asserts there are no `og:`/`twitter:` meta tags and that `robots=noindex` stays.
- **[minor] Fact grid.** It is now one terminal-style panel: the same border and panel background as the code panes, in mono, with lowercase accent keys in a 15ch column (2-space indent, like the `cmd_why` fields) and values in `--fg`. Below 30rem it stacks key over value. Both colour pairs (`--accent`/`--fg` on `--panel`) are already in the contrast comment. The 3-column grid rule is gone.
- **Process note.** While editing, a bad slice briefly wrote a corrupted `site.css`. I recovered it exactly (the inserted block was a fixed string, so I split it back out and verified the result) before making the real edit. The final CSS is the round-1 file plus the `.facts` changes.
- **Checks.**
  - The full test command passes.
  - `scripts/audit_public.py --tree` exits 0.
  - Budget: 23,835 bytes.
  - Re-rendered with headless Chromium (temporary `http.server` on 127.0.0.1:18431, stopped afterwards): 1440 px dark and 390 px light. The facts panel and intent panel render correctly, with no horizontal page scroll.
  - Tab order is unchanged by these fixes (only roles and labels were added; tabindex is unchanged).
