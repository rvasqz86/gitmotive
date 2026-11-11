#!/usr/bin/env python3
"""Public-release audit: scan the working tree and/or full git history for things that
must not ship in a public repo (secrets, denylisted names, captured transcripts, internal
hosts, other users' home paths, build artifacts).

Dev-only and stdlib-only; not part of the installed package.

    python3 scripts/audit_public.py [--tree] [--history] [--denylist PATH] [--allow PATH]
                                    [--json] [--root DIR]

Neither scope flag means both. Exit 0: no high/medium findings; 1: high/medium findings;
2: usage error.

Self-match rule: literal regex prefixes below are built by string concatenation so this
file never matches its own patterns.
"""
from __future__ import annotations

import argparse
import fnmatch
import getpass
import json
import os
import re
import subprocess
import sys
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

SEVERITY: dict[str, str] = {
    "secret": "high",
    "denylist": "high",
    "transcript": "high",
    "host": "medium",
    "path": "medium",
    "artifact": "medium",
}

EXCERPT_MAX = 120
BINARY_PROBE = 8192
DENYLIST_ENV = "GITMOTIVE_AUDIT_DENYLIST"
DENYLIST_FILE = ".audit-denylist"
ALLOW_FILE = ".audit-allow"

# --- patterns (prefixes concatenated: see module docstring) -------------------------------

_SECRET_PATTERNS = [
    re.compile(r"(?<![A-Za-z0-9])" + "AK" + "IA" + r"[A-Z0-9]{16}(?![A-Za-z0-9])"),
    re.compile(r"(?<![A-Za-z0-9_])" + "gh" + "[pousr]_" + r"[A-Za-z0-9]{36,}"),
    re.compile(r"(?<![A-Za-z0-9_])" + "github" + "_pat_" + r"[A-Za-z0-9_]{22,}"),
    re.compile(r"(?<![A-Za-z0-9_-])" + "sk" + "-ant-" + r"[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?<![A-Za-z0-9_-])" + "sk" + "-" + r"[A-Za-z0-9]{20,}"),
    re.compile(r"(?<![A-Za-z0-9_])" + "xo" + "x[baprs]-" + r"[A-Za-z0-9-]{10,}"),
    re.compile("-----" + "BEGIN " + r"(?:[A-Z0-9]+ )*" + "PRIVATE" + " KEY-----"),
    re.compile(r"(?i)\b(?:api[_-]?key|sec" + "ret|tok" + "en|pass" + r"word)\s*[:=]\s*['\"][^'\"\s]{12,}['\"]"),
]

_OCTET = r"(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])"
_IPV4_PRIVATE = re.compile(
    r"(?<![0-9.])(?:"
    + "1" + r"0\." + _OCTET + r"\." + _OCTET + r"\." + _OCTET
    + "|" + "17" + r"2\.(?:1[6-9]|2[0-9]|3[01])\." + _OCTET + r"\." + _OCTET
    + "|" + "19" + r"2\.168\." + _OCTET + r"\." + _OCTET
    + r")(?![0-9.])"
)
_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
_HOSTNAME = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:" + _LABEL + r"\.)+(?:internal|corp|intranet|lan|local)(?![A-Za-z0-9_(-]|\.[A-Za-z0-9])",
    re.IGNORECASE,
)
_HOME_PATH = re.compile(r"(?<![A-Za-z0-9_.-])/(?:" + "ho" + "me|Us" + r"ers)/([A-Za-z0-9._-]+)/")

_TRANSCRIPT_MARKERS = ('"hook_event_name"', '"transcript_path"', '"tool_use_id"')
_TRANSCRIPT_KIND = re.compile(r'"kind"\s*:\s*"prompt"')


@dataclass
class Finding:
    check: str
    severity: str
    where: str
    commit: str | None
    excerpt: str


class UsageError(Exception):
    pass


