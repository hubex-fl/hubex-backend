param(
  [string]$Base = $(if ($env:HUBEX_BASE) { $env:HUBEX_BASE } else { "http://127.0.0.1:8000" }),
  [string]$Token = $env:HUBEX_TOKEN
)

$ErrorActionPreference = "Stop"

if (-not $Token) {
  throw "HUBEX_TOKEN missing"
}

$Headers = @{ Authorization = "Bearer $Token" }
$Endpoint = "$Base/api/v1/devices"

function CallOnce {
  try {
    $resp = Invoke-WebRequest -UseBasicParsing -Method GET -Uri $Endpoint -Headers $Headers -ErrorAction Stop
    return @{ status = [int]$resp.StatusCode }
  } catch {
    $ex = $_.Exception
    $status = $null
    if ($ex.Response) {
      $status = [int]$ex.Response.StatusCode
    }
    return @{ status = $status }
  }
}

Write-Host "SMOKE_RL_BASE=$Base"

$counts = @{}
function IncStatus($code) {
  if (-not $counts.ContainsKey($code)) { $counts[$code] = 0 }
  $counts[$code] += 1
}

if ($env:HUBEX_RL_ENABLED -eq "1") {
  $max = 60
  $found = $false
  for ($i = 0; $i -lt $max; $i++) {
    $res = CallOnce
    IncStatus $res.status
    if ($res.status -eq 429) {
      $found = $true
      break
    }
  }
  if (-not $found) {
    throw "FAIL: expected 429 with HUBEX_RL_ENABLED=1"
  }
  Write-Host "OK: 429 observed (rate limit enabled)"
} else {
  for ($i = 0; $i -lt 15; $i++) {
    $res = CallOnce
    IncStatus $res.status
    if ($res.status -eq 429) {
      throw "FAIL: unexpected 429 with HUBEX_RL_ENABLED!=1"
    }
  }
  Write-Host "OK: no 429 (rate limit disabled)"
}

$hist = ($counts.GetEnumerator() | Sort-Object Name | ForEach-Object { "$($_.Name)=$($_.Value)" }) -join ", "
Write-Host "STATUS_HISTOGRAM $hist"
