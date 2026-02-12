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

$tmp = Join-Path $env:TEMP "hubex-gates"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

function Invoke-NativeStep(
  [string]$Name,
  [string]$FilePath,
  [string[]]$ArgList,
  [string]$WorkingDirectory = $root
) {
  Write-Host "STEP $Name"

  $stamp = Get-Date -Format "yyyyMMdd-HHmmssfff"
  $safe  = ($Name -replace '[^a-zA-Z0-9]+','_').Trim('_')
  if ([string]::IsNullOrWhiteSpace($safe)) { $safe = "step" }

  $out = Join-Path $tmp ("{0}-{1}.out.log" -f $safe, $stamp)
  $err = Join-Path $tmp ("{0}-{1}.err.log" -f $safe, $stamp)

  $p = Start-Process -FilePath $FilePath -ArgumentList $ArgList -WorkingDirectory $WorkingDirectory `
        -NoNewWindow -Wait -PassThru -RedirectStandardOutput $out -RedirectStandardError $err

  if (Test-Path -LiteralPath $out) { Get-Content -LiteralPath $out | ForEach-Object { Write-Host $_ } }
  if (Test-Path -LiteralPath $err) { Get-Content -LiteralPath $err | ForEach-Object { Write-Host $_ } }

  if ($p.ExitCode -ne 0) {
    Write-Host "FAIL $Name (Exit=$($p.ExitCode))" -ForegroundColor Red
    exit $p.ExitCode
  }
  Write-Host "OK  $Name"
}

# npm on Windows must run via npm.cmd for Start-Process
$npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
if (-not $npm) {
  $npm = (Get-Command npm -ErrorAction Stop).Source
}

Invoke-NativeStep "compileall" $py @("-m","compileall","app","-q")
Invoke-NativeStep "alembic upgrade head" $py @("-m","alembic","upgrade","head")
Invoke-NativeStep "pytest" $py @("-m","pytest","-q")
Invoke-NativeStep "check alembic single head" $py @("scripts\check_alembic_single_head.py")
Invoke-NativeStep "check capability coverage" $py @("scripts\check_capability_coverage.py")
Invoke-NativeStep "openapi snapshot check" $py @("scripts\gen-openapi-snapshot.py","--check")
Invoke-NativeStep "frontend typecheck" $npm @("--prefix","frontend","run","typecheck")
Invoke-NativeStep "frontend test" $npm @("--prefix","frontend","run","test")
Invoke-NativeStep "frontend build" $npm @("--prefix","frontend","run","build")