class Denylist(list):
    """list[str] of terms that also remembers each term's 1-based line number in its file."""

    def __init__(self, terms=(), line_numbers=None):
        super().__init__(terms)
        self.line_numbers = list(line_numbers) if line_numbers is not None else list(range(1, len(self) + 1))


# --- denylist ----------------------------------------------------------------------------

def load_denylist(path: str | None, root: Path) -> list[str] | None:
    """First existing of: `path`, $GITMOTIVE_AUDIT_DENYLIST, <root>/.audit-denylist. None if none."""
    candidates = [path, os.environ.get(DENYLIST_ENV), str(Path(root) / DENYLIST_FILE)]
    for c in candidates:
        if c and Path(c).is_file():
            terms, lines = [], []
            for n, raw in enumerate(Path(c).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                t = raw.strip()
                if t and not t.startswith("#"):
                    terms.append(t)
                    lines.append(n)
            return Denylist(terms, lines)
    return None


def _term_ids(denylist) -> list[int]:
    ids = getattr(denylist, "line_numbers", None)
    if ids is None or len(ids) != len(denylist):
        ids = list(range(1, len(denylist) + 1))
    return ids


def _term_re(term: str) -> re.Pattern:
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(term) + r"(?![A-Za-z0-9_])", re.IGNORECASE)


def _denylist_res(denylist) -> list[tuple[int, re.Pattern]]:
    if not denylist:
        return []
    return [(n, _term_re(t)) for n, t in zip(_term_ids(denylist), denylist) if t]


def redact(text: str, denylist: list[str] | None) -> str:
    """Replace every denylist hit (case-insensitive, whole word) with <denylist:N>."""
    if not text or not denylist:
        return text
    # also substring-redact so a term never survives inside a longer word in output
    for n, t in sorted(zip(_term_ids(denylist), denylist), key=lambda p: -len(p[1])):
        if t:
            text = re.sub(re.escape(t), f"<denylist:{n}>", text, flags=re.IGNORECASE)
    return text


# --- scanning ----------------------------------------------------------------------------

def _mask_secrets(line: str) -> str:
    for rx in _SECRET_PATTERNS:
        line = rx.sub(lambda m: m.group(0)[:4] + "…[masked]", line)
    return line


def _excerpt(text: str, start: int, end: int, denylist) -> str:
    ls = text.rfind("\n", 0, start) + 1
    le = text.find("\n", end)
    le = len(text) if le == -1 else le
    line = text[ls:le]
    # Mask and redact the whole line first, then window the result: windowing first could
    # cut a denylist term or secret so that it no longer matches and prints in part.
    safe = redact(_mask_secrets(line), denylist)
    if len(safe) <= EXCERPT_MAX:
        return safe.strip()
    # anchor near the match; any position is safe because `safe` is already scrubbed
    pos = min(len(redact(_mask_secrets(line[:start - ls]), denylist)), len(safe))
    lo = max(0, min(pos - 30, len(safe) - EXCERPT_MAX))
    return safe[lo:lo + EXCERPT_MAX].strip()


