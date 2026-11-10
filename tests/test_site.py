"""Static site checks (site/): meta tags, CSP-safe markup, external-URL allowlist, internal
links, the size budget, colour contrast, headers and binary assets.

Every `.html` under site/ is checked, so later pages are picked up automatically. The checkers
are plain functions over strings so the self-tests can feed them synthetic pages.
"""
from __future__ import annotations

import html
import posixpath
import re
import struct
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

ORIGIN = "https://gitmotive.tech"
REPO = "https://github.com/rvasqz86/gitmotive"
PENDING_DIRS = ("/demo/", "/docs/")  # allowed as link targets only until they exist
BUDGET = 100 * 1024
CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
       "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
GENERIC_TAGS = ("pre", "div", "span", "b", "i", "u", "s", "small", "code", "p")
URL_ATTRS = ("href", "src", "srcset", "action", "poster", "data", "formaction")


# --- parsing -------------------------------------------------------------------------------

class Page(HTMLParser):
    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict]] = []
        self.ids: set[str] = set()
        self.inline_scripts = 0
        self.style_blocks = 0
        self.style_attrs = 0
        self.title = ""
        self.text_parts: list[str] = []
        self._in: list[str] = []
        self._script_has_src = False
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        self.tags.append((tag, a))
        if "id" in a:
            self.ids.add(a["id"])
        if "style" in a:
            self.style_attrs += 1
        if tag == "style":
            self.style_blocks += 1
        if tag == "script":
            self._script_has_src = "src" in a
            if not self._script_has_src:
                self.inline_scripts += 1
        if tag not in ("meta", "link", "br", "img", "input", "hr", "source"):
            self._in.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self._in and self._in[-1] == tag:
            self._in.pop()

    def handle_endtag(self, tag):
        if tag in self._in:
            while self._in and self._in.pop() != tag:
                pass

    def handle_data(self, data):
        if "title" in self._in:
            self.title += data
        if "script" in self._in and self._script_has_src and data.strip():
            self.inline_scripts += 1  # <script src=…>code</script> still runs nothing, but forbid
        self.text_parts.append(data)

    @property
    def text(self) -> str:
        return re.sub(r"\s+", " ", "".join(self.text_parts))

    def find(self, tag, **want) -> list[dict]:
        return [a for t, a in self.tags if t == tag and all(a.get(k) == v for k, v in want.items())]

    def meta(self, key: str) -> str | None:
        for t, a in self.tags:
            if t == "meta" and (a.get("name") == key or a.get("property") == key):
                return a.get("content")
        return None


def html_pages() -> list[Path]:
    return sorted(SITE.rglob("*.html"))


def page(rel: str) -> Page:
    return Page((SITE / rel).read_text(encoding="utf-8"))


# --- checkers ------------------------------------------------------------------------------

def markup_problems(p: Page) -> list[str]:
    out = []
    if p.inline_scripts:
        out.append(f"{p.inline_scripts} inline <script>")
    if p.style_blocks:
        out.append(f"{p.style_blocks} <style> block(s)")
    if p.style_attrs:
        out.append(f"{p.style_attrs} style= attribute(s)")
    for t, a in p.tags:
        for k in a:
            if k.startswith("on"):
                out.append(f"inline handler {k}= on <{t}>")
        # these map to the generic role, where ARIA 1.2 prohibits aria-label: the name is dropped
        if t in GENERIC_TAGS and "aria-label" in a and not a.get("role"):
            out.append(f"aria-label on <{t}> without a role")
    return out


def page_basics(p: Page) -> list[str]:
    out = []
    if not any(t == "html" and a.get("lang") == "en" for t, a in p.tags):
        out.append('missing <html lang="en">')
    if not p.title.strip():
        out.append("missing <title>")
    if not p.find("main"):
        out.append("missing <main>")
    skip = [a for t, a in p.tags if t == "a" and a.get("href", "").startswith("#")]
    if not skip or skip[0]["href"][1:] not in p.ids or "skip" not in skip[0].get("class", ""):
        out.append("first in-page link is not a skip link to an existing id")
    if not any(a.get("rel") == "icon" and a.get("href") == "/favicon.svg" for a in p.find("link")):
        out.append('missing <link rel="icon" href="/favicon.svg">')
    if not p.find("meta", name="viewport"):
        out.append("missing viewport meta")
    return out


def urls_in(p: Page) -> list[str]:
    urls = []
    for t, a in p.tags:
        for k in URL_ATTRS:
            if k in a:
                urls += [u.split()[0] for u in a[k].split(",")] if k == "srcset" else [a[k]]
    return [u.strip() for u in urls if u.strip()]


