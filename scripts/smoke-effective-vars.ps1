$ErrorActionPreference = "Stop"

$Base = $env:HUBEX_BASE
if (-not $Base) { $Base = "http://127.0.0.1:8000" }
$Token = $env:HUBEX_TOKEN
if (-not $Token) { Write-Host "FAIL: HUBEX_TOKEN missing"; exit 1 }

$DeviceUid = "sim-effective-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"

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

function Parse-Json {
    param([string]$Body, [string]$Label)
    try {
        return $Body | ConvertFrom-Json
    } catch {
        Fail "$Label (invalid JSON)" @{ Status = -1; Body = $Body }
    }
}

function Ensure-Def {
    param([string]$Key, [string]$Scope, [string]$ValueType, [object]$DefaultValue)
    $payload = @{
        key = $Key
        scope = $Scope
        valueType = $ValueType
        defaultValue = $DefaultValue
    } | ConvertTo-Json -Compress
    $resp = Invoke-Api "POST" "$Base/api/v1/variables/definitions" $payload @{
        "Authorization" = "Bearer $Token"
        "Content-Type" = "application/json"
    }
    if ($resp.Status -eq 200) { return }
    if ($resp.Status -eq 409) {
        $detail = (Parse-Json $resp.Body "definition conflict").detail
        if ($detail.code -eq "VAR_DEF_EXISTS") { return }
    }
    Fail "create definition $Key" $resp
}

Write-Host "Provision device..."
$helloBody = @{
    device_uid = $DeviceUid
    firmware_version = "sim-1.0"
    capabilities = @{ vars = $true }
} | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$Base/api/v1/devices/hello" $helloBody @{ "Content-Type" = "application/json" }
if ($resp.Status -ne 200) { Fail "devices/hello" $resp }

Write-Host "Ensure definitions..."
Ensure-Def "system.units" "global" "string" "metric"
Ensure-Def "device.temp_offset" "device" "float" 0.0

Write-Host "Set global system.units..."
$payload = @{
    key = "system.units"
    scope = "global"
    value = "metric"
} | ConvertTo-Json -Compress
$resp = Invoke-Api "PUT" "$Base/api/v1/variables/value" $payload @{
    "Authorization" = "Bearer $Token"
    "Content-Type" = "application/json"
}
if ($resp.Status -ne 200) { Fail "set system.units" $resp }

Write-Host "Set device.temp_offset override..."
$payload = @{
    key = "device.temp_offset"
    scope = "device"
    deviceUid = $DeviceUid
    value = 1.5
} | ConvertTo-Json -Compress
$resp = Invoke-Api "PUT" "$Base/api/v1/variables/value" $payload @{
    "Authorization" = "Bearer $Token"
    "Content-Type" = "application/json"
}
if ($resp.Status -ne 200) { Fail "set temp_offset" $resp }

Write-Host "Effective variables..."
$resp = Invoke-Api "GET" "$Base/api/v1/variables/effective?deviceUid=$DeviceUid" $null @{ "Authorization" = "Bearer $Token" }
if ($resp.Status -ne 200) { Fail "effective variables" $resp }
$body = Parse-Json $resp.Body "effective variables"
$items = $body.items
$deviceItem = $items | Where-Object { $_.key -eq "device.temp_offset" } | Select-Object -First 1
$globalItem = $items | Where-Object { $_.key -eq "system.units" } | Select-Object -First 1
if (-not $deviceItem) { Fail "missing device.temp_offset" $resp }
if ($deviceItem.source -ne "device_override") { Fail "device.temp_offset source" $resp }
if ([double]$deviceItem.value -ne 1.5) { Fail "device.temp_offset value" $resp }
if (-not $globalItem) { Fail "missing system.units" $resp }
if ($globalItem.source -ne "global_default") { Fail "system.units source" $resp }
if ($globalItem.value -ne "metric") { Fail "system.units value" $resp }

Write-Host "Pairing start..."
$payload = @{ device_uid = $DeviceUid } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$Base/api/v1/pairing/start" $payload @{
    "Authorization" = "Bearer $Token"
    "Content-Type" = "application/json"
}
if ($resp.Status -ne 200) { Fail "pairing start" $resp }
$pairing = Parse-Json $resp.Body "pairing start"
$pairingCode = $pairing.pairing_code
if (-not $pairingCode) { Fail "missing pairing_code" $resp }

Write-Host "Pairing confirm..."
$payload = @{ device_uid = $DeviceUid; pairing_code = $pairingCode } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$Base/api/v1/pairing/confirm" $payload @{ "Content-Type" = "application/json" }
if ($resp.Status -ne 200) { Fail "pairing confirm" $resp }
$confirm = Parse-Json $resp.Body "pairing confirm"
$deviceToken = $confirm.device_token
if (-not $deviceToken) { Fail "missing device_token" $resp }

Write-Host "Run simulator..."
& python -m app.simulator --base $Base --device-uid $DeviceUid --device-token $deviceToken --user-token $Token --vars-effective --vars-poll-seconds 2 --seconds 8 --interval 2
if ($LASTEXITCODE -ne 0) { Fail "simulator failed" $null }

Write-Host "OK"