def _line_no(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def scan_text(text: str, where: str, denylist: list[str] | None,
              checks: tuple[str, ...] = ("secret", "host", "denylist")) -> list[Finding]:
    """Content checks over `text`. Supports check ids secret, host, denylist, path."""
    found: list[Finding] = []
    rwhere = redact(where, denylist)

    def add(check, m, severity=None):
        found.append(Finding(check, severity or SEVERITY[check], f"{rwhere}:{_line_no(text, m.start())}",
                             None, _excerpt(text, m.start(), m.end(), denylist)))

    if "secret" in checks:
        for rx in _SECRET_PATTERNS:
            for m in rx.finditer(text):
                add("secret", m)
    if "denylist" in checks:
        for _n, rx in _denylist_res(denylist):
            for m in rx.finditer(text):
                add("denylist", m)
    if "host" in checks:
        for rx in (_IPV4_PRIVATE, _HOSTNAME):
            for m in rx.finditer(text):
                add("host", m)
    if "path" in checks:
        me = _current_user()
        for m in _HOME_PATH.finditer(text):
            add("path", m, "info" if m.group(1) == me else None)
    return found


def _current_user() -> str:
    try:
        return getpass.getuser()
    except Exception:
        return ""


def _is_binary(data: bytes) -> bool:
    return b"\0" in data[:BINARY_PROBE]


def _path_checks(path: str, denylist, tracked: bool) -> list[Finding]:
    out = []
    rpath = redact(path, denylist)
    parts = path.split("/")
    if ".gitmotive" in parts[:-1]:
        out.append(Finding("transcript", SEVERITY["transcript"], rpath, None, "path under .gitmotive/"))
    if tracked:
        dirs = parts[:-1]
        if "build" in dirs or "dist" in dirs or any(d.endswith(".egg-info") for d in dirs) \
                or path.endswith(".whl"):
            out.append(Finding("artifact", SEVERITY["artifact"], rpath, None, "build artifact is tracked"))
    for _n, rx in _denylist_res(denylist):
        if rx.search(path):
            out.append(Finding("denylist", SEVERITY["denylist"], rpath, None, "denylist term in path"))
            break
    return out


def _content_checks(path: str, data: bytes, denylist) -> list[Finding]:
    if _is_binary(data):
        return []
    text = data.decode("utf-8", errors="replace")
    out = scan_text(text, path, denylist, checks=("secret", "host", "denylist", "path"))
    if path.endswith(".jsonl") and (any(k in text for k in _TRANSCRIPT_MARKERS) or _TRANSCRIPT_KIND.search(text)):
        out.append(Finding("transcript", SEVERITY["transcript"], redact(path, denylist), None,
                           "jsonl contains hook/transcript records"))
    return out


def scan_file(path: str, data: bytes, denylist, tracked: bool = True) -> list[Finding]:
    return _path_checks(path, denylist, tracked) + _content_checks(path, data, denylist)


def _history_entries(root: Path) -> list[tuple[str, str, str]]:
    """(commit, path, blob) for every blob added or modified by any commit in --all, oldest
    commit first. Merges are diffed against each parent (-m) so no tree entry is missed."""
    raw = _git(root, "log", "--all", "--reverse", "-m", "--format=%x01%H", "--raw",
               "--no-abbrev", "--no-renames", "-z")
    toks = raw.decode("utf-8", errors="replace").split("\0")
    out, commit, i = [], None, 0
    while i < len(toks):
        t = toks[i].lstrip("\n")
        i += 1
        if t.startswith("\x01"):
            commit = t[1:]
        elif t.startswith(":") and i < len(toks):
            meta, path = t[1:].split(), toks[i]
            i += 1
            # meta: <src-mode> <dst-mode> <src-sha> <dst-sha> <status>
            if len(meta) >= 5 and meta[4] != "D" and meta[1] not in ("160000", "000000"):
                out.append((commit, path, meta[3]))
    return out


# --- git ---------------------------------------------------------------------------------

def _git(root: Path, *args: str, input: bytes | None = None) -> bytes:
    r = subprocess.run(["git", *args], cwd=root, input=input, capture_output=True)
    if r.returncode != 0:
        raise UsageError(f"git {args[0]} failed: {r.stderr.decode(errors='replace').strip()}")
    return r.stdout


def _z(out: bytes) -> list[str]:
    return [p for p in out.decode("utf-8", errors="replace").split("\0") if p]


def scan_tree(root: Path, denylist) -> list[Finding]:
    tracked = _z(_git(root, "ls-files", "-z"))
    untracked = _z(_git(root, "ls-files", "-z", "-o", "--exclude-standard"))
    out = []
    for paths, is_tracked in ((tracked, True), (untracked, False)):
        for p in paths:
            f = root / p
            if not f.is_file():
                continue  # deleted in worktree, or a submodule dir
            try:
                data = f.read_bytes()
            except OSError:
                continue
            out += scan_file(p, data, denylist, tracked=is_tracked)
    return out


def _read_blobs(root: Path, shas: list[str]):
    """Yield (sha, bytes) for blob shas via one `git cat-file --batch`."""
    if not shas:
        return
    proc = subprocess.Popen(["git", "cat-file", "--batch"], cwd=root, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def feed():
        try:
            proc.stdin.write(("\n".join(shas) + "\n").encode())
        finally:
            proc.stdin.close()

    threading.Thread(target=feed, daemon=True).start()
    rd = proc.stdout
    try:
        while True:
            header = rd.readline()
            if not header:
                break
            parts = header.split()
            if len(parts) < 3:  # "<sha> missing"
                continue
            size = int(parts[2])
            data = rd.read(size)
            rd.read(1)  # trailing LF
            yield parts[0].decode(), data
    finally:
        rd.close()
        proc.wait()


def introducing_commit(root: Path, blob: str) -> str | None:
    out = _git(root, "log", "--all", "--reverse", "--format=%H", f"--find-object={blob}")
    lines = out.decode().split()
    return lines[0] if lines else None


def scan_history(root: Path, denylist) -> list[Finding]:
    out: list[Finding] = []
    # Path checks run once per distinct historical path (a blob may live at many paths);
    # content checks run once per distinct blob.
    first_commit_of_path: dict[str, str] = {}
    path_of: dict[str, str] = {}
    for commit, path, blob in _history_entries(root):
        first_commit_of_path.setdefault(path, commit)
        path_of.setdefault(blob, path)
    for path, commit in first_commit_of_path.items():
        for f in _path_checks(path, denylist, tracked=True):
            f.commit = commit
            out.append(f)
    intro: dict[str, str | None] = {}
    for sha, data in _read_blobs(root, list(path_of)):
        fs = _content_checks(path_of[sha], data, denylist)
        if fs:
            if sha not in intro:
                intro[sha] = introducing_commit(root, sha)
            for f in fs:
                f.commit = intro[sha]
            out += fs

    # commit messages and identities
    raw = _git(root, "log", "--all", "--format=%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%B%x1e")
    for rec in raw.decode("utf-8", errors="replace").split("\x1e"):
        rec = rec.strip("\n")
        if not rec:
            continue
        fields = rec.split("\x1f")
        if len(fields) < 6:
            continue
        sha, an, ae, cn, ce, msg = fields[0], fields[1], fields[2], fields[3], fields[4], "\x1f".join(fields[5:])
        for f in scan_text(msg, "commit-message", denylist):
            f.commit = sha
            out.append(f)
        for label, value in (("author", f"{an} <{ae}>"), ("committer", f"{cn} <{ce}>")):
            for f in scan_text(value, label, denylist, checks=("denylist",)):
                f.commit = sha
                f.where = label
                out.append(f)
    return out


# --- allow-list --------------------------------------------------------------------------

def load_allow(path: Path) -> list[tuple[str, str]]:
    rules = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        body, sep, reason = line.partition("#")
        if not sep or not reason.strip():
            raise UsageError(f"{path.name}:{n}: entry needs a '# reason'")
        toks = body.split()
        if len(toks) != 2:
            raise UsageError(f"{path.name}:{n}: expected '<path-glob> <check-id>  # reason'")
        if toks[1] not in SEVERITY:
            raise UsageError(f"{path.name}:{n}: unknown check id {toks[1]!r}")
        rules.append((toks[0], toks[1]))
    return rules


def _strip_line(where: str) -> str:
    head, sep, tail = where.rpartition(":")
    return head if sep and tail.isdigit() else where


def apply_allow(findings: list[Finding], rules) -> list[tuple[Finding, bool]]:
    out = []
    for f in findings:
        p = _strip_line(f.where)
        allowed = f.severity != "info" and any(c == f.check and fnmatch.fnmatch(p, g) for g, c in rules)
        if allowed:
            f.severity = "info"
        out.append((f, allowed))
    return out


# --- CLI ---------------------------------------------------------------------------------

def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="audit_public.py", description="Public-release audit (tree and history).")
    p.add_argument("--tree", action="store_true", help="scan tracked + untracked-unignored files")
    p.add_argument("--history", action="store_true", help="scan every blob, message and identity in --all")
    p.add_argument("--denylist", metavar="PATH")
    p.add_argument("--allow", metavar="PATH")
    p.add_argument("--json", action="store_true")
    p.add_argument("--root", metavar="DIR")
    return p


def _run(argv, denylist_box) -> int:
    args = _parser().parse_args(argv)
    if args.root:
        root = Path(args.root).resolve()
    else:
        try:
            root = Path(_git(Path.cwd(), "rev-parse", "--show-toplevel").decode().strip())
        except (UsageError, OSError):
            raise UsageError("not inside a git repository (use --root)")
    if not root.is_dir():
        raise UsageError(f"--root {args.root!r} is not a directory")
    _git(root, "rev-parse", "--git-dir")  # raises UsageError when not a repo
    if args.denylist and not Path(args.denylist).is_file():
        raise UsageError("--denylist file not found")
    denylist = load_denylist(args.denylist, root)
    denylist_box.append(denylist)

    if args.allow:
        if not Path(args.allow).is_file():
            raise UsageError("--allow file not found")
        rules = load_allow(Path(args.allow))
    elif (root / ALLOW_FILE).is_file():
        rules = load_allow(root / ALLOW_FILE)
    else:
        rules = []

    do_tree = args.tree or not args.history
    do_hist = args.history or not args.tree
    findings: list[Finding] = []
    if do_tree:
        findings += scan_tree(root, denylist)
    if do_hist:
        findings += scan_history(root, denylist)
    rows = apply_allow(findings, rules)
    for f, _a in rows:  # belt and braces: nothing unredacted leaves this process
        f.where, f.excerpt = redact(f.where, denylist), redact(f.excerpt, denylist)

    counts = {s: sum(1 for f, _ in rows if f.severity == s) for s in ("high", "medium", "info")}
    dl_status = "skipped (no denylist)" if denylist is None else f"{len(denylist)} terms"
    scopes = "+".join(s for s, on in (("tree", do_tree), ("history", do_hist)) if on)
    summary = (f"audit[{scopes}]: high={counts['high']} medium={counts['medium']} info={counts['info']}"
               f"  denylist: {dl_status}")
    order = {"high": 0, "medium": 1, "info": 2}
    rows.sort(key=lambda r: (order[r[0].severity], r[0].check, r[0].where))

    if args.json:
        print(json.dumps({
            "summary": summary, "counts": counts, "denylist": dl_status, "scopes": scopes.split("+"),
            "findings": [dict(asdict(f), allowed=a) for f, a in rows],
        }, indent=2, ensure_ascii=False))
    else:
        for f, a in rows:
            sev = "allowed" if a else f.severity
            commit = f.commit[:10] if f.commit else "-"
            print(f"{sev:<8} {f.check:<10} {commit:<10} {f.where}  {f.excerpt}")
        print(summary)
    return 1 if counts["high"] or counts["medium"] else 0


def main(argv: list[str] | None = None) -> int:
    box: list = []
    try:
        return _run(argv, box)
    except SystemExit as e:  # argparse
        return int(e.code) if isinstance(e.code, int) else 2
    except UsageError as e:
        print(f"audit_public: {redact(str(e), box[0] if box else None)}", file=sys.stderr)
        return 2
    except Exception as e:  # never leak a denylist term through a traceback
        dl = box[0] if box else None
        print(f"audit_public: error: {redact(f'{type(e).__name__}: {e}', dl)}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
