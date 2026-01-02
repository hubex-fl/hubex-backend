param(
  [string]$Base = "http://127.0.0.1:8000",
  [string]$Token = $env:HUBEX_TOKEN
)

$ErrorActionPreference = "Stop"

Write-Host "SMOKE_CAPS base=$Base"

# Enforce=0 (log-only)
$env:HUBEX_CAPS_ENFORCE = "0"
Write-Host "MODE enforce=0"

function Invoke-Req($method, $url, $headers, $bodyObj=$null) {
  $json = $null
  if ($null -ne $bodyObj) { $json = ($bodyObj | ConvertTo-Json -Depth 10 -Compress) }
  try {
    $resp = Invoke-WebRequest -Method $method -Uri $url -Headers $headers -Body $json -ContentType "application/json" -ErrorAction Stop
    return @{ status = $resp.StatusCode; body = $resp.Content }
  } catch {
    $ex = $_.Exception
    $status = $null
    $content = $null
    if ($ex.Response) {
      $status = [int]$ex.Response.StatusCode
      $sr = New-Object System.IO.StreamReader($ex.Response.GetResponseStream())
      $content = $sr.ReadToEnd()
    }
    return @{ status = $status; body = $content }
  }
}

# 1) Whitelisted route without token should be reachable
$uid = "smoke-caps-" + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$hello = Invoke-Req "POST" "$Base/api/v1/devices/hello" @{} @{ device_uid = $uid }
if ($hello.status -ne 200) {
  Write-Host "FAIL whitelist /devices/hello expected 200 got $($hello.status)" -ForegroundColor Red
  Write-Host $hello.body
  exit 1
}
Write-Host "OK whitelist /devices/hello"

# 2) Non-whitelisted without token => 401 (handler-level auth)
$noauth = Invoke-Req "GET" "$Base/api/v1/devices" @{} $null
if ($noauth.status -ne 401) {
  Write-Host "FAIL non-whitelist without token expected 401 got $($noauth.status)" -ForegroundColor Red
  Write-Host $noauth.body
  exit 1
}
Write-Host "OK non-whitelist without token => 401"

# 3) Non-whitelisted with token should pass in enforce=0 (no cap blocking)
if ($Token) {
  $headers = @{ Authorization = "Bearer $Token" }
  $ok = Invoke-Req "GET" "$Base/api/v1/devices" $headers $null
  if ($ok.status -ne 200) {
    Write-Host "FAIL enforce=0 expected 200 got $($ok.status)" -ForegroundColor Red
    Write-Host $ok.body
    exit 1
  }
  Write-Host "OK enforce=0 non-whitelist with token => 200"
} else {
  Write-Host "HUBEX_TOKEN missing; skip enforce=0 token check" -ForegroundColor Yellow
}

# Enforce=1 (real blocking)
$env:HUBEX_CAPS_ENFORCE = "1"
Write-Host "MODE enforce=1"

# 4) Non-whitelisted with token lacking caps => 403
if (-not $Token) {
  Write-Host "HUBEX_TOKEN missing; cannot verify 403 on insufficient caps" -ForegroundColor Yellow
  exit 0
}
$headers = @{ Authorization = "Bearer $Token" }
$forbidden = Invoke-Req "GET" "$Base/api/v1/devices" $headers $null
if ($forbidden.status -ne 403) {
  Write-Host "FAIL enforce=1 expected 403 got $($forbidden.status)" -ForegroundColor Red
  Write-Host $forbidden.body
  exit 1
}
Write-Host "OK enforce=1 non-whitelist with token lacking caps => 403"
