$ErrorActionPreference = "Stop"

param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$WorkerId = "worker-demo",
  [string]$DefinitionKey = "demo.rules_min",
  [switch]$StartBackend,
  [switch]$NoSeed,
  [int]$RunTimeoutSec = 45
)

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $repo
Set-Location -LiteralPath $repo

$py = ".\\.venv\\Scripts\\python.exe"
if (-not (Test-Path -LiteralPath $py)) {
  throw "missing venv python: $py"
}

$token = $env:HUBEX_TOKEN
if (-not $token) {
  throw "HUBEX_TOKEN is required (needs executions.write; executions.read for verification)"
}

if ($StartBackend) {
  Write-Host "Starting backend..."
  $backend = Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\\scripts\\dev-backend.ps1"
  ) -PassThru -WindowStyle Hidden

  $ready = $false
  1..10 | ForEach-Object {
    try {
      $resp = Invoke-WebRequest -Uri "$BaseUrl/api/v1/openapi.json" -UseBasicParsing -TimeoutSec 2
      if ($resp.StatusCode -eq 200) { $ready = $true; return }
    } catch {
      Start-Sleep -Seconds 2
    }
  }
  if (-not $ready) {
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    throw "backend not reachable at $BaseUrl"
  }
}

if (-not $NoSeed) {
  Write-Host "Seeding definition/run..."
  $headers = @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" }
  $defBody = @{ key = $DefinitionKey; name = $DefinitionKey; version = "v1"; enabled = $true } | ConvertTo-Json -Compress
  Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/executions/definitions" -Headers $headers -Body $defBody | Out-Null

  $runBody = @{
    definition_key = $DefinitionKey
    idempotency_key = "demo-$([Guid]::NewGuid().ToString("N"))"
    requested_by = "demo"
    input_json = @{ ok = $true }
  } | ConvertTo-Json -Compress
  Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/executions/runs" -Headers $headers -Body $runBody | Out-Null
}

Write-Host "Running worker (RUN_ONCE=1)..."
$env:HUBEX_BASE_URL = $BaseUrl
$env:WORKER_ID = $WorkerId
$env:DEFINITION_KEY = $DefinitionKey
$env:RUN_ONCE = "1"

$worker = Start-Process -FilePath $py -ArgumentList @("scripts\\execution_worker_service.py") -PassThru -NoNewWindow
$finished = $worker.WaitForExit($RunTimeoutSec * 1000)
if (-not $finished) {
  Stop-Process -Id $worker.Id -Force -ErrorAction SilentlyContinue
  throw "worker did not exit within $RunTimeoutSec seconds"
}
if ($worker.ExitCode -ne 0) {
  throw "worker exited with code $($worker.ExitCode)"
}

try {
  $headers = @{ Authorization = "Bearer $token" }
  $workers = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/v1/executions/workers?limit=200" -Headers $headers
  $ids = @($workers.items | ForEach-Object { $_.id })
  if ($ids -notcontains $WorkerId) {
    throw "worker heartbeat not found for $WorkerId"
  }
  Write-Host "OK: heartbeat registered for $WorkerId"
} catch {
  Write-Host "WARNING: unable to verify heartbeat via GET /executions/workers (requires executions.read)."
}

Write-Host "DONE."
