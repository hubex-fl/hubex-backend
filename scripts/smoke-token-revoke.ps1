param(
  [string]$Base = $env:HUBEX_BASE,
  [string]$Email = $env:HUBEX_EMAIL,
  [string]$Password = $env:HUBEX_PASSWORD
)

$ErrorActionPreference = "Stop"

if (-not $Base) { $Base = "http://127.0.0.1:8000" }
if (-not $Email) { $Email = "dev@example.com" }
if (-not $Password) { $Password = "devdevdev" }

function Invoke-Req($method, $url, $headers, $bodyObj = $null) {
  try {
    $json = $null
    if ($bodyObj -ne $null) { $json = ($bodyObj | ConvertTo-Json -Depth 10) }
    $status = $null
    $resp = Invoke-RestMethod -Method $method -Uri $url -Headers $headers -Body $json -ContentType "application/json" -StatusCodeVariable status -ErrorAction Stop
    return @{ status = $status; body = ($resp | ConvertTo-Json -Depth 10) }
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

function Get-JtiFromJwt($token) {
  try {
    $parts = $token.Split(".")
    if ($parts.Length -lt 2) { return $null }
    $payload = $parts[1]
    $pad = "=" * ((4 - ($payload.Length % 4)) % 4)
    $json = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String(($payload -replace "-", "+" -replace "_", "/") + $pad))
    $obj = $json | ConvertFrom-Json
    return $obj.jti
  } catch {
    return $null
  }
}

try {
  $loginObj = Invoke-RestMethod -Method POST -Uri "$Base/api/v1/auth/login" -Body (@{ email = $Email; password = $Password } | ConvertTo-Json -Depth 10) -ContentType "application/json" -ErrorAction Stop
} catch {
  Write-Host "FAIL login request failed" -ForegroundColor Red
  $ex = $_.Exception
  if ($ex.Response) {
    $sr = New-Object System.IO.StreamReader($ex.Response.GetResponseStream())
    Write-Host $sr.ReadToEnd()
  } else {
    Write-Host $ex.Message
  }
  exit 1
}
$token = $loginObj.access_token
if (-not $token) {
  Write-Host "FAIL login missing access_token" -ForegroundColor Red
  Write-Host ($loginObj | ConvertTo-Json -Depth 10)
  exit 1
}
$jti = Get-JtiFromJwt $token
if (-not $jti) {
  Write-Host "FAIL login token missing jti" -ForegroundColor Red
  exit 1
}

$headers = @{ Authorization = "Bearer $token" }

$res1 = Invoke-Req "GET" "$Base/api/v1/users/me" $headers
if ($res1.status -ne 200) {
  Write-Host "FAIL pre-check expected 200 got $($res1.status)" -ForegroundColor Red
  Write-Host $res1.body
  exit 1
}
Write-Host "OK pre-check authenticated"

& "$PSScriptRoot\\revoke-token.ps1" -Token $token | Out-Null

$res2 = Invoke-Req "GET" "$Base/api/v1/users/me" $headers
if ($res2.status -ne 401) {
  Write-Host "FAIL revoked token expected 401 got $($res2.status)" -ForegroundColor Red
  Write-Host $res2.body
  exit 1
}
Write-Host "OK token revoked immediately"
