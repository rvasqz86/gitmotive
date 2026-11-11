"""Deploy config checks (tasks 18, 28): line-level checks on .github/workflows/site-checks.yml
(checks only; Cloudflare Pages deploys through its Git integration), site/_redirects syntax, and
launch/DEPLOY.md content. No YAML parser: stdlib only.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "site-checks.yml"
REDIRECTS = ROOT / "site" / "_redirects"
DEPLOY_MD = ROOT / "launch" / "DEPLOY.md"

REDIRECT_STATUSES = {"301", "302", "303", "307", "308", "200"}
EXPECTED_PATHS = ["site/**", "gitmotive/**", "scripts/gen_docs.py", "scripts/docs_src/**"]


def _lines(path: Path) -> list[str]:
    return [l.rstrip() for l in path.read_text(encoding="utf-8").splitlines()]


def _block(lines: list[str], header: str, indent: str) -> list[str]:
    """Lines under `header` that are indented deeper than `indent`, until the block ends."""
    i = lines.index(header)
    out = []
    for l in lines[i + 1:]:
        if l and not l.startswith(indent + " "):
            break
        out.append(l)
    return out


def redirect_problems(text: str) -> list[str]:
    probs = []
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        fields = s.split()
        if len(fields) != 3:
            probs.append(f"line {n}: {len(fields)} fields, want 3: {s!r}")
        elif fields[2] not in REDIRECT_STATUSES:
            probs.append(f"line {n}: bad status {fields[2]!r}")
    return probs


# --- workflow ------------------------------------------------------------------------------

def test_workflow_name():
    assert "name: site-checks" in _lines(WORKFLOW)
    assert not (ROOT / ".github" / "workflows" / "deploy-site.yml").exists(), "old workflow still present"


def test_workflow_triggers():
    lines = _lines(WORKFLOW)
    assert "on:" in lines, "no top-level on:"
    on = _block(lines, "on:", "")
    keys = [l.strip() for l in on if l.startswith("  ") and not l.startswith("   ")]
    assert keys == ["push:", "pull_request:", "workflow_dispatch:"], keys
    push = _block(lines, "  push:", "  ")
    assert "    branches: [main]" in push, "push must be limited to main"
    pr = _block(lines, "  pull_request:", "  ")
    for name, block in (("push", push), ("pull_request", pr)):
        paths = [l for l in block if l.strip().startswith("paths:")]
        assert len(paths) == 1, (name, paths)
        got = re.findall(r"'([^']+)'", paths[0])
        assert got == EXPECTED_PATHS, (name, got)


def test_workflow_permissions():
    lines = _lines(WORKFLOW)
    block = [l.strip() for l in _block(lines, "permissions:", "") if l.strip()]
    assert block == ["contents: read"], block


def test_workflow_single_checks_job():
    lines = _lines(WORKFLOW)
    jobs = [l.strip() for l in _block(lines, "jobs:", "") if l.startswith("  ") and not l.startswith("   ")]
    assert jobs == ["checks:"], jobs
    assert not any(l.strip().startswith("if:") for l in lines), "checks job needs no branch guard"


def test_workflow_steps_in_order():
    text = WORKFLOW.read_text(encoding="utf-8")
    markers = [
        "uses: actions/checkout@",
        "uses: actions/setup-python@",
        "python-version: '3.12'",
        "run: python3 scripts/gen_docs.py --check",
        'run: for f in tests/test_site*.py tests/test_docs_sync.py tests/test_viewer.py; '
        'do python3 "$f" || exit 1; done',
    ]
    pos = [text.find(m) for m in markers]
    assert all(p >= 0 for p in pos), [m for m, p in zip(markers, pos) if p < 0]
    assert pos == sorted(pos), "steps out of order"
    steps = [l for l in text.splitlines() if l.strip().startswith(("- uses:", "- name:"))]
    assert len(steps) == 4, steps


def test_workflow_deploys_nothing():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "secrets." not in text, "workflow must not use secrets"
    assert "wrangler" not in text.lower(), "workflow must not deploy with wrangler"
    assert "deployments:" not in text


# --- _redirects ----------------------------------------------------------------------------

def test_redirect_checker_self_test():
    assert redirect_problems("/a /b 301\n# c\n\n/x /y 200\n") == []
    assert redirect_problems("/a /b\n")
    assert redirect_problems("/a /b 404\n")
    assert redirect_problems("/a /b 301 extra\n")


def test_redirects_file():
    text = REDIRECTS.read_text(encoding="utf-8")
    assert redirect_problems(text) == [], redirect_problems(text)
    rules = [l.split() for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    assert rules == [["/docs", "/docs/", "301"]], rules


# --- launch/DEPLOY.md ----------------------------------------------------------------------

def test_deploy_md_content():
    t = DEPLOY_MD.read_text(encoding="utf-8")
    for s in ("`gitmotive`",
              "Connect to Git", "Install & Authorize", "Save and Deploy", "`site`",
              "https://developers.cloudflare.com/pages/get-started/git-integration/",
              "<ns1>.ns.cloudflare.com", "<ns2>.ns.cloudflare.com",
              "CNAME @ gitmotive.pages.dev", "CNAME www gitmotive.pages.dev",
              "Custom domains", "www.gitmotive.tech", "https://gitmotive.tech${uri}", "301",
              "Preserve query string",
              "dig +short gitmotive.tech",
              "curl -sI https://www.gitmotive.tech/ | grep -i location",
              "curl -s https://gitmotive.tech/install.sh | head -3",
              "curl -sI https://gitmotive.tech/ | head -1", "HTTP/2 200",
              "serves the site directly; it is not a redirect",
              "A @ 76.76.21.21", "CNAME www cname.vercel-dns.com",
              "Create application",
              "Set up a domain", "522"):
        assert s in t, f"DEPLOY.md missing: {s}"
    assert t.count("(proxied") >= 2, "both CNAMEs must be proxied"
    for s in ("CLOUDFLARE_API_TOKEN", "Upload assets"):
        assert s not in t, f"DEPLOY.md has stale text: {s}"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("OK")
