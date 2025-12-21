$ErrorActionPreference = "Stop"

$Base = $env:HUBEX_BASE
if (-not $Base) { $Base = "http://127.0.0.1:8000" }
$Email = $env:HUBEX_EMAIL
if (-not $Email) { $Email = "dev@example.com" }
$Password = $env:HUBEX_PASSWORD
if (-not $Password) { $Password = "devdevdev" }

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

function Extract-Token {
    param([string]$Body)
    $obj = Parse-Json $Body "auth response"
    if ($obj.access_token) { return $obj.access_token }
    if ($obj.token) { return $obj.token }
    return $null
}

$payload = @{ email = $Email; password = $Password } | ConvertTo-Json -Compress

Write-Host "Login..."
$resp = Invoke-Api "POST" "$Base/api/v1/auth/login" $payload @{ "Content-Type" = "application/json" }
if ($resp.Status -ne 200) {
    Write-Host "Register..."
    $reg = Invoke-Api "POST" "$Base/api/v1/auth/register" $payload @{ "Content-Type" = "application/json" }
    if ($reg.Status -ne 200) { Fail "register" $reg }
    $resp = Invoke-Api "POST" "$Base/api/v1/auth/login" $payload @{ "Content-Type" = "application/json" }
    if ($resp.Status -ne 200) { Fail "login" $resp }
}

$token = Extract-Token $resp.Body
if (-not $token) { Fail "login token missing" $resp }

Write-Host "OK: token acquired"
Write-Host "HUBEX_TOKEN=$token"
Write-Host "PowerShell:  $env:HUBEX_TOKEN=\"$token\""
Write-Host "bash:        export HUBEX_TOKEN=\"$token\""
