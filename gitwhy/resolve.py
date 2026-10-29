"""Resolve a file:line to the intent that produced it."""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import store

TRIVIAL = re.compile(r"^[\s{}()\[\];,]*$")


@dataclass
class BlameInfo:
    commit: str
    orig_file: str
    orig_line: int
    author: str
    author_time: int
    summary: str


def blame_line(root: Path, file: str, line: int) -> Optional[BlameInfo]:
    try:
        out = subprocess.run(
            ["git", "blame", "-p", "-w", "-C", "-C", "-L", f"{line},{line}", "--", file],
            cwd=root, capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    lines = out.splitlines()
    if not lines:
        return None
    head = lines[0].split()
    commit, orig_line = head[0], int(head[1])
    meta = {}
    for l in lines[1:]:
        if l.startswith("\t"):
            break
        k, _, v = l.partition(" ")
        meta[k] = v
    return BlameInfo(
        commit=commit,
        orig_file=meta.get("filename", file),
        orig_line=orig_line,
        author=meta.get("author", ""),
        author_time=int(meta.get("author-time", "0") or 0),
        summary=meta.get("summary", ""),
    )


def line_text(root: Path, file: str, line: int) -> Optional[str]:
    p = root / file
    try:
        with p.open(encoding="utf-8", errors="replace") as f:
            for i, l in enumerate(f, 1):
                if i == line:
                    return l.rstrip("\n")
    except OSError:
        return None
    return None


def _contains_line(hay: Optional[str], needle: str) -> bool:
    if not hay:
        return False
    n = needle.strip()
    if not n or TRIVIAL.match(n) or len(n) < 4:
        return False
    return any(l.strip() == n for l in hay.splitlines())


@dataclass
class Match:
    edit: store.Event
    prompt: Optional[store.Event]
    score: int
    why: str


def find(root: Path, file: str, line: int, events: Optional[list[store.Event]] = None) -> tuple[Optional[BlameInfo], str | None, list[Match]]:
    events = events if events is not None else store.read_all(root)
    by_id = {e.id: e for e in events}
    bl = blame_line(root, file, line)
    text = line_text(root, file, line)
    uncommitted = bl is not None and bl.commit.startswith("0" * 40)

    candidates: list[Match] = []
    files = {file}
    if bl:
        files.add(bl.orig_file)

    for e in events:
        if e.kind != "edit" or e.file not in files:
            continue
        score, reasons = 0, []
        if bl and not uncommitted and e.commit == bl.commit:
            score += 100
            reasons.append("same commit")
        if text and _contains_line(e.new, text):
            score += 50
            reasons.append("line text in edit")
        if uncommitted and e.commit is None:
            score += 10
            reasons.append("uncommitted")
        if score == 0:
            continue
        candidates.append(Match(edit=e, prompt=by_id.get(e.prompt_id or ""), score=score, why=", ".join(reasons)))

    candidates.sort(key=lambda m: (m.score, m.edit.ts), reverse=True)
    return bl, text, candidates


def siblings(events: list[store.Event], prompt_id: Optional[str]) -> list[str]:
    if not prompt_id:
        return []
    seen, out = set(), []
    for e in events:
        if e.kind == "edit" and e.prompt_id == prompt_id and e.file and e.file not in seen:
            seen.add(e.file)
            out.append(e.file)
    return out
