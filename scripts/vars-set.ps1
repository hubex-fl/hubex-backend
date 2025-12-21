$ErrorActionPreference = "Stop"

$Base = $env:HUBEX_BASE
if (-not $Base) { $Base = "http://127.0.0.1:8000" }
$Token = $env:HUBEX_TOKEN
if (-not $Token) { Write-Host "FAIL: HUBEX_TOKEN missing"; exit 1 }
$Key = $env:HUBEX_VAR_KEY
if (-not $Key) { Write-Host "FAIL: HUBEX_VAR_KEY missing"; exit 1 }
$Scope = $env:HUBEX_VAR_SCOPE
if (-not $Scope) { $Scope = "global" }
$DeviceUid = $env:HUBEX_DEVICE_UID
$ValueJson = $env:HUBEX_VAR_VALUE_JSON
$ValueRaw = $env:HUBEX_VAR_VALUE
$Expected = $env:HUBEX_VAR_EXPECTED_VERSION
$Force = $env:HUBEX_VAR_FORCE
$DeviceToken = $env:HUBEX_DEVICE_TOKEN

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
    param([string]$Method, [string]$Url, [string]$Body, [hashtable]$Headers)
    $args = @("-sS", "-X", $Method, $Url, "-w", "`n%{http_code}")
    if ($Headers) {
        foreach ($k in $Headers.Keys) { $args += @("-H", "${k}: $($Headers[$k])") }
    }
    if ($Body -ne $null) {
        $out = $Body | & curl.exe @args --data-binary '@-'
    } else {
        $out = & curl.exe @args
    }
    if ($LASTEXITCODE -ne 0) { Fail "curl failed: $Method $Url" $null }
    $lines = $out -split "`n"
    if ($lines.Length -eq 1) { return @{ Status = [int]$lines[0]; Body = "" } }
    $status = [int]$lines[-1]
    $body = ($lines[0..($lines.Length - 2)] -join "`n")
    return @{ Status = $status; Body = $body }
}

if ($Scope -eq "device" -and -not $DeviceUid) {
    Write-Host "FAIL: HUBEX_DEVICE_UID missing"
    exit 1
}

$valueObj = $null
if ($ValueJson) {
    try { $valueObj = $ValueJson | ConvertFrom-Json } catch { $valueObj = $ValueJson }
} elseif ($ValueRaw) {
    $valueObj = $ValueRaw
} else {
    Write-Host "FAIL: HUBEX_VAR_VALUE or HUBEX_VAR_VALUE_JSON missing"
    exit 1
}

$payload = @{
    key = $Key
    scope = $Scope
    value = $valueObj
}
if ($Scope -eq "device") { $payload.deviceUid = $DeviceUid }
if ($Expected) { $payload.expectedVersion = [int]$Expected }
if ($Force) { $payload.force = $true }

$body = $payload | ConvertTo-Json -Compress
$headers = @{ "Content-Type" = "application/json" }
if ($DeviceToken) {
    $headers["X-Device-Token"] = $DeviceToken
} else {
    $headers["Authorization"] = "Bearer $Token"
}
$resp = Invoke-Api "POST" "$Base/api/v1/variables/set" $body $headers
if ($resp.Status -ne 200) { Fail "set value" $resp }

Write-Host "OK"
Write-Host $resp.Body
