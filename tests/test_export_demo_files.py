"""scripts/export_demo.py: a prompt's sibling `files` list keeps only repo-relative paths.

Kept apart from tests/test_export_demo.py because that file is one of the exporter's default
demo files, and the exporter refuses to export files with uncommitted changes.
Self-match rule: the scratchpad path is built by concatenation at runtime.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_export_demo as t  # noqa: E402
from test_export_demo import ROOT  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))


def test_sibling_files_are_repo_relative_only():
    scratch = ("/" + "tmp/claude-1000/-" + "home-someuser-development-repo/"
               "adb86f35-03aa-4ab0-961c-01a147581c47/scratchpad/walk.mjs")
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        root, dl, env = t.setup(d)
        old = dict(os.environ)
        os.environ.update(env)
        try:
            ts = t.store.now()
            for i, f in enumerate([scratch, str(root.resolve() / "lib" / "inside.py"), "../elsewhere/x.py",
                                   "docs/notes.md", "/" + "home/someuser/other/y.py"]):
                t.edit(root, ts + i, f"sib{i}", "pa", f, "x\n")
        finally:
            os.environ.clear()
            os.environ.update(old)
        out = d / "data.json"
        r = t.run(root, env, "--file", "app.py", "--out", str(out))
        assert r.returncode == 0, r.stderr
        files = json.loads(out.read_text())["prompts"]["pa"]["files"]
        assert files == ["app.py", "lib/inside.py", "docs/notes.md"], files
        raw = out.read_text()
        assert "/" + "tmp/" not in raw and "-" + "home-" not in raw and "scratchpad" not in raw


def test_repo_files_unit():
    import export_demo
    root = Path("/" + "srv/repo")
    got = export_demo.repo_files(root, ["a.py", "./b/c.py", "/" + "srv/repo/d.py", "/" + "srv/other/e.py",
                                        "../f.py", "C:\\Users\\x\\g.py", "a.py"])
    assert got == ["a.py", "b/c.py", "d.py"], got


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"ok: {len(fns)} test(s)")
