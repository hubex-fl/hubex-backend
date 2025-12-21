$ErrorActionPreference = "Stop"

$Base = $env:HUBEX_BASE
if (-not $Base) { $Base = "http://127.0.0.1:8000" }
$Token = $env:HUBEX_TOKEN
if (-not $Token) { Write-Host "FAIL: HUBEX_TOKEN missing"; exit 1 }

$DeviceUid = "sim-var-1"

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

Write-Host "Get device variables..."
$resp = Invoke-Api "GET" "$Base/api/v1/variables/device/$DeviceUid" $null @{ "Authorization" = "Bearer $Token" }
if ($resp.Status -ne 200) { Fail "variables device" $resp }

Write-Host "Set temp_offset=1.5..."
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
$version = (Parse-Json $resp.Body "set temp_offset").version
if (-not $version) { Fail "missing version" $resp }

Write-Host "Update temp_offset=2.5 with expectedVersion..."
$payload = @{
    key = "device.temp_offset"
    scope = "device"
    deviceUid = $DeviceUid
    value = 2.5
    expectedVersion = [int]$version
} | ConvertTo-Json -Compress
$resp = Invoke-Api "PUT" "$Base/api/v1/variables/value" $payload @{
    "Authorization" = "Bearer $Token"
    "Content-Type" = "application/json"
}
if ($resp.Status -ne 200) { Fail "update temp_offset" $resp }
$version2 = (Parse-Json $resp.Body "update temp_offset").version
if ($version2 -le $version) { Fail "version did not increment" $resp }

Write-Host "Update with stale expectedVersion (expect 409)..."
$payload = @{
    key = "device.temp_offset"
    scope = "device"
    deviceUid = $DeviceUid
    value = 3.0
    expectedVersion = [int]$version
} | ConvertTo-Json -Compress
$resp = Invoke-Api "PUT" "$Base/api/v1/variables/value" $payload @{
    "Authorization" = "Bearer $Token"
    "Content-Type" = "application/json"
}
if ($resp.Status -ne 409) { Fail "stale version should 409" $resp }
$detail = (Parse-Json $resp.Body "stale version").detail
if ($detail.code -ne "VAR_VERSION_CONFLICT") { Fail "stale version code" $resp }

Write-Host "Audit..."
$resp = Invoke-Api "GET" "$Base/api/v1/variables/audit?key=device.temp_offset&scope=device&deviceUid=$DeviceUid" $null @{
    "Authorization" = "Bearer $Token"
}
if ($resp.Status -ne 200) { Fail "audit" $resp }

Write-Host "OK"
