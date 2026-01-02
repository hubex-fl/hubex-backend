$ErrorActionPreference = "Stop"

$py = ".\\.venv\\Scripts\\python.exe"
if (-not (Test-Path $py)) {
  $py = "python"
}
Write-Host "PY=$py"
try {
  & $py -m pytest --version | Out-Null
} catch {
  Write-Host "WARN pytest missing: install requirements-dev.txt" -ForegroundColor Yellow
}

$steps = @(
  @{ Name = "compileall"; Cmd = { & $py -m compileall app -q } },
  @{ Name = "alembic upgrade head"; Cmd = { & $py -m alembic upgrade head } },
  @{ Name = "pytest"; Cmd = { & $py -m pytest -q } },
  @{ Name = "alembic single head"; Cmd = { & $py scripts/check_alembic_single_head.py } },
  @{ Name = "capability coverage"; Cmd = { & $py scripts/check_capability_coverage.py } },
  @{ Name = "openapi snapshot"; Cmd = { & $py scripts/gen-openapi-snapshot.py --check } },
  @{ Name = "repo hygiene"; Cmd = { & $py scripts/check_repo_hygiene.py } }
  @{ Name = "feature freeze marker"; Cmd = { & $py scripts/check_feature_frozen_marker.py } }
)

foreach ($step in $steps) {
  Write-Host "STEP $($step.Name)"
  try {
    & $step.Cmd
    Write-Host "OK  $($step.Name)"
  } catch {
    Write-Host "FAIL $($step.Name)" -ForegroundColor Red
    exit 1
  }
}
