#!/bin/sh
# Fresh-machine smoke test: install gitmotive from a locally built wheel into a clean environment and run
# scripts/smoke_inner.sh (install hooks in a sample repo, fire the installed Claude hooks, commit, query).
#
#   sh scripts/smoke_fresh.sh            # --docker if `docker info` works, else --venv
#   sh scripts/smoke_fresh.sh --docker   # python:3.12-slim, wheel mounted read-only, pipx install
#   sh scripts/smoke_fresh.sh --venv     # new venv under $TMPDIR, temp HOME, pip install --no-index
#
# GITMOTIVE_WHEEL=<path> uses that wheel instead of building one.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
PY=${PYTHON:-python3}
IMAGE=${SMOKE_IMAGE:-python:3.12-slim}

MODE=
case "${1:-}" in
  --docker) MODE=docker ;;
  --venv) MODE=venv ;;
  "") if docker info >/dev/null 2>&1; then MODE=docker; else MODE=venv; fi ;;
  *) echo "usage: sh scripts/smoke_fresh.sh [--docker|--venv]" >&2; exit 2 ;;
esac
if [ "$MODE" = docker ] && ! docker info >/dev/null 2>&1; then
  echo "smoke_fresh: --docker needs a working Docker daemon (docker info failed); try --venv" >&2
  exit 2
fi

WORK=$(mktemp -d "${TMPDIR:-/tmp}/gitmotive-fresh.XXXXXX")
trap 'rm -rf "$WORK"' EXIT
DIST="$WORK/dist"
mkdir -p "$DIST"

# The wheel, alone in $DIST. Build from a neutral cwd: the checkout's build/ dir shadows the `build` module.
if [ -n "${GITMOTIVE_WHEEL:-}" ]; then
  cp "$GITMOTIVE_WHEEL" "$DIST/"
else
  echo "== building wheel on the host"
  if (cd "$WORK" && "$PY" -m build --version) >/dev/null 2>&1; then
    BPY=$PY
  else
    "$PY" -m venv "$WORK/buildenv"
    "$WORK/buildenv/bin/python" -m pip install -q --disable-pip-version-check build
    BPY="$WORK/buildenv/bin/python"
  fi
  (cd "$WORK" && "$BPY" -m build --wheel --outdir "$DIST" "$ROOT") >/dev/null
fi
WHEEL=$(ls "$DIST"/gitmotive-*.whl)
echo "== wheel: $(basename "$WHEEL")  mode: $MODE"

if [ "$MODE" = docker ]; then
  docker run --rm \
    -v "$DIST:/dist:ro" -v "$ROOT:/src:ro" \
    -e PIP_DISABLE_PIP_VERSION_CHECK=1 -e PIP_ROOT_USER_ACTION=ignore -e DEBIAN_FRONTEND=noninteractive \
    "$IMAGE" sh -euc '
      echo "== container: $(python3 --version)"
      apt-get update -qq >/dev/null && apt-get install -y -qq --no-install-recommends git >/dev/null
      python3 -m pip install -q pipx
      pipx install /dist/gitmotive-*.whl
      export PATH="$HOME/.local/bin:$PATH"
      SMOKE_SRC=/src SMOKE_WHEEL=$(ls /dist/gitmotive-*.whl) sh /src/scripts/smoke_inner.sh
    '
else
  unset GITMOTIVE_STORE GITMOTIVE_HOME GITMOTIVE_BIN PYTHONPATH
  export HOME="$WORK/home"
  mkdir -p "$HOME"
  "$PY" -m venv "$WORK/venv"
  "$WORK/venv/bin/python" -m pip install -q --disable-pip-version-check --no-index "$WHEEL"
  PATH="$WORK/venv/bin:$PATH" TMPDIR="$WORK" SMOKE_SRC="$ROOT" SMOKE_WHEEL="$WHEEL" \
    sh "$ROOT/scripts/smoke_inner.sh"
fi
