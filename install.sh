#!/bin/sh
# Install gitmotive into its own venv at ~/.gitmotive/venv and put `gitmotive` + `git-motive`
# on PATH via ~/.local/bin. No system pip needed. Pure stdlib package, so if the venv has no pip
# (Debian/Ubuntu without python3-venv) it falls back to a .pth file.
#
#   sh install.sh            # from a clone of this repo
#   sh install.sh --agent copilot,claude --scope user   # also run `gitmotive install` with these args
set -e

SRC="$(cd "$(dirname "$0")" && pwd)"
HOME_DIR="${GITMOTIVE_HOME:-$HOME/.gitmotive}"
VENV="$HOME_DIR/venv"
BIN="${GITMOTIVE_BIN:-$HOME/.local/bin}"
PY="${PYTHON:-python3}"

"$PY" -c 'import sys; assert sys.version_info >= (3, 10), "need python >= 3.10"'

mkdir -p "$HOME_DIR" "$BIN"
[ -x "$VENV/bin/python" ] || "$PY" -m venv "$VENV" 2>/dev/null || "$PY" -m venv --without-pip "$VENV"

if "$VENV/bin/python" -m pip --version >/dev/null 2>&1; then
  "$VENV/bin/python" -m pip install -q --upgrade "$SRC"
else
  # no pip in venv: point the venv at the source tree directly
  SITE="$("$VENV/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
  echo "$SRC" > "$SITE/gitmotive.pth"
fi

for name in gitmotive git-motive; do
  cat > "$BIN/$name" <<EOF
#!/bin/sh
exec "$VENV/bin/python" -m gitmotive "\$@"
EOF
  chmod +x "$BIN/$name"
done

echo "installed: $BIN/gitmotive  (venv: $VENV)"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo "add to your shell rc:  export PATH=\"$BIN:\$PATH\"" ;;
esac

if [ "$#" -gt 0 ]; then
  "$VENV/bin/python" -m gitmotive install "$@"
fi
