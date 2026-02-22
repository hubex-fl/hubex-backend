param(
  [int]$Port = 8000,
  [int]$StartupTimeoutSeconds = 15
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
  Write-Host "Missing .venv. Create it with:" -ForegroundColor Yellow
  Write-Host "  python -m venv .venv"
  Write-Host "  .\.venv\Scripts\Activate.ps1"
  Write-Host "  python -m pip install -r requirements.txt"
  exit 1
}

$envPort = $env:HUBEX_PORT
if ($envPort) { $Port = [int]$envPort }
$BindHost = $env:HUBEX_HOST
if (-not $BindHost) { $BindHost = "0.0.0.0" }
$Reload = $env:HUBEX_RELOAD
if (-not $Reload) { $Reload = "1" }

$repo = (Get-Item ".").FullName
$runDir = Join-Path $repo ".run"
New-Item -ItemType Directory -Path $runDir -Force | Out-Null
$pidFile = Join-Path $runDir "uvicorn.pid"
$stdout = Join-Path $runDir "uvicorn.out.log"
$stderr = Join-Path $runDir "uvicorn.err.log"

if (Test-Path $pidFile) {
  $pidText = Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($pidText) {
    $pidValue = [int]$pidText
    $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    if ($proc) {
      Write-Host ("Backend already running (PID={0}, port={1}). Not starting another instance." -f $pidValue, $Port)
      Write-Host ("URL: http://{0}:{1}" -f $BindHost, $Port)
      exit 0
    }
  }
}

$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
  $pids = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
  Write-Host ("Port {0} is already in use by PID(s): {1}" -f $Port, ($pids -join ", "))
  foreach ($pidValue in $pids) {
    $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    if ($proc) {
      Write-Host ("  PID {0}: {1} ({2})" -f $pidValue, $proc.ProcessName, $proc.Path)
    }
  }
  Write-Host "Stop the existing process or set HUBEX_PORT to a free port."
  exit 1
}

Write-Host "Activating venv..."
. .\.venv\Scripts\Activate.ps1

Write-Host "Tip: install deps if needed: python -m pip install -r requirements.txt"
Write-Host ("Starting backend on http://{0}:{1} (reload={2})..." -f $BindHost, $Port, $Reload)

$args = @("-m", "uvicorn", "app.main:app", "--host", $BindHost, "--port", $Port)
if ($Reload -eq "1" -or $Reload -eq "true" -or $Reload -eq "True") {
  $args += "--reload"
}

$proc = Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList $args `
  -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
$proc.Id | Set-Content -LiteralPath $pidFile -Encoding ascii

$deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
$listeners = $null
while ((Get-Date) -lt $deadline) {
  $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if ($listeners) { break }
  Start-Sleep -Milliseconds 300
}

if (-not $listeners) {
  Write-Host "Backend did not start in time. Last errors:"
  if (Test-Path $stderr) { Get-Content -LiteralPath $stderr -Tail 50 | Write-Host }
  exit 1
}

Write-Host ("Backend running: http://{0}:{1} (PID={2})" -f $BindHost, $Port, $proc.Id)
