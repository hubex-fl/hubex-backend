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
