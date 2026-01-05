#!/usr/bin/env sh
set -eu

root=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$root" ]; then
  echo "Not inside a git repo. Run from within the hubex repo." >&2
  exit 1
fi
cd "$root"

if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif [ -x ".venv/Scripts/python.exe" ]; then
  PY=".venv/Scripts/python.exe"
else
  echo "Missing .venv python. Create venv and install deps first." >&2
  exit 1
fi

echo "PY=$PY"

step() {
  echo "STEP $1"
  shift
  "$@"
}

step "phase1 gates" "$root/scripts/run-phase1-gates.sh"
step "frontend typecheck" npm --prefix frontend run typecheck
step "frontend test" npm --prefix frontend run test
step "frontend build" npm --prefix frontend run build
