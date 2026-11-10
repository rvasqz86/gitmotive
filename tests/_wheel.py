"""Shared helper: build a wheel once per process (not a test_*.py, so the runner skips it)."""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_cache = {}


def build_wheel():
    """Isolated `python -m build --wheel` into a cached temp dir. None if build is missing or fails."""
    if "wheel" in _cache:
        return _cache["wheel"]
    out = Path(tempfile.mkdtemp(prefix="gitmotive-wheel-"))
    try:
        r = subprocess.run([sys.executable, "-m", "build", "--wheel", "--outdir", str(out), str(ROOT)],
                           capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.SubprocessError):
        r = None
    wheels = sorted(out.glob("*.whl")) if r is not None and r.returncode == 0 else []
    _cache["wheel"] = wheels[0] if wheels else None
    return _cache["wheel"]
