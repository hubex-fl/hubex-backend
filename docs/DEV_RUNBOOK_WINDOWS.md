# HUBEX Windows Dev Runbook (Backend + UI)

## A) Start Docker services (db + redis)

```powershell
Set-Location C:\Users\lange\Documents\vs_code\projects\backend\hubex\v0.1\hubex-backend
docker compose up -d
docker compose ps
```

## B) Set DB URL + wait for DB

```powershell
$env:HUBEX_DATABASE_URL="postgresql+asyncpg://hubex:hubex@127.0.0.1:5432/hubex"
.\.venv\Scripts\python.exe -m app.scripts.wait_for_db --timeout 60 --interval 1
```

## C) Seed dev user caps

```powershell
.\.venv\Scripts\python.exe -m app.scripts.seed_dev_user_caps
```

After seeding, logout/login in the UI so the JWT refreshes with new caps.

## D) Start backend (uvicorn)

```powershell
.\scripts\dev-backend.ps1 -Follow
```

Troubleshooting:
- If you see `connect failed 127.0.0.1:5432`, ensure `docker compose up -d` is running and port 5432 is not blocked.
- If backend is already running, stop the old PID or set `HUBEX_PORT` before starting.

## E) Start frontend (Vite)

```powershell
Set-Location C:\Users\lange\Documents\vs_code\projects\backend\hubex\v0.1\hubex-backend\frontend
npm install
npm run dev
```

UI URL: http://localhost:5173

## F) Tests

```powershell
Set-Location C:\Users\lange\Documents\vs_code\projects\backend\hubex\v0.1\hubex-backend
.\.venv\Scripts\python.exe -m pytest -q
.\scripts\run-phase1-gates.ps1
.\scripts\run-gates.ps1
npm -C frontend test
```