$ErrorActionPreference = "Stop"

$Base = $env:HUBEX_BASE
if (-not $Base) { $Base = "http://127.0.0.1:8000" }
$Token = $env:HUBEX_TOKEN
if (-not $Token) { Write-Host "FAIL: HUBEX_TOKEN missing"; exit 1 }
$Scope = $env:HUBEX_VAR_SCOPE

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

$url = "$Base/api/v1/variables/defs"
if ($Scope) { $url = "$url?scope=$Scope" }
$resp = Invoke-Api "GET" $url $null @{ "Authorization" = "Bearer $Token" }
if ($resp.Status -ne 200) { Fail "list definitions" $resp }

Write-Host "OK"
$defs = @()
try { $defs = $resp.Body | ConvertFrom-Json } catch {}
if ($defs -and $defs.Count -gt 0) {
    $defs | ForEach-Object { Write-Host "$($_.key) $($_.scope)" }
} else {
    Write-Host $resp.Body
}
