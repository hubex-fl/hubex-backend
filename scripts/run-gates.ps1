param()

$ErrorActionPreference = "Stop"
# Native tools may write INFO to stderr; gates must fail only on exit codes.
$PSNativeCommandUseErrorActionPreference = $false

$root = (git rev-parse --show-toplevel) 2>$null
if (-not $root) {
  throw "Not in a git repo; run from hubex-backend repo root."
}
Set-Location $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  throw "Missing .venv python at $py. Create .venv and install deps first."
}
Write-Host "PY=$py"

function Run-Step([string]$name, [scriptblock]$cmd, [switch]$IsAlembic) {
  Write-Host "STEP $name"
  if ($IsAlembic) {
    $out = & $cmd 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host $out; throw "FAIL $name" }
    Write-Host "OK  $name"
    return
  }

  & $cmd
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  Write-Host "OK  $name"
}

Run-Step "compileall" { & $py -m compileall app -q }
Run-Step "alembic upgrade head" { & $py -m alembic upgrade head } -IsAlembic
Run-Step "pytest" { & $py -m pytest -q }
Run-Step "check alembic single head" { & $py scripts\check_alembic_single_head.py }
Run-Step "check capability coverage" { & $py scripts\check_capability_coverage.py }
Run-Step "openapi snapshot check" { & $py scripts\gen-openapi-snapshot.py --check }
Run-Step "frontend typecheck" { npm --prefix frontend run typecheck }
Run-Step "frontend test" { npm --prefix frontend run test }
Run-Step "frontend build" { npm --prefix frontend run build }
