"""resolve.stamp: in-memory stamping with persist=False never touches the store file."""
import contextlib
import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))

from gitmotive import cli, resolve, store  # noqa: E402


def git(root, *a):
    return subprocess.run(["git", *a], cwd=root, capture_output=True, text=True, check=True).stdout


@contextlib.contextmanager
def env(**kv):
    saved = {k: os.environ.get(k) for k in kv}
    try:
        for k, v in kv.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def make_repo(d: Path) -> tuple[Path, str]:
    """A repo with one committed agent edit recorded in the store (unstamped). Returns (root, sha)."""
    root = d / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")
    src = root / "fetch.py"
    src.write_text("def fetch(url):\n    return http.get(url)\n")
    git(root, "add", "fetch.py")
    git(root, "commit", "-qm", "init")
    new = "def fetch(url):\n    for attempt in range(3):\n        return http.get(url)\n"
    ts = store.now() - 60
    store.append(store.Event(kind="prompt", session="s", ts=ts, id="p1", prompt="add retry"), root)
    store.append(store.Event(kind="edit", session="s", ts=ts, id="e1", file="fetch.py", tool="Edit",
                             prompt_id="p1", old="    return http.get(url)\n", new=new), root)
    src.write_text(new)
    git(root, "add", "fetch.py")
    git(root, "commit", "-qm", "add retry")
    return root, git(root, "rev-parse", "HEAD").strip()


def check_no_persist(root: Path, sha: str) -> None:
    path = store.events_path(root)
    before = path.read_bytes()
    events = store.read_all(root)
    assert resolve.stamp(root, events, persist=False) == 1
    edit = [e for e in events if e.kind == "edit"][0]
    assert edit.commit == sha, edit.commit
    assert path.read_bytes() == before
    assert all(e.commit is None for e in store.read_all(root))


def test_no_persist_user_scope():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        with env(GITMOTIVE_HOME=str(d / "home"), GITMOTIVE_STORE="user"):
            root, sha = make_repo(d)
            path = store.events_path(root)
            assert str(path).startswith(str(d / "home")), path
            assert not (root / store.STORE_DIR).exists()
            check_no_persist(root, sha)


def test_no_persist_repo_scope():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        with env(GITMOTIVE_HOME=str(d / "home"), GITMOTIVE_STORE=None):
            root, sha = make_repo(d)
            assert store.events_path(root) == root / store.STORE_DIR / store.EVENTS_FILE
            check_no_persist(root, sha)


def test_persist_rewrites_store():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        with env(GITMOTIVE_HOME=str(d / "home"), GITMOTIVE_STORE=None):
            root, sha = make_repo(d)
            events = store.read_all(root)
            assert resolve.stamp(root, events) == 1
            reread = [e for e in store.read_all(root) if e.kind == "edit"]
            assert reread[0].commit == sha
            # already stamped: nothing pending, nothing to do
            assert resolve.stamp(root, store.read_all(root)) == 0


def test_cmd_stamp_output():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        cwd = os.getcwd()
        with env(GITMOTIVE_HOME=str(d / "home"), GITMOTIVE_STORE=None):
            root, sha = make_repo(d)
            try:
                os.chdir(root)
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    assert cli.cmd_stamp([]) == 0
                assert out.getvalue() == "stamped 1 edit(s)\n", out.getvalue()
                # no edit waiting: prints nothing, as before
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    assert cli.cmd_stamp([]) == 0
                assert out.getvalue() == "", out.getvalue()
            finally:
                os.chdir(cwd)
            assert [e.commit for e in store.read_all(root) if e.kind == "edit"] == [sha]


def test_layering():
    cli_src = (PKG / "gitmotive" / "cli.py").read_text()
    for name in ("def _stamp", "_stamp(", "_commit_has", "_blob_lines"):
        assert name not in cli_src.replace("cmd_stamp(", ""), name
    res_src = (PKG / "gitmotive" / "resolve.py").read_text()
    assert "import cli" not in res_src and "from .cli" not in res_src and "cli." not in res_src


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
