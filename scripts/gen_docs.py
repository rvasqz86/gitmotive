#!/usr/bin/env python3
"""Generate site/docs/index.html from the real CLI and hand-written Markdown.

Sources:
  - gitmotive.cli.USAGE, cli.__doc__ and cli.EXPERIMENTAL   -> CLI reference
  - dataclasses.fields(store.Event) + store.FIELD_DOCS      -> data-format table
  - scripts/docs_src/{install,quickstart,adapters,data-format}.md

    python3 scripts/gen_docs.py            # write the page
    python3 scripts/gen_docs.py --check    # exit 0 in sync, 1 stale (with a diff summary)

The Markdown renderer is a deliberately small stdlib subset: ATX headings, paragraphs, fenced
code, unordered and ordered lists, inline code and links. Everything else is plain text.

List-continuation limit: an indented line directly under an item joins that item's text, and
a blank line followed by another item keeps the list going. A blank line followed by anything
else (an indented second paragraph, a nested list, a fenced block) ends the list; nested lists
and multi-paragraph items are not supported.
"""
from __future__ import annotations

import dataclasses
import difflib
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(__file__).resolve().parent / "docs_src"
OUT = ROOT / "site" / "docs" / "index.html"
SECTIONS = ("install", "quickstart", "adapters")   # data-format comes after the CLI reference
ORIGIN = "https://gitmotive.tech"
REPO = "https://github.com/rvasqz86/gitmotive"

sys.path.insert(0, str(ROOT))
from gitmotive import cli, store  # noqa: E402


def esc(s: str) -> str:
    return html.escape(s, quote=True)


# --- Markdown subset ----------------------------------------------------------------------

