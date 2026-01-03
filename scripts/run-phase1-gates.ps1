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
  @{ Name = "db connectivity"; Cmd = { & $py scripts/smoke-db.py } },
  @{ Name = "pytest"; Cmd = { & $py -m pytest -q } },
  @{ Name = "app boot smoke"; Cmd = { & $py scripts/smoke-app-boot.py } },
  @{ Name = "auth caps smoke"; Cmd = { & $py scripts/smoke-auth-caps.py } },
  @{ Name = "alembic single head"; Cmd = { & $py scripts/check_alembic_single_head.py } },
  @{ Name = "capability coverage"; Cmd = { & $py scripts/check_capability_coverage.py } },
  @{ Name = "openapi snapshot"; Cmd = { & $py scripts/gen-openapi-snapshot.py --check } },
  @{ Name = "repo hygiene"; Cmd = { & $py scripts/check_repo_hygiene.py } },
  @{ Name = "feature freeze marker"; Cmd = { & $py scripts/check_feature_frozen_marker.py } },
  @{ Name = "api readonly catalog"; Cmd = { & $py scripts/check_api_readonly_catalog.py } },
  @{ Name = "changelog entry"; Cmd = { & $py scripts/check_changelog_entry.py } }
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
