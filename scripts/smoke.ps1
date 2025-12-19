$ErrorActionPreference = "Stop"

function Fail {
    param([string]$Message, [hashtable]$Resp)
    Write-Host "FAIL: $Message"
    if ($Resp) {
        Write-Host "Status: $($Resp.Status)"
        Write-Host "Body: $($Resp.Body)"
    }
    exit 1
}

function Assert-Status {
    param([hashtable]$Resp, [int[]]$Expected, [string]$Label)
    if (-not ($Expected -contains $Resp.Status)) {
        Fail "$Label (expected $($Expected -join ', '))" $Resp
    }
}

function Parse-Json {
    param([string]$Body, [string]$Label)
    try {
        return $Body | ConvertFrom-Json
    } catch {
        Fail "$Label (invalid JSON)" @{ Status = -1; Body = $Body }
    }
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

function Get-DatabaseUrl {
    if ($env:DATABASE_URL) {
        return $env:DATABASE_URL
    }
    if ($env:HUBEX_DATABASE_URL) {
        return $env:HUBEX_DATABASE_URL
    }
    if (Test-Path ".env") {
        $line = Select-String -Path ".env" -Pattern "^(DATABASE_URL|HUBEX_DATABASE_URL)=" -SimpleMatch | Select-Object -First 1
        if ($line) {
            return ($line.Line -split "=", 2)[1]
        }
    }
    return $null
}

function Try-ExpirePairing {
    param([string]$DbUrl, [string]$DeviceUid, [string]$PairingCode)
    if (-not $DbUrl) {
        return $false
    }
    if ($DbUrl.StartsWith("postgresql+asyncpg")) {
        $DbUrl = $DbUrl -replace "^postgresql\\+asyncpg", "postgresql"
    }
    $env:PAIR_DB_URL = $DbUrl
    $env:PAIR_DEVICE_UID = $DeviceUid
    $env:PAIR_CODE = $PairingCode
    $py = @'
import os
import sys
import psycopg2

db = os.environ["PAIR_DB_URL"]
uid = os.environ["PAIR_DEVICE_UID"]
code = os.environ["PAIR_CODE"]

conn = psycopg2.connect(db)
cur = conn.cursor()
cur.execute(
    "update pairing_sessions set expires_at = now() - interval '1 minute' "
    "where device_uid=%s and pairing_code=%s",
    (uid, code),
)
conn.commit()
print(f"expired:{cur.rowcount}")
sys.exit(0 if cur.rowcount == 1 else 2)
'@
    $out = $py | python -
    if ($LASTEXITCODE -ne 0) {
        return $false
    }
    return $out -match "expired:1"
}

$baseUrl = "http://localhost:8000/api/v1"
$pw = "Test1234!"
$email = "codex+$((Get-Date).ToString('yyyyMMddHHmmss'))@example.com"
$deviceUid = "device-20251219-$((Get-Date).ToString('yyyyMMddHHmmss'))"

Write-Host "Register..."
$registerBody = @{ email = $email; password = $pw } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$baseUrl/auth/register" $registerBody @{ "Content-Type" = "application/json" }
Assert-Status $resp 200 "register"

Write-Host "Login..."
$resp = Invoke-Api "POST" "$baseUrl/auth/login" $registerBody @{ "Content-Type" = "application/json" }
Assert-Status $resp 200 "login"
$token = (Parse-Json $resp.Body "login").access_token
if (-not $token) { Fail "login token missing" $resp }

Write-Host "User me..."
$resp = Invoke-Api "GET" "$baseUrl/users/me" $null @{ "Authorization" = "Bearer $token" }
Assert-Status $resp 200 "users/me"

Write-Host "Pairing start (no JWT, expect 401)..."
$pairingBody = @{ device_uid = $deviceUid } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$baseUrl/pairing/start" $pairingBody @{ "Content-Type" = "application/json" }
Assert-Status $resp 401 "pairing start without JWT"

Write-Host "Device hello..."
$helloBody = @{ device_uid = $deviceUid; firmware_version = "1.0.0"; capabilities = @{ wifi = $true } } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$baseUrl/devices/hello" $helloBody @{ "Content-Type" = "application/json" }
Assert-Status $resp 200 "devices/hello"
$helloObj = Parse-Json $resp.Body "devices/hello"
if ($helloObj.claimed -ne $false) {
    Fail "devices/hello claimed should be false for new device" $resp
}

Write-Host "Pairing start..."
$resp = Invoke-Api "POST" "$baseUrl/pairing/start" $pairingBody @{ "Authorization" = "Bearer $token"; "Content-Type" = "application/json" }
Assert-Status $resp 200 "pairing start"
$pairingObj = Parse-Json $resp.Body "pairing start"

Write-Host "Pairing confirm (wrong code, expect 404)..."
$wrongBody = @{ device_uid = $deviceUid; pairing_code = "WRONG123" } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$baseUrl/pairing/confirm" $wrongBody @{ "Content-Type" = "application/json" }
Assert-Status $resp 404 "pairing confirm wrong code"

Write-Host "Pairing confirm (expired, expect 410)..."
$expiredOk = Try-ExpirePairing (Get-DatabaseUrl) $deviceUid $pairingObj.pairing_code
if ($expiredOk) {
    $expireBody = @{ device_uid = $deviceUid; pairing_code = $pairingObj.pairing_code } | ConvertTo-Json -Compress
    $resp = Invoke-Api "POST" "$baseUrl/pairing/confirm" $expireBody @{ "Content-Type" = "application/json" }
    Assert-Status $resp 410 "pairing confirm expired"
} else {
    Write-Host "SKIP: pairing expiry check (DATABASE_URL/.env or psycopg2 unavailable)"
}

Write-Host "Pairing start (fresh)..."
$resp = Invoke-Api "POST" "$baseUrl/pairing/start" $pairingBody @{ "Authorization" = "Bearer $token"; "Content-Type" = "application/json" }
Assert-Status $resp 200 "pairing start fresh"
$pairingObj = Parse-Json $resp.Body "pairing start fresh"

Write-Host "Pairing confirm (no JWT)..."
$confirmBody = @{ device_uid = $deviceUid; pairing_code = $pairingObj.pairing_code } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$baseUrl/pairing/confirm" $confirmBody @{ "Content-Type" = "application/json" }
Assert-Status $resp 200 "pairing confirm"
$confirmObj = Parse-Json $resp.Body "pairing confirm"
$deviceToken = $confirmObj.device_token
$deviceId = $confirmObj.device_id
if (-not $deviceToken -or $null -eq $deviceId) { Fail "pairing confirm missing token or device_id" $resp }

Write-Host "Pairing confirm replay (expect 409)..."
$resp = Invoke-Api "POST" "$baseUrl/pairing/confirm" $confirmBody @{ "Content-Type" = "application/json" }
Assert-Status $resp 409 "pairing confirm replay"

Write-Host "Device whoami (missing token, expect 401)..."
$resp = Invoke-Api "GET" "$baseUrl/devices/whoami" $null @{}
Assert-Status $resp 401 "devices/whoami without token"

Write-Host "Device whoami (device token)..."
$resp = Invoke-Api "GET" "$baseUrl/devices/whoami" $null @{ "X-Device-Token" = $deviceToken }
Assert-Status $resp 200 "devices/whoami"

Write-Host "Task context heartbeat..."
$contextKey = "default"
$contextBody = @{ context_key = $contextKey; capabilities = @{ tasks = @("io.write", "config.apply") }; meta = @{ version = "1.0" } } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$baseUrl/tasks/context/heartbeat" $contextBody @{ "Content-Type" = "application/json"; "X-Device-Token" = $deviceToken }
Assert-Status $resp 200 "tasks context heartbeat"

Write-Host "Owner enqueue task (unknown context, expect 409)..."
$badTaskBody = @{ type = "config.apply"; payload = @{ mode = "safe" }; execution_context_key = "missing" } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$baseUrl/devices/$deviceId/tasks" $badTaskBody @{ "Content-Type" = "application/json"; "Authorization" = "Bearer $token" }
Assert-Status $resp 409 "owner enqueue task unknown context"

Write-Host "Owner enqueue task..."
$taskBody = @{ type = "config.apply"; payload = @{ mode = "safe" }; execution_context_key = $contextKey } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$baseUrl/devices/$deviceId/tasks" $taskBody @{ "Content-Type" = "application/json"; "Authorization" = "Bearer $token" }
Assert-Status $resp 200 "owner enqueue task"
$taskObj = Parse-Json $resp.Body "owner enqueue task"
$taskId = $taskObj.id
if (-not $taskId) { Fail "task id missing" $resp }

Write-Host "Task poll (missing token, expect 401)..."
$resp = Invoke-Api "POST" "$baseUrl/tasks/poll?limit=1&context_key=$contextKey" $null @{}
Assert-Status $resp 401 "tasks poll without token"

Write-Host "Task poll (device token)..."
$resp = Invoke-Api "POST" "$baseUrl/tasks/poll?limit=1&context_key=$contextKey" $null @{ "X-Device-Token" = $deviceToken }
Assert-Status $resp 200 "tasks poll"
$pollObj = Parse-Json $resp.Body "tasks poll"
if ($pollObj.Count -lt 1) { Fail "tasks poll empty" $resp }

Write-Host "Task complete (done)..."
$completeBody = @{ status = "done"; result = @{ ok = $true } } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$baseUrl/tasks/$taskId/complete" $completeBody @{ "Content-Type" = "application/json"; "X-Device-Token" = $deviceToken }
Assert-Status $resp 200 "tasks complete"

Write-Host "Owner list tasks..."
$resp = Invoke-Api "GET" "$baseUrl/devices/$deviceId/tasks?limit=10" $null @{ "Authorization" = "Bearer $token" }
Assert-Status $resp 200 "owner list tasks"
$tasksList = Parse-Json $resp.Body "owner list tasks"
$taskFound = $false
foreach ($t in $tasksList) {
    if ($t.id -eq $taskId) { $taskFound = $true }
}
if (-not $taskFound) { Fail "task not found in owner list" $resp }

Write-Host "Telemetry post (missing token, expect 401)..."
$telemetryBody = @{ event_type = "boot"; payload = @{ temp_c = 21; ok = $true } } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$baseUrl/telemetry" $telemetryBody @{ "Content-Type" = "application/json" }
Assert-Status $resp 401 "telemetry post without token"

Write-Host "Telemetry post (payload not object, expect 422)..."
$badTelemetryBody = @{ event_type = "bad"; payload = "not-an-object" } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$baseUrl/telemetry" $badTelemetryBody @{ "Content-Type" = "application/json"; "X-Device-Token" = $deviceToken }
Assert-Status $resp 422 "telemetry post payload not object"

Write-Host "Telemetry post (device token)..."
$resp = Invoke-Api "POST" "$baseUrl/telemetry" $telemetryBody @{ "Content-Type" = "application/json"; "X-Device-Token" = $deviceToken }
Assert-Status $resp 200 "telemetry post"
$telemetryObj = Parse-Json $resp.Body "telemetry post"
$telemetryId = $telemetryObj.telemetry_id
if (-not $telemetryId) { Fail "telemetry_id missing" $resp }

Write-Host "Telemetry recent (device token)..."
$resp = Invoke-Api "GET" "$baseUrl/telemetry/recent?limit=5" $null @{ "X-Device-Token" = $deviceToken }
Assert-Status $resp 200 "telemetry recent"
$recentObj = Parse-Json $resp.Body "telemetry recent"
$telemetryFound = $false
foreach ($t in $recentObj) {
    if ($t.id -eq $telemetryId) { $telemetryFound = $true }
}
if (-not $telemetryFound) { Fail "telemetry not found in recent list" $resp }

Write-Host "User telemetry recent (owner)..."
$resp = Invoke-Api "GET" "$baseUrl/devices/$deviceId/telemetry/recent?limit=5" $null @{ "Authorization" = "Bearer $token" }
Assert-Status $resp 200 "user telemetry recent owner"
$userTelem = Parse-Json $resp.Body "user telemetry recent owner"
$userTelemFound = $false
foreach ($t in $userTelem) {
    if ($t.id -eq $telemetryId) { $userTelemFound = $true }
}
if (-not $userTelemFound) { Fail "owner telemetry missing" $resp }

Write-Host "Devices list (owner)..."
$resp = Invoke-Api "GET" "$baseUrl/devices" $null @{ "Authorization" = "Bearer $token" }
Assert-Status $resp 200 "devices list owner"
$listObj = Parse-Json $resp.Body "devices list owner"
$found = $false
foreach ($d in $listObj) {
    if ($d.device_uid -eq $deviceUid) { $found = $true }
}
if (-not $found) { Fail "devices list missing device" $resp }

Write-Host "Device detail (owner)..."
$resp = Invoke-Api "GET" "$baseUrl/devices/$deviceId" $null @{ "Authorization" = "Bearer $token" }
Assert-Status $resp 200 "devices detail owner"

Write-Host "Register other user..."
$email2 = "codex+$((Get-Date).ToString('yyyyMMddHHmmss'))+other@example.com"
$registerBody2 = @{ email = $email2; password = $pw } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$baseUrl/auth/register" $registerBody2 @{ "Content-Type" = "application/json" }
Assert-Status $resp 200 "register other user"

Write-Host "Login other user..."
$resp = Invoke-Api "POST" "$baseUrl/auth/login" $registerBody2 @{ "Content-Type" = "application/json" }
Assert-Status $resp 200 "login other user"
$token2 = (Parse-Json $resp.Body "login other user").access_token
if (-not $token2) { Fail "other user token missing" $resp }

Write-Host "Devices list (other user, expect no device)..."
$resp = Invoke-Api "GET" "$baseUrl/devices" $null @{ "Authorization" = "Bearer $token2" }
Assert-Status $resp 200 "devices list other user"
$listObj2 = Parse-Json $resp.Body "devices list other user"
$found2 = $false
foreach ($d in $listObj2) {
    if ($d.device_uid -eq $deviceUid) { $found2 = $true }
}
if ($found2) { Fail "other user sees device in list" $resp }

Write-Host "Device detail (other user, expect 403/404)..."
$resp = Invoke-Api "GET" "$baseUrl/devices/$deviceId" $null @{ "Authorization" = "Bearer $token2" }
Assert-Status $resp @(403, 404) "device detail other user"

Write-Host "Owner enqueue task (other user, expect 404)..."
$resp = Invoke-Api "POST" "$baseUrl/devices/$deviceId/tasks" $taskBody @{ "Content-Type" = "application/json"; "Authorization" = "Bearer $token2" }
Assert-Status $resp 404 "owner enqueue task other user"

Write-Host "Owner list tasks (other user, expect 404)..."
$resp = Invoke-Api "GET" "$baseUrl/devices/$deviceId/tasks?limit=10" $null @{ "Authorization" = "Bearer $token2" }
Assert-Status $resp 404 "owner list tasks other user"

Write-Host "User telemetry recent (other user, expect 404)..."
$resp = Invoke-Api "GET" "$baseUrl/devices/$deviceId/telemetry/recent?limit=5" $null @{ "Authorization" = "Bearer $token2" }
Assert-Status $resp 404 "user telemetry recent other user"

Write-Host "OK: smoke checks passed"
exit 0
