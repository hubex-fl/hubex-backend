$ErrorActionPreference = "Stop"

$baseUrl = "http://localhost:8000/api/v1"
$pw = "Test1234!"
$email = "codex+$((Get-Date).ToString('yyyyMMddHHmmss'))@example.com"
$deviceUid = "device-1234"

Write-Host "Register..."
$null = curl.exe -s -X POST "$baseUrl/auth/register" `
  -H "Content-Type: application/json" `
  -d "{\"email\":\"$email\",\"password\":\"$pw\"}"

Write-Host "Login..."
$login = curl.exe -s -X POST "$baseUrl/auth/login" `
  -H "Content-Type: application/json" `
  -d "{\"email\":\"$email\",\"password\":\"$pw\"}"
$token = ($login | ConvertFrom-Json).access_token

Write-Host "User me..."
curl.exe -s -X GET "$baseUrl/users/me" `
  -H "Authorization: Bearer $token"

Write-Host "Device hello..."
curl.exe -s -X POST "$baseUrl/devices/hello" `
  -H "Content-Type: application/json" `
  -d "{\"device_uid\":\"$deviceUid\",\"firmware_version\":\"1.0.0\",\"capabilities\":{\"wifi\":true}}"

Write-Host "Pairing start..."
$pairing = curl.exe -s -X POST "$baseUrl/pairing/start" `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d "{\"device_uid\":\"$deviceUid\"}"
$pairingObj = $pairing | ConvertFrom-Json

Write-Host "Pairing confirm (no JWT)..."
$confirm = curl.exe -s -X POST "$baseUrl/pairing/confirm" `
  -H "Content-Type: application/json" `
  -d "{\"device_uid\":\"$deviceUid\",\"pairing_code\":\"$($pairingObj.pairing_code)\"}"
$confirmObj = $confirm | ConvertFrom-Json
$deviceToken = $confirmObj.device_token
$deviceId = $confirmObj.device_id

Write-Host "Device whoami (device token)..."
curl.exe -s -X GET "$baseUrl/devices/whoami" `
  -H "X-Device-Token: $deviceToken"

Write-Host "Devices list (owner)..."
curl.exe -s -X GET "$baseUrl/devices" `
  -H "Authorization: Bearer $token"

Write-Host "Device detail (owner)..."
curl.exe -s -X GET "$baseUrl/devices/$deviceId" `
  -H "Authorization: Bearer $token"
