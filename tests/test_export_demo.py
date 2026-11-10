"""scripts/export_demo.py: schema, referenced-only prompts, sanitisation, per-record gate,
whole-output rescan, dirty-file abort, source-line fatal path, store bytes unchanged.

Self-match rule: planted secrets and home paths are built by concatenation at runtime.
The denylist term is synthetic.
"""
import ast
import getpass
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "export_demo.py"
sys.path.insert(0, str(ROOT))

from gitmotive import store  # noqa: E402

TERM = "acme-widgets"
SECRET = "sk" + "-ant-" + "api03_" + "Q" * 24
OTHER_HOME = "/" + "home" + "/someoneelse/" + "notes.txt"
HOME = os.path.expanduser("~")
USER_HOME = "/" + "home/" + getpass.getuser()
HOST = "build" + "." + "corp"


def git(root, *a):
    return subprocess.run(["git", *a], cwd=root, capture_output=True, text=True, check=True).stdout


def base_env(d: Path, denylist: Path | None) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in ("GITMOTIVE_AUDIT_DENYLIST", "GITMOTIVE_STORE")}
    env["GITMOTIVE_HOME"] = str(d / "gmhome")
    env["GITMOTIVE_STORE"] = "user"
    if denylist is not None:
        env["GITMOTIVE_AUDIT_DENYLIST"] = str(denylist)
    return env


def run(root: Path, env: dict, *args):
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args],
                          capture_output=True, text=True, env=env)


def edit(root, ts, eid, pid, file, new, **kw):
    store.append(store.Event(kind="edit", session=kw.pop("session", "sess-abcdef123"), ts=ts, id=eid,
                             file=file, tool="Edit", prompt_id=pid, old="", new=new, **kw), root)


def prompt(root, ts, pid, text, session="sess-abcdef123"):
    store.append(store.Event(kind="prompt", session=session, ts=ts, id=pid, prompt=text), root)


