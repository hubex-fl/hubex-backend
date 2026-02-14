# Phase 5 Runbook (Execution Worker v1 + UI Dev)

This runbook is the canonical “make it run” guide for local dev and demos. It uses only existing Phase‑4 APIs.

## Backend (dev)
PowerShell:
```
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
.\scripts\dev-backend.ps1
```

Default API base: `http://127.0.0.1:8000`

## UI (dev)
PowerShell:
```
cd frontend
npm install
$env:VITE_API_TARGET="http://127.0.0.1:8000"
$env:VITE_DEV_HOST="0.0.0.0"     # use 127.0.0.1 for local-only
$env:VITE_DEV_PORT="5173"
npm run dev
```
Open: `http://127.0.0.1:5173`

UI smoke (build artifact):
```
.\scripts\smoke-ui.ps1
```

Notes:
- Vite proxies `/api` → `VITE_API_TARGET`, so UI calls `/api/v1/...` without CORS in dev.
- The UI stores the JWT in LocalStorage key `hubex_access_token`.

## Worker (local)
Required env:
- `HUBEX_TOKEN`
- `WORKER_ID`

Optional env:
- `HUBEX_BASE_URL` (default `http://127.0.0.1:8000`)
- `LEASE_SECONDS` (default `60`)
- `HEARTBEAT_EVERY` (default `20`, 1..LEASE_SECONDS)
- `POLL_DELAY` (default `2.0`)
- `DEFINITION_KEY` (optional; omit to use subscriptions)
- `MAX_RUNS` (optional)
- `RUN_ONCE` (if set, max_runs=1)

Run once:
```
$env:HUBEX_BASE_URL="http://127.0.0.1:8000"
$env:WORKER_ID="worker-1"
$env:HUBEX_TOKEN="..."
$env:RUN_ONCE="1"
.\.venv\Scripts\python.exe scripts\execution_worker_service.py
```

Exit codes:
- `0` normal completion
- `1` runtime error
- `2` misconfiguration (auth/caps/required params/subscriptions)
- `130` keyboard interrupt

## Worker (docker)
```
docker build -t hubex-worker-v1 -f Dockerfile.worker_v1 .
docker run --rm `
  -e HUBEX_BASE_URL=http://host.docker.internal:8000 `
  -e HUBEX_TOKEN=... `
  -e WORKER_ID=worker-1 `
  -e RUN_ONCE=1 `
  hubex-worker-v1
```

## End-to-end demo (backend + worker + UI)
1) Start backend (see above).
2) Start UI (see above).
3) Run demo helper:
```
.\scripts\demo-phase5.ps1
```

## Troubleshooting
- **UI not reachable from LAN**: set `VITE_DEV_HOST=0.0.0.0` and confirm firewall rules.
- **Worker misconfig (exit 2)**: ensure `HUBEX_TOKEN` includes `executions.write` and, if using subscriptions, that the worker is subscribed.
- **CORS issues**: use the Vite proxy (`/api` → `VITE_API_TARGET`) and keep frontend requests relative (`/api/v1/...`).
