"""End-to-end per agent: install hooks, run the exact installed command strings through `sh -c` with
synthetic payloads on stdin, commit, then query with `python3 -m gitmotive why` as a subprocess."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))

from gitmotive import cli  # noqa: E402

ORIGINAL = "def fetch(url):\n    return http.get(url)\n"
OLD = "    return http.get(url)\n"
NEW = ("    for attempt in range(3):\n        try:\n            return http.get(url)\n"
       "        except http.Error:\n            time.sleep(2 ** attempt)\n    raise\n")
PROMPT = "add retry with exponential backoff to fetch()"
REASONING = "Wrapping the call in a retry loop; 3 attempts with backoff since the upstream flakes."
MODEL = "claude-sonnet-4-5-20250929"


def _env(home: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GITMOTIVE_")}
    env["HOME"] = str(home)
    env["PYTHONPATH"] = str(PKG)
    return env


def git(root, *a):
    return subprocess.run(["git", *a], cwd=root, capture_output=True, text=True, check=True).stdout


@contextlib.contextmanager
def scratch():
    """Temp git repo plus temp HOME; cwd and HOME/GITMOTIVE_* env restored afterwards."""
    saved_cwd = os.getcwd()
    saved_env = {k: os.environ.get(k) for k in ("HOME", "GITMOTIVE_STORE", "GITMOTIVE_HOME")}
    with tempfile.TemporaryDirectory() as d:
        root, home = Path(d) / "repo", Path(d) / "home"
        root.mkdir()
        home.mkdir()
        os.environ["HOME"] = str(home)
        os.environ.pop("GITMOTIVE_STORE", None)
        os.environ.pop("GITMOTIVE_HOME", None)
        try:
            git(root, "init", "-q")
            git(root, "config", "user.email", "t@t")
            git(root, "config", "user.name", "t")
            (root / "fetch.py").write_text(ORIGINAL)
            git(root, "add", "fetch.py")
            git(root, "commit", "-qm", "init")
            os.chdir(root)
            yield root, home
        finally:
            os.chdir(saved_cwd)
            for k, v in saved_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def install(agent: str) -> None:
    with contextlib.redirect_stdout(io.StringIO()):
        assert cli.main(["install", "--agent", agent]) == 0


def run_hook(command: str, payload: dict, cwd: Path, home: Path) -> None:
    r = subprocess.run(["sh", "-c", command], input=json.dumps(payload), cwd=cwd, env=_env(home),
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    assert "capture error" not in r.stderr, r.stderr


def why(root: Path, home: Path, target: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "gitmotive", "why", target], cwd=root, env=_env(home),
                          capture_output=True, text=True, timeout=30)


def edit_file(root: Path) -> None:
    (root / "fetch.py").write_text(ORIGINAL.replace(OLD, NEW))


def commit(root: Path) -> None:
    git(root, "add", "fetch.py")
    git(root, "commit", "-qm", "add retry")


def assert_untouched_line(root: Path, home: Path) -> None:
    r = why(root, home, "fetch.py:1")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "(none recorded)" in r.stdout, r.stdout


def test_claude_installed_hooks():
    with scratch() as (root, home):
        install("claude")
        cfg = json.loads((root / ".claude" / "settings.json").read_text())
        prompt_cmd = cfg["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        edit_cmd = cfg["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
        assert "gitmotive capture" in prompt_cmd and "gitmotive capture" in edit_cmd

        session, tuid = "sess-claude-1", "toolu_01"
        transcript = home / "transcript.jsonl"
        recs = [
            {"type": "user", "message": {"role": "user", "content": PROMPT}},
            {"type": "assistant", "message": {"role": "assistant", "model": MODEL, "content": [
                {"type": "text", "text": REASONING},
                {"type": "tool_use", "id": tuid, "name": "Edit", "input": {}},
            ]}},
        ]
        transcript.write_text("\n".join(json.dumps(r) for r in recs) + "\n")

        run_hook(prompt_cmd, {"hook_event_name": "UserPromptSubmit", "session_id": session,
                              "cwd": str(root), "transcript_path": str(transcript), "prompt": PROMPT},
                 root, home)
        edit_file(root)
        run_hook(edit_cmd, {"hook_event_name": "PostToolUse", "session_id": session, "cwd": str(root),
                            "transcript_path": str(transcript), "tool_use_id": tuid, "tool_name": "Edit",
                            "tool_input": {"file_path": str(root / "fetch.py"),
                                           "old_string": OLD, "new_string": NEW}},
                 root, home)
        commit(root)

        r = why(root, home, "fetch.py:6")
        assert r.returncode == 0, r.stdout + r.stderr
        assert PROMPT in r.stdout, r.stdout
        assert "retry loop" in r.stdout, r.stdout
        assert "model claude-" in r.stdout, r.stdout
        assert_untouched_line(root, home)


def test_cursor_installed_hooks_workspace_roots_only():
    with scratch() as (root, home):
        install("cursor")
        cfg = json.loads((root / ".cursor" / "hooks.json").read_text())
        prompt_cmd = cfg["hooks"]["beforeSubmitPrompt"][0]["command"]
        edit_cmd = cfg["hooks"]["afterFileEdit"][0]["command"]
        assert "--agent cursor" in prompt_cmd and "--agent cursor" in edit_cmd

        # Current Cursor payloads: hook_event_name + workspace_roots, no cwd. Run from elsewhere.
        elsewhere = home
        conv = "conv-cursor-1"
        run_hook(prompt_cmd, {"conversation_id": conv, "generation_id": "g1",
                              "hook_event_name": "beforeSubmitPrompt", "workspace_roots": [str(root)],
                              "prompt": PROMPT, "attachments": []},
                 elsewhere, home)
        edit_file(root)
        run_hook(edit_cmd, {"conversation_id": conv, "generation_id": "g2",
                            "hook_event_name": "afterFileEdit", "workspace_roots": [str(root)],
                            "file_path": str(root / "fetch.py"),
                            "edits": [{"old_string": OLD, "new_string": NEW}]},
                 elsewhere, home)
        commit(root)

        store_file = root / ".gitmotive" / "events.jsonl"
        kinds = [json.loads(l)["kind"] for l in store_file.read_text().splitlines() if l.strip()]
        assert kinds == ["prompt", "edit"], kinds
        assert not (elsewhere / ".gitmotive").exists()
        assert not (home / ".gitmotive").exists()

        r = why(root, home, "fetch.py:6")
        assert r.returncode == 0, r.stdout + r.stderr
        assert PROMPT in r.stdout, r.stdout
        assert "via cursor" in r.stdout, r.stdout
        assert_untouched_line(root, home)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
