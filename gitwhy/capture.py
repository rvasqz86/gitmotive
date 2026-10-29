"""Claude Code hook entrypoint. Reads one hook payload JSON from stdin, appends an event.

Wired via settings.json:
  UserPromptSubmit -> records the prompt
  PostToolUse (Edit|Write|MultiEdit) -> records the edit, linked to latest prompt in session,
                                        plus the assistant text that preceded the tool call
                                        (best-effort, from transcript_path).

Always exits 0. Never blocks the agent.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

from . import store


def _rel(path: str, root: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(root.resolve()))
    except ValueError:
        return path


def _preceding_assistant_text(transcript_path: Optional[str], tool_use_id: Optional[str]) -> Optional[str]:
    """Walk the transcript JSONL, find the assistant text block(s) just before the given tool_use.
    Falls back to the last assistant text block in the file. Best-effort; returns None on any failure."""
    if not transcript_path or not os.path.exists(transcript_path):
        return None
    try:
        last_text: Optional[str] = None
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = rec.get("message") if isinstance(rec, dict) else None
                if not isinstance(msg, dict) or msg.get("role") != "assistant":
                    continue
                content = msg.get("content")
                if isinstance(content, str):
                    last_text = content.strip() or last_text
                    continue
                if not isinstance(content, list):
                    continue
                texts = []
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text" and block.get("text", "").strip():
                        texts.append(block["text"].strip())
                    if block.get("type") == "tool_use" and tool_use_id and block.get("id") == tool_use_id:
                        # text in this same message, or carried over from previous assistant message
                        return "\n".join(texts) if texts else last_text
                if texts:
                    last_text = "\n".join(texts)
        return last_text
    except OSError:
        return None


def handle(payload: dict) -> Optional[store.Event]:
    event_name = payload.get("hook_event_name", "")
    session = payload.get("session_id", "unknown")
    root = store.repo_root(payload.get("cwd"))

    if event_name == "UserPromptSubmit":
        prompt = payload.get("prompt")
        if not prompt:
            return None
        ev = store.Event(kind="prompt", session=session, ts=store.now(), prompt=prompt)
        store.append(ev, root)
        return ev

    if event_name == "PostToolUse":
        tool = payload.get("tool_name", "")
        ti = payload.get("tool_input") or {}
        file_path = ti.get("file_path")
        if not file_path:
            return None
        events = store.read_all(root)
        p = store.latest_prompt(events, session)
        reasoning = _preceding_assistant_text(payload.get("transcript_path"), payload.get("tool_use_id"))
        rel = _rel(file_path, root)

        if tool == "MultiEdit" and isinstance(ti.get("edits"), list):
            last = None
            for e in ti["edits"]:
                ev = store.Event(
                    kind="edit", session=session, ts=store.now(), file=rel, tool=tool,
                    old=e.get("old_string"), new=e.get("new_string"),
                    reasoning=reasoning, prompt_id=p.id if p else None,
                )
                store.append(ev, root)
                last = ev
            return last

        ev = store.Event(
            kind="edit", session=session, ts=store.now(), file=rel, tool=tool,
            old=ti.get("old_string"),
            new=ti.get("new_string") if "new_string" in ti else ti.get("content"),
            reasoning=reasoning, prompt_id=p.id if p else None,
            raw=None,
        )
        store.append(ev, root)
        return ev

    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    try:
        handle(payload)
    except Exception as e:  # never block the agent
        sys.stderr.write(f"gitwhy capture error: {e}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