def external_ok(url: str) -> bool:
    s = urlsplit(url)
    if not s.scheme and not url.startswith("//"):
        return True  # relative, root-relative or a fragment
    if s.scheme in ("mailto",):
        return False
    if url.startswith("//") or s.scheme not in ("http", "https"):
        return False
    if s.scheme != "https":
        return False
    full = f"{s.scheme}://{s.netloc}{s.path}"
    if s.netloc == "gitmotive.tech":
        return True
    return full == REPO or full.startswith(REPO + "/")


def external_problems(p: Page) -> list[str]:
    bad = [u for u in urls_in(p) if not external_ok(u)]
    # meta content URLs (og:image, og:url) must be on our own origin
    for t, a in p.tags:
        c = a.get("content", "")
        if t == "meta" and re.match(r"(?i)[a-z]+:", c) and "://" in c and not c.startswith(ORIGIN + "/"):
            bad.append(c)
    return [f"external URL not allowed: {u}" for u in bad]


def css_external_problems(css: str) -> list[str]:
    out = []
    for m in re.finditer(r"url\(\s*['\"]?([^'\")]+)", css):
        if re.match(r"(?i)(https?:)?//", m.group(1)):
            out.append(f"external url() in css: {m.group(1)}")
    if re.search(r"@import", css):
        out.append("@import in css")
    return out


def resolve_internal(url: str, page_path: Path, site: Path = SITE) -> Path | None:
    """The file under site/ that `url` serves, or None for external / fragment-only links."""
    s = urlsplit(url)
    if s.scheme or url.startswith("//"):
        if s.netloc != "gitmotive.tech":
            return None
        path = s.path or "/"
    else:
        path = s.path
        if not path:
            return None
        if not path.startswith("/"):
            base = page_path.parent.relative_to(site).as_posix()
            joined = posixpath.normpath("/" + ("" if base == "." else base + "/") + path)
            path = joined + ("/" if path.endswith("/") and joined != "/" else "")
    target = site / path.lstrip("/")
    if path.endswith("/"):
        target = target / "index.html"
    return target


def link_problems(p: Page, page_path: Path, site: Path = SITE) -> list[str]:
    out = []
    for u in urls_in(p):
        if u.startswith("#"):
            if u[1:] and u[1:] not in p.ids:
                out.append(f"fragment {u} has no matching id")
            continue
        target = resolve_internal(u, page_path, site)
        if target is None:
            continue
        if target.is_file():
            frag = urlsplit(u).fragment
            if frag and target == page_path and frag not in p.ids:
                out.append(f"fragment {u} has no matching id")
            continue
        path = urlsplit(u).path or "/"
        if path in PENDING_DIRS and not (site / path.strip("/")).exists():
            continue  # pending: filled in by a later task
        out.append(f"internal link does not resolve: {u}")
    return out


def _lum(hexcol: str) -> float:
    h = hexcol.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


PAIR = re.compile(r"(--[\w-]+)\s+(#[0-9a-fA-F]{6})\s+on\s+(--[\w-]+)\s+(#[0-9a-fA-F]{6})\s+([\d.]+):1")


def contrast_problems(css: str) -> list[str]:
    comment = next((c for c in re.findall(r"/\*.*?\*/", css, re.S) if "contrast" in c.lower()), "")
    pairs = PAIR.findall(comment)
    if not pairs:
        return ["no colour-pair contrast comment"]
    out = []
    for fg_name, fg, bg_name, bg, stated in pairs:
        actual = contrast(fg, bg)
        if actual < 4.5:
            out.append(f"{fg_name} {fg} on {bg_name} {bg}: {actual:.2f}:1 < 4.5:1")
        if abs(actual - float(stated)) > 0.05:
            out.append(f"{fg_name} on {bg_name}: comment says {stated}, actual {actual:.2f}")
    # every documented colour must be the value the stylesheet actually declares
    declared = {}
    for block in re.findall(r":root\s*\{([^}]*)\}", css):
        for name, val in re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})", block):
            declared.setdefault(name, set()).add(val.lower())
    for fg_name, fg, bg_name, bg, _ in pairs:
        for name, val in ((fg_name, fg), (bg_name, bg)):
            if val.lower() not in declared.get(name, set()):
                out.append(f"comment lists {name} {val}, not declared in :root")
    return out


def png_size(data: bytes) -> tuple[int, int]:
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    return struct.unpack(">II", data[16:24])