def make_repo(d: Path) -> Path:
    """Repo with app.py whose lines come from six synthetic agent edits, plus an hq task file."""
    root = d / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "tester")
    (root / ".hq" / "tasks").mkdir(parents=True)
    (root / ".hq" / "tasks" / "07-widget.md").write_text(
        "# Task 07: Add the widget\n## Goal\nRender a widget per row.\n")
    lines = {
        "a": "def alpha():  # claude edit with reasoning",
        "h": "def hq_task():  # from an hq prompt",
        "p": "def pasted():  # from a pasted prompt",
        "d": "def deny():  # from a denylisted prompt",
        "s": "def secret():  # from a secret prompt",
        "v": "def deny_v2():  # from a prompt with the term inside an identifier",
        "i": "def host():  # from a prompt naming a private host",
        "x": "def other_file_only():",
    }
    (root / "app.py").write_text("\n".join(lines[k] for k in "ahpdsvi") + "\n")
    (root / "other.py").write_text(lines["x"] + "\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "init")

    ts = store.now() - 600
    sess_path = HOME + "/.claude/projects/x/" + "9f8e7d6c5b4a-session.jsonl"
    prompt(root, ts, "pa", "make alpha; see " + HOME + "/notes.txt and " + USER_HOME + "/w.txt",
           session=sess_path)
    edit(root, ts + 1, "ea", "pa", "app.py", lines["a"] + "\n", session=sess_path,
         reasoning="I will add alpha. " + "r" * 200, agent="claude", model="claude-opus-5-5")
    prompt(root, ts + 2, "ph", "Implement .hq/tasks/07-widget.md, round 1.")
    # stale capture fallback from an older event: under 3 words, dropped by the exporter
    edit(root, ts + 3, "eh", "ph", "app.py", lines["h"] + "\n", reasoning="READY")
    prompt(root, ts + 4, "pp", "fix this <pasted_content id=1>SECRET TRACEBACK BODY</pasted_content> please")
    edit(root, ts + 5, "ep", "pp", "app.py", lines["p"] + "\n")
    prompt(root, ts + 6, "pd", "rename for " + TERM.upper() + " customers")
    edit(root, ts + 7, "ed", "pd", "app.py", lines["d"] + "\n", reasoning="notes are in " + OTHER_HOME)
    prompt(root, ts + 8, "ps", "use key " + SECRET + " here")
    edit(root, ts + 9, "es", "ps", "app.py", lines["s"] + "\n")
    prompt(root, ts + 12, "pv", "move it to ~/" + TERM + "_v2/api.py")
    edit(root, ts + 13, "ev", "pv", "app.py", lines["v"] + "\n")
    prompt(root, ts + 14, "pi", "deploy to " + HOST + " after")
    edit(root, ts + 15, "ei", "pi", "app.py", lines["i"] + "\n")
    # unreferenced: its edit is on a file that is not exported
    prompt(root, ts + 10, "pu", "run gitmotive blame on everything")
    edit(root, ts + 11, "eu", "pu", "other.py", lines["x"] + "\n")
    return root


def setup(d: Path):
    """Build the repo and its store under a temp GITMOTIVE_HOME, restoring os.environ after."""
    old = dict(os.environ)
    os.environ.update(base_env(d, None))
    try:
        root = make_repo(d)
    finally:
        os.environ.clear()
        os.environ.update(old)
    dl = d / "denylist"
    dl.write_text("# synthetic\n" + TERM + "\n")
    return root, dl, base_env(d, dl)


def store_bytes(env, root):
    old = dict(os.environ)
    os.environ.update(env)
    try:
        return store.events_path(root).read_bytes()
    finally:
        os.environ.clear()
        os.environ.update(old)


def test_export_schema_sanitisation_and_gate():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        root, dl, env = setup(d)
        before = store_bytes(env, root)
        out = d / "data.json"
        r = run(root, env, "--file", "app.py", "--out", str(out), "--max-prompt-chars", "60")
        assert r.returncode == 0, r.stderr
        assert store_bytes(env, root) == before, "store file changed"

        raw = out.read_text()
        for stream in (raw, r.stdout, r.stderr):
            assert TERM not in stream.lower(), "denylist term leaked"
            assert SECRET not in stream
            assert "SECRET TRACEBACK BODY" not in stream
            assert HOME + "/" not in stream and USER_HOME + "/" not in stream
            assert HOST not in stream
        assert "gitmotive blame" not in raw
        assert "omitted 5 field(s): secret=1 denylist=2 host=1 path=1" in r.stderr, r.stderr

        data = json.loads(raw)
        assert set(data) == {"version", "generated_at", "repo", "rev", "files", "prompts"}
        assert data["version"] == 1 and len(data["rev"]) == 40
        assert data["rev"] == git(root, "rev-parse", "HEAD").strip()
        assert data["generated_at"].endswith("Z")
        [f] = data["files"]
        assert f["path"] == "app.py" and [l["n"] for l in f["lines"]] == [1, 2, 3, 4, 5, 6, 7]
        for l in f["lines"]:
            assert set(l) == {"n", "text", "commit", "author", "date", "match"}
            assert l["author"] == "tester" and len(l["commit"]) == 10 and len(l["date"]) == 10
            m = l["match"]
            assert set(m) == {"edit_id", "prompt_id", "why", "ts", "tool", "agent", "model",
                              "session", "commit", "reasoning"}
            assert m["commit"] == l["commit"], "stamped in memory"
            assert "same commit" in m["why"]
        ids = {l["match"]["prompt_id"] for l in f["lines"]}
        assert set(data["prompts"]) == ids == {"pa", "ph", "pp", "pd", "ps", "pv", "pi"}
        assert "pu" not in data["prompts"]

        by = {l["match"]["edit_id"]: l["match"] for l in f["lines"]}
        a = by["ea"]
        assert a["agent"] == "claude" and a["model"] == "claude-opus-5-5"
        assert a["session"] == "9f8e7d6c", a["session"]
        assert len(a["reasoning"]) == 60 and a["reasoning"].endswith("…")
        assert by["ed"]["reasoning"] == "[omitted: path]"
        assert by["eh"]["reasoning"] is None, "reasoning under 3 words is dropped"
        assert by["eh"]["session"] == "sess-abc"

        P = data["prompts"]
        assert P["pa"]["text"].startswith("make alpha; see ~/notes.txt and ~/w.txt"), P["pa"]["text"]
        assert P["pa"]["session"] == "9f8e7d6c" and P["pa"]["hq"] is None
        assert P["pa"]["files"] == ["app.py"]
        assert P["pp"]["text"] == "fix this [pasted content omitted] please"
        assert P["pd"]["text"] == "[omitted: denylist]"
        assert P["ps"]["text"] == "[omitted: secret]"
        assert P["pv"]["text"] == "[omitted: denylist]", "substring denylist hit"
        assert P["pi"]["text"] == "[omitted: host]"
        assert P["ph"]["hq"] == {"kind": "implement", "task": ".hq/tasks/07-widget.md",
                                 "task_title": "Task 07: Add the widget",
                                 "goal": "Render a widget per row.", "round": 1}
        for p in P.values():
            assert set(p) == {"text", "ts", "session", "hq", "files"}


def test_dirty_file_aborts():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        root, dl, env = setup(d)
        with (root / "app.py").open("a") as fh:
            fh.write("x = 1\n")
        out = d / "data.json"
        r = run(root, env, "--file", "app.py", "--out", str(out))
        assert r.returncode == 2, (r.returncode, r.stderr)
        assert "uncommitted" in r.stderr and not out.exists()


def test_skip_worktree_and_assume_unchanged_edits_abort():
    """`git status` hides these flags' local edits; the blob comparison must still catch them."""
    for flag in ("--skip-worktree", "--assume-unchanged"):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            root, dl, env = setup(d)
            git(root, "update-index", flag, "app.py")
            with (root / "app.py").open("a") as fh:
                fh.write("x = 1\n")
            assert git(root, "status", "--porcelain", "--", "app.py").strip() == ""
            out = d / "data.json"
            r = run(root, env, "--file", "app.py", "--out", str(out))
            assert r.returncode == 2, (flag, r.returncode, r.stderr)
            assert "uncommitted" in r.stderr and "app.py" in r.stderr and not out.exists(), r.stderr


def test_missing_files_skipped_and_usage():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        root, dl, env = setup(d)
        out = d / "data.json"
        r = run(root, env, "--file", "app.py", "--file", "nope.py", "--out", str(out))
        assert r.returncode == 0, r.stderr
        assert "skipping nope.py" in r.stderr
        assert [f["path"] for f in json.loads(out.read_text())["files"]] == ["app.py"]
        assert run(root, env, "--rev", "HEAD").returncode == 2
        assert run(root, env, "--bogus").returncode == 2
        assert run(root, env, "--file", "nope.py", "--out", str(d / "o2.json")).returncode == 2


def test_no_denylist_exits_2_unless_flag():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        root, _dl, _env = setup(d)
        env = base_env(d, None)
        out = d / "data.json"
        r = run(root, env, "--file", "app.py", "--out", str(out))
        assert r.returncode == 2 and "no denylist" in r.stderr and not out.exists(), r.stderr
        r = run(root, env, "--file", "app.py", "--out", str(out), "--no-denylist")
        assert r.returncode == 0, r.stderr
        assert out.exists()


def test_source_line_hit_is_fatal():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        root, dl, env = setup(d)
        (root / "leak.py").write_text("x = 1\nNAME = '" + TERM + "'\n")
        git(root, "add", "leak.py")
        git(root, "commit", "-qm", "leak")
        out = d / "data.json"
        r = run(root, env, "--file", "app.py", "--file", "leak.py", "--out", str(out))
        assert r.returncode == 1, (r.returncode, r.stderr)
        assert not out.exists()
        assert "source line denylist" in r.stderr and "<denylist:2>" in r.stderr, r.stderr
        assert TERM not in (r.stderr + r.stdout).lower()


def test_whole_output_rescan_blocks_write():
    """A hit in a field the per-record gate does not cover (here: the blame author) survives
    into the serialised output; the rescan must refuse to write."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        root, dl, env = setup(d)
        (root / "b.py").write_text("y = 2\n")
        git(root, "add", "b.py")
        git(root, "commit", "-qm", "b", "--author", "Bob " + TERM + " <b@b>")
        out = d / "data.json"
        r = run(root, env, "--file", "app.py", "--file", "b.py", "--out", str(out))
        assert r.returncode == 1, (r.returncode, r.stderr)
        assert "survived in the output" in r.stderr and not out.exists(), r.stderr
        assert TERM not in (r.stderr + r.stdout).lower()


def test_home_override_still_rewrites_user_home():
    """With $HOME pointing elsewhere (sudo, CI), the login user's /home/<user> is still `~`."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        root, dl, env = setup(d)
        env = dict(env, HOME=str(d / "fakehome"))
        out = d / "data.json"
        r = run(root, env, "--file", "app.py", "--out", str(out))
        assert r.returncode == 0, r.stderr
        raw = out.read_text()
        assert USER_HOME + "/" not in raw and USER_HOME + "/" not in r.stderr
        assert "~/w.txt" in json.loads(raw)["prompts"]["pa"]["text"]


def test_rejects_files_not_in_head():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        root, dl, env = setup(d)
        (root / ".gitignore").write_text("local.cfg\n")
        git(root, "add", ".gitignore")
        git(root, "commit", "-qm", "ignore")
        (root / "local.cfg").write_text("db = x\nuser = y\n")
        (d / "outside.txt").write_text("outside\n")
        (root / "untracked.py").write_text("z = 3\n")
        out = d / "data.json"
        for f, msg in (("local.cfg", "not tracked at HEAD"), ("../outside.txt", "outside --root"),
                       (str(d / "outside.txt"), "outside --root"), ("untracked.py", "not tracked at HEAD")):
            r = run(root, env, "--file", "app.py", "--file", f, "--out", str(out))
            assert r.returncode == 2, (f, r.returncode, r.stderr)
            assert msg in r.stderr and not out.exists(), (f, r.stderr)


def test_rescan_checks_string_leaves_raw():
    """JSON escaping turns `"` into `\\"`, hiding a quoted-assignment secret from the
    serialised-text scan; the raw string-leaf scan must still catch it in an ungated field."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import export_demo
    leak = "api_" + "key = " + '"' + "Z" * 16 + '"'
    data = {"files": [{"lines": [{"match": {"why": leak}}]}], "prompts": {}}
    text = json.dumps(data)
    import audit_public
    assert not export_demo.blocking(audit_public.scan_text(text, "t", None, checks=export_demo.CHECKS))
    hits = export_demo.rescan(data, text, None)
    assert [h.check for h in hits] == ["secret"], hits
    assert "why" in hits[0].where
    # and the substring denylist rule applies in the rescan too
    hits = export_demo.rescan({"author": "x" + TERM + "2"}, "{}", [TERM])
    assert [h.check for h in hits] == ["denylist"] and TERM not in hits[0].excerpt.lower()


def test_substring_denylist_excerpt_masks_secrets():
    """A line with a secret and a non-whole-word denylist hit: no finding's excerpt may carry
    the secret (the substring finding builds its own excerpt)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import export_demo
    line = "k = " + SECRET + " in x" + TERM + "2"
    hits = export_demo.scan(line, "t", [TERM])
    assert {h.check for h in hits} == {"secret", "denylist"}, hits
    for h in hits:
        assert SECRET not in h.excerpt and SECRET[8:] not in h.excerpt, h
        assert TERM not in h.excerpt.lower(), h
    assert any("<denylist:" in h.excerpt for h in hits if h.check == "denylist")
    hits = export_demo.rescan({"author": line}, "{}", [TERM])
    assert hits and all(SECRET[8:] not in h.excerpt for h in hits), hits


def test_short_reasoning_dropped():
    sys.path.insert(0, str(ROOT / "scripts"))
    import export_demo
    for s in (None, "", "READY", "  ok  done \n", "two words"):
        assert export_demo.reasoning_text(s) is None, s
    assert export_demo.reasoning_text("Adding a guard.") == "Adding a guard."


def test_imports_only_library_modules():
    tree = ast.parse(SCRIPT.read_text())
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            mods.add(node.module)
            if node.module == "gitmotive":
                mods |= {"gitmotive." + a.name for a in node.names}
    project = {m for m in mods if m.startswith("gitmotive") or m == "audit_public"}
    assert project == {"gitmotive", "gitmotive.store", "gitmotive.resolve", "gitmotive.hq", "audit_public"}, project
    assert "gitmotive.cli" not in mods


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok {fn.__name__}")
    print(f"{len(fns)} passed")
