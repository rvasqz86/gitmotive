"""Agent and model on events: capture, installers (run through sh -c), upsert, why output."""
import contextlib
import dataclasses
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))

from gitmotive import capture, cli, store  # noqa: E402


@contextlib.contextmanager
def scratch_repo():
    """Temp git repo as cwd, HOME and GITMOTIVE_HOME pointed at a temp dir."""
    old_cwd, old_env = os.getcwd(), dict(os.environ)
    with tempfile.TemporaryDirectory() as d:
        root, home = Path(d) / "repo", Path(d) / "home"
        root.mkdir()
        home.mkdir()
        os.environ["HOME"] = str(home)
        os.environ["GITMOTIVE_HOME"] = str(home / ".gitmotive")
        os.environ.pop("GITMOTIVE_STORE", None)
        for a in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
            subprocess.run(["git", *a], cwd=root, check=True, capture_output=True)
        os.chdir(root)
        try:
            yield root.resolve(), home
        finally:
            os.chdir(old_cwd)
            os.environ.clear()
            os.environ.update(old_env)


def _transcript(path, tuid, model="claude-opus-5-5"):
    msg = {"role": "assistant", "content": [{"type": "text", "text": "Adding a guard."},
                                            {"type": "tool_use", "id": tuid, "name": "Edit", "input": {}}]}
    if model:
        msg["model"] = model
    recs = [{"type": "user", "message": {"role": "user", "content": "guard it"}},
            {"type": "assistant", "message": msg}]
    Path(path).write_text("\n".join(json.dumps(r) for r in recs) + "\n")


def _claude_edit(root, transcript=None, tuid="toolu_1", **extra):
    p = {"hook_event_name": "PostToolUse", "session_id": "sess-1", "cwd": str(root),
         "tool_name": "Edit", "tool_use_id": tuid,
         "tool_input": {"file_path": str(root / "a.py"), "old_string": "x = 1", "new_string": "x = 2"}}
    if transcript:
        p["transcript_path"] = str(transcript)
    p.update(extra)
    return p


def _cursor_edit(root, **extra):
    p = {"conversation_id": "conv-1", "generation_id": "g1", "cwd": str(root),
         "file_path": str(root / "a.py"), "edits": [{"old_string": "x = 1", "new_string": "x = 2"}]}
    p.update(extra)
    return p


def test_old_lines_load_with_none():
    line = json.dumps({"kind": "edit", "session": "s", "ts": 1.0, "id": "abc", "file": "a.py"})
    ev = store.Event.from_json(line)
    assert ev.agent is None and ev.model is None


def test_field_docs_cover_every_field():
    assert store.FIELD_DOCS.keys() == {f.name for f in dataclasses.fields(store.Event)}


def test_claude_model_from_transcript_and_payload_wins():
    with scratch_repo() as (root, _):
        t = root / "t.jsonl"
        _transcript(t, "toolu_1")
        ev = capture.handle(_claude_edit(root, t))
        assert ev.agent == "claude" and ev.model == "claude-opus-5-5"
        assert ev.reasoning == "Adding a guard."
        ev = capture.handle(_claude_edit(root, t, model="claude-sonnet-5-5"))
        assert ev.model == "claude-sonnet-5-5"
        # no matching tool_use: most recent assistant model in the transcript
        ev = capture.handle(_claude_edit(root, t, tuid="toolu_other"))
        assert ev.model == "claude-opus-5-5"
        # no model anywhere in the transcript or payload: None
        _transcript(t, "toolu_1", model=None)
        ev = capture.handle(_claude_edit(root, t, tuid="toolu_other"))
        assert ev.model is None
        stored = store.read_all(root)
        assert [e.model for e in stored] == ["claude-opus-5-5", "claude-sonnet-5-5", "claude-opus-5-5", None]


def _unflushed_turn_transcript(path):
    """Real failure shape: Claude Code persists the current turn's per-block assistant records
    (the ones carrying message.model) together with the first tool_result, which is after
    PostToolUse fires for the first tool of the turn. At hook time the file holds only earlier
    turns: per-block assistant records with model, the tool_result, and an `api-request-blob`
    record whose message has role assistant, the batched content blocks and no model."""
    rid = "msg_prev"
    recs = [
        {"type": "user", "message": {"role": "user", "content": "first ask"}},
        {"type": "assistant", "message": {"id": rid, "role": "assistant", "model": "claude-opus-5-5",
                                          "content": [{"type": "thinking", "thinking": ""}]}},
        {"type": "assistant", "message": {"id": rid, "role": "assistant", "model": "claude-opus-5-5",
                                          "content": [{"type": "text", "text": "Reading first."}]}},
        {"type": "assistant", "message": {"id": rid, "role": "assistant", "model": "claude-opus-5-5",
                                          "content": [{"type": "tool_use", "id": "toolu_prev",
                                                       "name": "Read", "input": {}}]}},
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_prev", "content": "ok"}]}},
        {"type": "api-request-blob", "hash": "h", "sessionId": "s", "message": {
            "role": "assistant", "content": [{"type": "thinking", "thinking": ""},
                                             {"type": "text", "text": "Reading first."},
                                             {"type": "tool_use", "id": "toolu_prev", "name": "Read",
                                              "input": {}}]}},
        {"type": "api-request", "id": "r", "sessionId": "s"},
        {"type": "file-history-delta", "messageId": "m"},
        # the current turn's assistant record holding toolu_now is not on disk yet
    ]
    Path(path).write_text("\n".join(json.dumps(r) for r in recs) + "\n")


