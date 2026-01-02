param(
  [string]$Base = $env:HUBEX_BASE,
  [string]$Token = $env:HUBEX_TOKEN
)

$ErrorActionPreference = "Stop"

if (-not $Base) { $Base = "http://127.0.0.1:8000" }
if (-not $Token) {
  Write-Host "HUBEX_TOKEN missing" -ForegroundColor Red
  exit 1
}

function Invoke-Req($method, $url, $headers) {
  try {
    $resp = Invoke-WebRequest -Method $method -Uri $url -Headers $headers -ErrorAction Stop
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

$headers = @{ Authorization = "Bearer $Token" }

$res1 = Invoke-Req "GET" "$Base/api/v1/users/me" $headers
if ($res1.status -ne 200) {
  Write-Host "FAIL pre-check expected 200 got $($res1.status)" -ForegroundColor Red
  Write-Host $res1.body
  exit 1
}
Write-Host "OK pre-check authenticated"

& "$PSScriptRoot\\revoke-token.ps1" -Token $Token | Out-Null

$res2 = Invoke-Req "GET" "$Base/api/v1/users/me" $headers
if ($res2.status -ne 401) {
  Write-Host "FAIL revoked token expected 401 got $($res2.status)" -ForegroundColor Red
  Write-Host $res2.body
  exit 1
}
Write-Host "OK token revoked immediately"
