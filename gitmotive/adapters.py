"""Normalize hook payloads from different agents into one shape.

Canonical dict returned by normalize():
  {
    "event": "prompt" | "edit" | None,
    "session": str,
    "cwd": str | None,
    "prompt": str | None,                      # prompt events
    "file_path": str | None,                   # edit events
    "edits": [{"old": str|None, "new": str}],  # edit events
    "tool": str | None,
    "tool_use_id": str | None,
    "transcript_path": str | None,
    "agent": str,                              # producing product: source label, else resolved agent
    "model": str | None,                       # payload model, if the agent sends one
  }

Agents:
  claude   Claude Code. hook_event_name + snake_case fields. Also what omp-hooks (oh-my-pi) and
           Copilot CLI's PascalCase-alias mode emit, so they ride this adapter.
  cursor   .cursor/hooks.json. conversation_id, prompt / file_path + edits[]. cwd may be absent;
           workspace_roots[0] stands in. Older payloads have no event name, so install passes --event
           on the command line; current ones also carry hook_event_name.
  copilot  GitHub Copilot CLI camelCase mode (sessionId, toolName, toolArgs). Field names for edit
           tools are not documented; we probe common ones. Prefer the PascalCase alias config, which
           yields Claude-shaped payloads.
"""
from __future__ import annotations

from typing import Any, Optional

EDIT_TOOLS = {"edit", "write", "multiedit", "create_file", "createfile", "replace_string_in_file",
              "insert_edit_into_file", "edit_file", "write_file", "editfiles", "str_replace_editor",
              "apply_patch"}


def _first(d: dict, *keys: str) -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _edits_from_tool_input(ti: dict) -> list[dict]:
    if isinstance(ti.get("edits"), list):
        return [{"old": e.get("old_string", e.get("old")), "new": e.get("new_string", e.get("new", ""))}
                for e in ti["edits"] if isinstance(e, dict)]
    new = _first(ti, "new_string", "content", "new_str", "text", "code", "newText")
    if new is None:
        return []
    return [{"old": _first(ti, "old_string", "old_str", "oldText"), "new": new}]


def _file_from_tool_input(ti: dict) -> Optional[str]:
    return _first(ti, "file_path", "filePath", "path", "target_file", "file")


def normalize(payload: dict, agent: Optional[str] = None, event: Optional[str] = None,
              source: Optional[str] = None) -> dict:
    """agent selects the payload shape; source labels the producing product (e.g. omp emits the
    claude shape but is recorded as omp)."""
    out = {"event": None, "session": "unknown", "cwd": payload.get("cwd"), "prompt": None,
           "file_path": None, "edits": [], "tool": None, "tool_use_id": None, "transcript_path": None}

    agent = agent or detect(payload)
    out["agent"] = source or agent
    model = payload.get("model")
    out["model"] = model if isinstance(model, str) and model else None
    ev = (event or payload.get("hook_event_name") or payload.get("hookEventName") or "").lower()

    if agent == "cursor":
        out["session"] = payload.get("conversation_id") or payload.get("session_id") or "unknown"
        roots = payload.get("workspace_roots")
        if not out["cwd"] and isinstance(roots, list) and roots and isinstance(roots[0], str):
            out["cwd"] = roots[0]
        if "prompt" in payload and (ev in ("", "beforesubmitprompt") or not payload.get("file_path")):
            out["event"], out["prompt"] = "prompt", payload["prompt"]
        elif payload.get("file_path"):
            out["event"] = "edit"
            out["file_path"] = payload["file_path"]
            out["tool"] = "cursor"
            out["edits"] = [{"old": e.get("old_string"), "new": e.get("new_string", "")}
                            for e in payload.get("edits") or [] if isinstance(e, dict)]
        return out

    # claude / copilot / omp-hooks: snake_case or camelCase
    out["session"] = _first(payload, "session_id", "sessionId") or "unknown"
    out["transcript_path"] = _first(payload, "transcript_path", "transcriptPath")
    out["tool_use_id"] = _first(payload, "tool_use_id", "toolUseId", "toolCallId")

    if ev in ("userpromptsubmit", "userpromptsubmitted", "prompt") or ("prompt" in payload and not ev):
        p = payload.get("prompt")
        if p:
            out["event"], out["prompt"] = "prompt", p
        return out

    if ev in ("posttooluse", "tool_result", "edit", "") :
        tool = _first(payload, "tool_name", "toolName") or ""
        ti = _first(payload, "tool_input", "toolInput", "toolArgs", "tool_args", "input", "arguments") or {}
        if not isinstance(ti, dict):
            return out
        fp = _file_from_tool_input(ti)
        if not fp:
            return out
        edits = _edits_from_tool_input(ti)
        if not edits and tool.lower() not in EDIT_TOOLS:
            return out
        out["event"], out["tool"], out["file_path"], out["edits"] = "edit", tool or "unknown", fp, edits
    return out


def detect(payload: dict) -> str:
    if "conversation_id" in payload:   # cursor, with or without hook_event_name
        return "cursor"
    if "sessionId" in payload or "toolName" in payload:
        return "copilot"
    return "claude"
