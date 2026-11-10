#!/usr/bin/env python3
"""Export dogfood provenance for the static demo: HEAD lines of a few files, the intent that
produced each line, and only the prompts those lines reference.

Dev-only and stdlib-only; not part of the installed package. Uses gitmotive.store,
gitmotive.resolve and gitmotive.hq as a library and never imports gitmotive.cli.

    python3 scripts/export_demo.py [--root DIR] [--file PATH ...] [--out site/demo/data.json]
                                   [--max-prompt-chars 4000] [--no-denylist]

The denylist comes from $GITMOTIVE_AUDIT_DENYLIST or <root>/.audit-denylist (see
audit_public.load_denylist). Exit 0 written; 1 a gate hit survived or a source line has a hit
(nothing written); 2 dirty exported files, no denylist, or a usage error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import getpass
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import audit_public  # noqa: E402
from gitmotive import hq, resolve, store  # noqa: E402

# Files written after the dogfood reinstall, so their matches carry `agent` and `model`.
DEFAULT_FILES = ("site/demo/viewer.js", "site/demo/viewer-core.mjs", "launch/DEPLOY.md",
                 "tests/test_export_demo.py")
DEFAULT_OUT = "site/demo/data.json"
CHECKS = ("secret", "host", "denylist", "path")
CHECK_ORDER = ("secret", "denylist", "host", "path")
SIZE_WARN = int(1.5 * 1024 * 1024)
PASTED = "[pasted content omitted]"
_PASTED_RE = re.compile(r"<pasted_content\b[^>]*>.*?(?:</pasted_content>|\Z)", re.S)


class UsageError(Exception):
    pass


class GateError(Exception):
    pass


# --- sanitisation -----------------------------------------------------------------------

def _home_re() -> re.Pattern | None:
    """$HOME plus /home/<user> and /Users/<user> for the current login user, so a `$HOME`
    override (sudo, CI) cannot leave the real user's home path unrewritten."""
    homes = set()
    home = os.path.expanduser("~").rstrip("/")
    if home and home != "~":
        homes.add(home)
    try:
        user = getpass.getuser()
    except Exception:
        user = ""
    if user:
        homes |= {"/home/" + user, "/Users/" + user}
    if not homes:
        return None
    alts = "|".join(re.escape(h) for h in sorted(homes, key=len, reverse=True))
    return re.compile(r"(?:" + alts + r")(?![A-Za-z0-9._-])")


_HOME = _home_re()


def tilde(s: str | None) -> str | None:
    if s is None or _HOME is None:
        return s
    return _HOME.sub("~", s)


def strip_pasted(s: str | None) -> str | None:
    return s if s is None else _PASTED_RE.sub(PASTED, s)


def truncate(s: str | None, n: int) -> str | None:
    if s is None or len(s) <= n:
        return s
    return s[: max(n - 1, 0)] + "…"


def short_session(s: str | None) -> str | None:
    if not s:
        return s
    if "/" in s or "\\" in s:
        return Path(s.replace("\\", "/")).stem[:8]
    return s[:8]


def blocking(findings) -> list:
    """Every `path` finding blocks here (own-home paths were already rewritten to `~`, so any
    that remain are not covered by the rewrite); other checks block at high/medium."""
    return [f for f in findings if f.check == "path" or f.severity in ("high", "medium")]


def scan(text: str, where: str, denylist) -> list:
    """Blocking findings for `text`. audit_public's denylist check is whole-word; for public
    data a term inside a longer identifier (`<term>_v2`, `my<term>`) must also count, so a
    case-insensitive substring hit is reported as a denylist finding too."""
    found = blocking(audit_public.scan_text(text, where, denylist, checks=CHECKS))
    if denylist and not any(f.check == "denylist" for f in found):
        if audit_public.redact(text, denylist) != text:
            # mask secrets before redacting, as audit_public's own excerpts do
            safe = audit_public.redact(audit_public._mask_secrets(text), denylist)
            line = next((l for l in safe.splitlines() if "<denylist:" in l), safe)
            found.append(audit_public.Finding("denylist", "high", audit_public.redact(where, denylist),
                                              None, line.strip()[:audit_public.EXCERPT_MAX]))
    return found


