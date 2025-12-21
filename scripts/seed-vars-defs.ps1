$ErrorActionPreference = "Stop"

$Base = $env:HUBEX_BASE
if (-not $Base) { $Base = "http://127.0.0.1:8000" }
$Token = $env:HUBEX_TOKEN
if (-not $Token) { Write-Host "FAIL: HUBEX_TOKEN missing"; exit 1 }

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
    $lines = $out -split "`n"
    if ($lines.Length -eq 1) { return @{ Status = [int]$lines[0]; Body = "" } }
    $status = [int]$lines[-1]
    $body = ($lines[0..($lines.Length - 2)] -join "`n")
    return @{ Status = $status; Body = $body }
}

$defs = @(
    @{ key = "system.units"; scope = "global"; valueType = "string"; defaultValue = "metric"; enumValues = @("metric","imperial") },
    @{ key = "device.telemetry_interval_ms"; scope = "device"; valueType = "int"; defaultValue = 5000; unit = "ms"; minValue = 500; maxValue = 60000; deviceWritable = $true; userWritable = $true },
    @{ key = "device.temp_offset"; scope = "device"; valueType = "float"; defaultValue = 0.0; minValue = -5; maxValue = 5; deviceWritable = $true; userWritable = $true },
    @{ key = "device.label"; scope = "device"; valueType = "string"; defaultValue = ""; deviceWritable = $true; userWritable = $true }
)

foreach ($def in $defs) {
    $body = $def | ConvertTo-Json -Compress
    $resp = Invoke-Api "POST" "$Base/api/v1/variables/defs" $body @{
        "Authorization" = "Bearer $Token"
        "Content-Type" = "application/json"
    }
    if ($resp.Status -eq 200 -or $resp.Status -eq 201) {
        Write-Host "OK: $($def.key)"
        continue
    }
    if ($resp.Status -eq 409) {
        Write-Host "SKIP: $($def.key) already exists"
        continue
    }
    Write-Host "FAIL: $($def.key)"
    Write-Host "Status: $($resp.Status)"
    Write-Host "Body: $($resp.Body)"
    exit 1
}

Write-Host "DONE"
