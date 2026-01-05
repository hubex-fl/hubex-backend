#!/usr/bin/env sh
set -eu

root=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$root" ]; then
  echo "Not in a git repo; run from hubex-backend repo root." >&2
  exit 1
fi
cd "$root"

if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif [ -x ".venv/Scripts/python.exe" ]; then
  PY=".venv/Scripts/python.exe"
else
  echo "Missing .venv python. Create .venv and install deps first." >&2
  exit 1
fi

echo "PY=$PY"

step() {
  echo "STEP $1"
  shift
  "$@"
  echo "OK $1"
}

step "compileall" "$PY" -m compileall app -q
step "alembic upgrade head" "$PY" -m alembic upgrade head
step "pytest" "$PY" -m pytest -q
step "check alembic single head" "$PY" scripts/check_alembic_single_head.py
step "check capability coverage" "$PY" scripts/check_capability_coverage.py
step "openapi snapshot check" "$PY" scripts/gen-openapi-snapshot.py --check
step "frontend typecheck" npm --prefix frontend run typecheck
step "frontend test" npm --prefix frontend run test
step "frontend build" npm --prefix frontend run build
