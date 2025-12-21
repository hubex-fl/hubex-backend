$ErrorActionPreference = "Stop"

$Base = $env:HUBEX_BASE
if (-not $Base) { $Base = "http://127.0.0.1:8000" }
$Token = $env:HUBEX_TOKEN
$DeviceId = $env:HUBEX_DEVICE_ID
$DeviceToken = $env:HUBEX_DEVICE_TOKEN
$ContextKey = $env:HUBEX_CONTEXT_KEY
if (-not $ContextKey) { $ContextKey = "default" }

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

if (-not $Token) { Fail "HUBEX_TOKEN required" $null }
if (-not $DeviceId) { Fail "HUBEX_DEVICE_ID required" $null }
if (-not $DeviceToken) { Fail "HUBEX_DEVICE_TOKEN required" $null }

$contextBody = @{ context_key = $ContextKey; capabilities = @{ tasks = @("config.apply") }; meta = @{ version = "1.0" } } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$Base/api/v1/tasks/context/heartbeat" $contextBody @{ "Content-Type" = "application/json"; "X-Device-Token" = $DeviceToken }
if ($resp.Status -ne 200) { Fail "context heartbeat" $resp }

$taskBody = @{ type = "config.apply"; payload = @{ mode = "seed" }; execution_context_key = $ContextKey } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$Base/api/v1/devices/$DeviceId/tasks" $taskBody @{ "Content-Type" = "application/json"; "Authorization" = "Bearer $Token" }
if ($resp.Status -ne 200) { Fail "owner enqueue task" $resp }
$taskObj = Parse-Json $resp.Body "owner enqueue task"
$taskId = $taskObj.id
if (-not $taskId) { Fail "task id missing" $resp }

$resp = Invoke-Api "POST" "$Base/api/v1/tasks/poll?limit=1&context_key=$ContextKey&lease_seconds=300" $null @{ "X-Device-Token" = $DeviceToken }
if ($resp.Status -ne 200) { Fail "task poll" $resp }
$pollObj = @((Parse-Json $resp.Body "task poll"))
if ($pollObj.Count -lt 1) { Fail "task poll empty" $resp }
$leaseToken = $pollObj[0].lease_token
if (-not $leaseToken) { Fail "lease_token missing" $resp }

Write-Host "OK: task claimed"
Write-Host "TASK_ID=$taskId"
Write-Host "LEASE_TOKEN=$leaseToken"
Write-Host "NOTE: task left in_flight to keep device busy"
