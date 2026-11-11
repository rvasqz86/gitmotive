import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def ignored(path):
    return git("check-ignore", "-q", "--no-index", path).returncode == 0


def test_no_tracked_build_artifacts():
    r = git("ls-files", "build", "dist", "*.whl", "*.egg-info")
    assert r.returncode == 0 and r.stdout.strip() == "", r.stdout


def test_root_ignores():
    for p in ["build/x.py", "dist/x.whl", "pkg.egg-info/PKG-INFO", ".gitmotive/db", "__pycache__/a.pyc"]:
        assert ignored(p), p


def test_hq_local_only_ignores():
    for p in [".hq/brief-source.md", ".hq/runtime.log", ".hq/runtime.log.1", ".hq/audit-report.md",
              ".hq/audit-report-2.md", ".hq/history-rewrite-plan.md", ".hq/deploy-readiness.md"]:
        assert ignored(p), p


def test_hq_itself_committed():
    for p in [".hq/spec.md", ".hq/architecture.md", ".hq/tasks/01-untrack-build.md"]:
        assert not ignored(p), p


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
