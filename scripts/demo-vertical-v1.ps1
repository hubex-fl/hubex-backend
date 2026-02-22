$ErrorActionPreference = "Stop"

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$py = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $py)) {
  throw "Python venv not found at $py"
}

$base = $env:HUBEX_BASE_URL
if (-not $base) { $base = "http://127.0.0.1:8000" }
$deviceUid = $env:DEMO_DEVICE_UID
if (-not $deviceUid) { $deviceUid = "demo-device-1" }
$definitionKey = $env:DEMO_DEFINITION_KEY
if (-not $definitionKey) { $definitionKey = "demo.v1" }
$workerId = $env:WORKER_ID
if (-not $workerId) { $workerId = "demo-worker-1" }
$leaseSeconds = if ($env:LEASE_SECONDS) { [int]$env:LEASE_SECONDS } else { 60 }
$heartbeatEvery = if ($env:HEARTBEAT_EVERY) { [int]$env:HEARTBEAT_EVERY } else { 20 }
$pollDelay = if ($env:POLL_DELAY) { [int]$env:POLL_DELAY } else { 2 }

$email = $env:DEMO_USER_EMAIL
if (-not $email) { $email = "demo@example.com" }
$password = $env:DEMO_USER_PASSWORD
if (-not $password) { $password = "demo-pass-123" }

function Get-JwtSub([string]$token) {
  $parts = $token.Split('.')
  if ($parts.Length -lt 2) { throw "invalid token" }
  $payload = $parts[1].Replace('-', '+').Replace('_', '/')
  switch ($payload.Length % 4) { 2 { $payload += '==' } 3 { $payload += '=' } }
  $bytes = [Convert]::FromBase64String($payload)
  $json = [Text.Encoding]::UTF8.GetString($bytes)
  return (ConvertFrom-Json $json).sub
}

function Invoke-Json([string]$method, [string]$url, [object]$body, [hashtable]$headers) {
  $payload = $null
  if ($body -ne $null) { $payload = ($body | ConvertTo-Json -Depth 8) }
  try {
    $res = Invoke-WebRequest -Method $method -Uri $url -Headers $headers -Body $payload -ContentType "application/json" -UseBasicParsing
    $status = [int]$res.StatusCode
    $raw = $res.Content
  } catch {
    $resp = $_.Exception.Response
    if (-not $resp) { throw }
    $status = [int]$resp.StatusCode
    $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
    $raw = $reader.ReadToEnd()
  }
  $data = $null
  if ($raw) { $data = $raw | ConvertFrom-Json }
  return @{ status = $status; data = $data; raw = $raw }
}

Write-Host "== Vertical Demo v1 =="
Write-Host "BASE=$base"
Write-Host "DEVICE_UID=$deviceUid"
Write-Host "DEFINITION_KEY=$definitionKey"

# Register/login
$reg = Invoke-Json POST "$base/api/v1/auth/register" @{ email = $email; password = $password } @{}
if ($reg.status -eq 409) {
  $login = Invoke-Json POST "$base/api/v1/auth/login" @{ email = $email; password = $password } @{}
  if ($login.status -ne 200) { throw "login failed: $($login.raw)" }
  $rawToken = $login.data.access_token
} elseif ($reg.status -eq 200) {
  $rawToken = $reg.data.access_token
} else {
  throw "register failed: $($reg.raw)"
}

$userId = Get-JwtSub $rawToken
$caps = @(
  "events.emit",
  "events.read",
  "events.ack",
  "executions.write",
  "executions.read",
  "vars.write",
  "vars.read",
  "devices.read",
  "pairing.start",
  "pairing.claim",
  "pairing.confirm",
  "pairing.status",
  "audit.read",
  "effects.read"
) -join ","

$tokenJson = & $py -m app.demo.vertical_demo_v1 issue-token --user-id $userId --caps $caps | ConvertFrom-Json
if (-not $tokenJson.ok) { throw "token issue failed" }
$bearer = $tokenJson.access_token
$authHeader = @{ Authorization = "Bearer $bearer" }
$emitHeaders = @{ "X-Device-Token" = $null; Authorization = "Bearer $bearer" }

# Device hello
$hello = Invoke-Json POST "$base/api/v1/devices/hello" @{ device_uid = $deviceUid } @{}
if ($hello.status -ne 200) { throw "device hello failed: $($hello.raw)" }

# Pairing hello -> claim -> confirm
$deviceToken = $env:HUBEX_DEVICE_TOKEN
if (-not $deviceToken) {
  $pairHello = Invoke-Json POST "$base/api/v1/devices/pairing/hello" @{ device_uid = $deviceUid } @{}
  if ($pairHello.status -ne 200) { throw "pairing hello failed: $($pairHello.raw)" }
  if (-not $pairHello.data.pairing_code) {
    throw "pairing code missing; set HUBEX_DEVICE_TOKEN if device already claimed"
  }
  $pairCode = $pairHello.data.pairing_code

  $claim = Invoke-Json POST "$base/api/v1/devices/pairing/claim" @{ device_uid = $deviceUid; pairing_code = $pairCode } $authHeader
  if ($claim.status -ne 200) { throw "pairing claim failed: $($claim.raw)" }

  $confirm = Invoke-Json POST "$base/api/v1/devices/pairing/confirm" @{ device_uid = $deviceUid; pairing_code = $pairCode } $authHeader
  if ($confirm.status -ne 200) { throw "pairing confirm failed: $($confirm.raw)" }
  $deviceToken = $confirm.data.device_token
}