def test_model_when_current_tool_use_not_flushed():
    with tempfile.TemporaryDirectory() as d:
        t = Path(d) / "t.jsonl"
        _unflushed_turn_transcript(t)
        reasoning, model = capture._transcript_context(str(t), "toolu_now")
        assert model == "claude-opus-5-5"
        # the only text on disk belongs to toolu_prev: record none rather than guess
        assert reasoning is None


def test_no_matching_tool_use_records_no_reasoning():
    with scratch_repo() as (root, _):
        t = root / "t.jsonl"
        _transcript(t, "toolu_1")
        ev = capture.handle(_claude_edit(root, t, tuid="toolu_other"))
        assert ev.reasoning is None and ev.model == "claude-opus-5-5"
        assert capture._transcript_context(str(t), None) == (None, "claude-opus-5-5")
        assert store.read_all(root)[-1].reasoning is None


def test_model_when_matched_record_has_no_model():
    """tool_use found only in a model-less record (e.g. api-request-blob): fall back to the most
    recent assistant record that has a model."""
    with tempfile.TemporaryDirectory() as d:
        t = Path(d) / "t.jsonl"
        recs = [
            {"type": "assistant", "message": {"role": "assistant", "model": "claude-opus-5-5",
                                              "content": [{"type": "text", "text": "Plan."}]}},
            {"type": "api-request-blob", "message": {"role": "assistant", "content": [
                {"type": "text", "text": "Plan."},
                {"type": "tool_use", "id": "toolu_b", "name": "Edit", "input": {}}]}},
        ]
        t.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
        assert capture._transcript_context(str(t), "toolu_b") == ("Plan.", "claude-opus-5-5")


def test_transcript_context_wrapper():
    with tempfile.TemporaryDirectory() as d:
        t = Path(d) / "t.jsonl"
        _transcript(t, "toolu_9")
        assert capture._transcript_context(str(t), "toolu_9") == ("Adding a guard.", "claude-opus-5-5")
        assert capture._preceding_assistant_text(str(t), "toolu_9") == "Adding a guard."
        assert capture._transcript_context(None, "toolu_9") == (None, None)


def test_prompt_event_gets_agent_and_payload_model():
    with scratch_repo() as (root, _):
        ev = capture.handle({"hook_event_name": "UserPromptSubmit", "session_id": "s", "cwd": str(root),
                             "prompt": "do it", "model": "claude-opus-5-5"}, source="omp")
        assert ev.agent == "omp" and ev.model == "claude-opus-5-5"


def test_cursor_model():
    with scratch_repo() as (root, _):
        ev = capture.handle(_cursor_edit(root, model="gpt-5"), agent="cursor", event="afterFileEdit")
        assert ev.agent == "cursor" and ev.model == "gpt-5"
        ev = capture.handle(_cursor_edit(root), agent="cursor", event="afterFileEdit")
        assert ev.model is None


def _quiet(fn, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a)


def _edit_commands(root):
    """The edit-hook command each installer wrote, keyed by agent."""
    claude = json.loads((root / ".claude" / "settings.json").read_text())
    omp = json.loads((root / ".omp" / "settings.json").read_text())
    cursor = json.loads((root / ".cursor" / "hooks.json").read_text())
    copilot = json.loads((root / ".github" / "hooks" / "gitmotive.json").read_text())
    return {
        "claude": claude["hooks"]["PostToolUse"][0]["hooks"][0]["command"],
        "omp": omp["hooks"]["PostToolUse"][0]["hooks"][0]["command"],
        "cursor": cursor["hooks"]["afterFileEdit"][0]["command"],
        "copilot": copilot["hooks"]["PostToolUse"][0]["command"],
    }


def test_installed_commands_record_agent():
    with scratch_repo() as (root, home):
        assert _quiet(cli.cmd_install, ["--agent", "all"]) == 0
        cmds = _edit_commands(root)
        assert "--source omp" in cmds["omp"] and "--source copilot" in cmds["copilot"]
        for agent, cmd in cmds.items():
            payload = _cursor_edit(root) if agent == "cursor" else _claude_edit(root)
            r = subprocess.run(["sh", "-c", cmd], input=json.dumps(payload), text=True,
                               capture_output=True, cwd=root, env={**os.environ, "HOME": str(home)})
            assert r.returncode == 0, r.stderr
            last = store.read_all(root)[-1]
            assert last.kind == "edit" and last.agent == agent, (agent, last.agent, r.stderr)


