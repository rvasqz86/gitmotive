"""Packaging metadata (always) and wheel contents (when a wheel can be built)."""
import fnmatch
import sys
import tomllib
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import _wheel  # noqa: E402

DATA = tomllib.loads((ROOT / "pyproject.toml").read_text())
PROJECT = DATA["project"]


def test_urls():
    urls = PROJECT["urls"]
    assert urls["Homepage"] == "https://gitmotive.tech", urls
    assert urls["Documentation"] == "https://gitmotive.tech/docs/", urls
    assert urls["Repository"] == "https://github.com/rvasqz86/gitmotive", urls
    assert urls["Issues"] == "https://github.com/rvasqz86/gitmotive/issues", urls


def test_deps_packages_scripts_license():
    assert PROJECT["dependencies"] == []
    assert DATA["tool"]["setuptools"]["packages"] == ["gitmotive"]
    assert PROJECT["scripts"] == {"gitmotive": "gitmotive.cli:main", "git-motive": "gitmotive.cli:main"}
    assert PROJECT["license"] == "MIT"
    assert not [c for c in PROJECT["classifiers"] if c.startswith("License ::")]


def test_classifiers():
    want = {
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Version Control :: Git",
    }
    assert want <= set(PROJECT["classifiers"]), want - set(PROJECT["classifiers"])


def test_dynamic_version_and_build_system():
    assert "version" not in PROJECT and PROJECT["dynamic"] == ["version"]
    assert DATA["tool"]["setuptools"]["dynamic"]["version"] == {"attr": "gitmotive.__version__"}
    assert DATA["build-system"]["requires"] == ["setuptools>=77"]


def test_wheel_contents():
    whl = _wheel.build_wheel()
    if whl is None:
        print("skip build")
        return
    names = zipfile.ZipFile(whl).namelist()
    bad = [n for n in names
           if not (fnmatch.fnmatch(n, "gitmotive/*.py") and n.count("/") == 1)
           and not fnmatch.fnmatch(n.split("/", 1)[0], "*.dist-info")]
    assert not bad, bad
    assert "gitmotive/cli.py" in names


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
