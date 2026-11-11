"""Fresh-machine smoke: `sh scripts/smoke_fresh.sh --venv` against a locally built wheel (skips when no
wheel can be built). The --docker variant is run manually and recorded in the task report."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import _wheel  # noqa: E402


def test_smoke_fresh_venv():
    whl = _wheel.build_wheel()
    if whl is None:
        print("skip smoke")
        return
    env = {k: v for k, v in os.environ.items() if not k.startswith("GITMOTIVE_")}
    env["GITMOTIVE_WHEEL"] = str(whl)
    env["PYTHON"] = sys.executable
    r = subprocess.run(["sh", str(ROOT / "scripts" / "smoke_fresh.sh"), "--venv"], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0 and "SMOKE OK" in r.stdout, r.stdout[-4000:] + r.stderr[-4000:]


def test_docker_flag_without_docker_exits_2():
    with tempfile.TemporaryDirectory() as d:
        fake = Path(d) / "docker"   # a docker whose `docker info` fails, shadowing any real one
        fake.write_text("#!/bin/sh\nexit 1\n")
        fake.chmod(0o755)
        env = {**os.environ, "PATH": f"{d}:{os.environ.get('PATH', '')}"}
        r = subprocess.run(["sh", str(ROOT / "scripts" / "smoke_fresh.sh"), "--docker"], cwd=ROOT, env=env,
                           capture_output=True, text=True, timeout=60)
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    assert "docker" in r.stderr.lower(), r.stderr


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
