"""Public-text guard: denylist + real-command checks over public-facing text.

Denylist check (README.md, site/**, launch/**, .hq/**): audit_public.load_denylist +
scan_text(..., checks=("denylist",)); prints `skipped denylist` when no denylist exists.
Command check (README.md, site/** except site/demo/data.json, launch/**): inside inline code,
fenced code, <code> or <pre> only, every `gitmotive <word>` must be a real command.

Files are listed with `git ls-files -co --exclude-standard`, so gitignored files are skipped.
The self-tests use a synthetic denylist term (acme-widgets) in temp repos.
"""
from __future__ import annotations

import atexit
import html
import os
import re
import subprocess
import sys
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import audit_public as ap  # noqa: E402

DENYLIST_SCOPE = ("README.md", "site", "launch", ".hq")
COMMAND_SCOPE = ("README.md", "site", "launch")
COMMAND_EXCLUDE = {"site/demo/data.json"}
REAL_COMMANDS = {"why", "log", "stamp", "install", "capture", "help", "--version", "-V"}

# a fence runs to its closing line, or to the end of the document when unclosed (CommonMark)
_FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,})[^\n]*(?:\n|\Z)(.*?)(?:^[ \t]*\1[ \t]*$|\Z)", re.M | re.S)
# an inline span stays within one paragraph (never crosses a blank line); runs must match exactly
_INLINE = re.compile(r"(?<!`)(`+)(?!`)((?:(?!\n[ \t]*\n)[^`])+?)(?<!`)\1(?!`)")
_HTML_CODE = re.compile(r"<(code|pre)\b[^>]*>(.*?)</\1\s*>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")
# `gitmotive` (any case) as a command word, optionally via a path such as `./gitmotive` or
# `bin/gitmotive` (but not a dotfile like `~/.gitmotive`), then its first argument
_INVOCATION = re.compile(
    r"(?:^|(?<=[\s;&|(`'\"$]))(?:[\w.~/-]*/)?gitmotive[ \t]+(-{1,2}[\w-]+|[A-Za-z][\w-]*)",
    re.I | re.M)


# --- file listing --------------------------------------------------------------------------

def public_files(root: Path, scope) -> list[str]:
    """Tracked + untracked-not-ignored files under `scope`; missing dirs are fine."""
    out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z", "--", *scope],
                         cwd=root, capture_output=True, check=True).stdout
    return sorted({p for p in out.decode("utf-8", "replace").split("\0")
                   if p and (Path(root) / p).is_file()})


def _read(root: Path, rel: str) -> str:
    return (Path(root) / rel).read_text(encoding="utf-8", errors="replace")


# --- denylist check ------------------------------------------------------------------------

def denylist_violations(root: Path, denylist) -> list[str] | None:
    """Redacted `where: excerpt` lines, or None when there is no denylist."""
    if denylist is None:
        return None
    found = []
    for rel in public_files(root, DENYLIST_SCOPE):
        for f in ap.scan_text(_read(root, rel), rel, denylist, checks=("denylist",)):
            found.append(ap.redact(f"{f.where}: {f.excerpt}", denylist))
    return found


# --- command check -------------------------------------------------------------------------

def code_regions(text: str) -> list[tuple[int, str]]:
    """(offset, code text) for fenced blocks, inline code, <code> and <pre>."""
    regions: list[tuple[int, str]] = []
    rest = list(text)
    for m in _FENCE.finditer(text):
        regions.append((m.start(2), m.group(2)))
        rest[m.start():m.end()] = [" "] * (m.end() - m.start())  # keep offsets; hide from inline
    unfenced = "".join(rest)
    for m in _INLINE.finditer(unfenced):
        regions.append((m.start(2), m.group(2)))
    for m in _HTML_CODE.finditer(text):
        regions.append((m.start(2), html.unescape(_TAG.sub(" ", m.group(2)))))
    return regions


