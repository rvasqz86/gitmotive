"""Deploy config checks (task 18): line-level checks on .github/workflows/deploy-site.yml,
site/_redirects syntax, and launch/DEPLOY.md content. No YAML parser: stdlib only.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-site.yml"
REDIRECTS = ROOT / "site" / "_redirects"
DEPLOY_MD = ROOT / "launch" / "DEPLOY.md"

REDIRECT_STATUSES = {"301", "302", "303", "307", "308", "200"}
EXPECTED_PATHS = ["site/**", "gitmotive/**", "scripts/gen_docs.py", "scripts/docs_src/**"]


def _lines(path: Path) -> list[str]:
    return [l.rstrip() for l in path.read_text(encoding="utf-8").splitlines()]


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

def test_workflow_triggers():
    lines = _lines(WORKFLOW)
    assert "on:" in lines, "no top-level on:"
    assert "  push:" in lines
    assert "    branches: [main]" in lines, "push must be limited to main"
    assert "  workflow_dispatch:" in lines
    # a manual dispatch from another branch must not publish as production (--branch=main)
    i = lines.index("  deploy:")
    assert "    if: github.ref == 'refs/heads/main'" in lines[i + 1:i + 4], "deploy job not guarded to main"
    paths = [l for l in lines if l.strip().startswith("paths:")]
    assert len(paths) == 1, paths
    got = re.findall(r"'([^']+)'", paths[0])
    assert got == EXPECTED_PATHS, got


def test_workflow_permissions():
    lines = _lines(WORKFLOW)
    i = lines.index("permissions:")
    block = []
    for l in lines[i + 1:]:
        if not l.startswith("  "):
            break
        block.append(l.strip())
    assert block == ["contents: read", "deployments: write"], block


def test_workflow_steps_in_order():
    text = WORKFLOW.read_text(encoding="utf-8")
    markers = [
        "uses: actions/checkout@",
        "uses: actions/setup-python@",
        "python-version: '3.12'",
        "run: python3 scripts/gen_docs.py --check",
        'run: for f in tests/test_site*.py tests/test_docs_sync.py tests/test_viewer.py; '
        'do python3 "$f" || exit 1; done',
        "uses: cloudflare/wrangler-action@v3",
    ]
    pos = [text.find(m) for m in markers]
    assert all(p >= 0 for p in pos), [m for m, p in zip(markers, pos) if p < 0]
    assert pos == sorted(pos), "steps out of order"


def test_workflow_secrets_and_project():
    text = WORKFLOW.read_text(encoding="utf-8")
    secrets = set(re.findall(r"\$\{\{\s*secrets\.(\w+)\s*\}\}", text))
    assert secrets == {"CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"}, secrets
    lines = [l.strip() for l in text.splitlines()]
    assert "apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}" in lines
    assert "accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}" in lines
    assert "command: pages deploy site --project-name=gitmotive --branch=main" in lines
    assert re.findall(r"--project-name=(\S+)", text) == ["gitmotive"]


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
    for s in ("Account › Cloudflare Pages › Edit", "direct-upload", "`gitmotive`",
              "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "Secrets and variables",
              "<ns1>.ns.cloudflare.com", "<ns2>.ns.cloudflare.com",
              "CNAME @ gitmotive.pages.dev", "CNAME www gitmotive.pages.dev",
              "Custom domains", "www.gitmotive.tech", "https://gitmotive.tech${uri}", "301",
              "Preserve query string",
              "dig +short gitmotive.tech",
              "curl -sI https://www.gitmotive.tech/ | grep -i location",
              "curl -s https://gitmotive.tech/install.sh | head -3",
              "curl -sI https://gitmotive.tech/ | head -1", "HTTP/2 200",
              "started from `main`",
              "serves the site directly; it is not a redirect",
              "A @ 76.76.21.21", "CNAME www cname.vercel-dns.com"):
        assert s in t, f"DEPLOY.md missing: {s}"
    assert t.count("(proxied") >= 2, "both CNAMEs must be proxied"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("OK")
