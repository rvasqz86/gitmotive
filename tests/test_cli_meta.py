"""CLI meta: --version, help, single-source USAGE, experimental labels."""
import contextlib
import inspect
import io
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))

from gitmotive import cli  # noqa: E402

NOTE = "note: {} support is experimental (prompt + edits only; payload shape not fully documented)"


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue(), err.getvalue()


@contextlib.contextmanager
def scratch():
    """Temp git repo as cwd plus temp HOME; restored afterwards."""
    saved_cwd, saved_env = os.getcwd(), dict(os.environ)
    with tempfile.TemporaryDirectory() as d:
        root, home = Path(d) / "repo", Path(d) / "home"
        root.mkdir()
        home.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        os.environ["HOME"] = str(home)
        for k in [k for k in os.environ if k.startswith("GITMOTIVE_")]:
            del os.environ[k]
        os.chdir(root)
        try:
            yield root, home
        finally:
            os.chdir(saved_cwd)
            os.environ.clear()
            os.environ.update(saved_env)


def test_version():
    for flag in ("--version", "-V"):
        code, out, _ = run([flag])
        assert code == 0, flag
        assert out == "gitmotive 0.1.0\n", out


def test_help_flags_print_doc():
    for argv in (["help"], ["-h"], ["--help"]):
        code, out, _ = run(argv)
        assert code == 0, argv
        assert out.strip() == cli.__doc__.strip(), argv


def test_help_one_command():
    code, out, _ = run(["help", "why"])
    assert code == 0
    assert "git motive <file>:<line>" in out
    for other in ("log", "stamp", "install", "capture"):
        assert f"gitmotive {other}" not in out, out
    assert out.strip() == cli._usage_entry("why").strip()


def test_bare_prints_help_exit_2():
    code, out, _ = run([])
    assert code == 2
    assert out.strip() == cli.__doc__.strip()


def test_usage_keys_and_doc():
    assert list(cli.USAGE) == ["why", "log", "stamp", "install", "capture", "help"]
    for k, (usage, desc) in cli.USAGE.items():
        assert k in cli.__doc__, k
        assert usage in cli.__doc__, usage


def test_every_dispatched_command_has_entry():
    src = inspect.getsource(cli.main)
    dispatched = set(re.findall(r'cmd == "([a-z]+)"', src))
    dispatched |= {c for t in re.findall(r"cmd in \(([^)]*)\)", src) for c in re.findall(r'"([a-z]+)"', t)}
    assert {"why", "log", "stamp", "install", "capture", "help"} <= dispatched, dispatched
    for c in dispatched:
        assert c in cli.USAGE, c


def test_doc_marks_experimental_and_source():
    doc = cli.__doc__
    assert "copilot (experimental)" in doc
    assert "omp (experimental)" in doc
    assert "--source" in doc
    assert cli.EXPERIMENTAL == ("copilot", "omp")


def test_install_note_copilot_once():
    with scratch():
        code, out, _ = run(["install", "--agent", "copilot,claude"])
        assert code == 0, out
        notes = [l for l in out.splitlines() if l.startswith("note: ")]
        assert notes == [NOTE.format("copilot")], notes


def test_install_note_all():
    with scratch():
        code, out, _ = run(["install", "--agent", "all"])
        assert code == 0, out
        notes = [l for l in out.splitlines() if l.startswith("note: ")]
        assert notes == [NOTE.format("copilot"), NOTE.format("omp")], notes


def test_install_claude_no_note():
    with scratch():
        code, out, _ = run(["install"])
        assert code == 0, out
        assert "experimental" not in out


def test_file_line_dispatch_unchanged():
    with scratch() as (root, _home):
        (root / "a.py").write_text("x = 1\n")
        code, out, _ = run(["a.py:1"])
        assert code == 1, out          # no events: routed to why, which reports none recorded
        assert out.startswith("a.py:1\n"), out
        assert "intent   (none recorded)" in out, out


def _snapshot(*dirs):
    return {str(p): p.stat().st_mtime_ns for d in dirs for p in Path(d).rglob("*")}


def test_subcommand_help_flag_prints_entry_and_runs_nothing():
    for cmd in cli.USAGE:
        for flag in ("-h", "--help"):
            for argv in ([cmd, flag], [cmd, "--agent", "all", flag]):
                with scratch() as (root, home):
                    before = _snapshot(root, home)
                    code, out, err = run(argv)
                    assert code == 0, (argv, err)
                    assert out.strip() == cli._usage_entry(cmd).strip(), (argv, out)
                    assert _snapshot(root, home) == before, argv   # nothing written (no hooks installed)


def test_install_help_writes_no_hooks():
    for flag in ("-h", "--help"):
        for scope in ("repo", "user"):
            with scratch() as (root, home):
                code, out, _ = run(["install", "--scope", scope, "--agent", "all", flag])
                assert code == 0
                assert "note:" not in out, out
                written = [p for d in (root, home) for p in Path(d).rglob("*")
                           if ".git" not in p.relative_to(d).parts]
                assert written == [], written


def test_help_fits_80_columns():
    assert cli.HELP_WIDTH == 80
    for line in cli.__doc__.splitlines():
        assert len(line) <= cli.HELP_WIDTH, line

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
