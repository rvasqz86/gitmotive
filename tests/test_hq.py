import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gitmotive import hq

def test_parse():
    r = hq.parse("Implement .hq/tasks/03-add-retry.md, round 2. Fix every finding in the latest round of .hq/reviews/03.md. When finished reply exactly DONE <path> or BLOCKED: <reason>.")
    assert r.kind == "implement" and r.task == ".hq/tasks/03-add-retry.md" and r.round == 2 and r.review == ".hq/reviews/03.md"
    r = hq.parse("Implement .hq/tasks/01-x.md, round 1. When finished reply exactly DONE <path> or BLOCKED: <reason>.")
    assert r.round == 1 and r.review is None
    r = hq.parse("Review task 03 round 2: .hq/tasks/03-add-retry.md against git diff HEAD and git status --porcelain.")
    assert r.kind == "review" and r.review == ".hq/reviews/03.md"
    r = hq.parse("Your role file is /x/roles/implementer.md. Read it now. Project root: /p. Do nothing else until the manager sends you a task. Reply READY.")
    assert r.kind == "role" and r.role == "implementer"
    assert hq.parse("add retry to fetch") is None

def test_resolve():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d); (root / ".hq" / "tasks").mkdir(parents=True); (root / ".hq" / "reviews").mkdir()
        (root / ".hq" / "brief.md").write_text("# Brief\nMake fetch resilient to flaky upstream.\n")
        (root / ".hq" / "tasks" / "03-add-retry.md").write_text("# Task 03: Add retry to fetch\nStatus: todo\n## Goal\nWrap http.get in bounded retry with backoff.\n## Files\n- fetch.py (modify)\n")
        (root / ".hq" / "reviews" / "03.md").write_text("## Round 1 — runtime\nclean\n## Round 1\n- FIX: backoff is linear, spec says exponential\n- NIT: missing test for max attempts\n## Round 2\n")
        r = hq.resolve(root, hq.parse("Implement .hq/tasks/03-add-retry.md, round 2. Fix every finding in the latest round of .hq/reviews/03.md."))
        assert r.task_title == "Task 03: Add retry to fetch"
        assert "bounded retry" in r.task_goal
        assert r.brief.startswith("Make fetch")
        assert any("exponential" in f for f in r.findings), r.findings
        lines = hq.describe(r, lambda s: "    " + s)
        assert any("Task 03" in l for l in lines)

if __name__ == "__main__":
    test_parse(); test_resolve(); print("ok hq")