def command_violations_in(text: str, where: str, denylist=None) -> list[str]:
    """One finding per (line, word); overlapping regions (e.g. `x` inside <code>) count once."""
    found, seen = [], set()
    for off, code in sorted(code_regions(text)):
        for m in _INVOCATION.finditer(code):
            word = m.group(1)
            if word in REAL_COMMANDS:  # exact: the CLI is case-sensitive
                continue
            line = text.count("\n", 0, off) + code.count("\n", 0, m.start()) + 1
            if (line, word) in seen:
                continue
            seen.add((line, word))
            found.append(ap.redact(f"{where}:{line}: unknown command `gitmotive {word}`", denylist))
    return found


def command_violations(root: Path, denylist=None) -> list[str]:
    found = []
    for rel in public_files(root, COMMAND_SCOPE):
        if rel in COMMAND_EXCLUDE:
            continue
        found += command_violations_in(_read(root, rel), rel, denylist)
    return found


# --- helpers for self-tests ----------------------------------------------------------------

TERM = "acme-widgets"
_TEMP_DIRS: list[Path] = []


@atexit.register
def _cleanup_temp_dirs() -> None:
    while _TEMP_DIRS:
        shutil.rmtree(_TEMP_DIRS.pop(), ignore_errors=True)


def _repo(files: dict[str, str]) -> Path:
    d = Path(tempfile.mkdtemp(prefix="pubtext-"))
    _TEMP_DIRS.append(d)
    subprocess.run(["git", "init", "-q"], cwd=d, check=True)
    for rel, body in files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return d


def _denylist(d: Path):
    p = d / "denylist.txt"
    p.write_text("# synthetic\n" + TERM + "\n", encoding="utf-8")
    return ap.load_denylist(str(p), d)


# --- self-tests ----------------------------------------------------------------------------

def test_denylist_detects_and_redacts():
    d = _repo({
        "README.md": "Built at Acme-Widgets for fun.\n",
        "site/index.html": "<p>acme-widgets</p>\n",
        "site/demo/data.json": '{"note": "acme-widgets"}\n',
        "launch/post.md": "hello " + TERM + "\n",
        ".hq/notes.md": TERM + "\n",
        ".hq/.gitignore": "secret.md\n",
        ".hq/secret.md": TERM + " is ignored\n",
        "other/file.md": TERM + " out of scope\n",
    })
    dl = _denylist(d)
    found = denylist_violations(d, dl)
    wheres = sorted(f.split(":")[0] for f in found)
    assert wheres == [".hq/notes.md", "README.md", "launch/post.md", "site/demo/data.json",
                      "site/index.html"], wheres
    blob = "\n".join(found)
    assert TERM not in blob.lower(), blob
    assert "<denylist:2>" in blob, blob


def test_denylist_none_returns_none():
    d = _repo({"README.md": TERM + "\n"})
    old = os.environ.pop(ap.DENYLIST_ENV, None)
    try:
        assert ap.load_denylist(None, d) is None
        assert denylist_violations(d, None) is None
    finally:
        if old is not None:
            os.environ[ap.DENYLIST_ENV] = old


def test_missing_dirs_are_fine():
    d = _repo({"README.md": "plain\n"})
    assert denylist_violations(d, _denylist(d)) == []
    assert command_violations(d) == []
    e = _repo({})
    assert public_files(e, DENYLIST_SCOPE) == []
    assert command_violations(e) == []


def test_command_check_ignores_prose():
    text = "gitmotive links lines to prompts. gitmotive init is not a thing in prose.\n"
    assert command_violations_in(text, "README.md") == []


def test_command_check_flags_fake_commands_in_code():
    text = (
        "Run `gitmotive init` first.\n"
        "```sh\npip install gitmotive\ngitmotive blame src/x.py\ngitmotive why a.py:3\n```\n"
        "<pre><code>$ gitmotive frobnicate</code></pre>\n"
        "<code>gitmotive --version</code> and `gitmotive -V` and `gitmotive help`\n"
    )
    found = command_violations_in(text, "README.md")
    words = sorted(re.search(r"`gitmotive (\S+)`", f).group(1) for f in found)
    assert words == ["blame", "frobnicate", "init"], found
    assert any(f.startswith("README.md:1:") for f in found), found
    assert any(f.startswith("README.md:4:") for f in found), found


