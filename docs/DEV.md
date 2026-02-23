# DEV

Single entry point for local development.

## Quickstart
PowerShell:
```
.\.venv\Scripts\Activate.ps1
python -m pip install -U -r requirements.txt -r requirements-dev.txt
```

bash:
```
source .venv/bin/activate
python -m pip install -U -r requirements.txt -r requirements-dev.txt
```

Note: `requirements.txt` uses `uvicorn[standard]` so local dev includes WebSocket support.
`scripts/dev-backend.ps1` binds to `0.0.0.0` by default and avoids double-start via `.run/uvicorn.pid` (override with `HUBEX_HOST`/`HUBEX_PORT`).
Startup verification polls for a listening port because `uvicorn --reload` starts a reloader process first.
Detached start and logs:
- Start: `.\scripts\dev-backend.ps1`
- Start + follow logs: `.\scripts\dev-backend.ps1 -Follow`
- Follow only: `.\scripts\dev-backend.ps1 -Action follow`
- Follow stderr only: `.\scripts\dev-backend.ps1 -Action follow -StderrOnly`
- Status: `.\scripts\dev-backend.ps1 -Action status`
- Stop: `.\scripts\dev-backend.ps1 -Action stop`
UI runs on http://127.0.0.1:5173 (Vite dev server). Backend API runs on http://127.0.0.1:8000.

## Claim a device (UI)
Open the Devices page, enter the pairing code in "Pairing code (claim)", and click Claim.
On success the devices list refreshes and the claimed device is visible for detail view.

## Phase-1 gates (local)
PowerShell:
```
.\scripts\run-phase1-gates.ps1
```

bash:
```
./scripts/run-phase1-gates.sh
```

Prereqs:
- .venv activated or repo .venv present
- dependencies installed (requirements.txt + requirements-dev.txt)

## Local gates (all)
PowerShell:
```
.\scripts\run-gates.ps1
```

bash:
```
./scripts/run-gates.sh
```
Note: Do not run `pytest` directly; use the gate runner to ensure the repo `.venv` is used.

## Environment variables
See `docs/ENV.md`.

## Local caps (dev)
If the UI shows "Capabilities unavailable", set caps on your dev user in DB and re-login to mint a new JWT.
Dev/test user caps include `devices.token.reissue` (see `app/scripts/seed_dev_user_caps.py`).
If the backend runs in Docker Desktop container `hubex-backend`, seed via:
`docker exec -it hubex-backend python -m app.scripts.seed_dev_user_caps`
Compose `exec` only works when the backend was started via that compose project.
Device detail shows the Recovery section when `devices.token.reissue` is present in the JWT.
```
UPDATE users
SET caps = '["devices.read","events.read","effects.read","vars.read"]'::jsonb
WHERE email = 'dev@example.com';
```

## Smoke scripts
See `docs/SMOKE.md`.

## CI gates
See `.github/workflows/phase1_gates.yml`.

## Release
See `docs/RELEASE.md`.
