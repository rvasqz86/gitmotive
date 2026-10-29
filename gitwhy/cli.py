"""gitwhy CLI.

  gitwhy why <file>:<line>     why does this line exist
  gitwhy log [file]            prompts recorded, with files they touched
  gitwhy stamp                 tag uncommitted edit events with HEAD (run from post-commit)
  gitwhy install [--agent claude|cursor|copilot|omp|all]
                               wire agent hooks + git post-commit hook in this repo
  gitwhy capture               (internal) hook entrypoint, reads payload on stdin
"""
from __future__ import annotations

import datetime as dt
import json
import os
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

from . import capture, resolve, store


def _fmt_ts(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def _wrap(s: str, indent: str = "    ", width: int = 88) -> str:
    return "\n".join(textwrap.fill(p, width=width, initial_indent=indent, subsequent_indent=indent)
                     if p.strip() else "" for p in s.split("\n"))


def cmd_why(args: list[str]) -> int:
    if not args or ":" not in args[0]:
        print("usage: gitwhy why <file>:<line>", file=sys.stderr)
        return 2
    file, _, line_s = args[0].rpartition(":")
    try:
        line = int(line_s)
    except ValueError:
        print(f"bad line number: {line_s}", file=sys.stderr)
        return 2
    root = store.repo_root()
    file = os.path.relpath(os.path.abspath(file), root)
    events = store.read_all(root)
    bl, text, matches = resolve.find(root, file, line, events)

    print(f"{file}:{line}")
    if text is not None:
        print(f"  | {text}")
    if bl:
        if bl.commit.startswith("0" * 40):
            print("  commit   (uncommitted)")
        else:
            when = dt.datetime.fromtimestamp(bl.author_time).strftime("%Y-%m-%d")
            print(f"  commit   {bl.commit[:10]}  {bl.author}  {when}  {bl.summary}")
    if not matches:
        print("  intent   (none recorded)")
        return 1

    top = matches[0]
    e, p = top.edit, top.prompt
    print(f"  edited   {_fmt_ts(e.ts)}  by {e.tool}  session {e.session[:8]}  [{top.why}]")
    if p:
        print("  prompt")
        print(_wrap(p.prompt))
    if e.reasoning:
        print("  reasoning")
        print(_wrap(e.reasoning))
    sib = [f for f in resolve.siblings(events, e.prompt_id) if f != e.file]
    if sib:
        print("  also changed for same prompt")
        for f in sib:
            print(f"    {f}")
    if len(matches) > 1:
        print(f"  ({len(matches) - 1} older candidate(s); use --all)")
        if "--all" in args:
            for m in matches[1:]:
                pp = m.prompt.prompt if m.prompt else "(no prompt)"
                print(f"    {_fmt_ts(m.edit.ts)} [{m.why}] {pp[:70]}")
    return 0


def cmd_log(args: list[str]) -> int:
    root = store.repo_root()
    events = store.read_all(root)
    filt = os.path.relpath(os.path.abspath(args[0]), root) if args else None
    edits_by_prompt: dict[str, list[store.Event]] = {}
    for e in events:
        if e.kind == "edit":
            edits_by_prompt.setdefault(e.prompt_id or "", []).append(e)
    for p in events:
        if p.kind != "prompt":
            continue
        edits = edits_by_prompt.get(p.id, [])
        files = sorted({e.file for e in edits if e.file})
        if filt and filt not in files:
            continue
        commits = sorted({e.commit[:8] for e in edits if e.commit})
        print(f"{_fmt_ts(p.ts)}  {p.id}  session {p.session[:8]}  {len(edits)} edit(s)  {' '.join(commits)}")
        print(_wrap(p.prompt[:300]))
        for f in files:
            print(f"      {f}")
    return 0


def cmd_stamp(_args: list[str]) -> int:
    root = store.repo_root()
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        changed = set(subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
            cwd=root, capture_output=True, text=True, check=True).stdout.split())
        ctime = int(subprocess.run(["git", "log", "-1", "--format=%ct"], cwd=root, capture_output=True, text=True, check=True).stdout.strip())
    except subprocess.CalledProcessError:
        return 0
    events = store.read_all(root)
    n = 0
    for e in events:
        if e.kind == "edit" and e.commit is None and e.file in changed and e.ts <= ctime + 5:
            e.commit = head
            n += 1
    if n:
        store.rewrite_all(events, root)
    print(f"stamped {n} edit(s) with {head[:8]}")
    return 0


HOOK_CMD = f"{sys.executable} -m gitwhy capture"
AGENTS = ("claude", "cursor", "copilot", "omp")


def _load_json(p: Path) -> dict:
    return json.loads(p.read_text()) if p.exists() else {}


