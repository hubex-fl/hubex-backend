# Hubex Backend

Developer entry point: `docs/DEV.md`

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

## Run SPA (Vue + Vite)

```powershell
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000`, so the UI can call
`/api/v1/...` without CORS in dev.

## Auth Overview

- User auth uses `Authorization: Bearer <JWT>`.
- Device auth uses `X-Device-Token: <token>` (separate from user JWTs).

## Smoke Flow (Windows PowerShell + curl.exe)

```powershell
$pw = "Test1234!"
$email = "codex+$((Get-Date).ToString('yyyyMMddHHmmss'))@example.com"

$registerBody = @{ email = $email; password = $pw } | ConvertTo-Json -Compress
$null = $registerBody | curl.exe -sS -X POST http://localhost:8000/api/v1/auth/register `
  -H "Content-Type: application/json" `
  --data-binary '@-'

$login = $registerBody | curl.exe -sS -X POST http://localhost:8000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  --data-binary '@-'
$token = ($login | ConvertFrom-Json).access_token

diff --git a/README.md b/README.md
index c521793..97ab410 100644
--- a/README.md
+++ b/README.md
@@ -179,6 +179,13 @@ curl.exe -sS -X GET "http://localhost:8000/api/v1/devices/$deviceId/tasks?limit=1
   -H "Authorization: Bearer $token"

$deviceUid = "device-20251219-$((Get-Date).ToString('yyyyMMddHHmmss'))"

$helloBody = @{ device_uid = $deviceUid; firmware_version = "1.0.0"; capabilities = @{ wifi = $true } } | ConvertTo-Json -Compress
$helloBody | curl.exe -sS -X POST http://localhost:8000/api/v1/devices/hello `
  -H "Content-Type: application/json" `
  --data-binary '@-'

$pairingBody = @{ device_uid = $deviceUid } | ConvertTo-Json -Compress
$pairing = $pairingBody | curl.exe -sS -X POST http://localhost:8000/api/v1/pairing/start `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  --data-binary '@-'
$pairingObj = $pairing | ConvertFrom-Json

$confirmBody = @{ device_uid = $deviceUid; pairing_code = $pairingObj.pairing_code } | ConvertTo-Json -Compress
$confirm = $confirmBody | curl.exe -sS -X POST http://localhost:8000/api/v1/pairing/confirm `
  -H "Content-Type: application/json" `
  --data-binary '@-'
$confirmObj = $confirm | ConvertFrom-Json
$deviceToken = $confirmObj.device_token
$deviceId = $confirmObj.device_id

curl.exe -s -X GET http://localhost:8000/api/v1/devices/whoami `
  -H "X-Device-Token: $deviceToken"

curl.exe -s -X GET http://localhost:8000/api/v1/devices `
  -H "Authorization: Bearer $token"

curl.exe -s -X GET http://localhost:8000/api/v1/devices/$deviceId `
  -H "Authorization: Bearer $token"
```

## Smoke Flow (Negative Checks)

The script `scripts/smoke.ps1` now also runs these checks and exits non-zero on failure:

- pairing start without JWT -> 401
- pairing confirm wrong code -> 404
- pairing confirm expired -> 410 (requires DATABASE_URL or .env + psycopg2)
- pairing confirm replay -> 409
- device whoami without device token -> 401
- devices list for other user -> device not present
- device detail for other user -> 403/404

If the expiry check cannot update the DB, the script prints a SKIP note and continues.

## Telemetry (Device Token)

Limits (MVP):

- Max payload size: 16 KB (JSON bytes)
- Max payload key length: 64 chars
- Rate limit: 60 requests/min per device, per process (in-memory, not shared across workers)

Exceeding size returns 413, rate limit returns 429.

POST telemetry:

```powershell
$telemetryBody = @{ event_type = "boot"; payload = @{ temp_c = 21; ok = $true } } | ConvertTo-Json -Compress
$telemetry = $telemetryBody | curl.exe -sS -X POST http://localhost:8000/api/v1/telemetry `
  -H "Content-Type: application/json" `
  -H "X-Device-Token: $deviceToken" `
  --data-binary '@-'
```

GET recent telemetry:

```powershell
curl.exe -sS -X GET "http://localhost:8000/api/v1/telemetry/recent?limit=5" `
  -H "X-Device-Token: $deviceToken"
```

## Tasks (Client + Owner)

Limits (MVP):

- Max JSON size: 16 KB (payload/result/capabilities/meta)
- In-memory rate limits are not applied to tasks.
- Idempotency is enforced per client_id + idempotency_key (partial unique in Postgres).
  Reusing the same idempotency_key returns the existing task (200).
- Poll returns a `lease_token` and clamps `lease_seconds` to 5..600; expired leases re-queue tasks.

Client context heartbeat (device token):

```powershell
$contextBody = @{ context_key = "default"; capabilities = @{ tasks = @("io.write", "config.apply") }; meta = @{ version = "1.0" } } | ConvertTo-Json -Compress
$context = $contextBody | curl.exe -sS -X POST http://localhost:8000/api/v1/tasks/context/heartbeat `
  -H "Content-Type: application/json" `
  -H "X-Device-Token: $deviceToken" `
  --data-binary '@-'
```

Owner enqueue task:

```powershell
$taskBody = @{ type = "config.apply"; payload = @{ mode = "safe" }; execution_context_key = "default" } | ConvertTo-Json -Compress
$task = $taskBody | curl.exe -sS -X POST http://localhost:8000/api/v1/devices/$deviceId/tasks `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $token" `
  --data-binary '@-'
```

Client poll + complete (device token):

```powershell
curl.exe -sS -X POST "http://localhost:8000/api/v1/tasks/poll?limit=1&context_key=default" `
  -H "X-Device-Token: $deviceToken"

$completeBody = @{ status = "done"; result = @{ ok = $true } } | ConvertTo-Json -Compress
$complete = $completeBody | curl.exe -sS -X POST http://localhost:8000/api/v1/tasks/<task_id>/complete `
  -H "Content-Type: application/json" `
  -H "X-Device-Token: $deviceToken" `
  --data-binary '@-'
```

Owner list tasks:

```powershell
curl.exe -sS -X GET "http://localhost:8000/api/v1/devices/$deviceId/tasks?limit=10" `
  -H "Authorization: Bearer $token"
```

Owner cancel task:

```powershell
curl.exe -sS -X POST "http://localhost:8000/api/v1/devices/$deviceId/tasks/<task_id>/cancel" `
  -H "Authorization: Bearer $token"
```

## Telemetry (Owner Read)

```powershell
curl.exe -sS -X GET "http://localhost:8000/api/v1/devices/$deviceId/telemetry/recent?limit=5" `
  -H "Authorization: Bearer $token"
```

## Dev: Reset Device (optional)

To unclaim a device locally without psql:

```powershell
.\scripts\dev_reset_device.ps1 -DeviceUid "device-20251219-20251219025140"
```

The script reads `DATABASE_URL` or `HUBEX_DATABASE_URL` (env or `.env`) and clears `owner_user_id`, `is_claimed`,
device tokens, and pairing sessions for the given device UID. Dev only.

## Dev: Telemetry Cleanup (optional)

Deletes telemetry older than N days (default 30):

```powershell
.\scripts\telemetry_cleanup.ps1 -Days 30
```

Uses `DATABASE_URL` or `HUBEX_DATABASE_URL` (env or `.env`) and `psycopg2`.

## Frontend UI Smoke

See `frontend/SMOKE_UI.md` for the minimal UI validation checklist.