def test_command_check_stray_backtick_does_not_shift_pairing():
    text = "a stray ` backtick here\n\n`gitmotive why` ok and `gitmotive init` bad\n"
    found = command_violations_in(text, "R")
    assert found == ["R:3: unknown command `gitmotive init`"], found


def test_command_check_unclosed_fence_runs_to_end():
    found = command_violations_in("intro\n```sh\ngitmotive init\n", "R")
    assert found == ["R:3: unknown command `gitmotive init`"], found
    found = command_violations_in("```\ngitmotive why x:1\n\ngitmotive blame", "R")
    assert found == ["R:4: unknown command `gitmotive blame`"], found


def test_command_check_paths_and_case():
    text = "`./gitmotive init` `bin/gitmotive blame` `Gitmotive Init` `/usr/bin/gitmotive why`\n"
    words = sorted(re.search(r"`gitmotive (\S+)`", f).group(1)
                   for f in command_violations_in(text, "R"))
    assert words == ["Init", "blame", "init"], words


def test_command_check_dedupes_overlapping_regions():
    found = command_violations_in("<code>`gitmotive init`</code>\n", "R")
    assert found == ["R:1: unknown command `gitmotive init`"], found


def test_temp_repos_are_cleaned_up():
    d = _repo({"README.md": "x\n"})
    assert d.exists()
    _cleanup_temp_dirs()
    assert not d.exists()


def test_command_check_accepts_real_commands():
    text = "".join(f"`gitmotive {c}`\n" for c in sorted(REAL_COMMANDS))
    text += "`git motive a.py:3`, `~/.gitmotive/venv`, `pip install gitmotive && gitmotive install`\n"
    text += "`git clone https://github.com/x/gitmotive && cd gitmotive`\n"
    assert command_violations_in(text, "README.md") == [], command_violations_in(text, "README.md")


def test_command_check_scope_and_redaction():
    bad = "`gitmotive init`\n"
    d = _repo({
        "README.md": bad,
        "site/docs/index.html": "<code>gitmotive blame</code>\n",
        "site/demo/data.json": '{"cmd": "`gitmotive init`"}\n',
        "launch/" + TERM + ".md": bad,
        ".hq/tasks/x.md": bad,
    })
    dl = _denylist(d)
    found = command_violations(d, dl)
    wheres = sorted(re.match(r"(.*?):\d+: ", f).group(1) for f in found)
    assert wheres == ["README.md", "launch/<denylist:2>.md", "site/docs/index.html"], wheres
    assert TERM not in "\n".join(found).lower()


# --- real tree -----------------------------------------------------------------------------

def test_real_tree():
    dl = ap.load_denylist(None, ROOT)
    found = denylist_violations(ROOT, dl)
    if found is None:
        print("skipped denylist")
    else:
        assert not found, "denylist hits:\n" + "\n".join(found)
    cmds = command_violations(ROOT, dl)
    assert not cmds, "unknown gitmotive commands:\n" + "\n".join(cmds)


def test_readme_links_site_and_pipx():
    text = _read(ROOT, "README.md")
    assert "https://gitmotive.tech" in text, "README must link https://gitmotive.tech"
    assert "pipx install gitmotive" in text, "README must contain `pipx install gitmotive`"


README_SECTIONS = ["Install", "Quickstart", "Supported agents", "Commands", "How it links",
                   "Privacy", "Known gaps", "Live demo and docs", "License"]