class Ids:
    """Unique, stable heading ids for one page."""

    def __init__(self) -> None:
        self.used: set[str] = set()

    def make(self, text: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"
        slug, n = base, 2
        while slug in self.used:
            slug, n = f"{base}-{n}", n + 1
        self.used.add(slug)
        return slug


_CODE_SPAN = re.compile(r"(`+)(.+?)\1")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def inline(text: str) -> str:
    """Escape text; render `code` spans and [text](url) links. Code spans are literal."""
    out, pos = [], 0
    for m in _CODE_SPAN.finditer(text):
        out.append(_links(text[pos:m.start()]))
        out.append(f"<code>{esc(m.group(2).strip())}</code>")
        pos = m.end()
    out.append(_links(text[pos:]))
    return "".join(out)


def _links(text: str) -> str:
    out, pos = [], 0
    for m in _LINK.finditer(text):
        out.append(esc(text[pos:m.start()]))
        out.append(f'<a href="{esc(m.group(2))}">{esc(m.group(1))}</a>')
        pos = m.end()
    out.append(esc(text[pos:]))
    return "".join(out)


def heading(level: int, hid: str, text_html: str) -> str:
    mark = '<span class="hash" aria-hidden="true">#</span>' if level == 2 else ""
    return f'<h{level} id="{hid}">{mark}{text_html}</h{level}>'


def code_block(code: str, label: str = "Code") -> str:
    return (f'<pre class="diff" tabindex="0" role="region" aria-label="{esc(label)}">'
            f"<code>{esc(code)}</code></pre>")


_HEADING = re.compile(r"^(#{1,4})\s+(.*?)\s*#*\s*$")
_ITEM = re.compile(r"^(?:([-*])|(\d+)[.)])\s+(.*)$")
_FENCE = re.compile(r"^(`{3,}|~{3,})(.*)$")


def render_md(text: str, ids: Ids, toc: list[tuple[int, str, str]]) -> str:
    """Render the subset. `# h` becomes <h2>, `## h` <h3> and so on (the page owns <h1>).
    Each heading gets a unique id and is appended to `toc` as (level, id, plain text)."""
    lines = text.splitlines()
    out: list[str] = []
    para: list[str] = []
    items: list[list[str]] = []
    list_kind: tuple[str, int] | None = None   # ("ul", 1) or ("ol", start)

    def flush_para() -> None:
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()

    def flush_list() -> None:
        nonlocal list_kind
        if items:
            tag, start = list_kind
            attr = f' start="{start}"' if tag == "ol" and start != 1 else ""
            body = "".join(f"<li>{inline(' '.join(it))}</li>" for it in items)
            out.append(f"<{tag}{attr}>{body}</{tag}>")
            items.clear()
        list_kind = None

    i = 0
    while i < len(lines):
        line = lines[i]
        fence = _FENCE.match(line.strip())
        if fence:
            flush_para()
            flush_list()
            marker, body = fence.group(1), []
            i += 1
            while i < len(lines) and not (lines[i].strip().startswith(marker)
                                          and lines[i].strip().strip(marker[0]) == ""):
                body.append(lines[i])
                i += 1
            i += 1   # closing fence (or end of input)
            lang = fence.group(2).strip()
            out.append(code_block("\n".join(body), "Shell commands" if lang == "sh" else "Code"))
            continue
        if not line.strip():
            flush_para()
            if items:   # a blank line ends a list item's text, but a following item continues it
                nxt = next((l for l in lines[i + 1:] if l.strip()), "")
                if not _ITEM.match(nxt):
                    flush_list()
            i += 1
            continue
        h = _HEADING.match(line)
        if h:
            flush_para()
            flush_list()
            level = len(h.group(1)) + 1
            hid = ids.make(h.group(2))
            toc.append((level, hid, h.group(2).replace("`", "")))
            out.append(heading(level, hid, inline(h.group(2))))
            i += 1
            continue
        it = _ITEM.match(line)
        if it:
            flush_para()
            kind = ("ul", 1) if it.group(1) else ("ol", int(it.group(2)))
            if list_kind is None or list_kind[0] != kind[0]:
                flush_list()
                list_kind = kind
            items.append([it.group(3)])
            i += 1
            continue
        if items and line[:1].isspace():
            items[-1].append(line.strip())
        else:
            flush_list()
            para.append(line.strip())
        i += 1
    flush_para()
    flush_list()
    return "\n".join(out)


# --- generated sections -------------------------------------------------------------------

def cli_reference(ids: Ids, toc: list[tuple[int, str, str]]) -> str:
    hid = ids.make("CLI reference")
    toc.append((2, hid, "CLI reference"))
    out = [heading(2, hid, "CLI reference"),
           "<p>Generated from the CLI itself. This is what <code>gitmotive help</code> prints:</p>",
           code_block(cli.__doc__.rstrip("\n"), "gitmotive help output")]
    exp = ", ".join(f"<code>{esc(a)}</code>" for a in cli.EXPERIMENTAL)
    out.append(f'<p>Experimental agents: {exp} <span class="exp">(experimental)</span>. '
               "They record prompts and edits only; their hook payloads are not fully documented.</p>")
    entries = [(cmd, usage, desc) for cmd, (usage, desc) in cli.USAGE.items()]
    entries.append(("--version", "gitmotive --version | -V", "print the version and exit"))
    for cmd, usage, desc in entries:
        sid = ids.make(f"cli {cmd}")
        title = f"gitmotive {cmd}" if cmd != "why" else "git motive / gitmotive why"
        toc.append((3, sid, title))
        out.append(heading(3, sid, f"<code>{esc(title)}</code>"))
        out.append(code_block(usage, f"{title} usage"))
        d = esc(desc)
        for a in cli.EXPERIMENTAL:
            d = d.replace(f"{a} (experimental)", f'{a} <span class="exp">(experimental)</span>')
        out.append(f"<p>{d}</p>")
    return "\n".join(out)


def field_table() -> str:
    rows = []
    for f in dataclasses.fields(store.Event):
        typ = f.type if isinstance(f.type, str) else getattr(f.type, "__name__", str(f.type))
        doc = store.FIELD_DOCS.get(f.name)
        if doc is None:
            raise SystemExit(f"store.FIELD_DOCS has no entry for Event.{f.name}")
        rows.append(f'<tr><th scope="row"><code>{esc(f.name)}</code></th>'
                    f"<td><code>{esc(typ)}</code></td><td>{esc(doc)}</td></tr>")
    return ('<table class="agents fields">\n<thead><tr><th scope="col">Field</th>'
            '<th scope="col">Type</th><th scope="col">Meaning</th></tr></thead>\n<tbody>\n'
            + "\n".join(rows) + "\n</tbody>\n</table>")


def toc_html(toc: list[tuple[int, str, str]]) -> str:
    out, open_sub = ['<nav class="toc" aria-labelledby="toc-h">',
                     '<h2 id="toc-h">On this page</h2>', "<ol>"], False
    for level, hid, text in toc:
        if level > 3:
            continue
        if level == 3 and not open_sub and not out[-1].startswith("<li>"):
            pass   # leading h3 (no h2 item to nest under): list it at the top level
        elif level == 3 and not open_sub:
            out[-1] = out[-1].removesuffix("</li>")
            out.append("<ol>")
            open_sub = True
        elif level == 2 and open_sub:
            out.append("</ol></li>")
            open_sub = False
        out.append(f'<li><a href="#{hid}">{esc(text)}</a></li>')
    if open_sub:
        out.append("</ol></li>")
    out += ["</ol>", "</nav>"]
    return "\n".join(out)


# --- page ---------------------------------------------------------------------------------

HEAD = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Docs · gitmotive</title>
<meta name="description" content="Install gitmotive, hook up Claude Code, Cursor, Copilot CLI or oh-my-pi, and ask any line why it exists. CLI reference and data format, generated from the real CLI.">
<meta name="theme-color" content="#131a24" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#f3f5f8" media="(prefers-color-scheme: light)">
<meta property="og:type" content="website">
<meta property="og:site_name" content="gitmotive">
<meta property="og:title" content="gitmotive docs">
<meta property="og:description" content="Install, quickstart, agent setup, CLI reference and data format for gitmotive.">
<meta property="og:image" content="{ORIGIN}/assets/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="The gitmotive tagline above a blame view of a Python file, with the prompt and reasoning for line 42">
<meta property="og:url" content="{ORIGIN}/docs/">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{ORIGIN}/docs/">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="stylesheet" href="/assets/site.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>

<header class="top">
  <nav class="bar" aria-label="Primary">
    <a class="mark" href="/"><span class="mark-glyph" aria-hidden="true">±</span>gitmotive</a>
    <ul>
      <li><a href="/demo/">Demo</a></li>
      <li><a href="/docs/" aria-current="page">Docs</a></li>
      <li><a href="{REPO}">GitHub</a></li>
    </ul>
  </nav>
</header>
"""

FOOT = f"""
<footer class="foot">
  <p><span class="mark-glyph" aria-hidden="true">±</span>gitmotive. MIT licensed.</p>
  <ul>
    <li><a href="/">Home</a></li>
    <li><a href="/demo/">Demo</a></li>
    <li><a href="{REPO}">GitHub</a></li>
  </ul>
</footer>
</body>
</html>
"""


def build() -> str:
    ids = Ids()
    ids.used.update({"main", "toc-h", "docs-h"})
    toc: list[tuple[int, str, str]] = []
    sections = []
    for name in SECTIONS:
        sections.append(render_md((SRC / f"{name}.md").read_text(encoding="utf-8"), ids, toc))
    sections.append(cli_reference(ids, toc))
    sections.append(render_md((SRC / "data-format.md").read_text(encoding="utf-8"), ids, toc)
                    + "\n" + field_table())
    body = "\n\n".join(f'<section class="block prose">\n{s}\n</section>' for s in sections)
    intro = ('<div class="block prose">\n<h1 id="docs-h">gitmotive docs</h1>\n'
             "<p>git blame tells you who. git motive tells you why. This page is generated from "
             "the CLI's own help text and the event schema, so it matches the version it ships with.</p>\n"
             + toc_html(toc) + "\n</div>")
    return (HEAD + '\n<main id="main">\n' + intro + "\n\n" + body + "\n</main>\n" + FOOT)


def check(out: Path = OUT) -> int:
    want = build()
    name = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    have = out.read_text(encoding="utf-8") if out.exists() else ""
    if have == want:
        print(f"{name} is up to date")
        return 0
    if not have:
        print(f"{name} is missing; run python3 scripts/gen_docs.py")
        return 1
    diff = list(difflib.unified_diff(have.splitlines(), want.splitlines(),
                                     "committed", "generated", lineterm="", n=0))
    added = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
    print(f"{name} is stale: {removed} line(s) differ from {added} generated line(s); "
          "run python3 scripts/gen_docs.py")
    for l in diff[:20]:
        print("  " + l[:160])
    if len(diff) > 20:
        print(f"  … {len(diff) - 20} more diff line(s)")
    return 1


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--check"]:
        return check()
    if argv:
        print("usage: python3 scripts/gen_docs.py [--check]", file=sys.stderr)
        return 2
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
