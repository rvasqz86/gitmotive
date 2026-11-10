#!/bin/sh
# Dry-run packaging check: build sdist + wheel in a throwaway venv and run
# `twine check --strict`. Never uploads; never reads or writes ~/.pypirc.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
PY=${PYTHON:-python3}
WORK=$(mktemp -d "${TMPDIR:-/tmp}/gitmotive-dist.XXXXXX")
trap 'rm -rf "$WORK/venv"' EXIT

"$PY" -m venv "$WORK/venv"
VPY="$WORK/venv/bin/python"
"$VPY" -m pip install -q --disable-pip-version-check build twine

DIST="$WORK/dist"
"$VPY" -m build --sdist --wheel --outdir "$DIST" "$ROOT"
"$VPY" -m twine check --strict "$DIST"/*

echo "dist files:"
for f in "$DIST"/*; do echo "  $f"; done
echo "to publish (not run):"
echo "  python -m twine upload $(echo "$DIST"/*)"
