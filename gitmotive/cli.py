from __future__ import annotations

import datetime as dt
import json
import os
import stat
import sys
import sysconfig
import textwrap
from pathlib import Path

from . import __version__, capture, hq, resolve, store

# Single source of truth for the command list: the module docstring (help) and the docs generator use it.
USAGE: dict[str, tuple[str, str]] = {
    "why": ("git motive <file>:<line>",
            "why does this line exist (also: gitmotive why <file>:<line>)"),
    "log": ("gitmotive log [file]",
            "prompts recorded, with files they touched"),
    "stamp": ("gitmotive stamp",
              "tag uncommitted edit events with HEAD (run from post-commit)"),
    "install": ("gitmotive install [--agent claude|cursor|copilot|omp|all] [--scope repo|user]",
                "copilot (experimental), omp (experimental). "
                "repo: hooks in this repo. user: hooks under ~/, zero repo footprint"),
    "capture": ("gitmotive capture [--agent A] [--event E] [--source S]",
                "(internal) hook entrypoint, reads payload on stdin. "
                "--source S labels the product (e.g. copilot, omp) over the payload agent"),
    "help": ("gitmotive help [cmd] | -h | --help",
             "show this help, or one command's entry. gitmotive --version | -V prints the version"),
}

EXPERIMENTAL: tuple[str, ...] = ("copilot", "omp")
EXPERIMENTAL_NOTE = "note: {agent} support is experimental (prompt + edits only; payload shape not fully documented)"


HELP_WIDTH = 80          # help text fits an 80-column terminal
_HELP_INDENT = 34        # column where descriptions start


def _usage_entry(cmd: str) -> str:
    usage, desc = USAGE[cmd]
    pad = " " * _HELP_INDENT
    lines = textwrap.wrap(desc, width=HELP_WIDTH - _HELP_INDENT, break_on_hyphens=False)
    if len(usage) <= _HELP_INDENT - 4:
        return "\n".join([f"  {usage:<{_HELP_INDENT - 2}}" + lines[0]] + [pad + r for r in lines[1:]])
    return "\n".join([f"  {usage}"] + [pad + r for r in lines])


__doc__ = ("git blame tells you who. git motive tells you why.\n\n"
           + "\n".join(_usage_entry(c) for c in USAGE) + "\n")