def _claude_style(cfg: dict, cmd: str, prompt_event: str, tool_event: str, matcher: str | None) -> None:
    """Claude Code settings.json hooks shape. Used by Claude Code, omp-hooks, and Copilot's alias mode."""
    hooks = cfg.setdefault("hooks", {})

    def ensure(event: str, m: str | None):
        lst = hooks.setdefault(event, [])
        for entry in lst:
            if any("gitwhy capture" in h.get("command", "") for h in entry.get("hooks", [])):
                return
        entry = {"hooks": [{"type": "command", "command": cmd, "timeout": 10}]}
        if m:
            entry["matcher"] = m
        lst.append(entry)

    ensure(prompt_event, None)
    ensure(tool_event, matcher)


def install_claude(root: Path, cmd: str) -> None:
    p = root / ".claude" / "settings.json"
    p.parent.mkdir(exist_ok=True)
    cfg = _load_json(p)
    _claude_style(cfg, cmd, "UserPromptSubmit", "PostToolUse", "Edit|Write|MultiEdit")
    p.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"wrote {p}")


def install_omp(root: Path, cmd: str) -> None:
    # oh-my-pi via the omp-hooks plugin: Claude-shaped payloads, Claude-shaped settings.
    # Tool names differ from Claude's, so match everything; capture ignores non-file tools.
    p = root / ".omp" / "settings.json"
    p.parent.mkdir(exist_ok=True)
    cfg = _load_json(p)
    _claude_style(cfg, cmd + " --agent claude", "UserPromptSubmit", "PostToolUse", None)
    p.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"wrote {p}  (requires: omp install omp-hooks)")


def install_cursor(root: Path, cmd: str) -> None:
    p = root / ".cursor" / "hooks.json"
    p.parent.mkdir(exist_ok=True)
    cfg = _load_json(p)
    cfg.setdefault("version", 1)
    hooks = cfg.setdefault("hooks", {})
    for event in ("beforeSubmitPrompt", "afterFileEdit"):
        lst = hooks.setdefault(event, [])
        c = f"{cmd} --agent cursor --event {event}"
        if not any("gitwhy capture" in h.get("command", "") for h in lst):
            lst.append({"command": c})
    p.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"wrote {p}")


def install_copilot(root: Path, cmd: str) -> None:
    # PascalCase event keys make Copilot CLI emit Claude-style snake_case payloads and tool names.
    p = root / ".github" / "hooks" / "gitwhy.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    cfg = _load_json(p)
    cfg.setdefault("version", 1)
    hooks = cfg.setdefault("hooks", {})
    for event in ("UserPromptSubmit", "PostToolUse"):
        lst = hooks.setdefault(event, [])
        if not any("gitwhy capture" in h.get("command", "") for h in lst):
            lst.append({"type": "command", "command": f"{cmd} --agent claude", "timeoutSec": 10})
    p.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"wrote {p}")


def cmd_install(args: list[str]) -> int:
    root = store.repo_root()
    pkg_dir = str(Path(__file__).resolve().parent.parent)
    cmd = f"PYTHONPATH={pkg_dir} {HOOK_CMD}"

    agents = ["claude"]
    if "--agent" in args:
        v = args[args.index("--agent") + 1]
        agents = list(AGENTS) if v == "all" else v.split(",")
    for a in agents:
        if a not in AGENTS:
            print(f"unknown agent {a}; choose from {', '.join(AGENTS)} or all", file=sys.stderr)
            return 2
        {"claude": install_claude, "cursor": install_cursor,
         "copilot": install_copilot, "omp": install_omp}[a](root, cmd)

    hook = root / ".git" / "hooks" / "post-commit"
    stamp_line = f"PYTHONPATH={pkg_dir} {sys.executable} -m gitwhy stamp >/dev/null 2>&1 || true\n"
    if hook.exists():
        body = hook.read_text()
        if "gitwhy stamp" not in body:
            hook.write_text(body.rstrip("\n") + "\n" + stamp_line)
    else:
        hook.write_text("#!/bin/sh\n" + stamp_line)
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"wrote {hook}")

    exclude = root / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    body = exclude.read_text() if exclude.exists() else ""
    if ".gitwhy/" not in body:
        exclude.write_text(body.rstrip("\n") + "\n.gitwhy/\n")
    print("excluded .gitwhy/ from git")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "capture":
        return capture.main(rest)
    if cmd == "why":
        return cmd_why(rest)
    if cmd == "log":
        return cmd_log(rest)
    if cmd == "stamp":
        return cmd_stamp(rest)
    if cmd == "install":
        return cmd_install(rest)
    print(__doc__)
    return 2
