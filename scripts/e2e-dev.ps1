$ErrorActionPreference = "Stop"

$Base = $env:HUBEX_BASE
if (-not $Base) { $Base = "http://127.0.0.1:8000" }
$Email = $env:HUBEX_EMAIL
if (-not $Email) { $Email = "dev@example.com" }
$Password = $env:HUBEX_PASSWORD
if (-not $Password) { $Password = "devdevdev" }
$RunSeconds = 30
if ($env:HUBEX_SIM_SECONDS) { $RunSeconds = [int]$env:HUBEX_SIM_SECONDS }

function Fail {
    param([string]$Message, [hashtable]$Resp)
    Write-Host "FAIL: $Message"
    if ($Resp) {
        Write-Host "Status: $($Resp.Status)"
        Write-Host "Body: $($Resp.Body)"
    }
    exit 1
}

function Invoke-Api {
    param(
        [string]$Method,
        [string]$Url,
        [string]$Body,
        [hashtable]$Headers
    )
    $args = @("-sS", "-X", $Method, $Url, "-w", "`n%{http_code}")
    if ($Headers) {
        foreach ($k in $Headers.Keys) {
            $args += @("-H", "${k}: $($Headers[$k])")
        }
    }
    if ($Body -ne $null) {
        $out = $Body | & curl.exe @args --data-binary '@-'
    } else {
        $out = & curl.exe @args
    }
    if ($LASTEXITCODE -ne 0) {
        Fail "curl failed: $Method $Url" $null
    }
    $lines = $out -split "`n"
    if ($lines.Length -eq 1) {
        return @{ Status = [int]$lines[0]; Body = "" }
    }
    $status = [int]$lines[-1]
    $body = ($lines[0..($lines.Length - 2)] -join "`n")
    return @{ Status = $status; Body = $body }
}

function Parse-Json {
    param([string]$Body, [string]$Label)
    try {
        return $Body | ConvertFrom-Json
    } catch {
        Fail "$Label (invalid JSON)" @{ Status = -1; Body = $Body }
    }
}

$payload = @{ email = $Email; password = $Password } | ConvertTo-Json -Compress
Write-Host "Login..."
$resp = Invoke-Api "POST" "$Base/api/v1/auth/login" $payload @{ "Content-Type" = "application/json" }
if ($resp.Status -ne 200) {
    Write-Host "Register..."
    $reg = Invoke-Api "POST" "$Base/api/v1/auth/register" $payload @{ "Content-Type" = "application/json" }
    if ($reg.Status -ne 200) { Fail "register" $reg }
    $resp = Invoke-Api "POST" "$Base/api/v1/auth/login" $payload @{ "Content-Type" = "application/json" }
    if ($resp.Status -ne 200) { Fail "login" $resp }
}
$token = (Parse-Json $resp.Body "login").access_token
if (-not $token) { Fail "login token missing" $resp }

$deviceUid = "e2e-$((Get-Date).ToString('yyyyMMddHHmmss'))"
$helloBody = @{ device_uid = $deviceUid; firmware_version = "sim-1.0"; capabilities = @{ sim = $true } } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$Base/api/v1/devices/hello" $helloBody @{ "Content-Type" = "application/json" }
if ($resp.Status -ne 200) { Fail "devices/hello" $resp }
$helloObj = Parse-Json $resp.Body "devices/hello"
$deviceId = $helloObj.device_id

$pairBody = @{ device_uid = $deviceUid } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$Base/api/v1/pairing/start" $pairBody @{ "Authorization" = "Bearer $token"; "Content-Type" = "application/json" }
if ($resp.Status -ne 200) { Fail "pairing start" $resp }
$pairObj = Parse-Json $resp.Body "pairing start"
$code = $pairObj.pairing_code
if (-not $code) { Fail "pairing start missing pairing_code" $resp }

$confirmBody = @{ device_uid = $deviceUid; pairing_code = $code } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$Base/api/v1/pairing/confirm" $confirmBody @{ "Content-Type" = "application/json" }
if ($resp.Status -ne 200) { Fail "pairing confirm" $resp }
$confirmObj = Parse-Json $resp.Body "pairing confirm"
$deviceToken = $confirmObj.device_token
if (-not $deviceToken) { Fail "pairing confirm missing token" $resp }

Write-Host "Lookup device..."
$resp = Invoke-Api "GET" "$Base/api/v1/devices/lookup/$deviceUid" $null @{ "Authorization" = "Bearer $token" }
if ($resp.Status -ne 200) { Fail "lookup" $resp }

Write-Host "Run simulator for $RunSeconds seconds..."
python -m app.simulator --base $Base --device-uid $deviceUid --device-token $deviceToken --seconds $RunSeconds | Out-Host

Write-Host "OK: e2e complete"
Write-Host "DEVICE_UID=$deviceUid"
Write-Host "DEVICE_ID=$deviceId"
Write-Host "DEVICE_TOKEN=$deviceToken"
