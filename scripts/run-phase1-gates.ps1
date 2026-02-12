param()
$ErrorActionPreference="Continue"
$root = (git rev-parse --show-toplevel) 2>$null
if (-not $root) { throw "Not in a git repo; run from hubex-backend." }
Set-Location -LiteralPath $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $py)) {
  throw "Missing .venv python at $py. Create .venv and install deps first."
}
Write-Host "PY=$py"

# Temp logs outside repo
$tmp = Join-Path $env:TEMP "hubex-gates"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

function Invoke-NativeStep(
  [string]$Name,
  [string]$FilePath,
  [string[]]$Args,
  [string]$WorkingDirectory = $root
) {
  Write-Host "STEP $Name"

  $stamp = Get-Date -Format "yyyyMMdd-HHmmssfff"
  $safe  = ($Name -replace '[^a-zA-Z0-9]+','_').Trim('_')
  if ([string]::IsNullOrWhiteSpace($safe)) { $safe = "step" }

  $out = Join-Path $tmp ("{0}-{1}.out.log" -f $safe, $stamp)
  $err = Join-Path $tmp ("{0}-{1}.err.log" -f $safe, $stamp)

  $p = Start-Process -FilePath $FilePath -ArgumentList $Args -WorkingDirectory $WorkingDirectory `
        -NoNewWindow -Wait -PassThru -RedirectStandardOutput $out -RedirectStandardError $err

  if (Test-Path -LiteralPath $out) { Get-Content -LiteralPath $out | ForEach-Object { Write-Host $_ } }
  if (Test-Path -LiteralPath $err) { Get-Content -LiteralPath $err | ForEach-Object { Write-Host $_ } }

  if ($p.ExitCode -ne 0) {
    Write-Host "FAIL $Name (Exit=$($p.ExitCode))" -ForegroundColor Red
    exit $p.ExitCode
  }
  Write-Host "OK  $Name"
}

# Optional: warn if pytest missing
try { & $py -m pytest --version | Out-Null } catch {
  Write-Host "WARN pytest missing: install requirements-dev.txt" -ForegroundColor Yellow
}

Invoke-NativeStep "compileall" $py @("-m","compileall","app","-q")
Invoke-NativeStep "alembic upgrade head" $py @("-m","alembic","upgrade","head")
Invoke-NativeStep "db connectivity" $py @("scripts\smoke-db.py")
Invoke-NativeStep "pytest" $py @("-m","pytest","-q")
Invoke-NativeStep "app boot smoke" $py @("scripts\smoke-app-boot.py")
Invoke-NativeStep "auth caps smoke" $py @("scripts\smoke-auth-caps.py")
Invoke-NativeStep "alembic single head" $py @("scripts\check_alembic_single_head.py")
Invoke-NativeStep "capability coverage" $py @("scripts\check_capability_coverage.py")
Invoke-NativeStep "openapi snapshot" $py @("scripts\gen-openapi-snapshot.py","--check")
Invoke-NativeStep "repo hygiene" $py @("scripts\check_repo_hygiene.py")
Invoke-NativeStep "feature freeze marker" $py @("scripts\check_feature_frozen_marker.py")
Invoke-NativeStep "api readonly catalog" $py @("scripts\check_api_readonly_catalog.py")
Invoke-NativeStep "changelog entry" $py @("scripts\check_changelog_entry.py")


