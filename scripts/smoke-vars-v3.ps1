$ErrorActionPreference = "Stop"

$Base = $env:HUBEX_BASE
if (-not $Base) { $Base = "http://127.0.0.1:8000" }
$Token = $env:HUBEX_TOKEN
if (-not $Token) { Write-Host "FAIL: HUBEX_TOKEN missing"; exit 1 }
$DeviceUid = "sim-var3-" + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
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

Write-Host "Seeding v3 defs..."
& "$PSScriptRoot\seed-vars-v3-defs.ps1"
if ($LASTEXITCODE -ne 0) { Fail "seed-vars-v3-defs failed" $null }

$defsResp = Invoke-Api "GET" "$Base/api/v1/variables/defs" $null @{
    "Authorization" = "Bearer $Token"
}
if ($defsResp.Status -ne 200) { Fail "list defs" $defsResp }
$defsJson = $defsResp.Body | ConvertFrom-Json
$globalDef = $defsJson | Where-Object { $_.scope -in @("system", "global") } | Select-Object -First 1
$tempDef = $defsJson | Where-Object { $_.key -eq "device.temp_offset" } | Select-Object -First 1
$labelDef = $defsJson | Where-Object { $_.key -eq "device.label" } | Select-Object -First 1
if (-not $globalDef) { Fail "no global definition available" $defsResp }
if (-not $tempDef) { Fail "no device.temp_offset definition" $defsResp }
if (-not $labelDef) { Fail "no device.label definition" $defsResp }

$globalKey = $globalDef.key
$globalScope = $globalDef.scope
$tempKey = $tempDef.key
$tempScope = $tempDef.scope
$labelKey = $labelDef.key
$labelScope = $labelDef.scope

# 1) Provision device
$helloBody = @{ device_uid = $DeviceUid; firmware_version = "sim"; capabilities = @{ sim = $true } } | ConvertTo-Json -Compress
$hello = Invoke-Api "POST" "$Base/api/v1/devices/hello" $helloBody @{ "Content-Type" = "application/json" }
if ($hello.Status -ne 200) { Fail "devices/hello" $hello }
Write-Host "OK: hello $DeviceUid"

# 2) Pairing start
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

# 3) Pairing confirm
$confirmBody = @{ device_uid = $DeviceUid; pairing_code = $code } | ConvertTo-Json -Compress
$confirm = Invoke-Api "POST" "$Base/api/v1/pairing/confirm" $confirmBody @{
    "Content-Type" = "application/json"
}
if ($confirm.Status -ne 200) { Fail "pairing/confirm" $confirm }
$confirmJson = $confirm.Body | ConvertFrom-Json
$deviceToken = $confirmJson.device_token
if (-not $deviceToken) { Fail "pairing/confirm missing device_token" $confirm }
Write-Host "OK: device token issued"

# 3b) Verify claim persisted
$lookup = Invoke-Api "GET" "$Base/api/v1/devices/lookup/$DeviceUid" $null @{
    "Authorization" = "Bearer $Token"
}
if ($lookup.Status -ne 200) { Fail "devices/lookup" $lookup }
$lookupJson = $lookup.Body | ConvertFrom-Json
if (-not $lookupJson.claimed) { Fail "pairing confirm did not persist claim" $lookup }
Write-Host "OK: claim persisted"

# 4) Set global + device overrides
$setGlobal = @{ key = $globalKey; scope = $globalScope; value = "metric" } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$Base/api/v1/variables/set" $setGlobal @{
    "Authorization" = "Bearer $Token"
    "Content-Type" = "application/json"
}
if ($resp.Status -ne 200) { Fail "set global var" $resp }

$setTemp = @{ key = $tempKey; scope = $tempScope; deviceUid = $DeviceUid; value = 1.5 } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$Base/api/v1/variables/set" $setTemp @{
    "Authorization" = "Bearer $Token"
    "Content-Type" = "application/json"
}
if ($resp.Status -ne 200) { Fail "set device temp var" $resp }

$setLabel = @{ key = $labelKey; scope = $labelScope; deviceUid = $DeviceUid; value = "kitchen-1" } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$Base/api/v1/variables/set" $setLabel @{
    "Authorization" = "Bearer $Token"
    "Content-Type" = "application/json"
}
if ($resp.Status -ne 200) { Fail "set device label" $resp }
Write-Host "OK: vars set"

# 5) Snapshot v3
$snapshot = Invoke-Api "GET" "$Base/api/v1/variables/snapshot?deviceUid=$DeviceUid" $null @{
    "X-Device-Token" = $deviceToken
}
if ($snapshot.Status -ne 200) { Fail "variables/snapshot" $snapshot }
$snapshotJson = $snapshot.Body | ConvertFrom-Json
if ($snapshotJson.schema -ne "vars.snapshot.v3") { Fail "snapshot schema mismatch" $snapshot }
if (-not $snapshotJson.effective_rev) { Fail "snapshot missing effective_rev" $snapshot }
if (-not $snapshotJson.server_time_ms) { Fail "snapshot missing server_time_ms" $snapshot }
if (-not $snapshotJson.vars -or $snapshotJson.vars.Count -lt 3) { Fail "snapshot missing vars" $snapshot }
Write-Host "OK: snapshot rev=$($snapshotJson.effective_rev)"

# 6) Ack v3
$results = @()
foreach ($item in $snapshotJson.vars) {
    if ($item.key) {
        $results += @{ key = $item.key; status = "OK" }
    }
}
$ackBody = @{
    deviceUid = $DeviceUid
    effectiveRev = $snapshotJson.effective_rev
    results = $results
} | ConvertTo-Json -Compress
$ack = Invoke-Api "POST" "$Base/api/v1/variables/ack" $ackBody @{
    "Content-Type" = "application/json"
    "X-Device-Token" = $deviceToken
}
if ($ack.Status -ne 200) { Fail "variables/ack" $ack }
$ackJson = $ack.Body | ConvertFrom-Json
if (-not $ackJson.ok -or $ackJson.failed -ne 0) { Fail "ack returned failed results" $ack }
Write-Host "OK: ack applied"

# 6b) Idempotent ack (stale/noop)
$ack2 = Invoke-Api "POST" "$Base/api/v1/variables/ack" $ackBody @{
    "Content-Type" = "application/json"
    "X-Device-Token" = $deviceToken
}
if ($ack2.Status -ne 200) { Fail "variables/ack idempotent" $ack2 }
$ack2Json = $ack2.Body | ConvertFrom-Json
if (($ack2Json.stale -lt 1) -and ($ack2Json.applied -gt 0)) {
    Fail "ack idempotency not detected" $ack2
}
Write-Host "OK: ack idempotent"

# 7) Simulator run
Write-Host "Running simulator..."
python -m app.simulator --base $Base --device-uid $DeviceUid --device-token $deviceToken --user-token $Token --vars-effective --vars-ack --vars-poll-seconds 5 --seconds $Seconds | Out-Host
if ($LASTEXITCODE -ne 0) { Fail "simulator returned non-zero" $null }

Write-Host "OK"