def _readme_section(text: str, name: str) -> str:
    m = re.search(rf"^## {re.escape(name)}[ \t]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    assert m, f"README has no `## {name}` section"
    return m.group(1)


def test_readme_section_order():
    text = _read(ROOT, "README.md")
    heads = re.findall(r"^## (.+?)[ \t]*$", text, re.M)
    assert heads == README_SECTIONS, f"README ## headings out of order: {heads}"


def test_readme_gif_and_recording_sequence():
    text = _read(ROOT, "README.md")
    gif = text.find("<!-- GIF: docs/demo.gif -->")
    install = text.find("\n## Install")
    assert 0 <= gif < install, "GIF placeholder must come before ## Install"
    m = re.match(r"\s*```[^\n]*\n(.*?)^```", text[gif + len("<!-- GIF: docs/demo.gif -->"):], re.M | re.S)
    assert m, "GIF placeholder must be followed by a fenced recording sequence"
    fence = m.group(1)
    steps = ["pipx install gitmotive", "cd your-repo", "gitmotive install --agent claude",
             "git commit -am", "git motive ", "gitmotive log"]
    pos = [fence.find(s) for s in steps]
    assert all(p >= 0 for p in pos), f"recording sequence missing steps: {steps}, {pos}"
    assert pos == sorted(pos), f"recording sequence out of order: {pos}"


def test_readme_why_example_matches_cmd_why():
    text = _read(ROOT, "README.md")
    edited = re.findall(r"^\s*edited .*$", text, re.M)
    assert edited, "README must show an example `edited` line"
    # cli.cmd_why: "  edited   <ts>  by <tool>  session <id8>  [<why>]  via <agent>  model <model>"
    layout = re.compile(r"^\s*edited   \d{4}-\d\d-\d\d \d\d:\d\d  by \S+  session [0-9a-f]{1,8}"
                        r"  \[[^\]]+\]  via \S+  model \S+$")
    for line in edited:
        assert layout.match(line), f"`edited` line does not match cmd_why layout: {line!r}"


def test_readme_commands_match_usage():
    sys.path.insert(0, str(ROOT))
    from gitmotive import cli
    section = _readme_section(_read(ROOT, "README.md"), "Commands").replace("\\|", "|")
    for cmd, (usage, _desc) in cli.USAGE.items():
        assert f"`{usage}`" in section, f"Commands section missing USAGE[{cmd!r}]: {usage}"
    assert "`gitmotive --version`" in section, "Commands section missing `gitmotive --version`"
    assert "-V" in section, "Commands section missing `-V`"


# --- launch drafts -------------------------------------------------------------------------

DRAFT_STATUS = "Status: DRAFT — do not post without review"
LAUNCH_FILES = ("launch/show-hn.md", "launch/product-hunt.md", "launch/linkedin.md")
ALLOWED_LINKS = {"https://gitmotive.tech", "https://gitmotive.tech/demo/",
                 "https://github.com/rvasqz86/gitmotive"}
# (file, section) -> (unit, max): "chars" counts the stripped section text, "words" splits on space
LAUNCH_LIMITS = {
    ("launch/show-hn.md", "Title"): ("chars", 80),
    ("launch/show-hn.md", "Body"): ("words", 250),
    ("launch/product-hunt.md", "Name"): ("chars", 60),
    ("launch/product-hunt.md", "Tagline"): ("chars", 60),
    ("launch/product-hunt.md", "Description"): ("chars", 260),
    ("launch/product-hunt.md", "First comment"): ("words", 200),
    ("launch/product-hunt.md", "Gallery captions"): ("chars", 1000),
    ("launch/product-hunt.md", "Topics"): ("chars", 500),
    ("launch/linkedin.md", "Post"): ("chars", 1300),
}
_URL = re.compile(r"https?://[^\s)\]>\"'`]+")
# a number (not an `[N]` placeholder) next to a traction word, e.g. "1,200 users", "500 stars"
_TRACTION = re.compile(r"\b\d[\d,.]*\s*[kKmM+]?\s*(?:users|stars|downloads|installs|customers"
                       r"|teams|companies|developers|signups|sign-ups)\b", re.I)


def _section(text: str, name: str) -> str | None:
    m = re.search(rf"^## {re.escape(name)}[ \t]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1).strip() if m else None


def section_length(text: str, unit: str) -> int:
    return len(text.split()) if unit == "words" else len(text)


def launch_violations(root: Path) -> list[str]:
    found = []
    texts = {}
    for rel in LAUNCH_FILES:
        p = Path(root) / rel
        if not p.is_file():
            found.append(f"{rel}: missing")
            continue
        texts[rel] = text = p.read_text(encoding="utf-8")
        if not text.startswith(DRAFT_STATUS):
            found.append(f"{rel}: must start with `{DRAFT_STATUS}`")
        for url in _URL.findall(text):
            url = url.rstrip(".,;:!?")
            if url not in ALLOWED_LINKS:
                found.append(f"{rel}: link not allowed: {url}")
        for m in _TRACTION.finditer(text):
            found.append(f"{rel}: traction claim (use [N]): {m.group(0)}")
    for (rel, name), (unit, limit) in LAUNCH_LIMITS.items():
        if rel not in texts:
            continue
        body = _section(texts[rel], name)
        if not body:
            found.append(f"{rel}: missing or empty `## {name}`")
            continue
        n = section_length(body, unit)
        if n > limit:
            found.append(f"{rel}: `## {name}` is {n} {unit}, limit {limit}")
    captions = _section(texts.get("launch/product-hunt.md", ""), "Gallery captions")
    if captions is not None:
        items = re.findall(r"^\s*(?:\d+[.)]|[-*])\s+\S", captions, re.M)
        if len(items) != 3:
            found.append(f"launch/product-hunt.md: `## Gallery captions` needs 3 items, has {len(items)}")
    return found


def test_launch_checks_catch_violations():
    over = " ".join(["word"] * 251)
    d = _repo({
        "launch/show-hn.md": f"{DRAFT_STATUS}\n## Title\n{'x' * 81}\n## Body\n{over}\n"
                             "see https://example.com/x. and https://gitmotive.tech/demo/.\n",
        "launch/product-hunt.md": "Status: draft\n## Name\nn\n## Tagline\nt\n## Description\n"
                                  "We have 1,200 users and [N] stars.\n## First comment\nhi\n"
                                  "## Gallery captions\n1. a\n2. b\n## Topics\nx\n",
    })
    found = launch_violations(d)
    blob = "\n".join(found)
    assert "launch/linkedin.md: missing" in blob, blob
    assert "`## Title` is 81 chars, limit 80" in blob, blob
    assert "`## Body` is 255 words, limit 250" in blob, blob  # 251 + "see", 2 links, "and"
    assert "link not allowed: https://example.com/x" in blob, blob
    assert "https://gitmotive.tech/demo/" not in blob, blob
    assert "product-hunt.md: must start with" in blob, blob
    assert "traction claim (use [N]): 1,200 users" in blob, blob
    assert "[N] stars" not in blob, blob
    assert "needs 3 items, has 2" in blob, blob


def test_launch_checks_accept_within_limits():
    d = _repo({
        "launch/show-hn.md": f"{DRAFT_STATUS}\n## Title\n{'x' * 80}\n## Body\n"
                             + " ".join(["w"] * 250) + "\n",
        "launch/product-hunt.md": f"{DRAFT_STATUS}\n## Name\nn\n## Tagline\n{'t' * 60}\n"
                                  f"## Description\n{'d' * 260}\n## First comment\nhi\n"
                                  "## Gallery captions\n1. a\n2. b\n3. c\n## Topics\n- x\n",
        # 1277 + 1 space + 22-char link = 1300 chars exactly
        "launch/linkedin.md": f"{DRAFT_STATUS}\n## Post\n{'p' * 1277} https://gitmotive.tech\n",
    })
    assert launch_violations(d) == [], launch_violations(d)


def test_launch_drafts_real_tree():
    found = launch_violations(ROOT)
    assert not found, "launch draft problems:\n" + "\n".join(found)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("OK")
