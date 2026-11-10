"""Demo viewer checks (site/demo/, task 14).

Runs the pure-function tests with `node --test tests/js/viewer-core.test.mjs` (prints `skip node`
when node is absent) and greps the viewer for inline styles, HTML sinks and extra network calls.
It also checks the palette contrast, the page markup, the fixture and the size budget.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "site" / "demo"
JS = DEMO / "viewer.js"
CORE = DEMO / "viewer-core.mjs"
CSS = DEMO / "viewer.css"
HTML = DEMO / "index.html"
FIXTURE = ROOT / "tests" / "js" / "fixture.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_site as site  # noqa: E402


def _code(path: Path) -> str:
    """Source with // and /* */ comments removed, so a comment never satisfies or trips a grep."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"(?m)(^|[^:\\])//.*$", r"\1", text)


# --- inline-style grep (the checker, then the real file) -----------------------------------

def inline_style_problems(js: str) -> list[str]:
    out = []
    if re.search(r"style\s*=", js):
        out.append("style= in viewer.js")
    if re.search(r"""setAttribute\(\s*['"`]style['"`]""", js):
        out.append("setAttribute('style', ...)")
    for m in re.finditer(r"\.style\b\s*(\.\s*(\w+)|\[|=)", js):
        if m.group(2) != "setProperty":
            out.append(f"style assignment: {m.group(0)!r}")
    if "cssText" in js:
        out.append("cssText")
    return out


def test_inline_style_checker():
    for bad in ('el.setAttribute("style", "color:red")', "el.style.color = 'red'",
                "el.style = 'x'", "el.style['color'] = 'x'", "x.innerHTML = '<p style=\"\">'",
                "el.style.cssText = ''"):
        assert inline_style_problems(bad), bad
    assert inline_style_problems("el.style.setProperty('--pc', v)") == []
    assert inline_style_problems("el.className = 'p3'") == []


def test_no_inline_styles():
    for path in (JS, CORE):
        probs = inline_style_problems(_code(path))
        assert not probs, f"{path.name}: {probs}"
    assert "style=" not in HTML.read_text(encoding="utf-8")


def test_no_html_sinks():
    """Data text goes through textContent / text nodes; no markup is parsed from strings."""
    for path in (JS, CORE):
        js = _code(path)
        for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "createContextualFragment",
                     "DOMParser", "eval(", "new Function"):
            assert sink not in js, f"{path.name} uses {sink}"
    assert "textContent" in _code(JS)


def test_only_network_request_is_data_json():
    js = _code(JS)
    fetches = re.findall(r"fetch\(([^;]*?)\)\s*[;,\n]", js)
    assert len(re.findall(r"\bfetch\(", js)) == 1, "exactly one fetch()"
    assert 'new URL("data.json", import.meta.url)' in js, fetches
    for api in ("XMLHttpRequest", "WebSocket", "EventSource", "sendBeacon", "import(", "Worker("):
        assert api not in js and api not in _code(CORE), api
    for path in (JS, CORE, CSS, HTML):
        text = _code(path) if path.suffix in (".js", ".mjs", ".css") else path.read_text(encoding="utf-8")
        urls = re.findall(r"https?://[^\s\"')<>]+", text)
        bad = [u for u in urls if not site.external_ok(u)]
        assert not bad, f"{path.name}: {bad}"
    imports = re.findall(r"""^\s*import\b[^;]*?from\s+['"]([^'"]+)['"]""", js, re.M)
    assert imports == ["./viewer-core.mjs"], imports
    assert not re.search(r"^\s*import\b", _code(CORE), re.M), "viewer-core.mjs imports nothing"


# --- node --test -------------------------------------------------------------------------------

