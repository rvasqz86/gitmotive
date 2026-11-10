#!/bin/sh
# gitmotive installer:  curl -fsSL https://gitmotive.tech/install.sh | sh
#                       curl -fsSL https://gitmotive.tech/install.sh | sh -s -- --agent claude
#
# With pipx: `pipx install gitmotive` (pipx writes its own entry points).
# Without pipx: a venv at ~/.gitmotive/venv plus `gitmotive` and `git-motive` wrappers in ~/.local/bin.
# Any arguments are passed to `gitmotive install`.
#
# Env: GITMOTIVE_PIP_SPEC (default: gitmotive), GITMOTIVE_HOME (default: ~/.gitmotive),
#      GITMOTIVE_BIN (default: ~/.local/bin), PYTHON (default: python3).
# Network: only pip or pipx fetching the package. No telemetry.
# Every `python -m gitmotive` here runs with -I so the current directory is never imported.

set -eu

say() { printf '%s\n' "$*"; }
die() { printf 'gitmotive install: %s\n' "$*" >&2; exit 1; }

check_python() {
  command -v "$PY" >/dev/null 2>&1 || die "python not found ('$PY'). Install Python 3.10 or newer, or set PYTHON=/path/to/python3."
  "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null \
    || die "gitmotive needs Python 3.10 or newer; '$PY' is $("$PY" -c 'import platform; print(platform.python_version())' 2>/dev/null || echo unknown). Set PYTHON=/path/to/python3.10+."
}

path_hint() {
  case ":$PATH:" in
    *":$1:"*) ;;
    *) say "add to your shell rc:  export PATH=\"$1:\$PATH\"" ;;
  esac
}

install_pipx() {
  say "installing $SPEC with pipx"
  pipx install --force --python "$PY" "$SPEC"
  PIPX_BIN="${PIPX_BIN_DIR:-}"
  [ -n "$PIPX_BIN" ] || PIPX_BIN="$(pipx environment --value PIPX_BIN_DIR 2>/dev/null || true)"
  [ -n "$PIPX_BIN" ] || PIPX_BIN="$HOME/.local/bin"
  GM="$PIPX_BIN/gitmotive"
  say "installed: $GM  (pipx)"
  path_hint "$PIPX_BIN"
}

install_venv() {
  VENV="$GM_HOME/venv"
  say "pipx not found; installing $SPEC into $VENV"
  mkdir -p "$GM_HOME" "$BIN"
  if [ ! -x "$VENV/bin/python" ]; then
    "$PY" -m venv "$VENV" || die "could not create a venv with '$PY -m venv' (on Debian/Ubuntu: apt install python3-venv, or install pipx)."
  fi
  "$VENV/bin/python" -m pip --version >/dev/null 2>&1 \
    || die "the venv at $VENV has no pip (on Debian/Ubuntu: apt install python3-venv, then remove $VENV and rerun)."
  "$VENV/bin/python" -m pip install -q --upgrade "$SPEC"
  for name in gitmotive git-motive; do
    cat > "$BIN/$name" <<EOF
#!/bin/sh
exec "$VENV/bin/python" -I -m gitmotive "\$@"
EOF
    chmod +x "$BIN/$name"
  done
  GM="$BIN/gitmotive"
  say "installed: $GM  (venv: $VENV)"
  path_hint "$BIN"
}

check_path() {
  # the path is written into a double-quoted heredoc in the wrappers
  case "$2" in
    *\"* | *\$* | *\`*) die "$1 must not contain \", \$ or a backtick: $2" ;;
  esac
}

main() {
  [ -n "${HOME:-}" ] || die "HOME is not set"
  SPEC="${GITMOTIVE_PIP_SPEC:-gitmotive}"
  GM_HOME="${GITMOTIVE_HOME:-$HOME/.gitmotive}"
  BIN="${GITMOTIVE_BIN:-$HOME/.local/bin}"
  PY="${PYTHON:-python3}"
  check_path GITMOTIVE_HOME "$GM_HOME"
  check_path GITMOTIVE_BIN "$BIN"

  check_python
  if command -v pipx >/dev/null 2>&1; then
    install_pipx
  else
    install_venv
  fi

  if [ "$#" -gt 0 ]; then
    "$GM" install "$@"
  else
    say "next: gitmotive install --agent claude"
  fi
}

main "$@"