# Ensure execution definition
$def = Invoke-Json POST "$base/api/v1/executions/definitions" @{ key = $definitionKey; name = "Demo v1"; version = "v1"; enabled = $true } $authHeader
if ($def.status -ne 200 -and $def.status -ne 409) { throw "definition create failed: $($def.raw)" }

$correlation = [Guid]::NewGuid().ToString("N")
Write-Host "CORRELATION_ID=$correlation"

# Emit signal
$emitHeaders["X-Device-Token"] = $deviceToken
$emit = Invoke-Json POST "$base/api/v1/events/emit" @{ type = "signal.demo_v1"; payload = @{ device_uid = $deviceUid; correlation_id = $correlation }; trace_id = $correlation } $emitHeaders
if ($emit.status -ne 200) { throw "event emit failed: $($emit.raw)" }

# Bridge signal -> execution run
$bridge = & $py -m app.demo.vertical_demo_v1 bridge --device-uid $deviceUid --trace-id $correlation --definition-key $definitionKey | ConvertFrom-Json
if (-not $bridge.ok) { throw "bridge failed" }
Write-Host "RUN_ID=$($bridge.run_id)"

# Run worker once
$env:HUBEX_BASE_URL = $base
$env:HUBEX_TOKEN = $bearer
$env:WORKER_ID = $workerId
$env:LEASE_SECONDS = $leaseSeconds
$env:HEARTBEAT_EVERY = $heartbeatEvery
$env:POLL_DELAY = $pollDelay
$env:RUN_ONCE = "1"
$env:DEFINITION_KEY = $definitionKey

$worker = Start-Process -FilePath $py -ArgumentList @("scripts/execution_worker_service.py","--max-runs","1","--definition-key",$definitionKey) -NoNewWindow -Wait -PassThru
if ($worker.ExitCode -ne 0) { throw "worker failed exit=$($worker.ExitCode)" }

# Poll for completed run
$found = $false
1..20 | ForEach-Object {
  $runs = Invoke-Json GET "$base/api/v1/executions/runs?definition_key=$definitionKey&status=completed&limit=50" $null $authHeader
  if ($runs.status -eq 200) {
    foreach ($item in $runs.data.items) {
      if ($item.input_json.correlation_id -eq $correlation) { $found = $true }
    }
  }
  if ($found) { return }
  Start-Sleep -Seconds 1
}
if (-not $found) { throw "completed run not found" }

# Ensure variable definition + set value
$varKey = "demo.v1.flag"
$defBody = @{ key = $varKey; scope = "device"; value_type = "bool"; default_value = $false; description = "demo flag"; unit = $null; min_value = $null; max_value = $null; enum_values = $null; regex = $null; is_secret = $false; is_readonly = $false; user_writable = $true; device_writable = $true; allow_device_override = $true }
$varDef = Invoke-Json POST "$base/api/v1/variables/definitions" $defBody $authHeader
if ($varDef.status -ne 200 -and $varDef.status -ne 409) { throw "variable definition failed: $($varDef.raw)" }

$valBody = @{ key = $varKey; scope = "device"; device_uid = $deviceUid; value = $true }
$val = Invoke-Json PUT "$base/api/v1/variables/value" $valBody $authHeader
if ($val.status -ne 200) { throw "variable set failed: $($val.raw)" }

# Device snapshot + ack
$snap = Invoke-Json GET "$base/api/v1/variables/snapshot?deviceUid=$deviceUid" $null @{ "X-Device-Token" = $deviceToken }
if ($snap.status -ne 200) { throw "snapshot failed: $($snap.raw)" }
$effectiveRev = $snap.data.effective_rev
$results = @(@{ key = $varKey; status = "OK" })
$ackBody = @{ effective_rev = $effectiveRev; results = $results }
$ack = Invoke-Json POST "$base/api/v1/variables/ack" $ackBody @{ "X-Device-Token" = $deviceToken }
if ($ack.status -ne 200) { throw "ack failed: $($ack.raw)" }

# Emit trace events for worker + ack
$emitWorker = Invoke-Json POST "$base/api/v1/events/emit" @{ type = "demo_v1.worker_done"; payload = @{ correlation_id = $correlation }; trace_id = $correlation } $emitHeaders
$emitAck = Invoke-Json POST "$base/api/v1/events/emit" @{ type = "demo_v1.ack"; payload = @{ correlation_id = $correlation; effective_rev = $effectiveRev }; trace_id = $correlation } $emitHeaders

Write-Host "OK demo complete"
Write-Host "Trace Hub: $base/#/trace-hub (stream=tenant.system, trace_id=$correlation)"
Write-Host "Events stream: tenant.system"
Write-Host "Correlation ID: $correlation"
