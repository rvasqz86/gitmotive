"""End-to-end: simulate Claude Code hook payloads against a scratch repo, commit, stamp, query."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))

from gitwhy import capture, resolve, store  # noqa: E402


def git(root, *a):
    return subprocess.run(["git", *a], cwd=root, capture_output=True, text=True, check=True).stdout


def write_transcript(path, tool_use_id, text):
    recs = [
        {"type": "user", "message": {"role": "user", "content": "add retry to fetch"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": text},
            {"type": "tool_use", "id": tool_use_id, "name": "Edit", "input": {}},
        ]}},
    ]
    Path(path).write_text("\n".join(json.dumps(r) for r in recs) + "\n")


def test_flow():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        git(root, "init", "-q")
        git(root, "config", "user.email", "t@t")
        git(root, "config", "user.name", "t")
        src = root / "fetch.py"
        src.write_text("def fetch(url):\n    return http.get(url)\n")
        git(root, "add", ".")
        git(root, "commit", "-qm", "init")

        session = "sess-abc"
        transcript = root / "transcript.jsonl"
        tuid = "toolu_01"
        write_transcript(transcript, tuid, "Wrapping the call in a retry loop; 3 attempts with backoff since the upstream flakes under load.")

        # 1. prompt hook
        capture.handle({
            "hook_event_name": "UserPromptSubmit", "session_id": session, "cwd": str(root),
            "prompt": "add retry with exponential backoff to fetch()",
        })
        # 2. agent edits file, then PostToolUse hook fires
        new = "def fetch(url):\n    for attempt in range(3):\n        try:\n            return http.get(url)\n        except http.Error:\n            time.sleep(2 ** attempt)\n    raise\n"
        src.write_text(new)
        capture.handle({
            "hook_event_name": "PostToolUse", "session_id": session, "cwd": str(root),
            "transcript_path": str(transcript), "tool_use_id": tuid, "tool_name": "Edit",
            "tool_input": {"file_path": str(src), "old_string": "    return http.get(url)\n", "new_string": new},
        })

        events = store.read_all(root)
        assert [e.kind for e in events] == ["prompt", "edit"]
        assert events[1].prompt_id == events[0].id
        assert "retry loop" in events[1].reasoning
        assert events[1].file == "fetch.py"

        # 3. uncommitted query
        bl, text, m = resolve.find(root, "fetch.py", 6, events)
        assert text.strip() == "time.sleep(2 ** attempt)"
        assert m and m[0].prompt.prompt.startswith("add retry")
        assert "uncommitted" in m[0].why

        # 4. commit + stamp
        git(root, "add", ".")
        git(root, "commit", "-qm", "add retry")
        from gitwhy import cli
        os.chdir(root)
        assert cli.cmd_stamp([]) == 0
        events = store.read_all(root)
        assert events[1].commit == git(root, "rev-parse", "HEAD").strip()

        # 5. committed query: same-commit match
        bl, text, m = resolve.find(root, "fetch.py", 6, events)
        assert bl.commit == events[1].commit
        assert "same commit" in m[0].why
        # unrelated untouched line: no intent
        _, _, m0 = resolve.find(root, "fetch.py", 1, events)
        assert not m0 or m0[0].score < 100

        # 6. CLI output
        rc = cli.cmd_why(["fetch.py:6"])
        assert rc == 0
        print("OK")


if __name__ == "__main__":
    test_flow()
