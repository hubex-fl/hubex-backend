$ErrorActionPreference = "Stop"

$Base = $env:HUBEX_BASE
if (-not $Base) { $Base = "http://127.0.0.1:8000" }
$Token = $env:HUBEX_TOKEN
if (-not $Token) { Write-Host "FAIL: HUBEX_TOKEN missing"; exit 1 }
$DevTools = $env:HUBEX_DEV_TOOLS
$DeviceUid = "sim-var2-" + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$Seconds = $env:HUBEX_SIM_SECONDS
if (-not $Seconds) { $Seconds = 12 }

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

if ($DevTools) {
    $env:HUBEX_DEV_TOOLS = $DevTools
}

# 1) Seed definitions
$defs = @(
    @{ key = "system.units"; scope = "global"; valueType = "string"; defaultValue = "metric"; enumValues = @("metric","imperial") },
    @{ key = "device.telemetry_interval_ms"; scope = "device"; valueType = "int"; defaultValue = 5000; unit = "ms"; minValue = 500; maxValue = 60000; deviceWritable = $true; userWritable = $true },
    @{ key = "device.temp_offset"; scope = "device"; valueType = "float"; defaultValue = 0.0; minValue = -5; maxValue = 5; deviceWritable = $true; userWritable = $true }
)
foreach ($def in $defs) {
    $body = $def | ConvertTo-Json -Compress
    $resp = Invoke-Api "POST" "$Base/api/v1/variables/defs" $body @{
        "Authorization" = "Bearer $Token"
        "Content-Type" = "application/json"
    }
    if ($resp.Status -ne 200 -and $resp.Status -ne 201 -and $resp.Status -ne 409) {
        Fail "seed vars defs" $resp
    }
}
Write-Host "OK: seeded defs"

# 1b) Fetch defs and select keys
$defsResp = Invoke-Api "GET" "$Base/api/v1/variables/defs" $null @{
    "Authorization" = "Bearer $Token"
}
if ($defsResp.Status -ne 200) { Fail "list vars defs" $defsResp }
$defsJson = $defsResp.Body | ConvertFrom-Json
$globalDef = $defsJson | Where-Object { $_.scope -in @("system", "global") } | Select-Object -First 1
$deviceDef = $defsJson | Where-Object { $_.scope -eq "device" } | Select-Object -First 1
if (-not $globalDef) { Fail "no global variable definitions available" $defsResp }
if (-not $deviceDef) { Fail "no device variable definitions available" $defsResp }
$globalKey = $globalDef.key
$globalScope = $globalDef.scope
$deviceKey = $deviceDef.key
$deviceScope = $deviceDef.scope

# 2) Provision device
$helloBody = @{ device_uid = $DeviceUid; firmware_version = "sim"; capabilities = @{ sim = $true } } | ConvertTo-Json -Compress
$hello = Invoke-Api "POST" "$Base/api/v1/devices/hello" $helloBody @{ "Content-Type" = "application/json" }
if ($hello.Status -ne 200) { Fail "devices/hello" $hello }
Write-Host "OK: hello $DeviceUid"

# 3) Pairing start
$startBody = @{ device_uid = $DeviceUid } | ConvertTo-Json -Compress
$start = Invoke-Api "POST" "$Base/api/v1/pairing/start" $startBody @{
    "Authorization" = "Bearer $Token"
    "Content-Type" = "application/json"
}
if ($start.Status -ne 200) { Fail "pairing/start" $start }
$startJson = $start.Body | ConvertFrom-Json
$code = $startJson.pairing_code
if (-not $code) { Fail "pairing/start missing pairing_code" $start }
Write-Host "OK: pairing_code=$code"

# 4) Pairing confirm
$confirmBody = @{ device_uid = $DeviceUid; pairing_code = $code } | ConvertTo-Json -Compress
$confirm = Invoke-Api "POST" "$Base/api/v1/pairing/confirm" $confirmBody @{
    "Content-Type" = "application/json"
}
if ($confirm.Status -ne 200) { Fail "pairing/confirm" $confirm }
$confirmJson = $confirm.Body | ConvertFrom-Json
$deviceToken = $confirmJson.device_token
if (-not $deviceToken) { Fail "pairing/confirm missing device_token" $confirm }
Write-Host "OK: device token issued"

# 5) Set global + device override
$setGlobal = @{ key = $globalKey; scope = $globalScope; value = "metric" } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$Base/api/v1/variables/set" $setGlobal @{
    "Authorization" = "Bearer $Token"
    "Content-Type" = "application/json"
}
if ($resp.Status -ne 200) { Fail "set global var" $resp }

$setDevice = @{ key = $deviceKey; scope = $deviceScope; deviceUid = $DeviceUid; value = 1.5 } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$Base/api/v1/variables/set" $setDevice @{
    "Authorization" = "Bearer $Token"
    "Content-Type" = "application/json"
}
if ($resp.Status -ne 200) { Fail "set device var" $resp }
Write-Host "OK: vars set"

# 6) Effective vars check
$effective = Invoke-Api "GET" "$Base/api/v1/variables/effective?deviceUid=$DeviceUid" $null @{
    "Authorization" = "Bearer $Token"
}
if ($effective.Status -ne 200) { Fail "effective vars" $effective }
Write-Host "OK: effective vars"

# 7) Simulator run
Write-Host "Running simulator..."
python -m app.simulator --base $Base --device-uid $DeviceUid --device-token $deviceToken --user-token $Token --vars-effective --vars-ack --vars-poll-seconds 5 --seconds $Seconds | Out-Host

Write-Host "OK"
