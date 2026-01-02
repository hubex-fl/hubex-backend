#!/usr/bin/env sh
set -eu

if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif [ -x ".venv/Scripts/python.exe" ]; then
  PY=".venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  PY="python"
fi

echo "PY=$PY"

run_step() {
  name="$1"
  shift
  echo "STEP $name"
  if "$@"; then
    echo "OK  $name"
  else
    echo "FAIL $name" >&2
    exit 1
  fi
}

run_step "compileall" "$PY" -m compileall app -q
run_step "alembic upgrade head" "$PY" -m alembic upgrade head
run_step "pytest" "$PY" -m pytest -q
run_step "alembic single head" "$PY" scripts/check_alembic_single_head.py
run_step "capability coverage" "$PY" scripts/check_capability_coverage.py
run_step "openapi snapshot" "$PY" scripts/gen-openapi-snapshot.py --check
run_step "repo hygiene" "$PY" scripts/check_repo_hygiene.py