def string_leaves(obj, path="data"):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from string_leaves(k, f"{path}.<key>")
            yield from string_leaves(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from string_leaves(v, f"{path}[{i}]")


def rescan(data: dict, text: str, denylist) -> list:
    """Whole-output rescan: the serialised text, plus every string leaf raw (JSON escaping
    turns `"` into `\\"`, which hides the quoted-assignment secret pattern)."""
    found = scan(text, "data.json", denylist)
    for where, s in string_leaves(data):
        found += scan(s, where, denylist)
    return found


class Gate:
    """Per-record gate: a hit replaces the field with `[omitted: <check>]` and is counted."""

    def __init__(self, denylist):
        self.denylist = denylist
        self.counts: dict[str, int] = {}

    def field(self, value: str | None, where: str) -> str | None:
        if not value:
            return value
        hits = scan(value, where, self.denylist)
        if not hits:
            return value
        found = {f.check for f in hits}
        check = next(c for c in CHECK_ORDER if c in found)
        self.counts[check] = self.counts.get(check, 0) + 1
        return f"[omitted: {check}]"

    def summary(self) -> str | None:
        n = sum(self.counts.values())
        if not n:
            return None
        parts = " ".join(f"{c}={self.counts[c]}" for c in CHECK_ORDER if c in self.counts)
        return f"omitted {n} field(s): {parts}"


def prose(gate: Gate, s: str | None, where: str, limit: int) -> str | None:
    """Prompt text / reasoning: home → ~, pasted bodies dropped, gate, then truncate.
    The gate runs before truncation so a cut can never leave a partial secret behind."""
    return truncate(gate.field(strip_pasted(tilde(s)), where), limit)


# --- git --------------------------------------------------------------------------------

def git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        raise UsageError(f"git {args[0]} failed: {r.stderr.strip()}")
    return r.stdout


def repo_slug(root: Path) -> str:
    try:
        url = git(root, "remote", "get-url", "origin").strip()
    except UsageError:
        return root.name
    m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?/?$", url)
    return m.group(1) if m else root.name


# --- export -----------------------------------------------------------------------------

def repo_files(root: Path, paths: list[str]) -> list[str]:
    """Sibling files as repo-relative POSIX paths. Absolute paths inside `root` are made
    relative; absolute paths elsewhere (scratchpads under /tmp, other checkouts) and relative
    paths that climb out of the repo are dropped, since they carry local usernames and paths."""
    out: list[str] = []
    for p in paths:
        p = p.replace("\\", "/")
        if p.startswith("/") or re.match(r"^[A-Za-z]:/", p):
            try:
                rel = Path(os.path.normpath(p)).relative_to(root).as_posix()
            except ValueError:
                continue
        else:
            rel = os.path.normpath(p).replace("\\", "/")
            if rel == ".." or rel.startswith("../"):
                continue
        if rel and rel != "." and rel not in out:
            out.append(rel)
    return out


def _hq_block(gate: Gate, root: Path, prompt: str, limit: int) -> dict | None:
    ref = hq.parse(prompt or "")
    if ref is None:
        return None
    ref = hq.resolve(root, ref)
    return {
        "kind": ref.kind,
        "task": gate.field(tilde(ref.task), "hq.task"),
        "task_title": gate.field(tilde(ref.task_title), "hq.task_title"),
        "goal": truncate(gate.field(strip_pasted(tilde(ref.task_goal)), "hq.goal"), limit),
        "round": ref.round,
    }


def build(root: Path, files: list[str], denylist, limit: int, err) -> tuple[dict, Gate]:
    events = store.read_all(root)
    resolve.stamp(root, events, persist=False)
    by_id = {e.id: e for e in events}
    gate = Gate(denylist)
    out_files, used_prompts, source_hits = [], [], []

    for rel in files:
        n_lines = len((root / rel).read_text(encoding="utf-8", errors="replace").splitlines())
        lines = []
        for n in range(1, n_lines + 1):
            bl, text, matches = resolve.find(root, rel, n, events)
            text = tilde(text)
            source_hits += scan(text or "", f"{rel}:{n}", denylist)
            row = {
                "n": n,
                "text": text,
                "commit": bl.commit[:10] if bl else None,
                "author": tilde(bl.author) if bl else None,
                "date": dt.datetime.fromtimestamp(bl.author_time, dt.timezone.utc).strftime("%Y-%m-%d") if bl else None,
                "match": None,
            }
            if matches:
                top = matches[0]
                e = top.edit
                pid = e.prompt_id if (e.prompt_id and e.prompt_id in by_id) else None
                if pid and pid not in used_prompts:
                    used_prompts.append(pid)
                row["match"] = {
                    "edit_id": e.id,
                    "prompt_id": pid,
                    "why": top.why,
                    "ts": e.ts,
                    "tool": e.tool,
                    "agent": e.agent,
                    "model": e.model,
                    "session": short_session(e.session),
                    "commit": e.commit[:10] if e.commit else None,
                    "reasoning": prose(gate, e.reasoning, f"reasoning:{e.id}", limit),
                }
            lines.append(row)
        out_files.append({"path": rel, "lines": lines})

    if source_hits:
        for f in source_hits:
            print(f"source line {f.check} ({f.severity}): {f.where}  {f.excerpt}", file=err)
        raise GateError(f"{len(source_hits)} hit(s) in source line text; nothing written")

    prompts = {}
    for pid in used_prompts:
        p = by_id[pid]
        prompts[pid] = {
            "text": prose(gate, p.prompt, f"prompt:{pid}", limit),
            "ts": p.ts,
            "session": short_session(p.session),
            "hq": _hq_block(gate, root, p.prompt, limit),
            "files": repo_files(root, resolve.siblings(events, pid)),
        }

    head = git(root, "rev-parse", "HEAD").strip()
    data = {
        "version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": repo_slug(root),
        "rev": head,
        "files": out_files,
        "prompts": prompts,
    }
    return data, gate


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="export_demo.py", description="Export demo provenance data (HEAD only).")
    p.add_argument("--root", metavar="DIR")
    p.add_argument("--file", action="append", metavar="PATH", help="repeatable; defaults to the demo files")
    p.add_argument("--out", metavar="PATH", default=DEFAULT_OUT, help="relative paths resolve against --root")
    p.add_argument("--max-prompt-chars", type=int, default=4000, metavar="N")
    p.add_argument("--no-denylist", action="store_true", help="allow exporting when no denylist is found")
    return p


