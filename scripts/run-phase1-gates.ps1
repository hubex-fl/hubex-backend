$ErrorActionPreference = "Stop"

$steps = @(
  @{ Name = "compileall"; Cmd = { python -m compileall app -q } },
  @{ Name = "alembic upgrade head"; Cmd = { alembic upgrade head } },
  @{ Name = "pytest"; Cmd = { pytest -q } },
  @{ Name = "alembic single head"; Cmd = { python scripts/check_alembic_single_head.py } },
  @{ Name = "capability coverage"; Cmd = { python scripts/check_capability_coverage.py } },
  @{ Name = "openapi snapshot"; Cmd = { python scripts/gen-openapi-snapshot.py --check } }
)

foreach ($step in $steps) {
  try {
    & $step.Cmd
    Write-Host "OK  $($step.Name)"
  } catch {
    Write-Host "FAIL $($step.Name)" -ForegroundColor Red
    exit 1
  }
}
