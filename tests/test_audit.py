"""scripts/audit_public.py: checks, severities, scopes, allow-list, denylist redaction.

Self-match rule: every planted secret, private IP, internal hostname and home path below is
built by string concatenation at runtime, so this file never matches the scanner itself.
Denylist terms are synthetic (acme-widgets, globex-internal).
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "audit_public.py"
sys.path.insert(0, str(ROOT / "scripts"))

import audit_public as ap  # noqa: E402

TERM = "acme-widgets"
TERM2 = "globex-internal"

# planted values (concatenated at runtime)
AWS = "AK" + "IA" + "Q" * 16
GH = "gh" + "p_" + "a1B2" * 9
GH_PAT = "github" + "_pat_" + "x" * 22
ANTH = "sk" + "-ant-" + "api03_" + "z" * 20
OPENAI = "sk" + "-" + "Ab1" * 7
SLACK = "xo" + "xb-" + "1234567890-abc"
PEM = "-----" + "BEGIN RSA " + "PRIVATE" + " KEY-----"
GENERIC = "api" + "_key = '" + "q9" * 7 + "'"
IP10 = "1" + "0.20.30.40"
IP172 = "17" + "2.16.0.9"
IP192 = "19" + "2.168.1.254"
HOSTNAME = "build" + "box." + "corp"
OTHER_HOME = "/" + "home" + "/someoneelse/" + "notes.txt"


def own_home():
    return "/" + "home" + "/" + ap._current_user() + "/" + "x"


def git(root, *a):
    return subprocess.run(["git", *a], cwd=root, capture_output=True, text=True, check=True).stdout


def new_repo(d):
    root = Path(d)
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    return root


def commit_all(root, msg="c"):
    git(root, "add", "-A")
    git(root, "commit", "-qm", msg, "--allow-empty")
    return git(root, "rev-parse", "HEAD").strip()


def run(root, *args, env_extra=None):
    env = {k: v for k, v in os.environ.items() if k != ap.DENYLIST_ENV}
    env.update(env_extra or {})
    r = subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args],
                       capture_output=True, text=True, env=env)
    return r


def run_json(root, *args, **kw):
    r = run(root, "--json", *args, **kw)
    assert r.returncode in (0, 1), (r.returncode, r.stderr)
    return r, json.loads(r.stdout)


def checks_of(findings):
    return {f.check for f in findings}


# --- scan_text unit tests ----------------------------------------------------------------

def test_secret_patterns_fire():
    for s in (AWS, GH, GH_PAT, ANTH, OPENAI, SLACK, PEM, GENERIC):
        fs = ap.scan_text("x = " + s + "\n", "f.py", None)
        assert [f.check for f in fs][:1] == ["secret"], s[:6]
        assert fs[0].severity == "high"
        assert s not in fs[0].excerpt or s == PEM  # token bodies are masked in output


def test_secret_bare_prefix_does_not_match():
    prose = ("Keys look like " + "AK" + "IA" + "..., tokens start with " + "gh" + "p_" + " or "
             + "sk" + "-ant-" + " or " + "sk" + "-" + "; slack uses " + "xo" + "xb-" + " and "
             + "github" + "_pat_" + ". The token: field is set elsewhere.")
    assert ap.scan_text(prose, "README.md", None) == []


def test_host_matches_private_quads_only():
    for ip in (IP10, IP172, IP192):
        fs = ap.scan_text("connect to " + ip + " now", "f", None)
        assert [f.check for f in fs] == ["host"] and fs[0].severity == "medium", ip
    negatives = [
        "version 10.1.2 released",
        "python 3.10.12.4.1",
        "1" + ".10.1.2.3",
        "1" + "0.1.2.300",               # octet > 255
        "17" + "2.32.0.1",               # outside 172.16/12
        "8.8.8.8",                       # public
        "1" + "0.0.0.1.5",               # followed by .digit
        "11" + "0." + "0.0.1",            # preceded by a digit
    ]
    for n in negatives:
        assert ap.scan_text(n, "f", None) == [], n


def test_hostname_rule():
    assert checks_of(ap.scan_text("ssh " + HOSTNAME + " please", "f", None)) == {"host"}
    assert checks_of(ap.scan_text("db." + "eng." + "internal", "f", None)) == {"host"}
    for n in ("~/.local/bin", "export PATH=$HOME/.local/bin:$PATH", ".env.local",
              "settings.local.json", "localhost:8080", ".local"):
        assert ap.scan_text(n, "f", None) == [], n


def test_path_own_home_is_info_other_is_medium():
    fs = ap.scan_text(OTHER_HOME, "f", None, checks=("path",))
    assert [(f.check, f.severity) for f in fs] == [("path", "medium")]
    fs = ap.scan_text(own_home(), "f", None, checks=("path",))
    assert [(f.check, f.severity) for f in fs] == [("path", "info")]


def test_denylist_whole_word_case_insensitive_and_redacted():
    dl = [TERM, TERM2]
    fs = ap.scan_text("Work for ACME-Widgets today", "notes.md", dl)
    assert [f.check for f in fs] == ["denylist"] and fs[0].severity == "high"
    assert "acme" not in fs[0].excerpt.lower() and "<denylist:1>" in fs[0].excerpt
    assert ap.scan_text("myacme-widgetsx", "f", dl) == []
    assert ap.redact("a " + TERM2 + " b", dl) == "a <denylist:2> b"
    assert ap.redact("x", None) == "x"


def test_load_denylist_sources_and_line_numbers():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        old = os.environ.pop(ap.DENYLIST_ENV, None)
        try:
            assert ap.load_denylist(None, root) is None
            (root / ".audit-denylist").write_text("# comment\n\n" + TERM + "\n")
            dl = ap.load_denylist(None, root)
            assert list(dl) == [TERM]
            assert ap.redact(TERM, dl) == "<denylist:3>"  # 1-based line number in the file
            other = root / "other.txt"
            other.write_text(TERM2 + "\n")
            os.environ[ap.DENYLIST_ENV] = str(other)
            assert list(ap.load_denylist(None, root)) == [TERM2]
            explicit = root / "explicit.txt"
            explicit.write_text("foo\n")
            assert list(ap.load_denylist(str(explicit), root)) == ["foo"]
        finally:
            os.environ.pop(ap.DENYLIST_ENV, None)
            if old is not None:
                os.environ[ap.DENYLIST_ENV] = old


def test_finding_and_severity_api():
    assert ap.SEVERITY == {"secret": "high", "denylist": "high", "transcript": "high",
                           "host": "medium", "path": "medium", "artifact": "medium"}
    f = ap.Finding(check="secret", severity="high", where="a", commit=None, excerpt="e")
    assert (f.check, f.severity, f.where, f.commit, f.excerpt) == ("secret", "high", "a", None, "e")


def test_excerpt_capped():
    fs = ap.scan_text("y" * 500 + " " + IP10 + " " + "y" * 500, "f", None)
    assert len(fs[0].excerpt) <= 120 and IP10 in fs[0].excerpt



def test_excerpt_window_never_cuts_a_denylist_term():
    dl = [TERM, TERM2]
    text = TERM + " " + "y" * 100 + " " + TERM2 + " tail"
    fs = ap.scan_text(text, "f", dl)
    assert len(fs) == 2
    for f in fs:
        low = f.excerpt.lower()
        assert len(f.excerpt) <= 120
        for frag in ("acme", "widgets", "globex", "internal"):
            assert frag not in low, f.excerpt
    # a term straddling the window edge on the far side as well
    text = "y" * 20 + " " + TERM2 + " " + "y" * 85 + TERM + "z" * 100
    for f in ap.scan_text(text, "f", dl):
        low = f.excerpt.lower()
        for frag in ("acme", "widgets", "globex", "internal"):
            assert frag not in low, f.excerpt


def test_excerpt_window_never_cuts_a_secret():
    # a host match whose excerpt window would cut a token mid-body
    text = IP10 + " " + "y" * 100 + " " + GH + " tail"
    fs = [f for f in ap.scan_text(text, "f", None) if f.check == "host"]
    assert fs and GH[:10] not in fs[0].excerpt, fs[0].excerpt


def test_hostname_rule_ignores_python_call():
    for n in ("threading" + ".local()", "x = obj" + ".internal(1)"):
        assert ap.scan_text(n, "f", None) == [], n

# --- CLI tests on temp repos -------------------------------------------------------------

def test_clean_repo_exits_0_and_reports_skipped_denylist():
    with tempfile.TemporaryDirectory() as d:
        root = new_repo(d)
        (root / "README.md").write_text("hello, version 10.1.2\nPATH=~/.local/bin\n")
        commit_all(root)
        r = run(root)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "denylist: skipped (no denylist)" in r.stdout
        r, j = run_json(root, "--tree")
        assert j["findings"] == [] and j["denylist"] == "skipped (no denylist)"


def test_each_check_fires_with_severities():
    with tempfile.TemporaryDirectory() as d:
        root = new_repo(d)
        (root / "cfg.py").write_text("key = '" + AWS + "'\n")
        (root / "hosts.txt").write_text("db at " + IP192 + "\n")
        (root / "paths.txt").write_text("see " + OTHER_HOME + "\nmine " + own_home() + "\n")
        (root / "names.md").write_text("Client: " + TERM + "\n")
        (root / "events.jsonl").write_text('{"hook_event_name": "PostToolUse"}\n')
        (root / "build").mkdir()
        (root / "build" / "lib.py").write_text("x = 1\n")
        commit_all(root)
        (root / ".gitmotive").mkdir()
        (root / ".gitmotive" / "store.txt").write_text("x\n")  # untracked, unignored
        dl = root / "dl.txt"
        dl.write_text(TERM + "\n")
        r, j = run_json(root, "--tree", "--denylist", str(dl))
        assert r.returncode == 1
        got = {(f["check"], f["severity"], f["where"].split(":")[0]) for f in j["findings"]}
        expected = {
            ("secret", "high", "cfg.py"),
            ("host", "medium", "hosts.txt"),
            ("path", "medium", "paths.txt"),
            ("path", "info", "paths.txt"),
            ("denylist", "high", "names.md"),
            ("transcript", "high", "events.jsonl"),
            ("transcript", "high", ".gitmotive/store.txt"),
            ("artifact", "medium", "build/lib.py"),
        }
        assert expected <= got, expected - got
        assert all(f["commit"] is None for f in j["findings"])


def test_own_home_only_exits_0():
    with tempfile.TemporaryDirectory() as d:
        root = new_repo(d)
        (root / "a.txt").write_text(own_home() + "\n")
        commit_all(root)
        r, j = run_json(root)
        assert r.returncode == 0 and [f["severity"] for f in j["findings"]] == ["info", "info"]


def test_history_only_secret_reports_oldest_introducing_commit():
    with tempfile.TemporaryDirectory() as d:
        root = new_repo(d)
        (root / "README.md").write_text("hi\n")
        commit_all(root, "init")
        (root / "leak.env").write_text("TOKEN=" + GH + "\n")
        c_intro = commit_all(root, "add env")
        (root / "leak.env").unlink()
        commit_all(root, "remove env")
        (root / "again.env").write_text("TOKEN=" + GH + "\n")  # same blob, re-added later
        commit_all(root, "re-add")
        (root / "again.env").unlink()
        commit_all(root, "remove again")

        r = run(root, "--tree")
        assert r.returncode == 0, r.stdout
        r, j = run_json(root, "--history")
        assert r.returncode == 1
        secrets = [f for f in j["findings"] if f["check"] == "secret"]
        assert len(secrets) == 1, secrets
        assert secrets[0]["commit"] == c_intro
        assert GH not in r.stdout



def test_history_reports_every_path_of_a_shared_blob():
    with tempfile.TemporaryDirectory() as d:
        root = new_repo(d)
        (root / "src").mkdir()
        (root / "src" / "x.py").write_text("print('x')\n")
        commit_all(root, "src")
        (root / "build" / "lib").mkdir(parents=True)
        (root / "build" / "lib" / "x.py").write_text("print('x')\n")  # identical blob
        (root / ".gitmotive").mkdir()
        (root / ".gitmotive" / "x.py").write_text("print('x')\n")  # identical blob again
        c_build = commit_all(root, "build copy")
        git(root, "rm", "-rq", "build", ".gitmotive")
        commit_all(root, "untrack")
        r, j = run_json(root, "--history")
        assert r.returncode == 1
        got = {(f["check"], f["where"], f["commit"]) for f in j["findings"]}
        assert ("artifact", "build/lib/x.py", c_build) in got, got
        assert ("transcript", ".gitmotive/x.py", c_build) in got, got

def test_history_denylist_in_commit_message_and_identity():
    with tempfile.TemporaryDirectory() as d:
        root = new_repo(d)
        (root / "a.txt").write_text("x\n")
        c = commit_all(root, "fix for the " + TERM.upper() + " rollout")
        git(root, "-c", "user.name=Dev", "-c", "user.email=dev@" + TERM2 + ".example",
            "commit", "-q", "--allow-empty", "-m", "noop")
        dl = root / ".audit-denylist"
        dl.write_text(TERM + "\n" + TERM2 + "\n")
        r, j = run_json(root, "--history")
        assert r.returncode == 1
        wheres = {(f["where"].split(":")[0], f["commit"]) for f in j["findings"] if f["check"] == "denylist"}
        assert ("commit-message", c) in wheres, wheres
        assert any(w == "author" for w, _ in wheres) and any(w == "committer" for w, _ in wheres)
        assert "denylist: 2 terms" in j["summary"]


def test_redaction_never_leaks_terms():
    with tempfile.TemporaryDirectory() as d:
        root = new_repo(d)
        (root / (TERM + "-notes.md")).write_text("Contract with " + TERM + " and " + TERM2.title() + "\n")
        commit_all(root, "notes about " + TERM)
        dl = root / "terms.txt"
        dl.write_text("# synthetic\n" + TERM + "\n" + TERM2 + "\n")
        for args in ((), ("--json",)):
            r = run(root, "--denylist", str(dl), *args)
            assert r.returncode == 1
            out = (r.stdout + r.stderr).lower()
            assert TERM not in out and TERM2 not in out, out
            assert "<denylist:2>" in r.stdout and "<denylist:3>" in r.stdout
        # env var source behaves the same
        r = run(root, env_extra={ap.DENYLIST_ENV: str(dl)})
        assert r.returncode == 1 and TERM not in r.stdout.lower()


def test_allow_list_downgrades_and_requires_reason():
    with tempfile.TemporaryDirectory() as d:
        root = new_repo(d)
        (root / "docs").mkdir()
        (root / "docs" / "net.md").write_text("example " + IP10 + "\n")
        (root / ".audit-allow").write_text("# header\ndocs/*.md host  # synthetic example address\n")
        commit_all(root)
        r, j = run_json(root, "--tree")
        assert r.returncode == 0, j
        assert [(f["check"], f["severity"], f["allowed"]) for f in j["findings"]] == [("host", "info", True)]
        r = run(root, "--tree")
        assert r.stdout.startswith("allowed "), r.stdout

        (root / ".audit-allow").write_text("docs/*.md host\n")
        assert run(root, "--tree").returncode == 2
        bad = root / "bad-allow"
        bad.write_text("docs/*.md host  #   \n")
        assert run(root, "--tree", "--allow", str(bad)).returncode == 2


def test_binary_blob_checked_by_path_only():
    with tempfile.TemporaryDirectory() as d:
        root = new_repo(d)
        (root / "img.bin").write_bytes(b"\x89PNG\0\0" + AWS.encode() + b" " + TERM.encode())
        (root / "dist").mkdir()
        (root / "dist" / "pkg.whl").write_bytes(b"PK\0\0" + AWS.encode())
        commit_all(root)
        (root / ".git" / "info" / "exclude").write_text(".audit-denylist\n")
        (root / ".audit-denylist").write_text(TERM + "\n")
        r, j = run_json(root)
        assert j["denylist"] == "1 terms"
        checks = sorted({(f["check"], f["where"]) for f in j["findings"]})
        assert checks == [("artifact", "dist/pkg.whl")], checks


def test_usage_errors_exit_2():
    with tempfile.TemporaryDirectory() as d:
        root = new_repo(d)
        assert run(root, "--bogus").returncode == 2
        assert run(root, "--denylist", str(Path(d) / "missing")).returncode == 2
        assert run(root, "--allow", str(Path(d) / "missing")).returncode == 2
    with tempfile.TemporaryDirectory() as d:
        assert run(Path(d)).returncode == 2  # not a git repo


def test_self_match_rule_on_this_repo():
    r = subprocess.run([sys.executable, str(SCRIPT), "--tree", "--json", "--root", str(ROOT)],
                       capture_output=True, text=True,
                       env={k: v for k, v in os.environ.items() if k != ap.DENYLIST_ENV})
    assert r.returncode in (0, 1), r.stderr
    mine = {"scripts/audit_public.py", "tests/test_audit.py"}
    bad = [f for f in json.loads(r.stdout)["findings"]
           if f["check"] in ("secret", "host") and f["where"].split(":")[0] in mine]
    assert bad == [], bad


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("OK")
