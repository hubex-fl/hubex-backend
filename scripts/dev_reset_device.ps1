$ErrorActionPreference = "Stop"

param(
    [Parameter(Mandatory = $true)]
    [string]$DeviceUid
)

function Fail {
    param([string]$Message)
    Write-Host "FAIL: $Message"
    exit 1
}

function Get-DatabaseUrl {
    if ($env:DATABASE_URL) {
        return $env:DATABASE_URL
    }
    if (Test-Path ".env") {
        $line = Select-String -Path ".env" -Pattern "^DATABASE_URL=" -SimpleMatch | Select-Object -First 1
        if ($line) {
            return $line.Line.Substring("DATABASE_URL=".Length)
        }
    }
    return $null
}

$dbUrl = Get-DatabaseUrl
if (-not $dbUrl) {
    Fail "DATABASE_URL not set and .env missing"
}
if ($dbUrl.StartsWith("postgresql+asyncpg")) {
    $dbUrl = $dbUrl -replace "^postgresql\\+asyncpg", "postgresql"
}

$env:RESET_DB_URL = $dbUrl
$env:RESET_DEVICE_UID = $DeviceUid

$py = @'
import os
import sys
import psycopg2

db = os.environ["RESET_DB_URL"]
uid = os.environ["RESET_DEVICE_UID"]

conn = psycopg2.connect(db)
cur = conn.cursor()
cur.execute("select id from devices where device_uid=%s", (uid,))
row = cur.fetchone()
if not row:
    print("not_found")
    sys.exit(2)
device_id = row[0]
cur.execute("update devices set owner_user_id=NULL, is_claimed=false where id=%s", (device_id,))
cur.execute("delete from device_tokens where device_id=%s", (device_id,))
cur.execute("delete from pairing_sessions where device_uid=%s", (uid,))
conn.commit()
print("reset_ok")
sys.exit(0)
'@

$out = $py | python -
if ($LASTEXITCODE -ne 0) {
    Fail "reset failed: $out"
}

Write-Host "OK: reset device $DeviceUid"
