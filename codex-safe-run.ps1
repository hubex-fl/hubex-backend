param(
  [Parameter(Mandatory = $true)]
  [string]$Cmd,
  [int]$Tail = 80
)

$ErrorActionPreference = "Stop"
# Native tools may write INFO/errors to stderr; runner must not terminate because of that.
$PSNativeCommandUseErrorActionPreference = $false

Set-Location $PSScriptRoot

$tmp = Join-Path $PSScriptRoot "tmp"
if (-not (Test-Path $tmp)) {
  New-Item -ItemType Directory -Path $tmp | Out-Null
}

$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$safe = ($Cmd -replace '[\\/:*?"<>|\s]+', '_').Trim('_')
if (-not $safe) { $safe = "cmd" }
$log = Join-Path $tmp ($safe + "-" + $ts + ".log")

$shell = (Get-Command pwsh -ErrorAction SilentlyContinue)
if (-not $shell) {
  $shell = (Get-Command powershell -ErrorAction SilentlyContinue)
}
if (-not $shell) {
  throw "No PowerShell runner found."
}

$exit = $null
try {
  & $shell.Source -NoProfile -ExecutionPolicy Bypass -Command $Cmd 2>&1 | Out-File -Append -FilePath $log -Encoding utf8
  $exit = $LASTEXITCODE
} catch {
  ($_ | Out-String).TrimEnd() | Out-File -FilePath $log -Append -Encoding utf8
  $exit = 1
}
if ($exit -eq $null) { $exit = 1 }

Write-Host "LOG=$log"
Write-Host "EXIT=$exit"
if (Test-Path $log) {
  Get-Content $log -Tail $Tail | ForEach-Object { Write-Host $_ }
}

exit $exit
