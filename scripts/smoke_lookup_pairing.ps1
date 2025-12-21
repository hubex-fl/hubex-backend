$ErrorActionPreference = "Stop"

$Base = "http://127.0.0.1:8000"
$Email = "dev@example.com"
$Password = "devdevdev"
$KnownUid = "debug-test-1"

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

Write-Host "Login..."
$loginBody = @{ email = $Email; password = $Password } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$Base/api/v1/auth/login" $loginBody @{ "Content-Type" = "application/json" }
if ($resp.Status -ne 200) { Fail "login" $resp }
$token = (Parse-Json $resp.Body "login").access_token
if (-not $token) { Fail "login token missing" $resp }

Write-Host "Lookup without token (expect 401)..."
$resp = Invoke-Api "GET" "$Base/api/v1/devices/lookup/$KnownUid" $null @{}
if ($resp.Status -ne 401) { Fail "lookup without token" $resp }

Write-Host "Lookup known UID..."
$resp = Invoke-Api "GET" "$Base/api/v1/devices/lookup/$KnownUid" $null @{ "Authorization" = "Bearer $token" }
if ($resp.Status -ne 200) { Fail "lookup known UID" $resp }

Write-Host "Lookup unknown UID..."
$resp = Invoke-Api "GET" "$Base/api/v1/devices/lookup/___does_not_exist___" $null @{ "Authorization" = "Bearer $token" }
if ($resp.Status -ne 404) { Fail "lookup unknown UID" $resp }
$detail = (Parse-Json $resp.Body "lookup unknown UID").detail
if ($detail.code -ne "DEVICE_UNKNOWN_UID") { Fail "lookup unknown UID detail code" $resp }
if ($detail.message -ne "Unknown device UID") { Fail "lookup unknown UID detail message" $resp }

Write-Host "Pairing start..."
$pairBody = @{ device_uid = $KnownUid } | ConvertTo-Json -Compress
$resp = Invoke-Api "POST" "$Base/api/v1/pairing/start" $pairBody @{ "Authorization" = "Bearer $token"; "Content-Type" = "application/json" }
if ($resp.Status -eq 200) {
    $pairCode = (Parse-Json $resp.Body "pairing start").pairing_code
    if (-not $pairCode) { Fail "pairing start missing pairing_code" $resp }
} elseif ($resp.Status -eq 409) {
    $detail = (Parse-Json $resp.Body "pairing start").detail
    if ($detail.code -ne "PAIRING_ALREADY_ACTIVE") { Fail "pairing start conflict code" $resp }
} else {
    Fail "pairing start" $resp
}

Write-Host "OK"