def test_core_with_node():
    node = shutil.which("node")
    if not node:
        print("skip node")
        return
    r = subprocess.run([node, "--test", "tests/js/viewer-core.test.mjs"], cwd=ROOT,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert re.search(r"(?m)^# fail 0$", r.stdout), r.stdout
    assert re.search(r"(?m)^# pass [1-9]", r.stdout), r.stdout


def test_core_exports():
    core = CORE.read_text(encoding="utf-8")
    for name in ("PALETTE_SIZE", "indexData", "colorFor", "parseHash", "escapeHtml", "detailModel"):
        assert re.search(rf"export (const|function) {name}\b", core), name
    assert re.search(r"export const PALETTE_SIZE = 12;", core)


# --- palette and css ---------------------------------------------------------------------------

def test_palette_classes_and_contrast():
    css = CSS.read_text(encoding="utf-8")
    base = (ROOT / "site" / "assets" / "site.css").read_text(encoding="utf-8")
    for i in range(12):
        assert re.search(rf"^\.p{i} \{{ --pc: var\(--p{i}\); \}}$", css, re.M), f".p{i}"
    comment = next(c for c in re.findall(r"/\*.*?\*/", css, re.S) if "contrast" in c.lower())
    pairs = site.PAIR.findall(comment)
    # every colour, both schemes, on both row backgrounds (--panel and --hl)
    want = {(f"--p{i}", bg, scheme) for i in range(12) for bg in ("--panel", "--hl") for scheme in "dl"}
    dark, light = comment.split("light (prefers-color-scheme: light)")
    got = {(f, b, "d") for f, _, b, _, _ in site.PAIR.findall(dark)} | \
          {(f, b, "l") for f, _, b, _, _ in site.PAIR.findall(light)}
    assert want <= got, sorted(want - got)
    assert len(pairs) == 48, len(pairs)
    # the stated values must be the ones declared, in the right scheme
    dark_root, light_root = re.findall(r":root\s*\{([^}]*)\}", css)[:2]
    decl = lambda block: dict(re.findall(r"(--p\d+)\s*:\s*(#[0-9a-fA-F]{6})", block))
    for part, block in ((dark, dark_root), (light, light_root)):
        d = decl(block)
        for f, fv, _, _, _ in site.PAIR.findall(part):
            assert d.get(f, "").lower() == fv.lower(), (f, fv, d.get(f))
    probs = site.contrast_problems(css + "\n" + base) + site.css_external_problems(css)
    assert not probs, "\n".join(probs)
    assert "prefers-color-scheme: light" in css and "prefers-reduced-motion" in css


def test_focus_ring_visible():
    css = CSS.read_text(encoding="utf-8")
    assert re.search(r"\.code tr:focus-visible \{ outline: 2px solid var\(--accent\)", css)
    assert re.search(r"\.detail:focus-visible \{ outline: 2px solid var\(--accent\)", css)


# --- markup ------------------------------------------------------------------------------------

def test_demo_page_markup():
    assert HTML in site.html_pages(), "test_site.py picks up site/demo/index.html"
    p = site.Page(HTML.read_text(encoding="utf-8"))
    probs = site.markup_problems(p) + site.page_basics(p) + site.external_problems(p) + \
        site.link_problems(p, HTML)
    assert not probs, probs
    live = [a for t, a in p.tags if a.get("aria-live")]
    assert [a.get("id") for a in live] == ["detail"] and live[0]["aria-live"] == "polite", live
    scripts = p.find("script")
    assert scripts == [{"type": "module", "src": "/demo/viewer.js"}], scripts
    sheets = [a["href"] for a in p.find("link", rel="stylesheet")]
    assert sheets == ["/assets/site.css", "/demo/viewer.css"], sheets
    assert any(a.get("aria-current") == "page" and a.get("href") == "/demo/" for a in p.find("a"))
    for id_ in ("files", "rows", "detail", "state", "meta", "viewer"):
        assert id_ in p.ids, id_
    assert p.meta("og:url") == "https://gitmotive.tech/demo/"


def test_budget():
    files = [HTML, CSS, JS, CORE, ROOT / "site" / "assets" / "site.css", ROOT / "site" / "favicon.svg"]
    total = sum(f.stat().st_size for f in files)
    assert total <= 100 * 1024, f"demo page html+css+js = {total} bytes > 102400"


# --- data ---------------------------------------------------------------------------------------

def _shape(data: dict) -> None:
    assert data["version"] == 1
    for k in ("generated_at", "repo", "rev", "files", "prompts"):
        assert k in data, k
    for f in data["files"]:
        assert isinstance(f["path"], str) and isinstance(f["lines"], list)
        for line in f["lines"]:
            assert {"n", "text", "commit", "author", "date", "match"} <= set(line), line
            m = line["match"]
            if m:
                assert {"prompt_id", "why", "ts", "tool", "agent", "model", "session", "commit",
                        "reasoning"} <= set(m), m
                assert m["prompt_id"] in data["prompts"], m["prompt_id"]


def test_fixture():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    _shape(data)
    text = FIXTURE.read_text(encoding="utf-8")
    assert "<script>" in text, "fixture carries a <script> payload"
    matches = [line["match"] for f in data["files"] for line in f["lines"] if line["match"]]
    assert any(m["model"] is None for m in matches), "fixture has a null model"
    assert any(p.get("hq") for p in data["prompts"].values()), "fixture has an hq block"
    assert any(":" in f["path"] for f in data["files"]), "fixture has a path with a colon"


def test_committed_data_matches_schema():
    data = json.loads((DEMO / "data.json").read_text(encoding="utf-8"))
    _shape(data)
    assert data["files"], "data.json lists files"


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok {fn.__name__}")
    print(f"{len(fns)} passed")