def ico_sizes(data: bytes) -> list[tuple[int, int]]:
    reserved, kind, n = struct.unpack("<HHH", data[:6])
    assert reserved == 0 and kind == 1 and n >= 1, "not an ICO"
    out = []
    for i in range(n):
        w, h = struct.unpack("<BB", data[6 + 16 * i: 8 + 16 * i])
        out.append((w or 256, h or 256))
    return out


# --- self-tests (synthetic pages) ----------------------------------------------------------

GOOD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width"><title>t</title>
<link rel="icon" href="/favicon.svg"><link rel="stylesheet" href="/assets/site.css"></head>
<body><a class="skip" href="#main">Skip</a><main id="main"><p>x</p></main></body></html>"""


def test_checker_accepts_clean_page():
    p = Page(GOOD)
    assert markup_problems(p) == [] and page_basics(p) == [] and external_problems(p) == []


def test_checker_flags_inline_script_style_and_handlers():
    bad = GOOD.replace("<p>x</p>", '<p style="color:red" onclick="x()">x</p><script>alert(1)</script>'
                                   '<style>p{}</style><script src="/a.js"></script>')
    probs = markup_problems(Page(bad))
    assert any("inline <script>" in s for s in probs), probs
    assert any("<style>" in s for s in probs), probs
    assert any("style=" in s for s in probs), probs
    assert any("onclick" in s for s in probs), probs
    assert markup_problems(Page(GOOD.replace("</main>", '</main><script src="/a.js"></script>'))) == []


def test_checker_flags_aria_label_without_role():
    bad = GOOD.replace("<p>x</p>", '<pre tabindex="0" aria-label="code"><code>x</code></pre>'
                                   '<div aria-label="d">y</div><span aria-label="s">z</span>')
    probs = markup_problems(Page(bad))
    for tag in ("pre", "div", "span"):
        assert any(f"aria-label on <{tag}>" in s for s in probs), probs
    ok = GOOD.replace("<p>x</p>", '<pre tabindex="0" role="region" aria-label="code"><code>x</code></pre>'
                                  '<nav aria-label="n"></nav><a href="/" aria-label="home">h</a>')
    assert markup_problems(Page(ok)) == [], markup_problems(Page(ok))


def test_checker_flags_missing_basics():
    bad = GOOD.replace(' lang="en"', "").replace("<title>t</title>", "").replace(
        '<main id="main">', '<div id="main">').replace("</main>", "</div>")
    probs = page_basics(Page(bad))
    assert any("lang" in s for s in probs) and any("title" in s for s in probs), probs
    assert any("<main>" in s for s in probs), probs
    assert any("skip link" in s for s in page_basics(Page(GOOD.replace('href="#main"', 'href="#nope"'))))


def test_external_allowlist():
    ok = [REPO, REPO + "/issues", "https://gitmotive.tech/install.sh", "/demo/", "#main", "x.css"]
    bad = ["https://github.com/someone/else", "https://github.com/rvasqz86/gitmotive-evil",
           "http://gitmotive.tech/", "//cdn.example.com/x.js", "https://fonts.googleapis.com/css",
           "https://evil.example/gitmotive.tech", "javascript:alert(1)"]
    assert all(external_ok(u) for u in ok), [u for u in ok if not external_ok(u)]
    assert not any(external_ok(u) for u in bad), [u for u in bad if external_ok(u)]
    p = Page(GOOD.replace("</head>", '<meta property="og:image" content="https://cdn.x/og.png"></head>'))
    assert external_problems(p), "meta content on a foreign origin must be flagged"
    assert css_external_problems("a{background:url(https://x/y.png)} @import 'z.css';")
    assert css_external_problems("a{background:url(data:image/png;base64,AA)}") == []


def test_internal_links_and_pending_dirs():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        site = Path(d)
        (site / "assets").mkdir()
        (site / "assets" / "site.css").write_text("")
        (site / "favicon.svg").write_text("")
        idx = site / "index.html"
        body = GOOD.replace("<p>x</p>", '<a href="/demo/">d</a><a href="/docs/">d</a>'
                                        '<a href="/missing.html">m</a><a href="#nope">n</a>')
        idx.write_text(body)
        probs = link_problems(Page(body), idx, site)
        assert probs == ["internal link does not resolve: /missing.html",
                         "fragment #nope has no matching id"], probs
        (site / "demo").mkdir()  # the directory exists now, so /demo/ must resolve to a file
        probs = link_problems(Page(body), idx, site)
        assert "internal link does not resolve: /demo/" in probs, probs
        (site / "demo" / "index.html").write_text(GOOD)
        assert "internal link does not resolve: /demo/" not in link_problems(Page(body), idx, site)


def test_contrast_checker():
    assert round(contrast("#000000", "#ffffff"), 2) == 21.0
    css = ":root{--a:#777777;--b:#ffffff}\n/* contrast\n --a #777777 on --b #ffffff 4.48:1 */"
    probs = contrast_problems(css)
    assert any("< 4.5:1" in s for s in probs), probs
    css2 = ":root{--a:#000000;--b:#ffffff}\n/* contrast\n --a #000000 on --b #ffffff 9.00:1 */"
    assert any("comment says" in s for s in contrast_problems(css2))
    css3 = ":root{--a:#111111;--b:#ffffff}\n/* contrast\n --a #000000 on --b #ffffff 21.00:1 */"
    assert any("not declared" in s for s in contrast_problems(css3))


# --- the real site -------------------------------------------------------------------------

def test_site_exists():
    for rel in ("index.html", "404.html", "assets/site.css", "favicon.svg", "favicon.ico",
                "assets/og.png", "_headers"):
        assert (SITE / rel).is_file(), f"missing site/{rel}"


def test_every_page_markup_basics_and_links():
    pages = html_pages()
    assert pages, "no html pages under site/"
    probs = []
    for path in pages:
        rel = path.relative_to(SITE)
        p = Page(path.read_text(encoding="utf-8"))
        for s in markup_problems(p) + page_basics(p) + external_problems(p) + link_problems(p, path):
            probs.append(f"site/{rel}: {s}")
        if path.stat().st_size > BUDGET:
            probs.append(f"site/{rel}: {path.stat().st_size} bytes > {BUDGET}")
    assert not probs, "\n".join(probs)


def test_home_meta():
    p = page("index.html")
    assert p.title.strip()
    assert p.meta("description")
    assert p.meta("og:title") and p.meta("og:description")
    assert p.meta("og:image") == f"{ORIGIN}/assets/og.png", p.meta("og:image")
    assert p.meta("og:url") == f"{ORIGIN}/", p.meta("og:url")
    assert p.meta("twitter:card") == "summary_large_image"
    assert re.fullmatch(r"#[0-9a-fA-F]{6}", p.meta("theme-color") or ""), p.meta("theme-color")
    assert any(a.get("href") == "/favicon.ico" for a in p.find("link", rel="icon"))


def test_home_copy():
    p = page("index.html")
    t = p.text
    for s in ("git blame tells you who.", "git motive tells you why.",
              "pipx install gitmotive", "curl -fsSL https://gitmotive.tech/install.sh | sh",
              "gitmotive install --agent claude", "git motive path/to/file.py:42",
              "more code than reviewers can absorb", "When the session ends, it is gone"):
        assert s in t, f"missing copy: {s!r}"
    # the three steps are an ordered list, in order: install, hook up, ask
    steps = re.search(r'<ol class="steps" role="list">(.*?)</ol>', (SITE / "index.html").read_text(), re.S)
    assert steps, "no ordered steps list"
    body = html.unescape(re.sub(r"<[^>]+>", "", steps.group(1)))
    order = [body.find("pipx install gitmotive"), body.find("gitmotive install --agent claude"),
             body.find("git motive path/to/file.py:42")]
    assert -1 not in order and order == sorted(order), order
    hrefs = {a.get("href") for a in p.find("a")}
    for h in (REPO, "/demo/", "/docs/"):
        assert h in hrefs, f"missing link to {h}"


def intent_panel_text() -> str:
    src = (SITE / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<pre[^>]*aria-label="git motive output[^"]*"[^>]*><code>(.*?)</code></pre>', src, re.S)
    assert m, "intent panel not found"
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))


def test_home_intent_panel_is_real_cmd_why_output():
    """The hero's intent panel must be exactly what `git motive src/fetch.py:42` prints."""
    import contextlib
    import datetime as dt
    import io
    import os
    sys.path.insert(0, str(ROOT))
    from gitmotive import cli, hq, resolve, store

    text = intent_panel_text()
    cmd, _, shown = text.partition("\n")
    assert cmd == "$ git motive src/fetch.py:42", cmd

    local = lambda s: dt.datetime.strptime(s, "%Y-%m-%d %H:%M").timestamp()
    prompt = store.Event(kind="prompt", session="3f9a2c1e" + "0" * 24, ts=local("2026-10-29 06:18"),
                         id="p1", prompt="add retry with exponential backoff to fetch()")
    edit = store.Event(kind="edit", session=prompt.session, ts=local("2026-10-29 06:19"), id="e1",
                       file="src/fetch.py", tool="Edit", prompt_id="p1", agent="claude",
                       model="claude-sonnet-4-5", commit="134d8dd9e6" + "a" * 30,
                       reasoning="Wrapping the call in a retry loop; 3 attempts with backoff since "
                                 "the upstream flakes under load.")
    bl = resolve.BlameInfo(commit=edit.commit, orig_file="src/fetch.py", orig_line=42, author="alex",
                           author_time=int(local("2026-10-29 06:30")), summary="add retry")
    match = resolve.Match(edit=edit, prompt=prompt, score=150, why="same commit, line text in edit")
    root = Path(os.getcwd())
    patches = [
        (store, "repo_root", lambda *a, **k: root),
        (store, "read_all", lambda *a, **k: [prompt, edit]),
        (cli, "_stamp", lambda *a, **k: 0),
        (resolve, "find", lambda *a, **k: (bl, "            time.sleep(2 ** attempt)", [match])),
        (resolve, "siblings", lambda *a, **k: ["src/fetch.py", "src/http_errors.py",
                                                "tests/test_fetch.py"]),
        (hq, "parse", lambda *a, **k: None),
    ]
    saved = [(m, n, getattr(m, n)) for m, n, _ in patches]
    out = io.StringIO()
    try:
        for m, n, f in patches:
            setattr(m, n, f)
        with contextlib.redirect_stdout(out):
            rc = cli.cmd_why(["src/fetch.py:42"])
    finally:
        for m, n, f in saved:
            setattr(m, n, f)
    assert rc == 0, rc
    assert shown == out.getvalue().rstrip("\n"), f"panel:\n{shown}\n---\ncmd_why:\n{out.getvalue()}"


