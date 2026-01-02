param(
  [string]$Base = $(if ($env:HUBEX_BASE) { $env:HUBEX_BASE } else { "http://127.0.0.1:8000" }),
  [string]$Token = $env:HUBEX_TOKEN
)

$ErrorActionPreference = "Stop"

if (-not $Token) {
  throw "HUBEX_TOKEN missing"
}

$Headers = @{ Authorization = "Bearer $Token" }
$Endpoint = "$Base/api/v1/variables/defs"

function CallOnce {
  try {
    $resp = Invoke-WebRequest -Method GET -Uri $Endpoint -Headers $Headers -ErrorAction Stop
    return @{ ok = $true; status = [int]$resp.StatusCode; body = $resp.Content }
  } catch {
    $ex = $_.Exception
    $status = $null
    $body = $null
    if ($ex.Response) {
      $status = [int]$ex.Response.StatusCode
      $sr = New-Object System.IO.StreamReader($ex.Response.GetResponseStream())
      $body = $sr.ReadToEnd()
    }
    return @{ ok = $false; status = $status; body = $body }
  }
}

Write-Host "SMOKE_RL_BASE=$Base"

$hits = @()
for ($i = 0; $i -lt 10; $i++) {
  $hits += CallOnce
}

$has429 = $hits | Where-Object { $_.status -eq 429 }

if ($env:HUBEX_RL_ENABLED -eq "1") {
  if (-not $has429) {
    throw "FAIL: expected 429 with HUBEX_RL_ENABLED=1"
  }
  Write-Host "OK: 429 observed (rate limit enabled)"
} else {
  if ($has429) {
    throw "FAIL: unexpected 429 with HUBEX_RL_ENABLED!=1"
  }
  Write-Host "OK: no 429 (rate limit disabled)"
}
