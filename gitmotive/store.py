"""Append-only event store for gitmotive.

Events live in <repo>/.gitmotive/events.jsonl. One JSON object per line.
Append-only so concurrent hook invocations never corrupt the file.

Event kinds:
  prompt  - a user prompt submitted to the agent
  edit    - a file write/edit performed by the agent (linked to the latest prompt in that session)
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable, Optional

STORE_DIR = ".gitmotive"
EVENTS_FILE = "events.jsonl"


def repo_root(start: Optional[str] = None) -> Path:
    cwd = start or os.getcwd()
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return Path(out)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path(cwd)


def user_home() -> Path:
    return Path(os.environ.get("GITMOTIVE_HOME") or Path.home() / ".gitmotive")


def user_store_dir(root: Path) -> Path:
    import hashlib
    h = hashlib.sha1(str(root.resolve()).encode()).hexdigest()[:16]
    return user_home() / "repos" / h


def events_path(root: Optional[Path] = None) -> Path:
    """Resolution order:
      1. GITMOTIVE_STORE=user  -> ~/.gitmotive/repos/<hash>/events.jsonl   (never touches the repo)
      2. <repo>/.gitmotive/ exists -> use it
      3. ~/.gitmotive/repos/<hash>/ exists -> use it
      4. default <repo>/.gitmotive/
    """
    root = root or repo_root()
    in_repo = root / STORE_DIR / EVENTS_FILE
    user = user_store_dir(root) / EVENTS_FILE
    if os.environ.get("GITMOTIVE_STORE") == "user":
        return user
    if in_repo.exists():
        return in_repo
    if user.exists():
        return user
    return in_repo


@dataclass
class Event:
    kind: str                       # "prompt" | "edit"
    session: str
    ts: float
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    # prompt
    prompt: Optional[str] = None
    # edit
    file: Optional[str] = None      # path relative to repo root
    tool: Optional[str] = None
    old: Optional[str] = None
    new: Optional[str] = None       # new_string, or full content for Write
    reasoning: Optional[str] = None # assistant text immediately preceding the edit
    prompt_id: Optional[str] = None # id of the prompt event this edit belongs to
    commit: Optional[str] = None    # stamped after commit
    raw: Optional[dict] = None      # original hook payload, for forward compat

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, line: str) -> "Event":
        d = json.loads(line)
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


def append(ev: Event, root: Optional[Path] = None) -> None:
    p = events_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(ev.to_json() + "\n")


def read_all(root: Optional[Path] = None) -> list[Event]:
    p = events_path(root)
    if not p.exists():
        return []
    out: list[Event] = []
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(Event.from_json(line))
            except (json.JSONDecodeError, TypeError):
                continue
    return out


def rewrite_all(events: Iterable[Event], root: Optional[Path] = None) -> None:
    """Full rewrite. Only used by non-hook commands (stamp), never by hooks."""
    p = events_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(ev.to_json() + "\n")
    os.replace(tmp, p)


def latest_prompt(events: list[Event], session: str) -> Optional[Event]:
    for ev in reversed(events):
        if ev.kind == "prompt" and ev.session == session:
            return ev
    return None


def now() -> float:
    return time.time()