def run(argv, err, box) -> int:
    args = _parser().parse_args(argv)
    if args.max_prompt_chars < 1:
        raise UsageError("--max-prompt-chars must be positive")
    root = Path(args.root).resolve() if args.root else store.repo_root()
    if not root.is_dir():
        raise UsageError("--root is not a directory")
    git(root, "rev-parse", "--git-dir")

    denylist = audit_public.load_denylist(None, root)
    box.append(denylist)
    if denylist is None and not args.no_denylist:
        raise UsageError(f"no denylist (set ${audit_public.DENYLIST_ENV} or create "
                         f"{audit_public.DENYLIST_FILE}); pass --no-denylist to export anyway")

    files = []
    for f in args.file or DEFAULT_FILES:
        full = (root / f).resolve()  # absolute f replaces root; symlinks are followed
        if full != root and root not in full.parents:
            raise UsageError(f"{f}: outside --root")
        rel = full.relative_to(root).as_posix()
        if not full.is_file():
            print(f"export_demo: skipping {rel}: not found", file=err)
            continue
        # HEAD only: `git status` does not list ignored files, so require the path in HEAD
        r = subprocess.run(["git", "cat-file", "-e", f"HEAD:{rel}"], cwd=root, capture_output=True)
        if r.returncode != 0:
            raise UsageError(f"{rel}: not tracked at HEAD")
        files.append(rel)
    if not files:
        raise UsageError("no exportable files")
    dirty = git(root, "status", "--porcelain", "--", *files).strip()
    # `git status` hides --skip-worktree / --assume-unchanged files: compare blobs directly
    changed = [rel for rel in files
               if git(root, "hash-object", "--", rel).strip() != git(root, "rev-parse", f"HEAD:{rel}").strip()]
    if dirty or changed:
        raise UsageError("exported files have uncommitted changes:\n" + (dirty or "\n".join(changed)))

    data, gate = build(root, files, denylist, args.max_prompt_chars, err)
    if gate.summary():
        print(gate.summary(), file=err)

    text = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
    survivors = rescan(data, text, denylist)
    if survivors:
        for f in survivors:
            print(f"output {f.check} ({f.severity}): {f.where}  {f.excerpt}", file=err)
        raise GateError(f"{len(survivors)} hit(s) survived in the output; nothing written")

    size = len(text.encode("utf-8"))
    if size > SIZE_WARN:
        print(f"export_demo: warning: output is {size / 1048576:.2f} MB (over 1.5 MB)", file=err)

    out = Path(args.out)
    out = out if out.is_absolute() else root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, out)
    n_match = sum(1 for f in data["files"] for l in f["lines"] if l["match"])
    print(f"wrote {os.path.relpath(out, root)}: {len(files)} file(s), {n_match} matched line(s), "
          f"{len(data['prompts'])} prompt(s), {size} bytes", file=err)
    return 0


def main(argv: list[str] | None = None, err=None) -> int:
    err = err or sys.stderr
    box: list = []

    def say(msg: str) -> None:
        print(f"export_demo: {audit_public.redact(msg, box[0] if box else None)}", file=err)

    class _Redacting:
        def write(self, s):
            return err.write(audit_public.redact(s, box[0] if box else None))

        def flush(self):
            err.flush()

    try:
        return run(argv, _Redacting(), box)
    except SystemExit as e:  # argparse
        return int(e.code) if isinstance(e.code, int) else 2
    except UsageError as e:
        say(str(e))
        return 2
    except GateError as e:
        say(str(e))
        return 1
    except Exception as e:  # never leak a denylist term through a traceback
        say(f"error: {type(e).__name__}: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
