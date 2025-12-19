# Hubex Backend

## Setup (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run Postgres (Docker)

```powershell
docker compose up -d
```

## Migrate DB

```powershell
.\.venv\Scripts\alembic.exe upgrade head
```

## Run API

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

If the venv is activated:

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

## Auth Overview

- User auth uses `Authorization: Bearer <JWT>`.
- Device auth uses `X-Device-Token: <token>` (separate from user JWTs).

## Smoke Flow (Windows PowerShell + curl.exe)

```powershell
$pw = "Test1234!"
$email = "codex+$((Get-Date).ToString('yyyyMMddHHmmss'))@example.com"

$null = curl.exe -s -X POST http://localhost:8000/api/v1/auth/register `
  -H "Content-Type: application/json" `
  -d "{\"email\":\"$email\",\"password\":\"$pw\"}"

$login = curl.exe -s -X POST http://localhost:8000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  -d "{\"email\":\"$email\",\"password\":\"$pw\"}"
$token = ($login | ConvertFrom-Json).access_token

curl.exe -s -X GET http://localhost:8000/api/v1/users/me `
  -H "Authorization: Bearer $token"

$pairing = curl.exe -s -X POST http://localhost:8000/api/v1/pairing/start `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d "{\"device_uid\":\"device-1234\"}"
$pairingObj = $pairing | ConvertFrom-Json

$confirm = curl.exe -s -X POST http://localhost:8000/api/v1/pairing/confirm `
  -H "Content-Type: application/json" `
  -d "{\"device_uid\":\"device-1234\",\"pairing_code\":\"$($pairingObj.pairing_code)\"}"
$deviceToken = ($confirm | ConvertFrom-Json).device_token

curl.exe -s -X GET http://localhost:8000/api/v1/devices/whoami `
  -H "X-Device-Token: $deviceToken"
```
