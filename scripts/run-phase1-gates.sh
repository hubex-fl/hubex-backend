#!/usr/bin/env sh
set -eu

run_step() {
  name="$1"
  shift
  if "$@"; then
    echo "OK  $name"
  else
    echo "FAIL $name" >&2
    exit 1
  fi
}

run_step "compileall" python -m compileall app -q
run_step "alembic upgrade head" alembic upgrade head
run_step "pytest" pytest -q
run_step "alembic single head" python scripts/check_alembic_single_head.py
run_step "capability coverage" python scripts/check_capability_coverage.py
run_step "openapi snapshot" python scripts/gen-openapi-snapshot.py --check
