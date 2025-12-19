$ErrorActionPreference = "Stop"

param(
    [int]$Days = $env:TELEMETRY_RETENTION_DAYS
)

if (-not $Days) {
    $Days = 30
}

function Fail {
    param([string]$Message)
    Write-Host "FAIL: $Message"
    exit 1
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

$dbUrl = Get-DatabaseUrl
if (-not $dbUrl) {
    Fail "DATABASE_URL not set and .env missing"
}
if ($dbUrl.StartsWith("postgresql+asyncpg")) {
    $dbUrl = $dbUrl -replace "^postgresql\\+asyncpg", "postgresql"
}

$env:CLEANUP_DB_URL = $dbUrl
$env:CLEANUP_DAYS = "$Days"

$py = @'
import os
import psycopg2

db = os.environ["CLEANUP_DB_URL"]
days = int(os.environ["CLEANUP_DAYS"])

conn = psycopg2.connect(db)
cur = conn.cursor()
cur.execute(
    "delete from device_telemetry where received_at < now() - interval %s",
    (f"{days} days",),
)
deleted = cur.rowcount
conn.commit()
print(f"deleted:{deleted}")
'@

$out = $py | python -
if ($LASTEXITCODE -ne 0) {
    Fail "cleanup failed: $out"
}

Write-Host "OK: $out"
