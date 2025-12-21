$ErrorActionPreference = "Stop"

$Base = $env:HUBEX_BASE
if (-not $Base) { $Base = "http://127.0.0.1:8000" }
$DeviceToken = $env:HUBEX_DEVICE_TOKEN
if (-not $DeviceToken) { $DeviceToken = $env:DEVICE_TOKEN }
$Count = 5
if ($env:HUBEX_TELEMETRY_COUNT) { $Count = [int]$env:HUBEX_TELEMETRY_COUNT }
$IntervalMs = 1000
if ($env:HUBEX_TELEMETRY_INTERVAL_MS) { $IntervalMs = [int]$env:HUBEX_TELEMETRY_INTERVAL_MS }

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

if (-not $DeviceToken) {
    Fail "HUBEX_DEVICE_TOKEN required" $null
}

$ok = 0
for ($i = 1; $i -le $Count; $i++) {
    $payload = @{ event_type = "sample"; payload = @{ temp_c = 20 + $i; voltage = 3.7; rssi = -65; ok = $true } } | ConvertTo-Json -Compress
    $resp = Invoke-Api "POST" "$Base/api/v1/telemetry" $payload @{ "Content-Type" = "application/json"; "X-Device-Token" = $DeviceToken }
    if ($resp.Status -ne 200) { Fail "telemetry post" $resp }
    $ok++
    if ($i -lt $Count) { Start-Sleep -Milliseconds $IntervalMs }
}

Write-Host "OK: telemetry sent $ok/$Count"
