# Task 29: Allow Cloudflare Web Analytics through the CSP
Status: done
Type: feat
Scope: site
Depends on: 28
## Goal
The human will turn on Cloudflare Web Analytics for the Pages project. Pages then injects a beacon script into every HTML page. The current CSP in `site/_headers` would block it, so the only change is to allow the beacon's two origins and nothing else. Don't add any analytics tag to the HTML; Cloudflare injects it.

## Changes
1. `site/_headers`, `/*` block. The CSP becomes exactly:
   `default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self' https://static.cloudflareinsights.com; connect-src 'self' https://cloudflareinsights.com; base-uri 'none'; frame-ancestors 'none'`
   Leave everything else in the file unchanged.
2. `tests/test_site.py`: update the `CSP` constant to match. If any test asserts "no third-party origins" in the headers, allow exactly these two origins. The HTML files must still contain no third-party script or URL.
3. `launch/DEPLOY.md`: add a short section after the custom domains/redirect steps, before "First deploy" or after it, whichever reads best. Call it "Web Analytics (optional)". It says:
   - The project's dashboard has a setting to enable Cloudflare Web Analytics. It is cookieless, and Pages injects the beacon on the next deploy.
   - The CSP in `site/_headers` already allows `static.cloudflareinsights.com` and `cloudflareinsights.com`.
   - **Do not bold or invent exact UI labels.** The dashboard labels have differed from the docs before. Say "in the Pages project's settings, enable Web Analytics" and link https://developers.cloudflare.com/pages/how-to/web-analytics/. Fetch that page; if it gives a click path, quote it verbatim.
   - Verify: after a deploy, `curl -s https://gitmotive.tech/ | grep -c cloudflareinsights` prints 1 or more.
   Update the DEPLOY.md asserts in `tests/test_deploy_config.py` only if needed (for example, assert that "cloudflareinsights" is present).
4. Grep the public text (README.md, site/, launch/) for any claim of "no analytics", "no tracking" or "no cookies". If you find one, reword it to say the site uses Cloudflare Web Analytics, which is cookieless. Don't touch `.hq/`.

Edit files with the Edit/Write tools. Don't commit.

## Acceptance criteria
- [ ] The CSP is exactly as in item 1, and the HTML has no third-party script
- [ ] The DEPLOY.md section exists and invents no UI labels
- [ ] The full test command passes: `export GITMOTIVE_AUDIT_DENYLIST=.hq/audit-denylist; for f in tests/test_*.py; do python3 "$f" || exit 1; done`
- [ ] `python3 scripts/audit_public.py --tree --denylist .hq/audit-denylist` exits 0
## Tests
test_site.py CSP constant; test_deploy_config.py if needed; the full suite.
## Spec issue
none (spec Open question 4 resolved by the manager)

## Implementation notes (round 1)
- `site/_headers`: CSP in the `/*` block is now exactly the string from item 1; nothing else changed.
- `tests/test_site.py`: `CSP` constant updated. No other test asserted "no third-party origins" in `_headers`; the HTML external-URL checks are unchanged, so the HTML still may contain no third-party script/URL (grep of site/*.html for cloudflareinsights: none).
- `launch/DEPLOY.md`: new "Web Analytics (optional)" section between section 5 (First deploy) and 6 (Verify). It uses the plain "in the Pages project's settings, enable Web Analytics" wording and then quotes Cloudflare's click path verbatim from https://developers.cloudflare.com/pages/how-to/web-analytics/ (fetched 2026-11-13; bold is the page's own). The page states the snippet is added "on the next deployment". Includes the `curl ... | grep -c cloudflareinsights` verify step.
- Note for reviewer: that Cloudflare page does not itself mention cookies; "cookieless" is per the task brief (Cloudflare's Web Analytics product docs describe it as not using client-side state like cookies), not quoted from the linked page.
- `tests/test_deploy_config.py`: asserts the section heading, "cloudflareinsights", the doc URL and the verify command.
- Item 4: grepped README.md, site/, launch/ for no analytics/no tracking/no cookies claims. Only hit is README "Privacy": "The CLI makes no network calls and has no telemetry", which is about the CLI, not the site, so left unchanged.
- Full test command: all pass. `audit_public.py --tree --denylist .hq/audit-denylist`: exit 0 (high=0 medium=0 info=2, both pre-existing in .hq/).
