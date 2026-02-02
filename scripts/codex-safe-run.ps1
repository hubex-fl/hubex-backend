param(
  [Parameter(Mandatory = $true)]
  [string]$Cmd,
  [int]$Tail = 80
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$root = (git rev-parse --show-toplevel) 2>$null
if (-not $root) {
  throw "Not in a git repo; run from hubex-backend repo root."
}
Set-Location $root

$tmp = Join-Path $root "tmp"
if (-not (Test-Path $tmp)) {
  New-Item -ItemType Directory -Path $tmp | Out-Null
}

$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$safe = ($Cmd -replace "[^a-zA-Z0-9]+", "_").Trim("_")
if (-not $safe) { $safe = "cmd" }
$log = Join-Path $tmp ($safe + "-" + $ts + ".log")

$runner = (Get-Command powershell -ErrorAction SilentlyContinue)
if (-not $runner) {
  $runner = (Get-Command pwsh -ErrorAction SilentlyContinue)
}
if (-not $runner) {
  throw "No PowerShell runner found."
}

& $runner.Source -NoProfile -ExecutionPolicy Bypass -Command $Cmd *>> $log 2>&1
$exit = $LASTEXITCODE

Write-Host "LOG=$log"
Write-Host "EXIT=$exit"
if (Test-Path $log) {
  Get-Content $log -Tail $Tail | ForEach-Object { Write-Host $_ }
}

exit $exit
