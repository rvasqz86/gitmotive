#!/bin/sh
# The stranger's path, run against an already-installed gitmotive (`gitmotive` and `git-motive` on PATH).
# Called by smoke_fresh.sh inside a clean venv or a python:3.12-slim container. Prints SMOKE OK or exits
# non-zero at the first miss.
#
# Optional: SMOKE_SRC=<source checkout> and SMOKE_WHEEL=<wheel> also run install.sh from inside the
# checkout and assert the hook commands it writes point at the install venv, never the checkout.
set -eu

fail() { echo "SMOKE FAIL: $*" >&2; exit 1; }
step() { echo "== $*"; }

PY=${SMOKE_PYTHON:-python3}
WORK=$(mktemp -d "${TMPDIR:-/tmp}/gitmotive-smoke.XXXXXX")
REPO="$WORK/repo"
PROMPT="add retry with exponential backoff to fetch"
REASONING="Wrapping the call in a retry loop because the upstream flakes."
MODEL="claude-opus-5-5"

step "1. gitmotive --version"
gitmotive --version || fail "gitmotive --version"

step "2. git init sample repo + first commit"
mkdir -p "$REPO"
cd "$REPO"
git init -q
git config user.email smoke@example.invalid
git config user.name smoke
printf 'def fetch(url):\n    return http.get(url)\n' > fetch.py
git add fetch.py
git commit -qm init

step "3. gitmotive install --agent claude"
gitmotive install --agent claude || fail "gitmotive install"

step "4. read hook commands from .claude/settings.json"
hook_cmd() {
  "$PY" -c 'import json,sys; c=json.load(open(".claude/settings.json")); print(c["hooks"][sys.argv[1]][0]["hooks"][0]["command"])' "$1"
}
PROMPT_CMD=$(hook_cmd UserPromptSubmit) || fail "no UserPromptSubmit hook"
EDIT_CMD=$(hook_cmd PostToolUse) || fail "no PostToolUse hook"
echo "UserPromptSubmit: $PROMPT_CMD"
echo "PostToolUse:      $EDIT_CMD"
case "$PROMPT_CMD$EDIT_CMD" in *"gitmotive capture"*) ;; *) fail "hooks are not gitmotive capture" ;; esac

step "5. prompt payload -> hook, apply edit, edit payload (+ transcript) -> hook"
TRANSCRIPT="$WORK/transcript.jsonl"
export PROMPT REASONING MODEL REPO TRANSCRIPT
"$PY" - <<'EOF'
import json, os
recs = [
    {"type": "user", "message": {"role": "user", "content": os.environ["PROMPT"]}},
    {"type": "assistant", "message": {"role": "assistant", "model": os.environ["MODEL"], "content": [
        {"type": "text", "text": os.environ["REASONING"]},
        {"type": "tool_use", "id": "toolu_smoke", "name": "Edit", "input": {}}]}},
]
with open(os.environ["TRANSCRIPT"], "w") as f:
    f.write("".join(json.dumps(r) + "\n" for r in recs))
EOF
"$PY" -c 'import json,os; print(json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "sess-smoke",
  "cwd": os.environ["REPO"], "transcript_path": os.environ["TRANSCRIPT"], "prompt": os.environ["PROMPT"]}))' \
  | sh -c "$PROMPT_CMD" || fail "prompt hook"
OLD='    return http.get(url)
'
NEW='    for attempt in range(3):
        try:
            return http.get(url)
        except http.Error:
            time.sleep(2 ** attempt)
    raise
'
printf 'def fetch(url):\n%s' "$NEW" > fetch.py
export OLD NEW
"$PY" -c 'import json,os; print(json.dumps({"hook_event_name": "PostToolUse", "session_id": "sess-smoke",
  "cwd": os.environ["REPO"], "transcript_path": os.environ["TRANSCRIPT"], "tool_use_id": "toolu_smoke",
  "tool_name": "Edit", "tool_input": {"file_path": os.environ["REPO"] + "/fetch.py",
  "old_string": os.environ["OLD"], "new_string": os.environ["NEW"]}}))' \
  | sh -c "$EDIT_CMD" || fail "edit hook"

step "6. git commit"
git add fetch.py
git commit -qm "add retry"

step "7. post-commit hook stamped the edit with HEAD (before any why/log)"
HEAD=$(git rev-parse HEAD)
export HEAD
"$PY" - <<'EOF' || fail "no edit in .gitmotive/events.jsonl stamped with HEAD"
import json, os, sys
evs = [json.loads(l) for l in open(".gitmotive/events.jsonl") if l.strip()]
edits = [e for e in evs if e.get("kind") == "edit"]
print("edit commits:", [e.get("commit") for e in edits])
sys.exit(0 if any(e.get("commit") and e["commit"] == os.environ["HEAD"] for e in edits) else 1)
EOF

step "8. git motive fetch.py:6"
OUT=$(git motive fetch.py:6) || fail "git motive exited non-zero"
echo "$OUT"
echo "$OUT" | grep -qF "$PROMPT" || fail "prompt text missing from git motive"
echo "$OUT" | grep -qF "retry loop because the upstream flakes" || fail "reasoning text missing from git motive"
echo "$OUT" | grep -qF "model $MODEL" || fail "model $MODEL missing from git motive"

step "9. gitmotive log"
OUT=$(gitmotive log) || fail "gitmotive log exited non-zero"
echo "$OUT"
echo "$OUT" | grep -qF "$PROMPT" || fail "prompt missing from gitmotive log"

if [ -n "${SMOKE_SRC:-}" ] && [ -n "${SMOKE_WHEEL:-}" ]; then
  step "9b. install.sh run from inside the checkout bakes the install venv into hooks, not the checkout"
  IH="$WORK/ihome"
  mkdir -p "$IH"
  ( cd "$SMOKE_SRC" && HOME="$IH" GITMOTIVE_HOME="$IH/.gitmotive" GITMOTIVE_BIN="$IH/bin" \
      GITMOTIVE_PKG="$SMOKE_WHEEL" PIP_NO_INDEX=1 sh ./install.sh --agent claude --scope user ) \
    || fail "install.sh"
  for ev in UserPromptSubmit PostToolUse; do
    C=$(cd "$IH" && "$PY" -c 'import json,sys; c=json.load(open(".claude/settings.json")); print(c["hooks"][sys.argv[1]][0]["hooks"][0]["command"])' "$ev") \
      || fail "install.sh wrote no $ev hook"
    echo "$ev: $C"
    case "$C" in *"$IH/.gitmotive/venv/"*) ;; *) fail "$ev hook does not use the install venv: $C" ;; esac
    case "$C" in *"PYTHONPATH=$SMOKE_SRC"*) fail "$ev hook references the source checkout: $C" ;; esac
  done
  W=$(cd "$SMOKE_SRC" && HOME="$IH" "$IH/bin/gitmotive" --version) || fail "installed wrapper"
  echo "wrapper from checkout cwd: $W"
fi

echo "SMOKE OK"
