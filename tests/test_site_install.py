"""site/install.sh: the curl | sh installer (pipx when present, else a venv plus wrappers)."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPT = ROOT / "site" / "install.sh"
sys.path.insert(0, str(HERE))

import _wheel  # noqa: E402


def _path_without_pipx():
    dirs = [d for d in os.environ.get("PATH", "").split(os.pathsep) if d and not (Path(d) / "pipx").exists()]
    return os.pathsep.join(dirs)


def _env(home, path, **extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GITMOTIVE_", "PIPX_", "PYTHON"))}
    env.update(HOME=str(home), PATH=path, PYTHON=sys.executable, **extra)
    return env


def _run(env, *args, cwd=None):
    return subprocess.run(["sh", str(SCRIPT), *args], env=env, cwd=cwd, capture_output=True, text=True, timeout=600)


def _write_exe(path, body):
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)


def test_sh_syntax():
    r = subprocess.run(["sh", "-n", str(SCRIPT)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    dash = shutil.which("dash")
    if dash:
        r = subprocess.run([dash, "-n", str(SCRIPT)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr


def test_posix_structure():
    text = SCRIPT.read_text()
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert lines[0] == "#!/bin/sh"
    assert "set -eu" in lines
    assert lines[-1] == 'main "$@"', lines[-1]
    assert re.search(r"^main\(\) \{$", text, re.M)
    # nothing but comments, set, function definitions and the final call at top level
    depth = 0
    for ln in text.splitlines():
        s = ln.strip()
        if depth == 0 and s and not s.startswith("#"):
            ok = s == "set -eu" or s == 'main "$@"' or re.match(r"^[a-z_]+\(\) \{", s)
            assert ok, f"top-level statement outside main: {ln!r}"
        if re.match(r"^[a-z_]+\(\) \{", s) and not s.endswith("}"):
            depth += 1
        elif s == "}":
            depth -= 1
    for bashism in ("[[", "function ", "local ", "source ", "$'", "<<<", "${BASH", "echo -e", "pipefail", "&>"):
        assert bashism not in text, f"bashism {bashism!r}"


def test_no_network_besides_pip_or_pipx():
    text = SCRIPT.read_text()
    code = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
    for tool in ("curl", "wget", "nc ", "/dev/tcp", "http://", "https://"):
        assert tool not in code, tool


def test_old_python_fails_with_clear_error():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        fake = d / "python-old"
        _write_exe(fake, 'case "$*" in *platform*) echo 3.8.10;; *) exit 1;; esac\n')
        env = _env(d, _path_without_pipx())
        env["PYTHON"] = str(fake)
        r = _run(env)
        assert r.returncode != 0
        assert "Python 3.10 or newer" in r.stderr and "3.8.10" in r.stderr, r.stderr
        assert not (d / ".gitmotive").exists() and not (d / ".local").exists()


def test_unset_home_fails_clearly():
    with tempfile.TemporaryDirectory() as d:
        env = _env(d, _path_without_pipx())
        del env["HOME"]
        r = _run(env, cwd=d)
        assert r.returncode != 0 and "HOME is not set" in r.stderr, r.stderr
        env["HOME"] = ""
        r = _run(env, cwd=d)
        assert r.returncode != 0 and "HOME is not set" in r.stderr, r.stderr


def test_rejects_shell_metachars_in_paths():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        for var in ("GITMOTIVE_HOME", "GITMOTIVE_BIN"):
            for bad in ('x"y', "x$y", "x`id`y"):
                env = _env(d, _path_without_pipx(), **{var: str(d / bad)})
                r = _run(env)
                assert r.returncode != 0, (var, bad)
                assert var in r.stderr and "backtick" in r.stderr, r.stderr
        assert not (d / ".gitmotive").exists() and not (d / ".local").exists()


def test_pipx_mode_writes_no_wrappers_and_passes_args():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        fakebin, pipxbin, ghome, gbin = d / "fakebin", d / "pipxbin", d / "gh", d / "gbin"
        fakebin.mkdir()
        log = d / "pipx.log"
        # fake pipx: logs its args; `install` drops a gitmotive entry point that logs its own args
        _write_exe(fakebin / "pipx", f'''echo "pipx $*" >> "{log}"
if [ "$1" = install ]; then
  mkdir -p "$PIPX_BIN_DIR"
  printf '#!/bin/sh\\necho "gitmotive $*" >> "{log}"\\n' > "$PIPX_BIN_DIR/gitmotive"
  chmod +x "$PIPX_BIN_DIR/gitmotive"
fi
''')
        env = _env(d, f"{fakebin}{os.pathsep}{_path_without_pipx()}", PIPX_BIN_DIR=str(pipxbin),
                   GITMOTIVE_PIP_SPEC="gitmotive==0.1.0", GITMOTIVE_HOME=str(ghome), GITMOTIVE_BIN=str(gbin))
        r = _run(env, "--agent", "claude", "--scope", "user")
        assert r.returncode == 0, r.stdout + r.stderr
        calls = log.read_text().splitlines()
        assert calls[0].startswith("pipx install") and calls[0].endswith(f"--python {sys.executable} gitmotive==0.1.0"), calls
        assert calls[-1] == "gitmotive install --agent claude --scope user", calls
        assert not gbin.exists() and not ghome.exists(), "pipx mode must write no wrappers or venv"
        assert not (d / ".local" / "bin" / "git-motive").exists()
        assert f'export PATH="{pipxbin}:$PATH"' in r.stdout, r.stdout

        log.unlink()
        r = _run(env)
        assert r.returncode == 0, r.stderr
        assert "next: gitmotive install --agent claude" in r.stdout
        assert not any(c.startswith("gitmotive ") for c in log.read_text().splitlines())


def test_venv_install_from_wheel():
    whl = _wheel.build_wheel()
    if whl is None:
        print("skip install run")
        return
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        env = _env(d, _path_without_pipx(), GITMOTIVE_PIP_SPEC=str(whl), PIP_NO_INDEX="1")
        r = _run(env, cwd=ROOT)   # cwd inside the checkout: the wrapper must still use the venv package
        assert r.returncode == 0, r.stdout + r.stderr
        assert "next: gitmotive install --agent claude" in r.stdout
        assert f'export PATH="{d}/.local/bin:$PATH"' in r.stdout, r.stdout
        for name in ("gitmotive", "git-motive"):
            w = d / ".local" / "bin" / name
            assert f'{d}/.gitmotive/venv/bin/python" -I -m gitmotive' in w.read_text(), w.read_text()
        v = subprocess.run([str(d / ".local" / "bin" / "gitmotive"), "--version"], env=env, cwd=ROOT,
                           capture_output=True, text=True, timeout=60)
        assert v.stdout.strip() == "gitmotive 0.1.0", v.stdout + v.stderr


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