def test_404_has_no_share_tags():
    p = page("404.html")
    assert p.meta("robots") == "noindex"
    for t, a in p.tags:
        if t == "meta":
            key = a.get("property", "") or a.get("name", "")
            assert not key.startswith(("og:", "twitter:")), key


def test_home_agents_labelled():
    src = (SITE / "index.html").read_text(encoding="utf-8")
    rows = {html.unescape(re.sub(r"<[^>]+>", " ", m)).split()[0]: re.sub(r"<[^>]+>", " ", m)
            for m in re.findall(r"<tr>(.*?)</tr>", src, re.S)}
    want = {"Claude": False, "Cursor": False, "GitHub": True, "oh-my-pi": True}
    for first, experimental in want.items():
        assert first in rows, f"agent row starting {first!r} missing; rows: {list(rows)}"
        assert ("Experimental" in rows[first]) == experimental, rows[first]
    assert "Copilot" in rows["GitHub"]


def test_css():
    css = (SITE / "assets" / "site.css").read_text(encoding="utf-8")
    assert "prefers-color-scheme" in css
    assert "prefers-reduced-motion" in css
    probs = contrast_problems(css) + css_external_problems(css)
    assert not probs, "\n".join(probs)


def test_budget():
    total = sum((SITE / f).stat().st_size for f in ("index.html", "assets/site.css", "favicon.svg"))
    assert total <= BUDGET, f"index.html + site.css + favicon.svg = {total} bytes > {BUDGET}"


def test_favicon_svg_is_self_contained():
    svg = (SITE / "favicon.svg").read_text(encoding="utf-8")
    assert svg.lstrip().startswith("<svg") and "<script" not in svg
    assert not re.search(r"(?i)(href|src)\s*=\s*['\"](https?:)?//", svg)


def test_binary_assets():
    assert png_size((SITE / "assets" / "og.png").read_bytes()) == (1200, 630)
    assert (32, 32) in ico_sizes((SITE / "favicon.ico").read_bytes())


def test_headers():
    text = (SITE / "_headers").read_text(encoding="utf-8")
    blocks: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            current = line.strip()
            blocks[current] = []
        else:
            assert current, "header line before any path"
            blocks[current].append(line.strip())
    allh = blocks.get("/*", [])
    assert f"Content-Security-Policy: {CSP}" in allh, allh
    assert "X-Content-Type-Options: nosniff" in allh, allh
    assert "Referrer-Policy: strict-origin-when-cross-origin" in allh, allh
    assert "Content-Type: text/plain; charset=utf-8" in blocks.get("/install.sh", []), blocks


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("OK")
