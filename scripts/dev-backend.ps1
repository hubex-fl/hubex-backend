param(
  [int]$Port = 8000,
  [int]$StartupTimeoutSeconds = 15,
  [ValidateSet("start", "follow", "stop", "status")]
  [string]$Action = "start",
  [switch]$Follow,
  [switch]$StderrOnly
)

$ErrorActionPreference = "Stop"

function Log([string]$Message) { Write-Output $Message }
function Warn([string]$Message) { Write-Warning $Message }
function Err([string]$Message) { Write-Error $Message }
function ReadPid([string]$Path) {
  if (-not (Test-Path $Path)) { return $null }
  $pidText = Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $pidText) { return $null }
  return [int]$pidText
}
function GetListeners([int]$ListenPort) {
  return Get-NetTCPConnection -LocalPort $ListenPort -State Listen -ErrorAction SilentlyContinue
}
function PrintPortOwners($Listeners) {
  if (-not $Listeners) { return }
  $pids = $Listeners | Select-Object -ExpandProperty OwningProcess -Unique
  Log ("Port {0} is already in use by PID(s): {1}" -f $Port, ($pids -join ", "))
  foreach ($pidValue in $pids) {
    $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    if ($proc) {
      Log ("  PID {0}: {1} ({2})" -f $pidValue, $proc.ProcessName, $proc.Path)
    }
  }
  Log "Stop the existing process or set HUBEX_PORT to a free port."
}
function TailFile([string]$Path) {
  if (-not (Test-Path $Path)) {
    Log ("Log not found: {0}" -f $Path)
    return
  }
  Get-Content -LiteralPath $Path -Tail 50 -Wait
}

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

if ($Action -eq "status") {
  $pidValue = ReadPid $pidFile
  if ($pidValue) {
    $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    if ($proc) {
      Log ("PID file: {0} (alive)" -f $pidValue)
    } else {
      Log ("PID file: {0} (not running)" -f $pidValue)
    }
  } else {
    Log "PID file: missing"
  }
  $listeners = GetListeners $Port
  if ($listeners) {
    PrintPortOwners $listeners
  } else {
    Log ("Port {0} is not listening." -f $Port)
  }
  Log ("Logs: {0} , {1}" -f $stdout, $stderr)
  exit 0
}

if ($Action -eq "stop") {
  $pidValue = ReadPid $pidFile
  if ($pidValue) {
    Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
  }
  $listeners = GetListeners $Port
  if ($listeners) {
    PrintPortOwners $listeners
    exit 1
  }
  Log "Backend stopped."
  exit 0
}

if ($Action -eq "follow") {
  if ($StderrOnly) {
    TailFile $stderr
    exit 0
  }
  $stdoutJob = Start-Job -ScriptBlock { param($p) Get-Content -LiteralPath $p -Tail 50 -Wait } -ArgumentList $stdout
  TailFile $stderr
  Stop-Job $stdoutJob -Force -ErrorAction SilentlyContinue
  Remove-Job $stdoutJob -Force -ErrorAction SilentlyContinue
  exit 0
}

$pidValue = ReadPid $pidFile
if ($pidValue) {
  $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
  if ($proc) {
    Log ("Backend already running (PID={0}, port={1}). Not starting another instance." -f $pidValue, $Port)
    Log ("URL: http://{0}:{1}" -f $BindHost, $Port)
    if ($Follow) {
      if ($StderrOnly) {
        TailFile $stderr
      } else {
        $stdoutJob = Start-Job -ScriptBlock { param($p) Get-Content -LiteralPath $p -Tail 50 -Wait } -ArgumentList $stdout
        TailFile $stderr
        Stop-Job $stdoutJob -Force -ErrorAction SilentlyContinue
        Remove-Job $stdoutJob -Force -ErrorAction SilentlyContinue
      }
    }
    exit 0
  }
}

$listeners = GetListeners $Port
if ($listeners) {
  PrintPortOwners $listeners
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
  -RedirectStandardOutput $stdout -RedirectStandardError $stderr -NoNewWindow -WorkingDirectory $repo -PassThru
$proc.Id | Set-Content -LiteralPath $pidFile -Encoding ascii

$deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
$listeners = $null
while ((Get-Date) -lt $deadline) {
  $listeners = GetListeners $Port
  if ($listeners) { break }
  Start-Sleep -Milliseconds 300
}

if (-not $listeners) {
  Log "Backend did not start in time. Last errors:"
  if (Test-Path $stderr) { Get-Content -LiteralPath $stderr -Tail 50 | Write-Output }
  exit 1
}

Log ("Backend running: http://{0}:{1} (PID={2})" -f $BindHost, $Port, $proc.Id)
if ($Follow) {
  if ($StderrOnly) {
    TailFile $stderr
  } else {
    $stdoutJob = Start-Job -ScriptBlock { param($p) Get-Content -LiteralPath $p -Tail 50 -Wait } -ArgumentList $stdout
    TailFile $stderr
    Stop-Job $stdoutJob -Force -ErrorAction SilentlyContinue
    Remove-Job $stdoutJob -Force -ErrorAction SilentlyContinue
  }
}
