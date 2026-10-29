import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gitmotive.adapters import normalize  # noqa: E402


def test_claude_prompt():
    n = normalize({"hook_event_name": "UserPromptSubmit", "session_id": "s", "prompt": "do x"})
    assert n["event"] == "prompt" and n["prompt"] == "do x" and n["session"] == "s"


def test_claude_edit():
    n = normalize({"hook_event_name": "PostToolUse", "session_id": "s", "tool_name": "Edit",
                   "tool_use_id": "t1", "transcript_path": "/t.jsonl",
                   "tool_input": {"file_path": "/r/a.py", "old_string": "a", "new_string": "b"}})
    assert n["event"] == "edit" and n["edits"] == [{"old": "a", "new": "b"}]
    assert n["tool_use_id"] == "t1" and n["transcript_path"] == "/t.jsonl"


def test_claude_write_and_multiedit():
    n = normalize({"hook_event_name": "PostToolUse", "session_id": "s", "tool_name": "Write",
                   "tool_input": {"file_path": "/r/a.py", "content": "whole file"}})
    assert n["edits"] == [{"old": None, "new": "whole file"}]
    n = normalize({"hook_event_name": "PostToolUse", "session_id": "s", "tool_name": "MultiEdit",
                   "tool_input": {"file_path": "/r/a.py", "edits": [{"old_string": "1", "new_string": "2"}, {"old_string": "3", "new_string": "4"}]}})
    assert [e["new"] for e in n["edits"]] == ["2", "4"]


def test_claude_non_file_tool_ignored():
    n = normalize({"hook_event_name": "PostToolUse", "session_id": "s", "tool_name": "Bash",
                   "tool_input": {"command": "ls"}})
    assert n["event"] is None


def test_cursor_prompt():
    n = normalize({"conversation_id": "c1", "generation_id": "g1", "prompt": "fix it", "attachments": []},
                  agent="cursor", event="beforeSubmitPrompt")
    assert n["event"] == "prompt" and n["session"] == "c1"


def test_cursor_edit():
    n = normalize({"conversation_id": "c1", "generation_id": "g2", "file_path": "/r/a.py",
                   "edits": [{"old_string": "", "new_string": "new code"}]},
                  agent="cursor", event="afterFileEdit")
    assert n["event"] == "edit" and n["edits"] == [{"old": "", "new": "new code"}] and n["tool"] == "cursor"


def test_cursor_autodetect():
    n = normalize({"conversation_id": "c1", "file_path": "/r/a.py", "edits": [{"new_string": "x"}]})
    assert n["event"] == "edit" and n["session"] == "c1"


def test_copilot_camelcase_edit():
    n = normalize({"sessionId": "cp1", "toolName": "Edit", "toolArgs": {"file_path": "/r/a.py", "new_string": "z"}},
                  event="postToolUse")
    assert n["event"] == "edit" and n["session"] == "cp1" and n["edits"][0]["new"] == "z"


def test_copilot_camelcase_prompt():
    n = normalize({"sessionId": "cp1", "prompt": "hi"}, event="userPromptSubmitted")
    assert n["event"] == "prompt" and n["session"] == "cp1"


def test_omp_lowercase_tool_any_matcher():
    n = normalize({"hook_event_name": "PostToolUse", "session_id": "o1", "tool_name": "write",
                   "tool_input": {"path": "/r/a.py", "content": "c"}})
    assert n["event"] == "edit" and n["file_path"] == "/r/a.py"
    n = normalize({"hook_event_name": "PostToolUse", "session_id": "o1", "tool_name": "bash",
                   "tool_input": {"command": "ls"}})
    assert n["event"] is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
