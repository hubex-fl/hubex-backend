param(
  [string]$ApiBase = 'http://127.0.0.1:8000',
  [Parameter(Mandatory=$true)][string]$OwnerJwt,
  [Parameter(Mandatory=$true)][string]$DeviceUid,
  [string]$OutFile = '.\device-token.json'
)

$ErrorActionPreference = 'Stop'

function Invoke-Json($method, $url, $headers, $bodyObj=$null) {
  $json = $null
  if ($bodyObj -ne $null) {
    $json = ($bodyObj | ConvertTo-Json -Depth 20)
  }
  return Invoke-RestMethod -Method $method -Uri $url -Headers $headers -ContentType 'application/json' -Body $json
}

$authHeaders = @{
  'Authorization' = "Bearer $OwnerJwt"
}

Write-Host '[1/3] Pairing start'
$start = Invoke-Json 'POST' "$ApiBase/api/v1/pairing/start" $authHeaders @{ device_uid = $DeviceUid }
$pairingCode = $start.pairing_code
Write-Host "pairing_code=$pairingCode"

Write-Host '[2/3] Device hello'
$hello = Invoke-Json 'POST' "$ApiBase/api/v1/devices/hello" $authHeaders @{ device_uid = $DeviceUid }
$deviceId = $hello.device_id

Write-Host '[3/3] Pairing confirm'
$confirm = Invoke-Json 'POST' "$ApiBase/api/v1/pairing/confirm" $authHeaders @{
  device_uid   = $DeviceUid
  pairing_code = $pairingCode
}

$out = @{
  device_id    = $confirm.device_id
  device_token = $confirm.device_token
}

$out | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 $OutFile
Write-Host "Saved device token to $OutFile"
