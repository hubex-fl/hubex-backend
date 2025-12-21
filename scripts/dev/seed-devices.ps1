$ErrorActionPreference = "Stop"

$Base = $env:HUBEX_BASE
if (-not $Base) { $Base = "http://127.0.0.1:8000" }
$Token = $env:HUBEX_TOKEN
$Count = 3
if ($env:HUBEX_DEVICE_COUNT) { $Count = [int]$env:HUBEX_DEVICE_COUNT }
$Prefix = $env:HUBEX_DEVICE_PREFIX
if (-not $Prefix) { $Prefix = "dev-seed" }
$ClaimOne = $env:HUBEX_CLAIM_ONE -eq "1"

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

$uids = @()
$ids = @()
$claimInfo = $null

for ($i = 1; $i -le $Count; $i++) {
    $uid = "$Prefix-$((Get-Date).ToString('yyyyMMddHHmmss'))-$i"
    $helloBody = @{ device_uid = $uid; firmware_version = "1.0.$i"; capabilities = @{ wifi = $true; sensors = @{ temp = $true } } } | ConvertTo-Json -Compress
    $resp = Invoke-Api "POST" "$Base/api/v1/devices/hello" $helloBody @{ "Content-Type" = "application/json" }
    if ($resp.Status -ne 200) { Fail "devices/hello" $resp }
    $obj = Parse-Json $resp.Body "devices/hello"
    $uids += $uid
    $ids += $obj.device_id

    if ($ClaimOne -and -not $claimInfo) {
        if (-not $Token) { Fail "HUBEX_TOKEN required to claim" $resp }
        $pairBody = @{ device_uid = $uid } | ConvertTo-Json -Compress
        $pair = Invoke-Api "POST" "$Base/api/v1/pairing/start" $pairBody @{ "Authorization" = "Bearer $Token"; "Content-Type" = "application/json" }
        if ($pair.Status -ne 200 -and $pair.Status -ne 409) { Fail "pairing start" $pair }
        $pairObj = Parse-Json $pair.Body "pairing start"
        $code = $pairObj.pairing_code
        if (-not $code) { Fail "pairing start missing pairing_code" $pair }
        $confirmBody = @{ device_uid = $uid; pairing_code = $code } | ConvertTo-Json -Compress
        $confirm = Invoke-Api "POST" "$Base/api/v1/pairing/confirm" $confirmBody @{ "Content-Type" = "application/json" }
        if ($confirm.Status -ne 200) { Fail "pairing confirm" $confirm }
        $confirmObj = Parse-Json $confirm.Body "pairing confirm"
        $claimInfo = @{ device_uid = $uid; device_id = $confirmObj.device_id; device_token = $confirmObj.device_token }
    }
}

Write-Host "OK: provisioned $Count device(s)"
Write-Host "DEVICE_UIDS=$($uids -join ',')"
Write-Host "DEVICE_IDS=$($ids -join ',')"
if ($claimInfo) {
    Write-Host "CLAIMED_DEVICE_UID=$($claimInfo.device_uid)"
    Write-Host "CLAIMED_DEVICE_ID=$($claimInfo.device_id)"
    Write-Host "CLAIMED_DEVICE_TOKEN=$($claimInfo.device_token)"
}
