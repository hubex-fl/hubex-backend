param(
  [string]$Token = $env:HUBEX_TOKEN,
  [string]$Jti = $env:HUBEX_JTI,
  [string]$Reason = $env:HUBEX_REVOKE_REASON
)

$ErrorActionPreference = "Stop"

if (-not $Token -and -not $Jti) {
  Write-Host "Missing token or jti. Set HUBEX_TOKEN or pass -Token / -Jti." -ForegroundColor Red
  exit 1
}

$args = @()
if ($Token) { $args += @("--token", $Token) }
if ($Jti) { $args += @("--jti", $Jti) }
if ($Reason) { $args += @("--reason", $Reason) }

& .\.venv\Scripts\python -m app.scripts.revoke_token @args
