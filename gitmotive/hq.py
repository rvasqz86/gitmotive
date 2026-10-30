"""hq (herdr-config) awareness.

hq drives crew agents with generated prompts like
    Implement .hq/tasks/03-add-retry.md, round 2. Fix every finding in the latest round of .hq/reviews/03.md. ...
The human's actual intent lives in files: .hq/brief.md (verbatim brief), .hq/tasks/NN-*.md (planner's
decomposition), .hq/reviews/NN.md (why later rounds exist). This module recognises hq prompts and
dereferences those files at display time. Nothing is stored beyond the prompt text itself.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

TASK_RE = re.compile(r"\.hq/tasks/([\w.\-]+\.md)")
ROUND_RE = re.compile(r"\bround\s+(\d+)", re.I)
REVIEW_RE = re.compile(r"\.hq/reviews/([\w.\-]+\.md)")
ROLE_RE = re.compile(r"Your role file is (\S+)")
KINDS = (
    (re.compile(r"^Implement\b", re.I), "implement"),
    (re.compile(r"^Review task\b", re.I), "review"),
    (re.compile(r"^Write \.hq/spec\.md", re.I), "plan"),
    (re.compile(r"^Review \.hq/spec\.md", re.I), "spec-review"),
)


@dataclass
class HqRef:
    kind: str                       # implement | review | plan | spec-review | role
    task: Optional[str] = None      # .hq/tasks/NN-slug.md
    review: Optional[str] = None    # .hq/reviews/NN.md
    round: Optional[int] = None
    role: Optional[str] = None
    # resolved at display time
    task_title: Optional[str] = None
    task_goal: Optional[str] = None
    brief: Optional[str] = None
    findings: list[str] = field(default_factory=list)


def parse(prompt: str) -> Optional[HqRef]:
    if not prompt:
        return None
    m = ROLE_RE.search(prompt)
    if m:
        return HqRef(kind="role", role=Path(m.group(1).rstrip(".")).stem)
    kind = next((k for rx, k in KINDS if rx.search(prompt)), None)
    t, r, rv = TASK_RE.search(prompt), ROUND_RE.search(prompt), REVIEW_RE.search(prompt)
    if not kind and not t:
        return None
    ref = HqRef(kind=kind or "task")
    if t:
        ref.task = f".hq/tasks/{t.group(1)}"
    if r:
        ref.round = int(r.group(1))
    if rv:
        ref.review = f".hq/reviews/{rv.group(1)}"
    elif ref.task and ref.round and ref.round > 1:
        nn = ref.task.split("/")[-1].split("-", 1)[0]
        ref.review = f".hq/reviews/{nn}.md"
    return ref


def _section(text: str, heading: str) -> Optional[str]:
    """Body of a '## heading' section, up to the next '## '."""
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return m.group(1).strip() if m else None


def _read(root: Path, rel: str) -> Optional[str]:
    p = root / rel
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def resolve(root: Path, ref: HqRef) -> HqRef:
    """Fill in titles/bodies from the working tree. Best-effort; missing files leave fields None."""
    if ref.task:
        txt = _read(root, ref.task)
        if txt:
            first = txt.splitlines()[0] if txt else ""
            ref.task_title = first.lstrip("# ").strip() or ref.task
            ref.task_goal = _section(txt, "Goal")
    brief = _read(root, ".hq/brief.md")
    if brief:
        body = _section(brief, "Brief") if "## Brief" in brief else None
        if body is None:
            body = re.sub(r"^#\s*Brief\s*$", "", brief, flags=re.M).strip()
        ref.brief = body.strip() or None
    if ref.review and ref.round and ref.round > 1:
        txt = _read(root, ref.review)
        if txt:
            prev = ref.round - 1
            lines: list[str] = []
            for m in re.finditer(rf"^##\s+Round\s+{prev}\b.*?$\n(.*?)(?=^##\s+Round\s|\Z)", txt, re.M | re.S):
                lines += [l.strip() for l in m.group(1).splitlines() if l.strip().startswith(("-", "*"))]
            ref.findings = lines[:8]
    return ref


def describe(ref: HqRef, wrap) -> list[str]:
    """Lines for the CLI. `wrap` is the caller's text wrapper (indent applied by caller)."""
    out: list[str] = []
    if ref.kind == "role":
        out.append(f"  hq       role prompt ({ref.role}); no task attached")
        return out
    head = f"  hq       {ref.kind}"
    if ref.task:
        head += f"  {ref.task}"
    if ref.round:
        head += f"  round {ref.round}"
    out.append(head)
    if ref.task_title:
        out.append(f"  task     {ref.task_title}")
    if ref.task_goal:
        out.append(wrap(ref.task_goal))
    if ref.findings:
        out.append(f"  round {ref.round} fixes findings from round {ref.round - 1}:")
        for f in ref.findings:
            out.append(f"    {f}")
    if ref.brief:
        out.append("  brief")
        out.append(wrap(ref.brief[:600] + ("…" if len(ref.brief) > 600 else "")))
    return out