def _fmt_ts(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def _wrap(s: str, indent: str = "    ", width: int = 88) -> str:
    return "\n".join(textwrap.fill(p, width=width, initial_indent=indent, subsequent_indent=indent)
                     if p.strip() else "" for p in s.split("\n"))


def cmd_why(args: list[str]) -> int:
    if not args or ":" not in args[0]:
        print("usage: gitmotive why <file>:<line>", file=sys.stderr)
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
    resolve.stamp(root, events)
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
    edited = f"  edited   {_fmt_ts(e.ts)}  by {e.tool}  session {e.session[:8]}  [{top.why}]"
    if e.agent:
        edited += f"  via {e.agent}"
    if e.model:
        edited += f"  model {e.model}"
    print(edited)
    if p:
        print("  prompt")
        print(_wrap(p.prompt))
        ref = hq.parse(p.prompt)
        if ref:
            for line in hq.describe(hq.resolve(root, ref), _wrap):
                print(line)
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
    resolve.stamp(root, events)
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
        ref = hq.parse(p.prompt)
        if ref and ref.kind != "role":
            ref = hq.resolve(root, ref)
            tag = f"[hq {ref.kind}" + (f" r{ref.round}" if ref.round else "") + "]"
            print(_wrap(f"{tag} {ref.task_title or ref.task or ''}".strip()))
        elif ref:
            print(_wrap(f"[hq role {ref.role}]"))
        else:
            print(_wrap(p.prompt[:300]))
        for f in files:
            print(f"      {f}")
    return 0


def cmd_stamp(_args: list[str]) -> int:
    root = store.repo_root()
    events = store.read_all(root)
    # unchanged output: nothing is printed when no edit is waiting for a stamp
    if any(e.kind == "edit" and e.commit is None and e.file for e in events):
        n = resolve.stamp(root, events)
        print(f"stamped {n} edit(s)")
    return 0


def _python_cmd() -> str:
    """How hook commands invoke this gitmotive. Installed into site-packages (wheel, pipx, install.sh
    venv): `<python> -I -m gitmotive`, isolated so a hook run with cwd inside a source checkout never
    imports the checkout's working tree. Running from a source tree: pin it with PYTHONPATH."""
    pkg_dir = Path(__file__).resolve().parent.parent
    site = {Path(sysconfig.get_paths()[k]).resolve() for k in ("purelib", "platlib")}
    if pkg_dir in site:
        return f"{sys.executable} -I -m gitmotive"
    return f"PYTHONPATH={pkg_dir} {sys.executable} -m gitmotive"


AGENTS = ("claude", "cursor", "copilot", "omp")


def _load_json(p: Path) -> dict:
    return json.loads(p.read_text()) if p.exists() else {}


def _claude_style(cfg: dict, cmd: str, prompt_event: str, tool_event: str, matcher: str | None) -> None:
    """Claude Code settings.json hooks shape. Used by Claude Code, omp-hooks, and Copilot's alias mode."""
    hooks = cfg.setdefault("hooks", {})

    def ensure(event: str, m: str | None):
        lst = hooks.setdefault(event, [])
        for entry in lst:
            found = False
            for h in entry.get("hooks", []):
                if "gitmotive capture" in h.get("command", ""):
                    h["command"] = cmd   # upsert: refresh stale paths and labels
                    found = True
            if found:
                return
        entry = {"hooks": [{"type": "command", "command": cmd, "timeout": 10}]}
        if m:
            entry["matcher"] = m
        lst.append(entry)

    ensure(prompt_event, None)
    ensure(tool_event, matcher)


def _upsert_flat(lst: list, entry: dict) -> None:
    """Flat hook list (cursor, copilot): replace the command of an existing gitmotive entry, else append."""
    for h in lst:
        if isinstance(h, dict) and "gitmotive capture" in h.get("command", ""):
            h["command"] = entry["command"]
            return
    lst.append(entry)


def install_claude(root: Path, cmd: str) -> None:
    p = (Path.home() / ".claude" / "settings.json") if root is None else (root / ".claude" / "settings.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    cfg = _load_json(p)
    _claude_style(cfg, cmd, "UserPromptSubmit", "PostToolUse", "Edit|Write|MultiEdit")
    p.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"wrote {p}")


def install_omp(root: Path, cmd: str) -> None:
    # oh-my-pi via the omp-hooks plugin: Claude-shaped payloads, Claude-shaped settings.
    # Tool names differ from Claude's, so match everything; capture ignores non-file tools.
    p = (Path.home() / ".omp" / "agent" / "settings.json") if root is None else (root / ".omp" / "settings.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    cfg = _load_json(p)
    _claude_style(cfg, cmd + " --agent claude --source omp", "UserPromptSubmit", "PostToolUse", None)
    p.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"wrote {p}  (requires: omp install omp-hooks)")


def install_cursor(root: Path, cmd: str) -> None:
    p = (Path.home() / ".cursor" / "hooks.json") if root is None else (root / ".cursor" / "hooks.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    cfg = _load_json(p)
    cfg.setdefault("version", 1)
    hooks = cfg.setdefault("hooks", {})
    for event in ("beforeSubmitPrompt", "afterFileEdit"):
        lst = hooks.setdefault(event, [])
        c = f"{cmd} --agent cursor --event {event}"
        _upsert_flat(lst, {"command": c})
    p.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"wrote {p}")


def install_copilot(root: Path, cmd: str) -> None:
    # PascalCase event keys make Copilot CLI emit Claude-style snake_case payloads and tool names.
    p = (Path.home() / ".copilot" / "hooks" / "gitmotive.json") if root is None else (root / ".github" / "hooks" / "gitmotive.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    cfg = _load_json(p)
    cfg.setdefault("version", 1)
    hooks = cfg.setdefault("hooks", {})
    for event in ("UserPromptSubmit", "PostToolUse"):
        lst = hooks.setdefault(event, [])
        _upsert_flat(lst, {"type": "command", "command": f"{cmd} --agent claude --source copilot", "timeoutSec": 10})
    p.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"wrote {p}")


def cmd_install(args: list[str]) -> int:
    py = _python_cmd()
    scope = args[args.index("--scope") + 1] if "--scope" in args else "repo"
    if scope not in ("repo", "user"):
        print("--scope must be repo or user", file=sys.stderr)
        return 2
    agents = ["claude"]
    if "--agent" in args:
        v = args[args.index("--agent") + 1]
        agents = list(AGENTS) if v == "all" else v.split(",")
    for a in agents:
        if a not in AGENTS:
            print(f"unknown agent {a}; choose from {', '.join(AGENTS)} or all", file=sys.stderr)
            return 2
    for a in dict.fromkeys(agents):
        if a in EXPERIMENTAL:
            print(EXPERIMENTAL_NOTE.format(agent=a))

    if scope == "user":
        # Nothing written into any repo. Hook configs under ~/, events under ~/.gitmotive/repos/<hash>/.
        cmd = f"GITMOTIVE_STORE=user {py} capture"
        for a in agents:
            {"claude": install_claude, "cursor": install_cursor,
             "copilot": install_copilot, "omp": install_omp}[a](None, cmd)
        print("events stored under ~/.gitmotive/repos/  (set GITMOTIVE_STORE=user in your shell so why/log read the same place)")
        print("stamping is lazy: why/log attach edits to commits on read, no git hook needed")
        return 0

    root = store.repo_root()
    cmd = f"{py} capture"
    for a in agents:
        {"claude": install_claude, "cursor": install_cursor,
         "copilot": install_copilot, "omp": install_omp}[a](root, cmd)

    hook = root / ".git" / "hooks" / "post-commit"
    stamp_line = f"{py} stamp >/dev/null 2>&1 || true\n"
    if hook.exists():
        # upsert: drop every existing gitmotive stamp line (stale paths heal), keep everything else
        kept = [l for l in hook.read_text().splitlines(keepends=True) if "gitmotive stamp" not in l]
        body = "".join(kept).rstrip("\n")
        hook.write_text((body + "\n" if body else "#!/bin/sh\n") + stamp_line)
    else:
        hook.write_text("#!/bin/sh\n" + stamp_line)
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"wrote {hook}")

    exclude = root / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    body = exclude.read_text() if exclude.exists() else ""
    if ".gitmotive/" not in body:
        exclude.write_text(body.rstrip("\n") + "\n.gitmotive/\n")
    print("excluded .gitmotive/ from git")
    return 0


def cmd_help(args: list[str]) -> int:
    if not args:
        print(__doc__)
        return 0
    if args[0] not in USAGE:
        print(f"unknown command {args[0]}; choose from {', '.join(USAGE)}", file=sys.stderr)
        return 2
    print(_usage_entry(args[0]))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd in ("--version", "-V"):
        print(f"gitmotive {__version__}")
        return 0
    if cmd in USAGE and ("-h" in rest or "--help" in rest):   # gitmotive install --help: never run it
        return cmd_help([cmd])
    if cmd in ("help", "-h", "--help"):
        return cmd_help(rest)
    if ":" in cmd and cmd.rsplit(":", 1)[1].isdigit():   # git motive file.py:42
        return cmd_why(argv)
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