def test_install_upserts_old_entry_and_is_idempotent():
    with scratch_repo() as (root, _):
        p = root / ".omp" / "settings.json"
        p.parent.mkdir()
        old = "PYTHONPATH=/stale /usr/bin/python3 -m gitmotive capture --agent claude"
        p.write_text(json.dumps({"hooks": {
            "UserPromptSubmit": [{"hooks": [{"type": "command", "command": old, "timeout": 10}]}],
            "PostToolUse": [{"hooks": [{"type": "command", "command": old, "timeout": 10}]}],
        }}, indent=2) + "\n")
        assert _quiet(cli.cmd_install, ["--agent", "omp"]) == 0
        cfg = json.loads(p.read_text())
        for event in ("UserPromptSubmit", "PostToolUse"):
            cmds = [h["command"] for e in cfg["hooks"][event] for h in e["hooks"]
                    if "gitmotive capture" in h["command"]]
            assert len(cmds) == 1 and cmds[0].endswith("--agent claude --source omp"), cmds
            assert "/stale" not in cmds[0]
        first = p.read_bytes()
        assert _quiet(cli.cmd_install, ["--agent", "omp"]) == 0
        assert p.read_bytes() == first


def test_install_upserts_flat_lists_idempotently():
    with scratch_repo() as (root, _):
        paths = [root / ".cursor" / "hooks.json", root / ".github" / "hooks" / "gitmotive.json",
                 root / ".claude" / "settings.json"]
        _quiet(cli.cmd_install, ["--agent", "cursor,copilot,claude"])
        first = [p.read_bytes() for p in paths]
        _quiet(cli.cmd_install, ["--agent", "cursor,copilot,claude"])
        assert [p.read_bytes() for p in paths] == first
        cp = json.loads(paths[1].read_text())
        assert all(len(v) == 1 for v in cp["hooks"].values())


def test_install_upserts_stale_post_commit_stamp_line():
    with scratch_repo() as (root, _):
        hook = root / ".git" / "hooks" / "post-commit"
        hook.parent.mkdir(parents=True, exist_ok=True)
        stale = "PYTHONPATH=/stale /usr/bin/python3 -m gitmotive stamp >/dev/null 2>&1 || true\n"
        hook.write_text("#!/bin/sh\necho other-hook\n" + stale)
        assert _quiet(cli.cmd_install, ["--agent", "claude"]) == 0
        body = hook.read_text()
        stamps = [l for l in body.splitlines() if "gitmotive stamp" in l]
        assert len(stamps) == 1 and "/stale" not in stamps[0], body
        assert stamps[0].startswith(cli._python_cmd() + " stamp"), stamps
        assert body.startswith("#!/bin/sh\necho other-hook\n"), body
        first = hook.read_bytes()
        assert _quiet(cli.cmd_install, ["--agent", "claude"]) == 0
        assert hook.read_bytes() == first


def test_python_cmd_installed_vs_source_tree():
    import sysconfig
    pkg_parent = str(Path(cli.__file__).resolve().parent.parent)
    real = sysconfig.get_paths
    try:
        sysconfig.get_paths = lambda *a, **k: {**real(), "purelib": pkg_parent, "platlib": pkg_parent}
        assert cli._python_cmd() == f"{sys.executable} -I -m gitmotive"
        sysconfig.get_paths = lambda *a, **k: {**real(), "purelib": "/nonexistent/site", "platlib": "/nonexistent/site"}
        assert cli._python_cmd() == f"PYTHONPATH={pkg_parent} {sys.executable} -m gitmotive"
    finally:
        sysconfig.get_paths = real


def _why_edited_line(root):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        cli.cmd_why(["a.py:1"])
    return next(l for l in out.getvalue().splitlines() if l.startswith("  edited"))


def test_why_shows_agent_and_model():
    with scratch_repo() as (root, _):
        (root / "a.py").write_text("x = 2\n")
        t = root / "t.jsonl"
        _transcript(t, "toolu_1")
        capture.handle({"hook_event_name": "UserPromptSubmit", "session_id": "sess-1",
                        "cwd": str(root), "prompt": "guard it"})
        capture.handle(_claude_edit(root, t))
        assert _why_edited_line(root).endswith("  via claude  model claude-opus-5-5")


def test_why_old_event_line_unchanged():
    with scratch_repo() as (root, _):
        (root / "a.py").write_text("x = 2\n")
        ev = store.Event(kind="edit", session="sess-old1", ts=1700000000.0, file="a.py", tool="Edit",
                         old="x = 1", new="x = 2")
        store.append(ev, root)
        line = _why_edited_line(root)
        assert "via" not in line and "model" not in line
        assert line.startswith(f"  edited   {cli._fmt_ts(ev.ts)}  by Edit  session sess-old")
        assert line.endswith("]")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
